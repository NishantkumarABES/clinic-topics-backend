from django.contrib import admin
from apps.cms.models import StaticPage, StaticPageVersion, ContactUsSubmission


class StaticPageVersionInline(admin.TabularInline):
    model = StaticPageVersion
    extra = 0
    readonly_fields = ("version", "created_by", "created_at")
    ordering = ("-version",)


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ("page_type", "is_active")
    inlines = [StaticPageVersionInline]


@admin.register(StaticPageVersion)
class StaticPageVersionAdmin(admin.ModelAdmin):
    list_display = (
        "page",
        "version",
        "is_published",
        "created_by",
        "created_at",
    )
    list_filter = ("is_published", "page")
    search_fields = ("title", "content")

@admin.register(ContactUsSubmission)
class ContactUsSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "phone_number",
        "is_resolved",
        "created_at",
    )
    list_filter = ("is_resolved", "created_at")
    search_fields = ("name", "email", "phone_number")
    readonly_fields = ("name", "email", "phone_number", "message", "created_at")