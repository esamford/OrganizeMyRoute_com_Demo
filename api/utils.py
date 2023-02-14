import copy
import datetime
import time

import requests
from geopy import distance

from api.models import API, APIRequest
from exceptions import NotRoutableException
from routing.models import Address, Route, RouteAddressConnection, AddressConnection

CONST_NUM_DAYS_ADDRESS_OUTDATED = 30


def wait_for_api_request(api: API, api_request: APIRequest):
    # Wait until this view's request is queued up.
    next_id = -1
    while api_request.id != next_id:
        time.sleep(0.05)
        next_id = APIRequest.objects.filter(api=api, status="waiting").order_by("id").first().id

    # Wait to prevent overburdening the external API.
    time.sleep(int(api.request_delay))


def get_closest_address_to_coordinates(coordinates: list or tuple, address_list: list) -> Address:
    assert isinstance(coordinates, list) or isinstance(coordinates, tuple)
    assert len(coordinates) == 2
    assert isinstance(coordinates[0], float)
    assert isinstance(coordinates[1], float)
    assert len(address_list) > 0

    address_list.sort(
        key=lambda x: distance.distance(
            coordinates,
            (x.latitude, x.longitude)
        ).meters
    )
    return address_list[0]


def save_trueway_routing_json_to_database(
        legs: list,
        start_address: Address,
        intermediate_addresses: list,
        end_address: Address,
        avoid_highways: bool,
        avoid_tolls: bool,
        avoid_ferries: bool
) -> Route:
    # Convert leg data to address_connections while preserving the route order.
    address_connections = []
    temp_address_list = [start_address, ] + copy.deepcopy(intermediate_addresses) + [end_address, ]
    print("Processing legs in route...")
    for leg in legs:
        leg_duration_seconds = leg['duration']
        leg_distance_meters = leg['distance']
        start_coordinates = (leg['start_point']['lat'], leg['start_point']['lng'])
        end_coordinates = (leg['end_point']['lat'], leg['end_point']['lng'])

        from_address = get_closest_address_to_coordinates(start_coordinates, temp_address_list)
        temp_address_list.pop(temp_address_list.index(from_address))  # Only use each address once.
        to_address = get_closest_address_to_coordinates(end_coordinates, temp_address_list)

        # Get the address connection if it already exists in the database. Otherwise, create it.
        address_connection = AddressConnection.objects.filter(
            from_address=from_address,
            to_address=to_address,
            avoid_highways=avoid_highways,
            avoid_tolls=avoid_tolls,
            avoid_ferries=avoid_ferries
        ).first()
        if address_connection:
            address_connection.distance_meters = leg_distance_meters
            address_connection.travel_seconds = leg_duration_seconds
            address_connection.save()  # Update the information.
        else:
            address_connection = AddressConnection(
                from_address=from_address,
                to_address=to_address,
                avoid_highways=avoid_highways,
                avoid_tolls=avoid_tolls,
                avoid_ferries=avoid_ferries,
                distance_meters=leg_distance_meters,
                travel_seconds=leg_duration_seconds,
            )
            address_connection.save()  # Create the information
        address_connections.append(address_connection)

    # Validate that the route start and end addresses are correct,
    # and that they weren't mixed in with the intermediate addresses.
    print("Asserting address connections...")
    assert len(address_connections) >= 1  # Only 1 in case of no intermediate addresses.
    assert address_connections[0].from_address == start_address
    assert address_connections[-1].to_address == end_address

    # TODO: Django cannot use foreign objects until they are saved.
    #  Save foreign models first, then revert back by deleting in case of errors.
    print("Saving data to database...")
    route = Route()
    route_address_connections = []
    try:
        # Save the address connections so they can be referenced by later modules.
        for connection in address_connections:
            connection.save()

        # NOTE: In case additional data is saved for user notes, to make each user's route unique for them, don't
        #   search for existing routes. Otherwise, it would pull up someone else's information.
        #   If I decide that will never happen, it would be more space-efficient to search for existing routes rather
        #   than creating new ones.

        # Since the route doesn't already exist, create it.
        route.save()
        for index, connection in enumerate(address_connections):
            route_address_connection = RouteAddressConnection(
                route=route,
                address_connection=connection,
                order=index
            )
            route_address_connection.save()
        return route
    except Exception as ex:
        # NOTE: Records in the AddressConnection model must not be deleted. It's possible they will be
        # used in multiple routes, so deleting it from one route would break others.

        # TODO: Something went wrong if the code reaches this point.
        #  Delete the Route and its RouteAddressConnection records, but not AddressConnections.
        routing_models = [route, ] + list(route_address_connections)
        for x in routing_models:
            try:
                if hasattr(x, "delete"):
                    x.delete()
            except Exception:
                continue

        raise ex


