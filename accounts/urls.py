from django.urls import path

from .views import (
    AccountCreateView,
    AccountDeleteView,
    AccountListView,
    AccountUpdateView,
)

urlpatterns = [
    path('', AccountListView.as_view(), name='account_list'),
    path('new/', AccountCreateView.as_view(), name='account_create'),
    path(
        '<int:pk>/edit/', AccountUpdateView.as_view(), name='account_update'
    ),
    path(
        '<int:pk>/delete/', AccountDeleteView.as_view(), name='account_delete'
    ),
]
