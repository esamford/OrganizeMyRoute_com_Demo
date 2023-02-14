from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.RoutingForm.as_view(), name="route_form"),
    path('<str:route_key>/', views.ShowRoute.as_view(), name="route_show"),
]
