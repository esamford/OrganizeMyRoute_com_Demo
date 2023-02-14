import datetime
import math
import random
import urllib
from typing import Any

from django.db import models

from traveling_salesman.settings import GMAPS_API_KEY
from . import model_utils


def clean_address_piece(val: str):
    if not isinstance(val, str):
        if (isinstance(val, list) or isinstance(val, tuple)) and len(val) == 1:
            val = val[0]
        else:
            raise Exception(
                "Could not parse address value. The function was expecting a string, but got: {}".format(type(val))
            )
    val = str(val).upper()
    val = val.strip(' ')
    while '  ' in val:
        val = val.replace('  ', ' ')
    # val = val.replace(' NORTH ', ' N ')
    # val = val.replace(' EAST ', ' E ')
    # val = val.replace(' WEST ', ' W ')
    # val = val.replace(' SOUTH ', ' S ')
    # val = val.replace(' NORTHWEST ', ' NW ')
    # val = val.replace(' NORTHEAST ', ' NE ')
    # val = val.replace(' SOUTHWEST ', ' SW ')
    # val = val.replace(' SOUTHEAST ', ' SE ')

    return val


class Address(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    street = models.CharField(max_length=300)
    city = models.CharField(max_length=200)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=30)
    country = models.CharField(max_length=100)
    latitude = models.DecimalField(decimal_places=6, max_digits=10)
    longitude = models.DecimalField(decimal_places=6, max_digits=10)

    def __str__(self):
        return "{} {} {}".format(self.get_addr_line_1(), self.get_addr_line_2(), self.get_addr_line_3())

    class Meta:
        unique_together = ('street', 'city', 'state', 'postal_code', 'country')

    def clean(self):
        self.street = clean_address_piece(self.street)
        self.city = clean_address_piece(self.city)
        self.state = clean_address_piece(self.state)
        self.postal_code = clean_address_piece(self.postal_code)
        self.country = clean_address_piece(self.country)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def to_dict(self) -> dict:
        return {
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'street': self.street,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country,
            'latitude': self.latitude,
            'longitude': self.longitude
        }

    @staticmethod
    def get_if_exists(address_dict: dict) -> Any or None:
        for key in ('street', 'city', 'state', 'postal_code', 'country'):
            if key not in address_dict:
                raise Exception("Key '{}' was not found.".format(key))
        temp_addr_model = Address(
            street=address_dict['street'],
            city=address_dict['city'],
            state=address_dict['state'],
            postal_code=address_dict['postal_code'],
            country=address_dict['country']
        )
        temp_addr_model.clean()
        found_addr_model = Address.objects.filter(
            street=temp_addr_model.street,
            city=temp_addr_model.city,
            state=temp_addr_model.state,
            postal_code=temp_addr_model.postal_code,
            country=temp_addr_model.country
        ).first()
        if found_addr_model:
            return found_addr_model
        else:
            return None

    @staticmethod
    def address_dict_is_valid(address_dict: dict):
        print(address_dict)
        is_valid = True
        if not isinstance(address_dict, dict):
            is_valid = False
            return is_valid
        for key in ('street', 'city', 'state', 'postal_code', 'country'):
            if key not in address_dict:
                is_valid = False
            elif len(address_dict[key]) == 0:
                is_valid = False
        return is_valid

    def get_addr_line_1(self) -> str:
        return str(self.street).title()

    def get_addr_line_2(self) -> str:
        return "{}, {} {}".format(self.city, self.state, self.postal_code).title()

    def get_addr_line_3(self) -> str:
        return str(self.country).title()