def get_or_create_address(address_dict: dict) -> Address:
    """
    :param address_dict:
        A dictionary containing address routing_data. Example:
            {
                'street': 'Woodlane & Capitol Avenue',
                'city': 'Little Rock',
                'state': 'AR',
                'country': '72201',
                'postal_code': 'United States':
            }
        All of the above keys are required.

    :return:
    """
    # Check that the data is valid before querying the external API.
    for required_key in ('street', 'city', 'state', 'country', 'postal_code'):
        if required_key not in address_dict:
            raise Exception("Required key '{}' is missing from JSON data.".format(required_key))
        else:
            if isinstance(address_dict[required_key], list) or isinstance(address_dict[required_key], tuple):
                if len(address_dict[required_key]) == 1:
                    address_dict[required_key] = address_dict[required_key][0]
                else:
                    raise Exception("Could not parse the '{}' value. The server was expecting a string.")
            if len(address_dict[required_key]) == 0:
                raise Exception("Value for '{}' is empty.".format(required_key))

    # Attempt to search for the address data in the database before querying the API.
    # If it exists and isn't too old, assume it's still accurate and return it.
    found_address = Address.get_if_exists(address_dict)
    if found_address is not None and \
            found_address.updated_at.timestamp() > \
            datetime.datetime.utcnow().timestamp() - \
            datetime.timedelta(days=CONST_NUM_DAYS_ADDRESS_OUTDATED).total_seconds():
        return found_address

    api_name = "Geolocate"
    api_geolocate = API.objects.filter(name=api_name).first()
    if not api_geolocate:
        raise Exception("The '{}' API does not exist in the database.".format(api_name))

    # Example: {"address": "505 Howard St, San Francisco", "language": "en"}
    query_dict = {
        "address": "{}, {}, {}, {} {}".format(
            address_dict['street'], address_dict['city'], address_dict['state'], address_dict['country'],
            address_dict['postal_code']
        ),
        "language": "en",
    }
    headers = {
        "X-RapidAPI-Key": api_geolocate.api_key,
        "X-RapidAPI-Host": "trueway-geocoding.p.rapidapi.com"
    }

    api_request = APIRequest(api=api_geolocate)
    api_request.save()

    try:
        wait_for_api_request(api_geolocate, api_request)

        for _ in range(api_geolocate.num_request_attempts):
            try:
                with requests.request("GET", api_geolocate.api_url, headers=headers, params=query_dict) as req:
                    req.raise_for_status()
                    coordinates = dict(req.json()['results'][0]['location'])

                    # Save the coordinates to the database, if they don't exist.
                    if found_address is not None:
                        found_address.latitude = coordinates['lat']
                        found_address.longitude = coordinates['lng']
                        found_address.save()
                        return_val = found_address
                    else:
                        new_address = Address(
                            # No need to clean data here. The model does that already before saving.
                            street=address_dict['street'],
                            city=address_dict['city'],
                            state=address_dict['state'],
                            postal_code=address_dict['postal_code'],
                            country=address_dict['country'],
                            latitude=coordinates['lat'],
                            longitude=coordinates['lng']
                        )
                        new_address.save()
                        return_val = new_address

                    api_request.status = "finished"
                    api_request.save()
                    return return_val
            except Exception:
                time.sleep(int(api_geolocate.request_delay) * 2)
                continue
    except Exception:
        raise Exception("The external geolocation API could not be reached. Please try again tomorrow.")
    finally:
        test_request = APIRequest.objects.filter(id=api_request.id).first()
        if test_request and test_request.status == "waiting":
            test_request.status = "error"
            test_request.save()


