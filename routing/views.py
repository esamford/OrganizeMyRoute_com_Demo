import random

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import get_user_model

from api.manual_tokens import get_user_jwt
from api import views as api_views
from routing.models import Route
from traveling_salesman.settings import token_generator_user
from security.models import HashedIP, TrackedAction

CONST_ACTION_STR_SUBMIT_ROUTING_FORM = "Submitted routing form"
CONST_ACTION_STR_LOAD_ROUTING_FORM_PAGE = "Loaded routing form page"


class RoutingForm(View):
    def get(self, request):
        # Force clients that have recently submitted the form to wait, in case bots are submitting forms automatically.
        # Check this first so that refreshes don't count add up and cause a redirect later.
        submitted_form_recently_action = TrackedAction.get_actions_within_last_x_minutes(
            request, action_type=CONST_ACTION_STR_SUBMIT_ROUTING_FORM, num_minutes=10
        ).first()
        if submitted_form_recently_action is not None:
            return render(request, 'waiting_page.html')

        # Prevent JWT farming by redirecting to the index page if the client reloads the form page too many times.
        form_load_actions = TrackedAction.get_actions_within_last_x_minutes(
            request, action_type=CONST_ACTION_STR_LOAD_ROUTING_FORM_PAGE, num_minutes=10
        )
        if len(form_load_actions) >= 5:
            return redirect('/')

        # Prevent clients that have used blacklisted JWTs from seeing the routing form for the day.
        form_blacklisted_actions = TrackedAction.get_actions_within_last_x_minutes(
            request, action_type=api_views.CONST_ACTION_STR_USED_BLACLISTED_JWT, num_minutes=60 * 24
        )
        if len(form_blacklisted_actions) >= 3:
            return redirect('/')

        # At this point, everything seems fine. Get the JWT for the client and return the desired page.
        user = get_user_model().objects.filter(username=token_generator_user['username']).first()
        if user is None:
            # The dummy user doesn't exist yet. Create it and save it to the database before continuing.
            user = User(username=token_generator_user['username'], password=token_generator_user['password'])
            user.save()
        token_data = get_user_jwt(user)
        TrackedAction.create_action_with_request_and_type(request, CONST_ACTION_STR_LOAD_ROUTING_FORM_PAGE)
        context = {
            'token': token_data['access'],  # Allows the user to submit data to the API.
        }
        return render(request, 'route_form.html', context=context)


class ShowRoute(View):
    def get(self, request, route_key):
        found_route = Route.objects.filter(route_key=route_key).first()
        if not found_route:
            # TODO: Redirect to a custom 404 error page that allows navigation back to the routing form.
            return redirect('/')

        context = {
            'route': found_route,
        }
        return render(request, 'show_route.html', context=context)
