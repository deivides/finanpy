from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.views.generic import TemplateView

from accounts.models import Account
from transactions.models import Transaction, TransactionType


class UserQuerySetMixin:
    """Restrict the view queryset to objects owned by the logged-in user.

    Use it in List/Detail/Update/Delete views of models with a `user` FK,
    always combined with `LoginRequiredMixin` placed before it in the MRO:
    `class AccountListView(LoginRequiredMixin, UserQuerySetMixin, ListView)`.
    Objects of other users fall outside the queryset, so they return 404.
    """

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class UserFormKwargsMixin:
    """Pass the logged-in user to the form as the `user` keyword argument.

    Required by forms that validate or filter data per user: the category
    create/update views (`CategoryForm` duplicate check) and the
    transaction create/update views (account/category querysets).
    """

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class HomeView(TemplateView):
    template_name = 'home.html'


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()

        # Account.balance runs one aggregate query per account, so compute
        # it once here and keep it on the instance for the template.
        accounts = list(Account.objects.filter(user=user))
        total_balance = Decimal('0')
        for account in accounts:
            account.current_balance = account.balance
            total_balance += account.current_balance

        transactions = Transaction.objects.filter(user=user)

        money = DecimalField(max_digits=12, decimal_places=2)
        zero = Value(Decimal('0'), output_field=money)
        totals = transactions.filter(
            date__year=today.year,
            date__month=today.month,
        ).aggregate(
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

        context['today'] = today
        context['accounts'] = accounts
        context['total_balance'] = total_balance
        context['month_income'] = totals['income']
        context['month_expense'] = totals['expense']
        context['month_result'] = totals['income'] - totals['expense']
        context['recent_transactions'] = transactions.select_related(
            'account', 'category'
        )[:5]
        return context
