from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce

from transactions.models import TransactionType


class AccountType(models.TextChoices):
    CHECKING = 'checking', 'Conta corrente'
    SAVINGS = 'savings', 'Poupança'
    WALLET = 'wallet', 'Carteira'
    INVESTMENT = 'investment', 'Investimento'


class Account(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='accounts',
        verbose_name='usuário',
    )
    name = models.CharField('nome', max_length=100)
    bank_name = models.CharField('banco', max_length=100, blank=True)
    account_type = models.CharField(
        'tipo',
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.CHECKING,
    )
    initial_balance = models.DecimalField(
        'saldo inicial',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'conta'
        verbose_name_plural = 'contas'

    def __str__(self):
        return self.name

    @property
    def balance(self):
        """Current balance: initial balance + income - expenses."""
        money = DecimalField(max_digits=12, decimal_places=2)
        zero = Value(Decimal('0'), output_field=money)
        totals = self.transactions.aggregate(
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
        return self.initial_balance + totals['income'] - totals['expense']
