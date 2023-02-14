from django.urls import path
from . import views

urlpatterns = [
    path('faq/', views.frequently_asked_questions, name="info_faq"),
]
