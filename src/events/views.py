from uuid import UUID

from django.db import IntegrityError, transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from src.events.models import Event, EventRegistration, Outbox
from src.events.serializers import EventRegistrationSerializer, EventSerializer
from src.events.utils.notifications import generate_confirmation_code


class EventViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Event.objects.select_related("venue").all().filter(status="open")
    serializer_class = EventSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {"name": ["exact", "icontains", "istartswith"]}
    ordering_fields = ["event_date"]


class EventRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id: str):
        try:
            ext_uuid = UUID(str(event_id))
            event = Event.objects.filter(external_id=ext_uuid).first()
        except Exception:
            event = None

        if event is None:
            return Response(
                {"detail": "Мероприятие не найдено. Проверьте id мероприятия"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EventRegistrationSerializer(
            data=request.data, context={"event": event}
        )
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                code = generate_confirmation_code()

                reg = EventRegistration.objects.create(
                    event=event,
                    full_name=serializer.validated_data["full_name"],
                    email=serializer.validated_data["email"],
                    confirmation_code=code,
                )

                Outbox.objects.create(
                    topic="registration",
                    payload={
                        "registration_id": str(reg.id),
                        "event_id": str(event.id),
                        "full_name": reg.full_name,
                        "email": reg.email,
                        "confirmation_code": reg.confirmation_code,
                    },
                )
        except IntegrityError:
            return Response(
                {"detail": "Для этого мероприятия такой email уже зарегистрирован"},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "detail": "Заявка на регистрацию получена, ждите код подтверждения на указанный email"
            },
            status=status.HTTP_201_CREATED,
        )
