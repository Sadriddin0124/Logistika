import django_filters
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from drf_yasg import openapi
from drf_yasg.openapi import Response
from drf_yasg.utils import swagger_auto_schema
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, \
    ListAPIView, RetrieveUpdateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from account.permission import CanDeleteUser
from data.flight.serializers import FlightListserializer, FlightListCReateserializer, FlightOrderedListserializer
from .models import Flight, Ordered
from ..finans.models import Logs
from ..finans.serializers import FinansListserializer


class FlightListAPIView(ListCreateAPIView):
    queryset = Flight.objects.all().order_by("-created_at")
    serializer_class = FlightListserializer
    # permission_classes = [IsAuthenticated]

    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = [
        'flight_type', "route", "status", "payment_type", "is_archived",
    ]
    ordering_fields = ('flight_type', "route", "status", "payment_type", "is_archived")
    search_fields = ('flight_type', "route", "status", "payment_type", "is_archived")


class FlightRetrieveAPIView(RetrieveUpdateAPIView):
    queryset = Flight.objects.all().order_by("-created_at")
    serializer_class = FlightListserializer
    permission_classes = [IsAuthenticated]


class FlightDeleteAPIView(DestroyAPIView):
    permission_classes = [IsAuthenticated, CanDeleteUser]
    authentication_classes = [JWTAuthentication]
    queryset = Flight.objects.all()


class FlightFilter(django_filters.FilterSet):
    car_id = django_filters.UUIDFilter(field_name='car__id', lookup_expr='exact')

    class Meta:
        model = Flight
        fields = ['car_id']


class FlightStatsAPIView(ListAPIView):
    serializer_class = FlightListCReateserializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = FlightFilter  # Use the filter class

    def get_queryset(self):
        car_id = self.kwargs.get('pk')
        if car_id:
            # Filter the queryset by car_id
            return Flight.objects.filter(car__id=car_id).order_by("-created_at")
        return Flight.objects.none()


class FlightHistoryAPIView(ListAPIView):
    serializer_class = FlightListCReateserializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = FlightFilter

    def get_queryset(self):
        driver_id = self.kwargs.get('pk')
        if driver_id:
            return Flight.objects.filter(driver__id=driver_id).order_by("-created_at")
        return Flight.objects.none()


class FlightHistoryStatsAPIView(ListAPIView):
    serializer_class = FlightListCReateserializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        flight_id = self.kwargs.get('pk')
        if flight_id:
            return Flight.objects.filter(id=flight_id).order_by("-created_at")
        return Flight.objects.none()


class FinanceFlightAPIView(ListAPIView):
    serializer_class = FinansListserializer

    def get_queryset(self):
        flight_id = self.kwargs.get('pk')
        if flight_id:
            return Logs.objects.filter(flight__id=flight_id).order_by("-created_at")
        return Logs.objects.none()


class FlightListNOPg(ListAPIView):
    serializer_class = FlightListCReateserializer
    permission_classes = (IsAuthenticated,)
    queryset = Flight.objects.all().order_by('-created_at')
    pagination_class = None  # Disable pagination for this view only

    def get_paginated_response(self, data):
        return Response(data)


class FlightOrderedListAPIView(ListCreateAPIView):
    serializer_class = FlightOrderedListserializer
    queryset = Ordered.objects.all().order_by("-created_at")
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = [
        "is_archived",
    ]
    ordering_fields = ("is_archived",)
    search_fields = ("is_archived",)


class FlightOrderedRetrieveAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Ordered.objects.all().order_by("-created_at")
    serializer_class = FlightOrderedListserializer
    permission_classes = (IsAuthenticated,)


class ExportFlightInfoAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter("type", openapi.IN_QUERY, description="Type of data to export (flight, ordered)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter("status", openapi.IN_QUERY, description="Filter by status (ACTIVE, INACTIVE)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter("flight_type", openapi.IN_QUERY, description="Filter by flight type (IN_UZB, OUT)",
                              type=openapi.TYPE_STRING),
        ],
        responses={200: "Excel file generated"}
    )
    def get(self, request):
        data_type = request.GET.get("type", "flight")  # Default to flight if not specified
        status = request.GET.get("status")
        flight_type = request.GET.get("flight_type")

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Flight Info"

        # Handle different types of data
        if data_type == "flight":
            queryset = Flight.objects.all()

            # Apply filters
            if status:
                queryset = queryset.filter(status=status)
            if flight_type:
                queryset = queryset.filter(flight_type=flight_type)

            headers = [
                "Регион", "Тип рейса", "Автомобиль", "Водитель",
                "Дата отправления", "Дата прибытия", "Цена (USD)", "Расходы водителя (USD)", "Расходы рейса(USD)",
                "Оплата за питание", "Прибыль", "Статус", "Дата создания",
                "Информация о грузе"
            ]
            sheet.append(headers)

            for flight in queryset:
                sheet.append([
                    flight.region.name if flight.region else "",
                    "Рейсы внутри Узбекистана" if flight.flight_type == "IN_UZB" else "Рейсы за пределы Узбекистана" if flight.flight_type else "",
                    flight.car.number if flight.car else "",
                    flight.driver.full_name if flight.driver else "",
                    flight.departure_date.strftime('%d-%m-%Y') if flight.departure_date else "",
                    flight.arrival_date.strftime('%d-%m-%Y') if flight.arrival_date else "",
                    flight.price_uzs or "",
                    flight.driver_expenses_uzs or "",
                    flight.flight_balance_uzs or "",
                    (
                        (max((flight.arrival_date - flight.departure_date).days, 0) * (flight.other_expenses_uzs or 0))
                        if flight.departure_date and flight.arrival_date
                        else ""
                    ),
                    flight.price_uzs - flight.driver_expenses_uzs - flight.flight_balance_uzs - (
                        (max((flight.arrival_date - flight.departure_date).days, 0) * (flight.other_expenses_uzs or 0))
                        if flight.departure_date and flight.arrival_date
                        else ""
                    ),
                    "Активный" if flight.status == "ACTIVE" else "Неактивный" if flight.status else "",
                    flight.created_at.strftime("%d-%m-%Y %H:%M") if flight.created_at else "",
                    flight.cargo_info or "",
                ])

        elif data_type == "ordered":
            queryset = Ordered.objects.all()

            # Apply filters
            if status:
                queryset = queryset.filter(status=status)
            if flight_type:
                queryset = queryset.filter(flight_type=flight_type)

            headers = [
                "Имя водителя", "Номер водителя", "Номер автомобиля", "Информация о грузе",
                "Статус", "Дата отправления", "Цена (UZS)", "Расходы водителя (UZS)",
                "Регион", "Тип рейса", "Дата создания"
            ]
            sheet.append(headers)

            for ordered in queryset:
                sheet.append([
                    ordered.driver_name or "",
                    ordered.driver_number or "",
                    ordered.car_number or "",
                    ordered.cargo_info or "",
                    "Активный" if ordered.status == "ACTIVE" else "Неактивный" if ordered.status else "",
                    ordered.departure_date.strftime('%d-%m-%Y') if ordered.departure_date else "",
                    ordered.price_uzs or "",
                    ordered.driver_expenses_uzs or "",
                    ordered.region.name if ordered.region else "",
                    "Рейсы внутри Узбекистана" if ordered.flight_type == "IN_UZB" else "Рейсы за пределы Узбекистана" if ordered.flight_type else "",
                    ordered.created_at.strftime('%d-%m-%Y %H:%M') if ordered.created_at else "",
                ])

        else:
            return HttpResponse("Invalid type parameter. Must be one of: flight, ordered.", status=400)

        # Apply styles to headers
        for col_num, header in enumerate(headers, 1):
            cell = sheet.cell(row=1, column=col_num)
            cell.font = Font(bold=True, size=12)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            sheet.column_dimensions[cell.column_letter].width = 20

        # Generate the response
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="Flight_Info_{data_type}.xlsx"'
        workbook.save(response)
        return response


from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from datetime import datetime
from icecream import ic
from .models import Flight
from .serializers import FlightListserializer


