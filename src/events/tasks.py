from celery import shared_task
from django.db import transaction
from django.db.models import F

from src.events.models import MessageStatus, Outbox
from src.events.utils.notifications import send_confirmation_email

BATCH_SIZE = 100
MAX_ATTEMPTS = 5


def claim_messages(batch_size: int = BATCH_SIZE):
    with transaction.atomic():
        qs = (
            Outbox.objects.filter(state=MessageStatus.PENDING)
            .order_by("id")
            .select_for_update(skip_locked=True)
        )
        ids = list(qs.values_list("id", flat=True)[:batch_size])
        if not ids:
            return []
        Outbox.objects.filter(id__in=ids).update(
            state=MessageStatus.PROCESSING,
            attempts=F("attempts") + 1,
        )
    return list(Outbox.objects.filter(id__in=ids))


@shared_task()
def send_messages(batch_size: int = BATCH_SIZE) -> int:
    msgs = claim_messages(batch_size)
    if not msgs:
        return 0

    processed = 0
    for msg in msgs:
        try:
            ok = send_confirmation_email(
                msg.id,
                msg.payload["email"],
                msg.payload["full_name"],
                msg.payload["confirmation_code"],
            )
            if not ok:
                raise Exception("Сервис недоступен. Не удалось отправить сообщение")
        except Exception as e:
            if msg.attempts < MAX_ATTEMPTS:
                Outbox.objects.filter(id=msg.id).update(
                    state=MessageStatus.PENDING,
                    error=str(e)[:1000],
                )
            else:
                Outbox.objects.filter(id=msg.id).update(
                    state=MessageStatus.FAILED,
                    error=str(e)[:1000],
                )
        else:
            Outbox.objects.filter(id=msg.id).update(
                state=MessageStatus.SENT,
                error="",
            )
            processed += 1
    return processed
