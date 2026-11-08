from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'birth_date')
    list_select_related = ('user',)
    search_fields = (
        'user__email',
        'user__first_name',
        'user__last_name',
        'phone',
    )
    readonly_fields = ('created_at', 'updated_at')
