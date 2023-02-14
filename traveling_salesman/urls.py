"""traveling_salesman URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path, include
from .db_setup import run_startup_code

# The main urls.py file runs only once after startup. Use this to call code that is required before serving content.
# NOTE: This code must be commented out before you create the database and its Django-related tables. Django will
#   crash before creating database tables otherwise.
# run_startup_code()


urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('index.urls')),
    path('route/', include('routing.urls')),
    path('api/', include('api.urls')),
    path('contact/', include('contact.urls')),
    path('info/', include('info.urls')),
] + staticfiles_urlpatterns()



