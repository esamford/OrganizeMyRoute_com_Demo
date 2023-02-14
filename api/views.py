import rest_framework.request
from django.shortcuts import render
from django.urls import reverse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes

from exceptions import NotRoutableException
from routing.models import Route
from routing import views as routing_views
from security.models import TrackedAction, HashedIP, JWTBlacklist
from . import utils

CONST_API_KEY_GEOLOCATE = ""
CONST_API_KEY_ROUTE = ""

CONST_ACTION_STR_USED_BLACLISTED_JWT = "Used a blacklisted JWT"


@api_view(http_method_names=["POST"])
@permission_classes([IsAuthenticated, ])
def geolocate(request) -> Response:
    """
    :param request: Accepts JSON address_dict specifying a specific address and converts that to GPS coordinates.
    :return: A JSON response containing 'lat' and 'lng' values for latitude and longitude coordinates.
    """
    try:
        data = dict(request.data)
    except Exception:
        return Response(
            {'errors': ["Could not parse JSON address_dict from request.", ]},
            status=400
        )

    try:
        address = utils.get_or_create_address(data)
        result_data = {
            'lat': address.latitude,
            'lng': address.longitude
        }
        return Response(result_data, status=200)
    except Exception as ex:
        result_data = {
            'errors': [
                str(ex),
            ]
        }
        return Response(result_data, status=400)


@api_view(http_method_names=["POST"])
@permission_classes([IsAuthenticated, ])
def route_addresses(request) -> Response:
    # Track the action for bot reduction.
    submit_form_action = TrackedAction(
        hashed_ip=HashedIP.get_or_create_from_request(request),
        action_type=routing_views.CONST_ACTION_STR_SUBMIT_ROUTING_FORM
    )
    submit_form_action.save()

    # Verify that the client isn't using blacklisted JWTs. If so, block them.
    if JWTBlacklist.check_if_jwt_is_blacklisted_with_request(request):
        TrackedAction.create_action_with_request_and_type(request, CONST_ACTION_STR_USED_BLACLISTED_JWT)
        return Response(
            {
                'errors': [
                    "The server refused your request for security reasons. Please refresh your page and try again.",
                ]
            },
            status=403
        )
    blacklisted_jwt = JWTBlacklist.create_by_request(request)
    found_actions = TrackedAction.get_actions_within_last_x_minutes(
        request, action_type=CONST_ACTION_STR_USED_BLACLISTED_JWT, num_minutes=60*24
    )
    if len(found_actions) >= 3:
        return Response(
            {
                'errors': [
                    "Are you trying to scrape the website? ಠ_ಠ",
                ]
            },
            status=403
        )

    assert isinstance(request, rest_framework.request.Request)
    try:
        data = dict(request.data)
    except Exception:
        return Response(
            {'errors': ["Could not parse JSON address_dict from request.", ]},
            status=400
        )

    try:
        print("Getting route.")
        route = utils.create_route(data)
        print("Got route.")
        assert isinstance(route, Route)
        result_data = {
            'route_key': route.route_key,
            'route_url': reverse('route_show', kwargs={'route_key': route.route_key})
        }
        return Response(result_data, status=200)
    except NotRoutableException:
        print("A NotRoutableException has been caught!")
        blacklisted_jwt.delete()     # Let the user re-enter their addresses after changing them.
        submit_form_action.delete()  # Let the user refresh the page without waiting.

        # Return a response that will pop up on the user's screen.
        result_data = {
            'notRoutableException': True
        }
        return Response(result_data, status=400)
    except Exception as ex:
        print("Caught regular exception.")
        result_data = {
            'errors': [
                str(ex),
            ]
        }
        return Response(result_data, status=400)



