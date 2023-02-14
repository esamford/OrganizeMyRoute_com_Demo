from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name="api_token_get"),
    path('token/refresh/', TokenRefreshView.as_view(), name="api_token_refresh"),
    path('geolocate/', views.geolocate, name="api_geolocate"),
    path('generate_route/', views.route_addresses, name="api_route_coordinates"),
]
