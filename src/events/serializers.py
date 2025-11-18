from rest_framework import serializers

from src.events.models import Event, EventRegistration, Venue


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ["name"]


class EventSerializer(serializers.ModelSerializer):
    venue = VenueSerializer()

    class Meta:
        model = Event
        fields = ["name", "event_date", "status", "venue"]


class EventRegistrationSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=128)
    email = serializers.EmailField()

    def validate(self, attrs):
        event = self.context.get("event")
        if event is None:
            raise
        serializers.ValidationError("Мероприятие не найдено")

        status = str(event.status).lower() if event.status is not None else ""
        if status != "open":
            raise serializers.ValidationError(
                "Регистрация возможна, если только мероприятие имеет статус открыто('open')"
            )

        email = attrs["email"]
        if EventRegistration.objects.filter(event=event, email=email).exists():
            raise serializers.ValidationError(
                "Указанный email уже зарегистрирован на мероприятие"
            )

        return attrs
