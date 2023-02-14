import json
import os
import random
import time
import unittest

import requests
from geopy import distance

# Allow for imports of app files. All "api.___" imports should come after this.
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "traveling_salesman.settings")
django.setup()

from api.utils import get_or_create_address, create_route
from api.models import API
from routing.models import Address, Route

random.seed(time.time())

CONST_TEST_USERNAME = "test_user_01"
CONST_TEST_PASSWORD = "a6UrxPkB"


CONST_URL_DOMAIN = "http://127.0.0.1:8000/"
CONST_URL_API_TOKEN_GET = CONST_URL_DOMAIN + "api/token/"
CONST_URL_API_TOKEN_REFRESH = CONST_URL_DOMAIN + "api/token/refresh/"
CONST_URL_API_GEOLOCATE = CONST_URL_DOMAIN + "api/geolocate/"
CONST_URL_API_GENERATE_ROUTE = CONST_URL_DOMAIN + "api/generate_route/"


def get_jwt_headers(data: dict) -> dict:
    return {
        # Simple_JWT requires this information in the request header to
        # authenticate the user token during a GET request.
        "Authorization": "Bearer {}".format(data['access'])
    }


class TestToken(unittest.TestCase):
    def test_get_token(self):
        data = {
            "username": CONST_TEST_USERNAME,
            "password": CONST_TEST_PASSWORD,
        }

        # Note that this is using "POST" rather than "GET"
        with requests.post(CONST_URL_API_TOKEN_GET, data=data) as req:
            req.raise_for_status()

            print(req.json())

    def test_refresh_token(self):
        data = {
            "username": CONST_TEST_USERNAME,
            "password": CONST_TEST_PASSWORD,
        }

        with requests.post(CONST_URL_API_TOKEN_GET, data=data) as req:
            req.raise_for_status()

            data = {
                # When refreshing tokens, the server requires teh original "refresh" value.
                'refresh': req.json()['refresh']
            }

        with requests.post(CONST_URL_API_TOKEN_REFRESH, data=data) as req:
            req.raise_for_status()

            print(req.json())

    def test_invalid_username_and_password(self):
        data = {
            "username": CONST_TEST_USERNAME,
            "password": CONST_TEST_PASSWORD + "a",  # Purposefully use an invalid password to be rejected.
        }

        with requests.post(CONST_URL_API_TOKEN_GET, data=data) as req:
            try:
                req.raise_for_status()
            except Exception as ex:
                print(ex)
                print("Invalid credentials found. Successfully raised status error.")
                return

            assert False  # The request should not have been successful.


class TestAPIGeolocate(unittest.TestCase):
    def test_get_response_with_server(self):
        # Get the token.
        data = {
            "username": CONST_TEST_USERNAME,
            "password": CONST_TEST_PASSWORD,
        }
        with requests.post(CONST_URL_API_TOKEN_GET, data=data) as req:
            req.raise_for_status()
            header = get_jwt_headers(req.json())
            print(header)

        # Fetch GPS coordinates.
        data = {}
        data['street'] = "Woodlane & Capitol Avenue"
        data['city'] = "Little Rock"
        data['state'] = "AR"
        data['postal_code'] = "72201"
        data['country'] = "United States"
        with requests.post(CONST_URL_API_GEOLOCATE, json=data, headers=header) as req:
            print(req)
            req.raise_for_status()
            print(req.json())
            self.assertTrue('lat' in req.json())
            self.assertTrue('lng' in req.json())
            self.assertIsInstance(req.json()['lat'], float)
            self.assertIsInstance(req.json()['lng'], float)

    def test_get_response_without_server(self):
        # Fetch GPS coordinates.
        data = {}
        data['street'] = "Woodlane & Capitol Avenue"
        data['city'] = "Little Rock"
        data['state'] = "AR"
        data['postal_code'] = "72201"
        data['country'] = "United States"

        result = get_or_create_address(address_dict=data)
        self.assertIsInstance(result, Address)
        self.assertIsInstance(float(result.latitude), float)
        self.assertIsInstance(float(result.longitude), float)


