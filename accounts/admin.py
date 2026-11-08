from django.contrib import admin

from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'bank_name',
        'account_type',
        'initial_balance',
        'user',
    )
    list_filter = ('account_type',)
    list_select_related = ('user',)
    search_fields = ('name', 'bank_name', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
