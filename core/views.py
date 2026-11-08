from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class UserQuerySetMixin:
    """Restrict the view queryset to objects owned by the logged-in user.

    Use it in List/Detail/Update/Delete views of models with a `user` FK,
    always combined with `LoginRequiredMixin` placed before it in the MRO:
    `class AccountListView(LoginRequiredMixin, UserQuerySetMixin, ListView)`.
    Objects of other users fall outside the queryset, so they return 404.
    """

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class HomeView(TemplateView):
    template_name = 'home.html'


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'
