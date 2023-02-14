from django.contrib import admin
from .models import APIRequest, API


class APIAdmin(admin.ModelAdmin):
    fields = ('name', 'description', 'api_url', 'api_key', 'request_delay', 'num_request_attempts')
    list_display = ('name', 'api_url', 'request_delay', 'num_request_attempts')

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


@admin.action(description="Mark requests as having errors.")
def api_request_status_error(modeladmin, request, queryset):
    queryset.update(status="error")


@admin.action(description="Mark requests as finished.")
def api_request_status_finished(modeladmin, request, queryset):
    queryset.update(status="finished")


class APIRequestAdmin(admin.ModelAdmin):
    fields = ('status',)
    list_display = ('api', 'status', 'time')
    list_filter = ['api', 'status']
    actions = [api_request_status_error, api_request_status_finished]

    def get_api_name(self, obj) -> str:
        return obj.api.name

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


admin.site.register(API, APIAdmin)
admin.site.register(APIRequest, APIRequestAdmin)
