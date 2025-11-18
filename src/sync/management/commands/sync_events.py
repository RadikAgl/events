import random
import time
from datetime import datetime
from uuid import UUID

import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max

from src.core.settings import JWT_TOKEN, PROVIDER_URL
from src.events.models import Event, EventStatus, Venue
from src.sync.models import SyncResult


def iso_to_dt(value: str) -> datetime | None:
    if not value:
        return None
    s = value.strip()
    return datetime.fromisoformat(s)


def backoff(attempt: int, backoff_cap) -> float:
    return min(backoff_cap, (2 ** (attempt - 1)) + random.uniform(0, 0.5))


def parse_retry_after(v: str | None) -> int | None:
    if not v:
        return None
    try:
        return max(1, int(v))
    except ValueError:
        return None


def iter_provider_events(url: str):
    RETRIABLE_STATUS = {408, 429, 500, 502, 503, 504}
    MAX_ATTEMPTS = 6
    BACKOFF_CAP = 60

    session = requests.Session()
    headers = {
        "Authorization": f"Bearer {JWT_TOKEN}",
        "Content-Type": "application/json",
    }
    next_url = url

    while next_url:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                resp = session.get(next_url, headers=headers, timeout=(5, 30))
            except requests.RequestException:
                time.sleep(backoff(attempt, BACKOFF_CAP))
                continue

            status = resp.status_code

            if status == 429:
                ra = parse_retry_after(resp.headers.get("Retry-After"))
                time.sleep(ra if ra else backoff(attempt, BACKOFF_CAP))
                continue

            if status in RETRIABLE_STATUS:
                time.sleep(backoff(attempt, BACKOFF_CAP))
                continue

            if 400 <= status < 500:
                print(f"Пропускаем URL {next_url}: HTTP {status}.")
                next_url = None
                break

            try:
                resp.raise_for_status()
            except requests.HTTPError as e:
                print(f"Пропускаем URL {next_url}: {e}")
                next_url = None
                break

            break
        else:
            print(f"Пропускаем URL {next_url}: лимит повторных попыток исчерпан.")
            break

        data = resp.json()
        results = data.get("results")

        if results:
            for item in results:
                yield item
                next_url = data.get("next")
        else:
            next_url = None


def get_status(status: str, deadline: str) -> EventStatus:
    status = status.strip().lower()
    if status not in ("new", "published"):
        return EventStatus.CLOSED

    dl = iso_to_dt(deadline)
    if dl is None:
        return EventStatus.CLOSED

    now = datetime.now(dl.tzinfo)
    return EventStatus.OPEN if dl > now else EventStatus.CLOSED


class Command(BaseCommand):
    help = "Синхронизация мероприятий из events-provider"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all", action="store_true", help="Полная синхронизация всех мероприятий"
        )
        parser.add_argument(
            "--since",
            type=str,
            help="Синхронизация, начиная с указанной даты (YYYY-MM-DD). "
            "Если не указано, берется по последней дате изменения.",
        )

    def handle(self, *args, **options):
        do_full = options.get("all")
        since_arg = options.get("since")

        if do_full:
            url = PROVIDER_URL
            self.stdout.write(self.style.NOTICE("Режим: полная синхронизация"))
        else:
            if since_arg:
                changed_date = since_arg
            else:
                last_changed = Event.objects.aggregate(m=Max("changed_at"))
                changed_date = last_changed.date().isoformat() if last_changed else None

            if changed_date:
                url = f"{PROVIDER_URL}?changed_at={changed_date}"
                self.stdout.write(
                    self.style.NOTICE(f"Инкрементальная синхронизация с {changed_date}")
                )
            else:
                url = PROVIDER_URL
                self.stdout.write(
                    self.style.NOTICE("Первая синхронизация: загрузка всех мероприятий")
                )

        added, updated = 0, 0

        with transaction.atomic():
            for item in iter_provider_events(url):
                try:
                    raw_id = item.get("id")
                    if not raw_id:
                        raise ValueError("Нет id у записи провайдера")

                    external_event_id = UUID(str(raw_id))
                    changed_at = iso_to_dt(item.get("changed_at"))

                    place = item.get("place")
                    if place:
                        venue_name = place.get("name")
                        external_venue_id = UUID(str(place.get("id")))
                        venue, _ = Venue.objects.get_or_create(
                            name=venue_name, external_id=external_venue_id
                        )
                    else:
                        venue = None

                    event_defaults = {
                        "name": item.get("name", ""),
                        "event_date": iso_to_dt(item.get("event_time")),
                        "status": get_status(
                            item.get("status"), item.get("registration_deadline")
                        ),
                        "changed_at": changed_at,
                        "venue": venue,
                    }

                    event, created = Event.objects.get_or_create(
                        external_id=external_event_id, defaults=event_defaults
                    )

                    if created:
                        added += 1
                        continue

                    if changed_at and (
                        event.changed_at is None or changed_at > event.changed_at
                    ):
                        for field, value in event_defaults.items():
                            setattr(event, field, value)
                        event.save(update_fields=list(event_defaults.keys()))
                        updated += 1

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Ошибка по записи {item}: {e}"))

            SyncResult.objects.create(added_count=added, updated_count=updated)

        self.stdout.write(
            self.style.SUCCESS(f"Готово. Добавлено: {added}, обновлено: {updated}")
        )
