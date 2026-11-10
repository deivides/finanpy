from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class TransactionType(models.TextChoices):
    INCOME = 'income', 'Entrada'
    EXPENSE = 'expense', 'Saída'


class Transaction(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='usuário',
    )
    account = models.ForeignKey(
        'accounts.Account',
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='conta',
    )
    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name='categoria',
    )
    description = models.CharField('descrição', max_length=200)
    amount = models.DecimalField(
        'valor',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    transaction_type = models.CharField(
        'tipo',
        max_length=10,
        choices=TransactionType.choices,
    )
    date = models.DateField('data', default=timezone.localdate)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'transação'
        verbose_name_plural = 'transações'

    def __str__(self):
        return f'{self.description} - {self.amount}'
