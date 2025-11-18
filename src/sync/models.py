from django.db import models


class SyncResult(models.Model):
    executed_at = models.DateTimeField(
        auto_now_add=True, db_index=True, verbose_name="Дата и время синхронизации"
    )
    added_count = models.PositiveIntegerField(
        default=0, verbose_name="Количество добавленных"
    )
    updated_count = models.PositiveIntegerField(
        default=0, verbose_name="Количество обновленных"
    )

    class Meta:
        verbose_name = "Результат синхронизации"
        verbose_name_plural = "Результаты синхронизации"
        ordering = ["-executed_at"]
