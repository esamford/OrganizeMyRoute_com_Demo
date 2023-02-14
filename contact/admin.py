from django.contrib import admin
from .models import Message


@admin.action(description="Mark selected messages as read")
def mark_as_read(modeladmin, request, queryset):
    queryset.update(read=True)


@admin.action(description="Mark selected messages as unread")
def mark_as_unread(modeladmin, request, queryset):
    queryset.update(read=False)


class MessageAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'subject_snip', 'message_snip', 'read',)
    list_filter = ('created_at', 'reason', 'read')
    actions = [mark_as_read, mark_as_unread]


# Register your models here.
admin.site.register(Message, MessageAdmin)
