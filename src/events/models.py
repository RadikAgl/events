from uuid import uuid4

from django.db import models


class Venue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Название")
    external_id = models.UUIDField(
        unique=True, db_index=True, verbose_name="ID в провайдере"
    )

    class Meta:
        verbose_name = "Площадка"
        verbose_name_plural = "Площадки"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name}"


class EventStatus(models.TextChoices):
    OPEN = "open", "Открыто"
    CLOSED = "closed", "Закрыто"


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    external_id = models.UUIDField(
        unique=True, db_index=True, verbose_name="ID в провайдере"
    )
    name = models.CharField(max_length=255, verbose_name="Название")
    event_date = models.DateTimeField(db_index=True, verbose_name="Дата проведения")
    changed_at = models.DateTimeField(
        db_index=True, verbose_name="Дата изменения у провайдера"
    )
    status = models.CharField(
        max_length=6,
        choices=EventStatus.choices,
        default=EventStatus.OPEN,
        verbose_name="Статус",
    )
    venue = models.ForeignKey(
        Venue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
        verbose_name="Площадка",
    )

    class Meta:
        verbose_name = "Мероприятие"
        verbose_name_plural = "Мероприятия"
        ordering = ["-event_date", "name"]

    def __str__(self) -> str:
        return f"{self.name}"


class EventRegistration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="registrations",
        verbose_name="Событие",
    )
    full_name = models.CharField(max_length=128, verbose_name="Имя регистрирующегося")
    email = models.EmailField(verbose_name="Электронная почта")
    confirmation_code = models.CharField(
        max_length=12, verbose_name="Код подтверждения"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Время отправки подтверждающего кода"
    )

    class Meta:
        verbose_name = "Регистрация"
        verbose_name_plural = "Регистрации"
        unique_together = [("event", "email")]
        indexes = [
            models.Index(fields=["event", "email"]),
        ]

    def __str__(self):
        return f"{self.email} -> {self.event}"


class MessageStatus(models.TextChoices):
    PENDING = "pending", "Ожидает отправки"
    PROCESSING = "processing", "В обработке"
    SENT = "sent", "Отправлено"
    FAILED = "failed", "Ошибка"


class Outbox(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    topic = models.CharField(max_length=200, db_index=True, verbose_name="Топик")
    payload = models.JSONField(verbose_name="Тело сообщения (payload)")
    state = models.CharField(
        max_length=16,
        choices=MessageStatus.choices,
        default=MessageStatus.PENDING,
        db_index=True,
        verbose_name="Статус доставки",
    )
    attempts = models.PositiveIntegerField(default=0, verbose_name="Количество попыток")
    error = models.TextField(blank=True, default="", verbose_name="Последняя ошибка")

    class Meta:
        verbose_name = "Outbox сообщение"
        verbose_name_plural = "Outbox сообщения"
