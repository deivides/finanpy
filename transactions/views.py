from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.views import UserFormKwargsMixin, UserQuerySetMixin

from .forms import TransactionForm
from .models import Transaction, TransactionType


class TransactionListView(LoginRequiredMixin, UserQuerySetMixin, ListView):
    model = Transaction
    template_name = 'transactions/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        # Parse the filters once so get_queryset() and get_context_data()
        # always agree. Invalid values are ignored (no filter, no error).
        self.current_month = ''
        self.filter_year = None
        self.filter_month = None
        month = request.GET.get('month', '').strip()
        if month:
            try:
                parsed = datetime.strptime(month, '%Y-%m')
            except ValueError:
                pass
            else:
                self.filter_year = parsed.year
                self.filter_month = parsed.month
                # Normalized 'YYYY-MM', ready for <input type="month">.
                self.current_month = f'{parsed.year:04d}-{parsed.month:02d}'
        transaction_type = request.GET.get('type', '').strip()
        if transaction_type in TransactionType.values:
            self.current_type = transaction_type
        else:
            self.current_type = ''

    def get_queryset(self):
        queryset = super().get_queryset().select_related('account', 'category')
        if self.filter_year is not None:
            queryset = queryset.filter(
                date__year=self.filter_year,
                date__month=self.filter_month,
            )
        if self.current_type:
            queryset = queryset.filter(transaction_type=self.current_type)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Totals cover the whole filtered queryset, not only the current
        # page (self.object_list is set by ListView.get() before paging).
        money = DecimalField(max_digits=12, decimal_places=2)
        zero = Value(Decimal('0'), output_field=money)
        totals = self.object_list.aggregate(
            income=Coalesce(
                Sum(
                    'amount',
                    filter=Q(transaction_type=TransactionType.INCOME),
                ),
                zero,
                output_field=money,
            ),
            expense=Coalesce(
                Sum(
                    'amount',
                    filter=Q(transaction_type=TransactionType.EXPENSE),
                ),
                zero,
                output_field=money,
            ),
        )
        context['total_income'] = totals['income']
        context['total_expense'] = totals['expense']
        context['current_month'] = self.current_month
        context['current_type'] = self.current_type
        context['type_choices'] = TransactionType.choices
        return context


class TransactionCreateView(
    LoginRequiredMixin, UserFormKwargsMixin, SuccessMessageMixin, CreateView
):
    model = Transaction
    form_class = TransactionForm
    template_name = 'transactions/transaction_form.html'
    success_url = reverse_lazy('transaction_list')
    success_message = 'Transação criada com sucesso.'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class TransactionUpdateView(
    LoginRequiredMixin,
    UserQuerySetMixin,
    UserFormKwargsMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = Transaction
    form_class = TransactionForm
    template_name = 'transactions/transaction_form.html'
    success_url = reverse_lazy('transaction_list')
    success_message = 'Transação atualizada com sucesso.'


class TransactionDeleteView(LoginRequiredMixin, UserQuerySetMixin, DeleteView):
    model = Transaction
    template_name = 'transactions/transaction_confirm_delete.html'
    success_url = reverse_lazy('transaction_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Transação excluída com sucesso.')
        return response
