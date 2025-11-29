import django_filters
from django.db.models import Sum
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
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
from data.finans.models import Logs
from data.flight.serializers import FlightListserializer, FlightListCReateserializer, FlightOrderedListserializer
from data.gas.models import GasPurchase, GasSale, Gas_another_station
from data.oil.models import OilPurchase, Utilized_oil
from data.salarka.models import Salarka, Sale, SalarkaAnotherStation
from .models import Flight, Ordered
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


class DashboardStatsView(APIView):

    def parse_date(self, date_str: str, field_name: str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError(
                {field_name: "yyyy-MM-dd formatida bolish kerak! Masalan: 2025-01-31"}
            )

    def get(self, request):
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        start_date = end_date = None

        if start_date_str:
            start_date = self.parse_date(start_date_str, "start_date")

        if end_date_str:
            end_date = self.parse_date(end_date_str, "end_date")

        if start_date and end_date and end_date < start_date:
            raise ValidationError(
                {"detail": "start_date end_date dan katta bolmasin"}
            )

        flight_qs = Flight.objects.all()
        if start_date:
            flight_qs = flight_qs.filter(departure_date__gte=start_date)
        if end_date:
            flight_qs = flight_qs.filter(departure_date__lte=end_date)

        order_qs = Ordered.objects.all()
        if start_date:
            order_qs = order_qs.filter(departure_date__gte=start_date)
        if end_date:
            order_qs = order_qs.filter(departure_date__lte=end_date)

        logs_qs = Logs.objects.all()
        if start_date:
            logs_qs = logs_qs.filter(created_at__date__gte=start_date)
        if end_date:
            logs_qs = logs_qs.filter(created_at__date__lte=end_date)

        total_flights = flight_qs.count()
        active_flights = flight_qs.filter(status="ACTIVE").count()
        in_uzb_flights = flight_qs.filter(flight_type="IN_UZB").count()
        out_uzb_flights = flight_qs.filter(flight_type="OUT").count()

        reys_na_zakaz = 0

        total_orders = order_qs.count()
        total_income = (
                logs_qs.filter(action="INCOME")
                .aggregate(s=Sum("amount_uzs"))["s"] or 0
        )

        total_expense = (
                logs_qs.filter(action="OUTCOME")
                .aggregate(s=Sum("amount_uzs"))["s"] or 0
        )

        employee_expense = (
                logs_qs.filter(
                    action="OUTCOME",
                    kind__in=["PAY_SALARY", "BONUS"],
                ).aggregate(s=Sum("amount_uzs"))["s"] or 0
        )

        other_expense = (
                logs_qs.filter(
                    action="OUTCOME",
                    kind__in=["OTHER", "FIX_CAR", "BUY_CAR", "FLIGHT"],
                ).aggregate(s=Sum("amount_uzs"))["s"] or 0
        )

        leasing_paid = (
                logs_qs.filter(
                    action="OUTCOME",
                    kind="LEASING",
                ).aggregate(s=Sum("amount_uzs"))["s"] or 0
        )

        try:
            from data.cars.models import Leasing
            leasing_balance = (
                    Leasing.objects.aggregate(s=Sum("balance"))["s"] or 0
            )
        except Exception:
            leasing_balance = 0

        total_for_all_cars = total_income - total_expense

        data = {
            "total_flights": total_flights,
            "active_flights": active_flights,
            "in_uzb_flights": in_uzb_flights,
            "out_uzb_flights": out_uzb_flights,
            "order_flight": reys_na_zakaz,

            "total_income": total_income,
            "total_expense": total_expense,
            "employee_expense": employee_expense,
            "other_expense": other_expense,

            "total_for_all_cars": total_for_all_cars,
            "leasing_balance": leasing_balance,
            "leasing_paid": leasing_paid,

            "total_orders": total_orders,
        }

        return Response(data)


class FinanceFuelStatsView(APIView):

    def parse_date(self, date_str: str, field_name: str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError(
                {field_name: "yyyy-MM-dd formatida bolish kerak! Masalan: 2025-01-31"}
            )

    def get(self, request):
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        start_date = end_date = None

        if start_date_str:
            start_date = self.parse_date(start_date_str, "start_date")

        if end_date_str:
            end_date = self.parse_date(end_date_str, "end_date")

        if start_date and end_date and end_date < start_date:
            raise ValidationError(
                {"detail": "start_date end_date dan katta bolmasin"}
            )

        def by_date(qs):
            if start_date:
                qs = qs.filter(created_at__date__gte=start_date)
            if end_date:
                qs = qs.filter(created_at__date__lte=end_date)
            return qs

        def sum_or_0(qs, field):
            return qs.aggregate(s=Sum(field))["s"] or 0

        logs_qs = by_date(Logs.objects.all())

        total_income = sum_or_0(logs_qs.filter(action="INCOME"), "amount_uzs")
        total_expense = sum_or_0(logs_qs.filter(action="OUTCOME"), "amount_uzs")
        total_for_all_cars = total_income - total_expense  # Итого по всем автомобилям

        leasing_paid = sum_or_0(
            logs_qs.filter(action="OUTCOME", kind="LEASING"),
            "amount_uzs",
        )
        try:
            from data.cars.models import Leasing
            leasing_balance = (
                    Leasing.objects.aggregate(s=Sum("balance"))["s"] or 0
            )
        except Exception:
            leasing_balance = 0

        gas_purchases_qs = by_date(GasPurchase.objects.all())
        gas_sales_qs = by_date(GasSale.objects.all())
        gas_other_station_qs = by_date(Gas_another_station.objects.all())

        gas_purchase_volume = (
                sum_or_0(gas_purchases_qs, "amount")
                + sum_or_0(gas_other_station_qs, "purchased_volume")
        )
        gas_sale_volume = sum_or_0(gas_sales_qs, "amount")
        gas_total_volume = gas_purchase_volume - gas_sale_volume
        oil_purchases_qs = by_date(OilPurchase.objects.all())
        utilized_oil_qs = by_date(Utilized_oil.objects.all())
        oil_purchase_volume = sum_or_0(oil_purchases_qs, "oil_volume")
        oil_sale_volume = sum_or_0(utilized_oil_qs, "quantity_utilized")
        oil_total_volume = oil_purchase_volume - oil_sale_volume
        salarka_purchases_qs = by_date(Salarka.objects.all())
        salarka_another_qs = by_date(SalarkaAnotherStation.objects.all())
        salarka_sales_qs = by_date(Sale.objects.all())

        salarka_purchase_volume = (
                sum_or_0(salarka_purchases_qs, "volume")
                + sum_or_0(salarka_another_qs, "volume")
        )
        salarka_sale_volume = sum_or_0(salarka_sales_qs, "volume")
        salarka_total_volume = salarka_purchase_volume - salarka_sale_volume

        data = {
            "leasing_balance": leasing_balance,
            "leasing_paid": leasing_paid,
            "gas_total_volume": gas_total_volume,
            "gas_sale_volume": gas_sale_volume,
            "gas_purchase_volume": gas_purchase_volume,
            "oil_total_volume": oil_total_volume,
            "oil_sale_volume": oil_sale_volume,
            "oil_purchase_volume": oil_purchase_volume,
            "salarka_total_volume": salarka_total_volume,
            "salarka_sale_volume": salarka_sale_volume,
            "salarka_purchase_volume": salarka_purchase_volume,
        }

        return Response(data)
