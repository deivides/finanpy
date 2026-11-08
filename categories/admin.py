from django.contrib import admin

from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'user')
    list_filter = ('category_type',)
    list_select_related = ('user',)
    search_fields = ('name', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
