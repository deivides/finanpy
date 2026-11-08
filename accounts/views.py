from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.views import UserQuerySetMixin

from .forms import AccountForm
from .models import Account


class AccountListView(LoginRequiredMixin, UserQuerySetMixin, ListView):
    model = Account
    template_name = 'accounts/account_list.html'
    context_object_name = 'accounts'


class AccountCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Account
    form_class = AccountForm
    template_name = 'accounts/account_form.html'
    success_url = reverse_lazy('account_list')
    success_message = 'Conta criada com sucesso.'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class AccountUpdateView(
    LoginRequiredMixin, UserQuerySetMixin, SuccessMessageMixin, UpdateView
):
    model = Account
    form_class = AccountForm
    template_name = 'accounts/account_form.html'
    success_url = reverse_lazy('account_list')
    success_message = 'Conta atualizada com sucesso.'


class AccountDeleteView(LoginRequiredMixin, UserQuerySetMixin, DeleteView):
    model = Account
    template_name = 'accounts/account_confirm_delete.html'
    success_url = reverse_lazy('account_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Conta excluída com sucesso.')
        return response
