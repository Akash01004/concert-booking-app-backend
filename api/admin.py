from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Concert, Ticket
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'is_admin', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('is_admin',)}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Concert)
admin.site.register(Ticket)