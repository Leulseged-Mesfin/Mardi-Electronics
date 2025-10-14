from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import UserAccount

# Register your models here.

class AccountAdmin(UserAdmin):
    model = UserAccount
    ordering = ['email']
    list_display = ('name', 'email', 'role', 'created_at', 'is_active', 'is_staff')
    search_fields = ('email', 'name', 'role')
    readonly_fields = ('created_at', 'updated_at')

    filter_horizontal = ()
    list_filter = ()
    # fieldsets = ()

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('name', 'gender', 'age', 'address', 'mobile', 'profile_image')}),
        ('Roles and Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Authentication', {'fields': ('last_login', 'date_joined')}),
        ('Important Dates', {'fields': ('created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'role', 'password1', 'password2'),
        }),
    )


admin.site.register(UserAccount, AccountAdmin)
# admin.site.register(AccountAdmin)