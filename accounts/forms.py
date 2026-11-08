from django import forms

from core.forms import StyledFormMixin

from .models import Account

# Limits of DecimalField(max_digits=12, decimal_places=2). Negative values
# are allowed (overdraft). An explicit `min` gives the browser a fixed step
# base; without it the `value` attribute is used, so a re-rendered invalid
# value such as 10.123 would shift the accepted steps.
BALANCE_MIN = '-9999999999.99'
BALANCE_MAX = '9999999999.99'


class AccountForm(StyledFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['initial_balance'].widget.attrs.update(
            {'min': BALANCE_MIN, 'max': BALANCE_MAX, 'step': '0.01'}
        )

    class Meta:
        model = Account
        fields = ('name', 'bank_name', 'account_type', 'initial_balance')
        labels = {
            'name': 'Nome',
            'bank_name': 'Banco',
            'account_type': 'Tipo',
            'initial_balance': 'Saldo inicial',
        }
        help_texts = {
            'initial_balance': 'Saldo da conta no momento do cadastro.',
        }
