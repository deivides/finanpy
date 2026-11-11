from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import RestrictedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.views import UserFormKwargsMixin, UserQuerySetMixin

from .forms import CategoryForm
from .models import Category, CategoryType


class CategoryListView(LoginRequiredMixin, UserQuerySetMixin, ListView):
    model = Category
    template_name = 'categories/category_list.html'
    context_object_name = 'categories'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = self.get_queryset()
        context['income_categories'] = categories.filter(
            category_type=CategoryType.INCOME
        )
        context['expense_categories'] = categories.filter(
            category_type=CategoryType.EXPENSE
        )
        return context


class CategoryCreateView(
    LoginRequiredMixin, UserFormKwargsMixin, SuccessMessageMixin, CreateView
):
    model = Category
    form_class = CategoryForm
    template_name = 'categories/category_form.html'
    success_url = reverse_lazy('category_list')
    success_message = 'Categoria criada com sucesso.'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class CategoryUpdateView(
    LoginRequiredMixin,
    UserQuerySetMixin,
    UserFormKwargsMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = Category
    form_class = CategoryForm
    template_name = 'categories/category_form.html'
    success_url = reverse_lazy('category_list')
    success_message = 'Categoria atualizada com sucesso.'


class CategoryDeleteView(LoginRequiredMixin, UserQuerySetMixin, DeleteView):
    model = Category
    template_name = 'categories/category_confirm_delete.html'
    success_url = reverse_lazy('category_list')

    def form_valid(self, form):
        # Transaction.category uses on_delete=RESTRICT, so a category that is
        # still referenced by transactions raises RestrictedError on delete
        # (unless the transactions are deleted in the same operation, e.g.
        # when the whole user is deleted).
        try:
            response = super().form_valid(form)
        except RestrictedError:
            messages.error(
                self.request,
                'Esta categoria possui transações e não pode ser excluída.',
            )
            return redirect('category_list')
        messages.success(self.request, 'Categoria excluída com sucesso.')
        return response
