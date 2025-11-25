from django.urls import path

from .views import *

urlpatterns = [
    path("", FlightListAPIView.as_view(), name="flight-list"),
    # path("create/", FlightCreateAPIView.as_view(), name="flight-create"),
    path("<uuid:pk>", FlightRetrieveAPIView.as_view(), name="flight-retrieve"),
    path("delete/<uuid:pk>", FlightDeleteAPIView.as_view(), name="flight-delete"),
    path("stats/<uuid:pk>", FlightStatsAPIView.as_view(), name="flight-list"),
    path("driver/<int:pk>", FlightHistoryAPIView.as_view(), name="flight-history"),
    path("history/<uuid:pk>", FlightHistoryAPIView.as_view(), name="flight-history"),

    path("list-pg", FlightListNOPg.as_view(), name="flight-list-pg"),

    path("ordered", FlightOrderedListAPIView.as_view(), name="flight-list-ordered"),
    path("ordered/<uuid:pk>", FlightOrderedRetrieveAPIView.as_view(), name="flight-list-ordered"),

    path("info/", ExportFlightInfoAPIView.as_view(), name="flight-info"),

    path("finance/<uuid:pk>", FinanceFlightAPIView.as_view(), name="flight-finance"),
    path("close/<uuid:pk>", FlightCloseApi.as_view(), name="flight-close"),
    path("statistics/", FlightStatsView.as_view(), name="flight-test"),

]
