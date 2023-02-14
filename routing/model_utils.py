import random
import urllib

from . import models


def route_get_unique_key() -> str:
    key = None
    while key is None or models.Route.objects.filter(route_key=key).first():
        key = "".join(
            [random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(16)]
        )
    return key


def get_url_encoded_address(address) -> str:
    return urllib.parse.quote_plus("{} {}, {} {} {}".format(
            str(address.street), str(address.city),
            str(address.state), str(address.country),
            str(address.postal_code)
        ))


def convert_km_to_miles(km: float) -> float:
    return round(km * 0.6213712, 2)
