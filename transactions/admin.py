from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'description',
        'transaction_type',
        'amount',
        'account',
        'category',
        'user',
    )
    list_filter = ('transaction_type', 'date')
    date_hierarchy = 'date'
    list_select_related = ('account', 'category', 'user')
    search_fields = ('description', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
