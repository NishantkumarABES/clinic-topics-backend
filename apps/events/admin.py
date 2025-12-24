from django.contrib import admin
from apps.events.models import Event, EventType, EventRegistration


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "start_datetime", "is_paid", "is_active")
    list_filter = ("is_paid", "event_type")


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "status")
    list_filter = ("event", "user", "status")
    search_fields = ("event__title", "user__username")
    raw_id_fields = ("event", "user")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True