class Route(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    route_key = models.CharField(default=model_utils.route_get_unique_key, max_length=32, unique=True)

    # Save the information to the model instance so the database doesn't need to be queried multiple times.
    __route_address_connections = None

    def __str__(self):
        return self.route_key

    def get_route_address_connections(self):
        if self.__route_address_connections is None:
            self.__route_address_connections = RouteAddressConnection.objects.filter(route=self).order_by('order')
        return self.__route_address_connections

    def get_gmaps_embed_src(self) -> str:
        """
        For a full list of Google Maps Direction parameters, check here:
            https://developers.google.com/maps/documentation/embed/embedding-map#directions_mode
        """
        found_racs = self.get_route_address_connections()
        assert len(found_racs) > 0
        found_address_connections = [x.address_connection for x in found_racs]
        assert len(found_racs) == len(found_address_connections)

        result = "https://www.google.com/maps/embed/v1/directions?"
        result += "key={}".format(GMAPS_API_KEY)
        result += "&mode=driving"

        # These should all be the same within a single route, so only the first needs to be checked.
        if found_address_connections[0].avoid_highways or \
                found_address_connections[0].avoid_tolls or \
                found_address_connections[0].avoid_ferries:
            result += "&avoid="
            if found_address_connections[0].avoid_highways:
                result += "highways|"
            if found_address_connections[0].avoid_tolls:
                result += "tolls|"
            if found_address_connections[0].avoid_ferries:
                result += "ferries"
            result = result.strip("|")

        result += "&origin="
        origin_address_connection = found_address_connections[0]
        result += model_utils.get_url_encoded_address(origin_address_connection.from_address)

        result += "&destination="
        destination_address_connection = found_address_connections[-1]
        result += model_utils.get_url_encoded_address(destination_address_connection.to_address)

        waypoint_connections = found_address_connections[:-1]
        if len(waypoint_connections) > 0:
            result += "&waypoints="
            for ac in found_address_connections[:-1]:
                result += model_utils.get_url_encoded_address(ac.to_address)
                result += "|"
            result = result.strip("|")

        return result

    def get_total_travel_time_string(self) -> str:
        racs = self.get_route_address_connections()
        total_travel_seconds = sum([int(x.address_connection.travel_seconds) for x in racs])

        minutes = math.ceil(total_travel_seconds / 60)
        hours = minutes // 60
        minutes -= 60 * hours
        days = hours // 24
        hours -= 24 * days

        result = ""
        if days == 1:
            result += "{} day".format(days)
        elif days > 1:
            result += "{} days".format(days)

        if days > 0 and hours > 0 and minutes > 0:
            result += ", "
        elif days > 0 and (hours > 0 or minutes > 0):
            result += " and "

        if hours == 1:
            result += "{} hour".format(hours)
        elif hours > 1:
            result += "{} hours".format(hours)

        if days > 0 and hours > 0 and minutes > 0:
            result += ", and "
        elif days == 0 and hours > 0 and minutes > 0:
            result += " and "

        if minutes == 1:
            result += "{} minute".format(minutes)
        elif minutes > 1:
            result += "{} minutes".format(minutes)

        return result

    def get_total_distance_miles(self) -> float:
        return model_utils.convert_km_to_miles(self.get_total_distance_km())

    def get_total_distance_km(self) -> float:
        racs = self.get_route_address_connections()
        total_km = sum([x.address_connection.get_distance_km() for x in racs])
        return round(total_km, 2)

    def get_created_at_day_str(self) -> str:
        creation_date = self.created_at.date()
        assert isinstance(creation_date, datetime.date)
        return creation_date.strftime("%B %d, %Y")

    def get_days_since_creation(self) -> int:
        creation_date = self.created_at.date()
        assert isinstance(creation_date, datetime.date)
        return (datetime.date.today() - creation_date).days


class AddressConnection(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    from_address = models.ForeignKey(Address, on_delete=models.CASCADE, related_name="from_address")
    to_address = models.ForeignKey(Address, on_delete=models.CASCADE, related_name="to_address")
    avoid_highways = models.BooleanField(default=False)
    avoid_tolls = models.BooleanField(default=False)
    avoid_ferries = models.BooleanField(default=True)
    distance_meters = models.PositiveIntegerField()
    travel_seconds = models.PositiveIntegerField()

    def get_travel_time_string(self) -> str:
        minutes = math.ceil(int(self.travel_seconds) / 60)
        hours = minutes // 60
        minutes -= 60 * hours

        result = ""
        if hours == 1:
            result += "{} hour".format(hours)
        elif hours > 1:
            result += "{} hours".format(hours)

        if hours > 0 and minutes > 0:
            result += " and "

        if minutes == 1:
            result += "{} minute".format(minutes)
        elif minutes > 1:
            result += "{} minutes".format(minutes)

        return result

    def get_distance_miles(self) -> float:
        return model_utils.convert_km_to_miles(self.get_distance_km())

    def get_distance_km(self) -> float:
        return round(int(self.distance_meters) / 1000, 2)

    def get_gmaps_embed_src(self) -> str:
        """
        For a full list of Google Maps Direction parameters, check here:
            https://developers.google.com/maps/documentation/embed/embedding-map#directions_mode
        """
        result = "https://www.google.com/maps/embed/v1/directions?"
        result += "key={}".format(GMAPS_API_KEY)
        result += "&mode=driving"
        if self.avoid_highways or self.avoid_tolls or self.avoid_ferries:
            result += "&avoid="
            if self.avoid_highways:
                result += "highways|"
            if self.avoid_tolls:
                result += "tolls|"
            if self.avoid_ferries:
                result += "ferries"
            result = result.strip("|")
        result += "&origin="
        result += model_utils.get_url_encoded_address(self.from_address)
        result += "&destination="
        result += model_utils.get_url_encoded_address(self.to_address)

        return result

    class Meta:
        unique_together = ('from_address', 'to_address', 'avoid_highways', 'avoid_tolls', 'avoid_ferries')

    def __str__(self):
        return "{}  -->  {}".format(self.from_address, self.to_address)


class RouteAddressConnection(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='route')
    address_connection = models.ForeignKey(
        AddressConnection, on_delete=models.CASCADE, related_name='address_connection'
    )
    order = models.PositiveIntegerField()

    def delete(self, using=None, keep_parents=False):
        rac_model = RouteAddressConnection.objects.filter(id=self.id).first()
        super().delete(using=using, keep_parents=keep_parents)

        # NOTE: Don't delete the AddressConnection model. That information may be useful for two-location routes,
        # just so long as it isn't outdated. It may also be used by other routes.

        # Delete the Route this belongs to. There should never be an incomplete route.
        r_model = Route.objects.filter(id=rac_model.route.id).first()
        if r_model:
            r_model.delete()

    def get_step_num(self):
        return self.order + 1