def create_route(routing_data: dict) -> Route:
    CONST_START_ADDRESS_KEY = 'start_address'
    CONST_INTERMEDIATE_ADDRESSES_KEY = 'intermediate_addresses'
    CONST_END_ADDRESS_KEY = 'end_address'

    # Add missing data.
    if 'avoid_highways' not in routing_data:
        routing_data['avoid_highways'] = False
    if 'avoid_tolls' not in routing_data:
        routing_data['avoid_tolls'] = False
    if 'avoid_ferries' not in routing_data:
        routing_data['avoid_ferries'] = True
    for key in ('avoid_highways', 'avoid_tolls', 'avoid_ferries',):
        if not isinstance(routing_data[key], bool):
            raise Exception("The '{}' should be a boolean value.".format(key))

    # Check for errors and raise exceptions if any are found.
    for required_key in (CONST_START_ADDRESS_KEY, CONST_END_ADDRESS_KEY,):
        if required_key not in routing_data:
            raise Exception("Required key '{}' is missing from JSON data.".format(required_key))
        elif len(routing_data[required_key]) == 0:
            raise Exception("Value for '{}' is empty.".format(required_key))
        elif required_key in (CONST_START_ADDRESS_KEY, CONST_END_ADDRESS_KEY) \
                and not Address.address_dict_is_valid(routing_data[required_key]):
            raise Exception(
                "The '{}' key contained invalid address data. "
                "The server was expecting a dictionary/JSON object with the following keys: "
                "'street', 'city', 'state', 'postal_code', 'country'. "
                "Your data was: {}".format(required_key, routing_data[required_key])
            )
    # Check for intermediate addresses.
    if CONST_INTERMEDIATE_ADDRESSES_KEY in routing_data:
        required_key = CONST_INTERMEDIATE_ADDRESSES_KEY
        if not isinstance(routing_data[required_key], list) and not isinstance(routing_data[required_key], tuple):
            raise Exception("The '{}' value was not an iterable list of JSON objects.".format(required_key))
        for address in routing_data[required_key]:
            if not Address.address_dict_is_valid(address):
                raise Exception(
                    "The '{}' key contained invalid address data. "
                    "The server was expecting a list of dictionary/JSON objects, each with the following keys: "
                    "'street', 'city', 'state', 'postal_code', 'country'. "
                    "Your data was: {}".format(required_key, routing_data[required_key])
                )
    if len(routing_data[CONST_INTERMEDIATE_ADDRESSES_KEY]) > 20:
        raise Exception("The server cannot process more than 20 intermediate addresses at once.")
    elif len(routing_data[CONST_INTERMEDIATE_ADDRESSES_KEY]) == 0 \
            and routing_data['start_address'] == routing_data['end_address']:
        raise Exception("The start and end addresses are the same, but there are no intermediate addresses.")

    # Convert all addresses to GPS coordinates.
    try:
        routing_data[CONST_START_ADDRESS_KEY] = get_or_create_address(routing_data[CONST_START_ADDRESS_KEY])
        for index in range(len(routing_data[CONST_INTERMEDIATE_ADDRESSES_KEY])):
            routing_data[CONST_INTERMEDIATE_ADDRESSES_KEY][index] = \
                get_or_create_address(routing_data[CONST_INTERMEDIATE_ADDRESSES_KEY][index])
        routing_data[CONST_END_ADDRESS_KEY] = get_or_create_address(routing_data[CONST_END_ADDRESS_KEY])
    except Exception:
        raise Exception("Could not parse your JSON data. Please make sure it is formatted correctly.")

    # Get response from routing API.
    api_name = "Routing"
    api_route = API.objects.filter(name=api_name).first()
    if not api_route:
        raise Exception("The '{}' API does not exist in the database.".format(api_name))

    query_dict = {
        'stops': "",
        'avoid_highways': routing_data['avoid_highways'],
        'avoid_tolls': routing_data['avoid_tolls'],
        'avoid_ferries': routing_data['avoid_ferries'],
        'optimize': True
    }
    for address in [routing_data[CONST_START_ADDRESS_KEY], ] + routing_data[CONST_INTERMEDIATE_ADDRESSES_KEY] + \
                   [routing_data[CONST_END_ADDRESS_KEY], ]:
        query_dict['stops'] += "{},{};".format(address.latitude, address.longitude)
    query_dict['stops'] = query_dict['stops'].strip(';')
    headers = {
        "X-RapidAPI-Key": api_route.api_key,
        "X-RapidAPI-Host": "trueway-directions2.p.rapidapi.com"
    }

    api_request = APIRequest(api=api_route)
    api_request.save()

    route_dict = {}
    try:
        wait_for_api_request(api_route, api_request)

        for _ in range(api_route.num_request_attempts):
            try:
                with requests.request("GET", api_route.api_url, headers=headers, params=query_dict) as req:
                    req.raise_for_status()
                    print("\n\n\n", req.json(), "\n\n\n")
                    if len(req.json()) == 0:
                        print("Raising NotRoutableException")
                        raise NotRoutableException
                    route_dict = dict(req.json()['route'])

                    api_request.status = "finished"
                    api_request.save()
            except NotRoutableException as ex:
                raise ex
            except Exception:
                time.sleep(int(api_route.request_delay) * 2)
                continue
    except NotRoutableException as ex:
        raise ex
    except Exception:
        raise Exception("The external geolocation API could not be reached. Please try again tomorrow.")
    finally:
        test_request = APIRequest.objects.filter(id=api_request.id).first()
        if test_request and test_request.status == "waiting":
            test_request.status = "error"
            test_request.save()

    # Parse and save JSON data to database, then return a Route object if successful.
    assert 'legs' in route_dict
    legs = route_dict['legs']
    route_model = save_trueway_routing_json_to_database(
        legs=legs,
        start_address=routing_data[CONST_START_ADDRESS_KEY],
        intermediate_addresses=routing_data[CONST_INTERMEDIATE_ADDRESSES_KEY],
        end_address=routing_data[CONST_END_ADDRESS_KEY],
        avoid_highways=routing_data['avoid_highways'],
        avoid_tolls=routing_data['avoid_tolls'],
        avoid_ferries=routing_data['avoid_ferries']
    )
    assert isinstance(route_model, Route)
    return route_model