class TestAPIRoute(unittest.TestCase):
    def test_get_response_with_server(self):
        # Get the token.
        data = {
            "username": CONST_TEST_USERNAME,
            "password": CONST_TEST_PASSWORD,
        }
        with requests.post(CONST_URL_API_TOKEN_GET, data=data) as req:
            req.raise_for_status()
            header = get_jwt_headers(req.json())

        data = {
            'start_address': {
                'street': '1315 10th St',
                'city': 'Sacramento',
                'state': 'California',
                'postal_code': '95814-4905',
                'country': 'America'
            },
            'intermediate_addresses': [
                {
                    'street': 'Woodlane & Capitol Avenue',
                    'city': 'Little Rock',
                    'state': 'AR',
                    'postal_code': '72201',
                    'country': 'United States'
                },
                {
                    'street': '2300 N Lincoln Blvd',
                    'city': 'Oklahoma City',
                    'state': 'OK',
                    'postal_code': '73105-4805',
                    'country': 'America'
                },
                {
                    'street': '1700 W Washington St',
                    'city': 'Phoenix',
                    'state': 'Arizona',
                    'postal_code': '85007-2812',
                    'country': 'United States'
                },
                {
                    'street': '490 Old Santa Fe Trail',
                    'city': 'Santa Fe',
                    'state': 'NM',
                    'postal_code': '87501',
                    'country': 'United States'
                },
                {
                    'street': '400 High St.',
                    'city': 'Jackson',
                    'state': 'Mississippi',
                    'postal_code': '39201',
                    'country': 'America'
                },
                {
                    'street': '600 Dexter Ave',
                    'city': 'Montgomery',
                    'state': 'AL',
                    'postal_code': '36130-3008',
                    'country': 'US'
                },
            ],
            'end_address': {
                'street': '400 S Monroe St, Apalachee Pkwy',
                'city': 'Tallahassee',
                'state': 'Florida',
                'postal_code': '32399-6536',
                'country': 'US'
            },
        }
        data['intermediate_addresses'].sort(key=lambda x: random.randint(1, 100))

        print("Route data before submitting to server:")
        print(data)
        print("\n\n")

        with requests.post(CONST_URL_API_GENERATE_ROUTE, json=data, headers=header) as req:
            print(req)
            req.raise_for_status()
            print(req.json())

            self.assertTrue('route_key' in req.json())
            self.assertTrue('route_url' in req.json())

    def test_get_response_without_server(self):
        data = {
            'start_address': {
                'street': '1315 10th St',
                'city': 'Sacramento',
                'state': 'California',
                'postal_code': '95814-4905',
                'country': 'America'
            },
            'intermediate_addresses': [
                {
                    'street': 'Woodlane & Capitol Avenue',
                    'city': 'Little Rock',
                    'state': 'AR',
                    'postal_code': '72201',
                    'country': 'United States'
                },
                {
                    'street': '2300 N Lincoln Blvd',
                    'city': 'Oklahoma City',
                    'state': 'OK',
                    'postal_code': '73105-4805',
                    'country': 'America'
                },
                {
                    'street': '1700 W Washington St',
                    'city': 'Phoenix',
                    'state': 'Arizona',
                    'postal_code': '85007-2812',
                    'country': 'United States'
                },
                {
                    'street': '490 Old Santa Fe Trail',
                    'city': 'Santa Fe',
                    'state': 'NM',
                    'postal_code': '87501',
                    'country': 'United States'
                },
                {
                    'street': '400 High St.',
                    'city': 'Jackson',
                    'state': 'Mississippi',
                    'postal_code': '39201',
                    'country': 'America'
                },
                {
                    'street': '600 Dexter Ave',
                    'city': 'Montgomery',
                    'state': 'AL',
                    'postal_code': '36130-3008',
                    'country': 'US'
                },
            ],
            'end_address': {
                'street': '400 S Monroe St, Apalachee Pkwy',
                'city': 'Tallahassee',
                'state': 'Florida',
                'postal_code': '32399-6536',
                'country': 'US'
            },
        }
        data['intermediate_addresses'].sort(key=lambda x: random.randint(1, 100))

        result = create_route(routing_data=data)
        self.assertIsInstance(result, Route)

    def test_no_intermediate_addresses_without_server(self):
        data = {
            'start_address': {
                'street': '1315 10th St',
                'city': 'Sacramento',
                'state': 'California',
                'postal_code': '95814-4905',
                'country': 'America'
            },
            'intermediate_addresses': [
            ],
            'end_address': {
                'street': '400 S Monroe St, Apalachee Pkwy',
                'city': 'Tallahassee',
                'state': 'Florida',
                'postal_code': '32399-6536',
                'country': 'US'
            },
        }

        result = create_route(routing_data=data)
        self.assertIsInstance(result, Route)

    def test_external_api(self):
        api_name = "Routing"
        api_route = API.objects.filter(name=api_name).first()
        if not api_route:
            raise Exception("The '{}' API does not exist in the database.".format(api_name))

        stops = (
            # These are already in the expected route order. Start is at index 0, and stop is the last item.
            (38.576614, -121.493258),  # Capital of California, United States
            (33.448438, -112.097865),  # Capital of Arizona, United States
            (35.682368, -105.939705),  # Capital of New Mexico, United States
            (35.492185, -97.502963),   # Capital of Oklahoma, United States
            (34.746419, -92.287923),   # Capital of Arkansas, United States
            (32.303869, -90.182265),   # Capital of Mississippi, United States
            (32.377693, -86.300501),   # Capital of Alabama, United States
            (30.438612, -84.28102)     # Capital of Florida, United States
        )
        query_dict = {
            'stops': "",
            'optimize': True
        }
        for coordinates in stops:
            query_dict['stops'] += "{},{};".format(coordinates[0], coordinates[1])
        query_dict['stops'] = query_dict['stops'].strip(';')
        headers = {
            "X-RapidAPI-Key": api_route.api_key,
            "X-RapidAPI-Host": "trueway-directions2.p.rapidapi.com"
        }

        with requests.request("GET", api_route.api_url, headers=headers, params=query_dict) as req:
            req.raise_for_status()
            route_dict = req.json()['route']

            self.assertTrue('legs' in route_dict)
            self.assertTrue(len(route_dict['legs']) > 0)

            route_points = [
                (route_dict['legs'][0]['start_point']['lat'], route_dict['legs'][0]['start_point']['lng'])
            ]
            for pos, leg in enumerate(route_dict['legs'], start=1):
                print("LEG {}".format(pos))
                print("Start point: {}".format(leg['start_point']))
                print("End point: {}".format(leg['end_point']))
                coordinates = (leg['end_point']['lat'], leg['end_point']['lng'])
                print(coordinates)
                route_points.append(coordinates)
                print()

            for expected_point, real_point in zip(stops, route_points):
                assert isinstance(expected_point, list) or isinstance(expected_point, tuple)
                assert isinstance(real_point, list) or isinstance(real_point, tuple)
                distance_meters = distance.distance(expected_point, real_point).meters
                self.assertTrue(
                    distance_meters <= 100.0,  # For reference, 100 meters is roughly the length of a football field.
                    "The expected and real distances were above 100 meters. This is inaccurate!"
                )
                print("DISTANCE BETWEEN {} AND {} IN METERS: {}".format(expected_point, real_point, distance_meters))

    def test_external_api_different_countries(self):
        api_name = "Routing"
        api_route = API.objects.filter(name=api_name).first()
        if not api_route:
            raise Exception("The '{}' API does not exist in the database.".format(api_name))

        stops = (
            # These are already in the expected route order. Start is at index 0, and stop is the last item.
            (36.5172445, -91.3464075),  # Capital of United States
            (51.5287718, -0.2416819),   # Capital of England
            (-35.2812958, 149.124822),  # Capital of Australia
        )
        query_dict = {
            'stops': "",
            'optimize': True
        }
        for coordinates in stops:
            query_dict['stops'] += "{},{};".format(coordinates[0], coordinates[1])
        query_dict['stops'] = query_dict['stops'].strip(';')
        headers = {
            "X-RapidAPI-Key": api_route.api_key,
            "X-RapidAPI-Host": "trueway-directions2.p.rapidapi.com"
        }

        with requests.request("GET", api_route.api_url, headers=headers, params=query_dict) as req:
            req.raise_for_status()

            # Invalid routes where it isn't possible to drive between locations should return nothing.
            self.assertTrue(len(req.json()) == 0)


