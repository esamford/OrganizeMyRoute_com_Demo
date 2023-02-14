"""
This file uses urls.py to call it once after startup. Any code within the "run_startup_code()" function will be
executed before serving web content to users.
"""
from api.models import APIRequest, API


def clear_database_api_request_waiting():
    for req in APIRequest.objects.filter(status="waiting"):
        req.status = "error"
        req.save()


def create_api_defaults_geolocation():
    # In case the API record doesn't already exist in the database, set default values and continue.
    api_name = "Geolocate"
    api_geolocate = API.objects.filter(name=api_name).first()
    if not api_geolocate:
        temp_data = {
            "name": api_name,
            "api_url": "https://trueway-geocoding.p.rapidapi.com/Geocode",
            "api_key": "739ea61a53msh94e86af504d3444p1a3311jsn85079586747c",
        }
        api_geolocate = API(**temp_data)
        api_geolocate.save()


def create_api_defaults_routing():
    api_name = "Routing"
    api_routing = API.objects.filter(name=api_name).first()
    if not api_routing:
        temp_data = {
            "name": api_name,
            "api_url": "https://trueway-directions2.p.rapidapi.com/FindDrivingRoute",
            "api_key": "739ea61a53msh94e86af504d3444p1a3311jsn85079586747c"
        }
        api_routing = API(**temp_data)
        api_routing.save()


def run_startup_code():
    """
    Run this code after project startup, and not during the main server runtime.
    """
    create_api_defaults_geolocation()
    create_api_defaults_routing()
    clear_database_api_request_waiting()
