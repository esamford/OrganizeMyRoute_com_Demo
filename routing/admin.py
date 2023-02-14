from django.contrib import admin
from .models import Address, Route, AddressConnection, RouteAddressConnection


class AddressAdmin(admin.ModelAdmin):
    list_display = ('street', 'city', 'state', 'country', 'created_at', 'updated_at')
    list_filter = ('city', 'state', 'country', 'created_at', 'updated_at')
    fields = ('created_at', 'updated_at', 'street', 'city', 'state', 'postal_code', 'country', 'latitude', 'longitude')
    readonly_fields = ('created_at', 'updated_at', 'latitude', 'longitude')

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class RouteAdmin(admin.ModelAdmin):
    list_display = ('route_key', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    fields = ('created_at', 'updated_at', 'route_key')
    readonly_fields = ('created_at', 'updated_at', 'route_key')

    def has_add_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class AddressConnectionAdmin(admin.ModelAdmin):
    list_display = (
        'created_at', 'updated_at', 'from_address', 'to_address',
        'avoid_highways', 'avoid_tolls', 'avoid_ferries',
        'distance_meters', 'travel_seconds'
    )
    list_filter = (
        'created_at', 'updated_at',
        'avoid_highways', 'avoid_tolls', 'avoid_ferries'
    )

    def has_add_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class RouteAddressConnectionAdmin(admin.ModelAdmin):
    list_display = ('route', '_get_route_created_at', 'order', '_from_address', '_to_address')
    fields = ('route', 'address_connection', 'order')
    readonly_fields = ('route', 'address_connection', 'order')

    def _get_route_created_at(self, rac):
        return rac.route.created_at
    _get_route_created_at.short_description = 'Route Created At'

    def _from_address(self, rac):
        return rac.address_connection.from_address
    _from_address.short_description = 'From Address'

    def _to_address(self, rac):
        return rac.address_connection.to_address
    _to_address.short_description = 'To Address'

    def has_add_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


admin.site.register(Address, AddressAdmin)
admin.site.register(Route, RouteAdmin)
admin.site.register(AddressConnection, AddressConnectionAdmin)
admin.site.register(RouteAddressConnection, RouteAddressConnectionAdmin)


