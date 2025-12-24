from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django import forms
from apps.accounts.models import User, AuthProvider
from apps.accounts.constants import UserRole, UserState


class Admin(User):
    class Meta:
        proxy = True
        verbose_name = "Admin User"
        verbose_name_plural = "Admin Users"

class AdminUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ("email", 'phone')
        required = ('email', 'phone')

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])

        # 🔐 HARD RULES FOR PLATFORM ADMIN
        user.role = UserRole.ADMIN
        user.is_staff = True
        user.is_superuser = False
        user.state = UserState.ACTIVE
        

        if commit:
            user.save()
        return user

@admin.register(Admin)
class AdminUserAdmin(DjangoUserAdmin):
    list_display = ("id", "email", "role", "is_staff", "is_superuser", "is_active")
    list_filter = ("is_active",)
    search_fields = ("email",)
    ordering = ("email",)

    add_form = AdminUserCreationForm
    model = Admin

    # ✅ IMPORTANT: override Django defaults
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "phone", "password1", "password2",),
        }),
    )

    fieldsets = (
        (None, {
            "fields": ("email", "password",),
        }),
        ("Personal info", {"fields": ("full_name", "phone",)}),
        ("Permissions", {
            "fields": ("role", "is_staff", "is_superuser", "is_active",)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(role=UserRole.ADMIN)

    # Optional: keep if you really want these
    actions = ["promote_to_superuser", "demote_from_superuser"]

    def promote_to_superuser(self, request, queryset):
        queryset.update(is_superuser=True)

    def demote_from_superuser(self, request, queryset):
        queryset.update(is_superuser=False)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "phone", "role", "state")
    list_filter = ("role", "state")
    search_fields = ("email", "phone")
    actions = ["activate_users", "suspend_users"]

    def activate_users(self, request, queryset):
        queryset.update(state="active")

    def suspend_users(self, request, queryset):
        queryset.update(state="suspended")

@admin.register(AuthProvider)
class AuthProviderAdmin(admin.ModelAdmin):
    list_display = ("provider", "provider_user_id", "user")
    list_filter = ("provider",)
    search_fields = ("provider_user_id",)