class FlightCloseApi(APIView):
    def put(self, request, pk, *args, **kwargs):
        data = request.data
        try:
            flight = Flight.objects.get(id=pk)

            if flight.status == "INACTIVE":
                return Response({"detail": "Flight is already closed."}, status=status.HTTP_400_BAD_REQUEST)

            flight.status = "INACTIVE"

            # Parse arrival_date if provided
            arrival_date_str = data.get("arrival_date")
            if arrival_date_str:
                arrival_date = datetime.strptime(arrival_date_str, "%Y-%m-%d").date()
            else:
                arrival_date = flight.arrival_date

            # Update other fields safely
            flight.end_km = data.get("end_km", flight.end_km or 0) or 0
            flight.flight_balance = data.get("flight_balance", flight.flight_balance or 0) or 0
            flight.arrival_date = arrival_date

            # Save flight updates
            flight.save()

            # Calculate lunch payments safely
            lunch_payments = 0
            if flight.departure_date and flight.arrival_date:
                days = max((flight.arrival_date - flight.departure_date).days, 0)
                lunch_payments = (flight.other_expenses_uzs or 0) * days
                ic(days, lunch_payments)

            # Handle flight_balance_uzs safely
            flight.flight_balance_uzs = data.get("flight_balance_uzs", flight.flight_balance_uzs or 0) or 0
            try:
                flight.flight_balance_uzs = float(flight.flight_balance_uzs or 0)
                flight.flight_expenses_uzs = float(flight.flight_balance_uzs or 0)

                if flight.flight_type == "OUT":
                    ic(f"Updating driver balance for {flight.driver.full_name}")

                    driver = flight.driver

                    driver.balance_uzs = float(driver.balance_uzs or 0)
                    driver.balance_uzs += float(lunch_payments or 0)

                    driver.balance_uzs -= float(flight.flight_balance_uzs or 0)
                    driver.save()

                    if flight.flight_balance_uzs < 0:
                        Logs.objects.create(
                            action="OUTCOME",
                            amount_uzs=flight.flight_balance_uzs,
                            kind="FLIGHT",
                            comment=f"оплата за рейс "
                                    f"{flight.car.name} {flight.car.number} для водителя {flight.driver.full_name}",
                            flight=flight,
                            employee=flight.driver
                        )
                    if flight.flight_balance_uzs > 0:
                        Logs.objects.create(
                            action="OUTCOME",
                            amount_uzs=flight.flight_balance_uzs,
                            kind="PAY_SALARY",
                            comment=f"оплата за рейс "
                                    f"{flight.car.name} {flight.car.number} для водителя {flight.driver.full_name}",
                            flight=flight,
                            employee=flight.driver
                        )
                    Logs.objects.create(
                        action="OUTCOME",
                        amount_uzs=lunch_payments,
                        kind="PAY_SALARY",
                        comment=f"за оплату еды для водителя {flight.driver.full_name} "
                                f"по рейсу {flight.car.name} {flight.car.number}",
                        flight=flight,
                        employee=flight.driver
                    )
                    Logs.objects.create(
                        action="OUTCOME",
                        amount_uzs=flight.driver_expenses_uzs or 0,
                        kind="PAY_SALARY",
                        comment=f"оплата за рейс "
                                f"{flight.car.name}  {flight.car.number} для водителя {flight.driver.full_name}",
                        flight=flight,
                        employee=flight.driver
                    )

                    ic(f"Updated driver balance for {flight.driver.full_name}")
                else:
                    ic("Driver is None, skipping balance update")
            except ValueError as e:
                return Response({"detail": f"Invalid data for flight_balance_uzs: {e}"},
                                status=status.HTTP_400_BAD_REQUEST)

            # Serialize and return response
            serializer = FlightListserializer(flight)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Flight.DoesNotExist:
            return Response({"detail": "Flight not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


extend_schema(tags=["FLIGHT_STATS"])


class FlightStatsView(APIView):
    def get(self, request):
        # /flight/statistics/?start_date=01.11.2025&end_date=30.12.2025
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        qs = Flight.objects.filter(is_archived=False)

        def parse_date(date_str: str, field_name: str):
            try:
                return datetime.strptime(date_str, "%d.%m.%Y").date()
            except ValueError:
                raise ValidationError(
                    {field_name: "дд.мм.гггг -> mana shu formatda bolish kere"}
                )

        start_date = end_date = None

        if start_date_str:
            start_date = parse_date(start_date_str, "start_date")
            qs = qs.filter(departure_date__gte=start_date)

        if end_date_str:
            end_date = parse_date(end_date_str, "end_date")
            qs = qs.filter(departure_date__lte=end_date)

        if start_date and end_date and end_date < start_date:
            raise ValidationError(
                {"detail": "start_date end_date dan katta bolmasin"}
            )

        stats = {
            "total_flights": qs.count(),
            "active_flights": qs.filter(status="ACTIVE").count(),
            "in_uzb_flights": qs.filter(flight_type="IN_UZB").count(),
            "out_uzb_flights": qs.filter(flight_type="OUT").count(),
        }

        return Response(stats)
