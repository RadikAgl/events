from django.contrib import admin

from src.events.models import Event, EventRegistration, Venue


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "external_id",
        "name",
        "event_date",
        "changed_at",
        "venue",
        "status",
    )


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("id", "external_id", "name")


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ("id", "event", "full_name", "email", "confirmation_code")
