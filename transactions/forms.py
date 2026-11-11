from django import forms

from accounts.models import Account
from categories.models import Category
from core.forms import StyledFormMixin

from .models import Transaction

CATEGORY_TYPE_MISMATCH_MESSAGE = (
    'A categoria selecionada não corresponde ao tipo da transação.'
)

# Limits of DecimalField(max_digits=12, decimal_places=2). The amount is
# always positive; transaction_type gives the sign. An explicit `min` also
# gives the browser a fixed step base (see accounts/forms.py).
AMOUNT_MIN = '0.01'
AMOUNT_MAX = '9999999999.99'


class CategoryChoiceField(forms.ModelChoiceField):
    # Shows the type next to each option, e.g. 'Mercado (Saída)'. Uses the
    # category's own column, so no extra query is made per option.
    # Category.__str__ stays the plain name because it is used elsewhere.
    def label_from_instance(self, obj):
        return f'{obj.name} ({obj.get_category_type_display()})'


class TransactionForm(StyledFormMixin, forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        # `user` is keyword-only, so it never reaches ModelForm.__init__.
        self.user = user
        super().__init__(*args, **kwargs)
        # Only the user's own accounts and categories are valid choices.
        # Without a user nothing is offered, so data can never leak.
        if user is None:
            accounts = Account.objects.none()
            categories = Category.objects.none()
        else:
            accounts = Account.objects.filter(user=user)
            categories = Category.objects.filter(user=user)
        self.fields['account'].queryset = accounts
        self.fields['category'].queryset = categories
        self.fields['account'].empty_label = 'Selecione uma conta'
        self.fields['category'].empty_label = 'Selecione uma categoria'
        self.fields['amount'].widget.attrs.update(
            {'min': AMOUNT_MIN, 'max': AMOUNT_MAX, 'step': '0.01'}
        )

    class Meta:
        model = Transaction
        fields = (
            'description',
            'amount',
            'transaction_type',
            'date',
            'account',
            'category',
        )
        field_classes = {
            'category': CategoryChoiceField,
        }
        labels = {
            'description': 'Descrição',
            'amount': 'Valor',
            'transaction_type': 'Tipo',
            'date': 'Data',
            'account': 'Conta',
            'category': 'Categoria',
        }
        widgets = {
            'date': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d',
            ),
        }

    def clean(self):
        # A transaction must use a category of the same type (PRD RF21).
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        transaction_type = cleaned_data.get('transaction_type')
        if (
            category
            and transaction_type
            and category.category_type != transaction_type
        ):
            self.add_error(
                'category',
                forms.ValidationError(
                    CATEGORY_TYPE_MISMATCH_MESSAGE,
                    code='category_type_mismatch',
                ),
            )
        return cleaned_data
