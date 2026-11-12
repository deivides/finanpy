import datetime
from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Account, AccountType
from categories.models import Category, CategoryType
from core.forms import BLANK_CHOICE_LABEL, CHECKBOX_CLASS, StyledFormMixin
from transactions.models import Transaction

User = get_user_model()

PASSWORD = 'Sup3r-Segura-2026!'
NO_ACCOUNTS_MESSAGE = 'Você ainda não cadastrou nenhuma conta.'
NO_TRANSACTIONS_MESSAGE = 'Você ainda não registrou nenhuma transação.'
NO_CATEGORY_MESSAGE = (
    'Cadastre uma categoria para registrar sua primeira transação.'
)
NO_ACCOUNT_AND_CATEGORY_MESSAGE = (
    'Cadastre uma conta e uma categoria para registrar sua primeira '
    'transação.'
)


def create_user(email='maria@example.com', password=PASSWORD, **extra):
    extra.setdefault('first_name', 'Maria')
    extra.setdefault('last_name', 'Silva')
    return User.objects.create_user(email=email, password=password, **extra)


def create_account(user, name='Nubank', **extra):
    extra.setdefault('initial_balance', Decimal('0.00'))
    return Account.objects.create(user=user, name=name, **extra)


def create_category(user, name='Salário', category_type=CategoryType.INCOME):
    return Category.objects.create(
        user=user, name=name, category_type=category_type,
    )


def create_transaction(account, category, amount=Decimal('100.00'), **extra):
    extra.setdefault('description', 'Lançamento')
    extra.setdefault('transaction_type', category.category_type)
    extra.setdefault('date', timezone.localdate())
    return Transaction.objects.create(
        user=account.user,
        account=account,
        category=category,
        amount=amount,
        **extra,
    )


def month_dates():
    """Dates around the current month, safe on month and year boundaries."""
    today = timezone.localdate()
    first_day = today.replace(day=1)
    next_month = (first_day + datetime.timedelta(days=32)).replace(day=1)
    return {
        'today': today,
        'first_day': first_day,
        'last_day': next_month - datetime.timedelta(days=1),
        'previous_month': first_day - datetime.timedelta(days=1),
        'next_month': next_month,
        'last_year': first_day.replace(year=first_day.year - 1),
    }


class HomeViewTests(TestCase):
    """PRD 9.6.1: the public home is open to anonymous visitors."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('home')
        cls.user = create_user()

    def test_anonymous_get_returns_200_with_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_anonymous_sees_signup_and_login_links(self):
        response = self.client.get(self.url)
        self.assertContains(
            response,
            f'<a href="{reverse("signup")}" class="btn-primary">'
            'Cadastre-se</a>',
            html=True,
        )
        self.assertContains(
            response,
            f'<a href="{reverse("login")}" class="btn-secondary">Entrar</a>',
            html=True,
        )
        self.assertNotContains(response, 'Ir para o dashboard')

    def test_authenticated_get_returns_200_without_redirect(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_authenticated_sees_dashboard_link_instead_of_signup(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(
            response,
            f'<a href="{reverse("dashboard")}" class="btn-primary">'
            'Ir para o dashboard</a>',
            html=True,
        )
        self.assertNotContains(response, 'Cadastre-se')
        self.assertNotContains(response, f'href="{reverse("signup")}"')
        self.assertNotContains(response, f'href="{reverse("login")}"')


class DashboardAccessTests(TestCase):
    """PRD 9.6.2: the dashboard requires login."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('dashboard')
        cls.user = create_user()

    def test_anonymous_get_redirects_to_login_with_next(self):
        response = self.client.get(self.url)
        self.assertRedirects(
            response, f'{reverse("login")}?next={self.url}',
        )

    def test_anonymous_response_has_no_dashboard_content(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTemplateNotUsed(response, 'dashboard.html')

    def test_authenticated_get_returns_200_with_template(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        self.assertContains(response, 'Olá, Maria!')

    def test_login_redirects_back_to_dashboard(self):
        response = self.client.post(
            f'{reverse("login")}?next={self.url}',
            {'username': self.user.email, 'password': PASSWORD},
        )
        self.assertRedirects(response, self.url)


class DashboardTotalsTests(TestCase):
    """PRD 9.6.3: total balance and current month totals."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('dashboard')
        cls.user = create_user()
        cls.bank = create_account(
            cls.user, 'Nubank', bank_name='Nu Pagamentos',
            initial_balance=Decimal('1000.00'),
        )
        cls.wallet = create_account(
            cls.user, 'Carteira', account_type=AccountType.WALLET,
            initial_balance=Decimal('-50.00'),
        )
        salary = create_category(cls.user, 'Salário', CategoryType.INCOME)
        food = create_category(cls.user, 'Alimentação', CategoryType.EXPENSE)
        dates = month_dates()
        # Current month, including its first and last days.
        create_transaction(
            cls.bank, salary, Decimal('3000.00'), date=dates['first_day'],
        )
        create_transaction(
            cls.wallet, salary, Decimal('500.50'), date=dates['last_day'],
        )
        create_transaction(
            cls.bank, food, Decimal('1200.25'), date=dates['first_day'],
        )
        create_transaction(
            cls.wallet, food, Decimal('99.75'), date=dates['today'],
        )
        # Other months: they count for the balance, not for the month.
        create_transaction(
            cls.bank, salary, Decimal('700.00'), date=dates['previous_month'],
        )
        create_transaction(
            cls.bank, food, Decimal('40.00'), date=dates['previous_month'],
        )
        create_transaction(
            cls.bank, food, Decimal('60.00'), date=dates['next_month'],
        )
        # Same month of the previous year.
        create_transaction(
            cls.bank, salary, Decimal('900.00'), date=dates['last_year'],
        )
        create_transaction(
            cls.wallet, food, Decimal('10.00'), date=dates['last_year'],
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.response = self.client.get(self.url)

    def test_total_balance_sums_every_account_balance(self):
        # Nubank: 1000 + 3000 - 1200.25 + 700 - 40 - 60 + 900 = 4299.75
        # Carteira: -50 + 500.50 - 99.75 - 10 = 340.75
        total_balance = self.response.context['total_balance']
        self.assertEqual(total_balance, Decimal('4640.50'))
        self.assertEqual(
            total_balance, self.bank.balance + self.wallet.balance,
        )
        self.assertIsInstance(total_balance, Decimal)

    def test_month_income_only_counts_current_month(self):
        month_income = self.response.context['month_income']
        self.assertEqual(month_income, Decimal('3500.50'))
        self.assertIsInstance(month_income, Decimal)

    def test_month_expense_only_counts_current_month(self):
        month_expense = self.response.context['month_expense']
        self.assertEqual(month_expense, Decimal('1300.00'))
        self.assertIsInstance(month_expense, Decimal)

    def test_month_result_is_income_minus_expense(self):
        self.assertEqual(
            self.response.context['month_result'], Decimal('2200.50'),
        )

    def test_today_is_in_context(self):
        self.assertEqual(self.response.context['today'], timezone.localdate())

    def test_accounts_are_listed_by_name_with_current_balance(self):
        accounts = self.response.context['accounts']
        self.assertEqual(accounts, [self.wallet, self.bank])
        self.assertEqual(
            [account.current_balance for account in accounts],
            [Decimal('340.75'), Decimal('4299.75')],
        )

    def test_totals_are_rendered_in_brazilian_format(self):
        self.assertContains(self.response, 'R$ 4.640,50')
        self.assertContains(self.response, '+R$ 3.500,50')
        self.assertContains(self.response, '−R$ 1.300,00')
        self.assertContains(self.response, '+R$ 2.200,50')

    def test_accounts_are_rendered_with_balance(self):
        self.assertContains(self.response, 'Nu Pagamentos')
        self.assertContains(self.response, 'R$ 4.299,75')
        self.assertContains(self.response, 'R$ 340,75')
        self.assertContains(self.response, 'Gerenciar contas')
        self.assertNotContains(self.response, NO_ACCOUNTS_MESSAGE)


class DashboardNegativeResultTests(TestCase):
    """PRD 9.6.3: expenses above income give negative values."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        account = create_account(cls.user, initial_balance=Decimal('100.00'))
        salary = create_category(cls.user, 'Salário', CategoryType.INCOME)
        food = create_category(cls.user, 'Alimentação', CategoryType.EXPENSE)
        create_transaction(account, salary, Decimal('200.00'))
        create_transaction(account, food, Decimal('550.40'))

    def setUp(self):
        self.client.force_login(self.user)
        self.response = self.client.get(reverse('dashboard'))

    def test_month_result_is_negative(self):
        context = self.response.context
        self.assertEqual(context['month_income'], Decimal('200.00'))
        self.assertEqual(context['month_expense'], Decimal('550.40'))
        self.assertEqual(context['month_result'], Decimal('-350.40'))

    def test_total_balance_is_negative(self):
        self.assertEqual(
            self.response.context['total_balance'], Decimal('-250.40'),
        )

    def test_negative_values_are_rendered_with_minus_sign(self):
        self.assertContains(self.response, '−R$ 350,40')
        self.assertContains(self.response, '−R$ 250,40')
        self.assertNotContains(self.response, '-350')
        self.assertNotContains(self.response, '-250')


class DashboardRecentTransactionsTests(TestCase):
    """PRD 9.6.3: the dashboard shows the 5 latest transactions."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        account = create_account(cls.user)
        food = create_category(cls.user, 'Alimentação', CategoryType.EXPENSE)
        today = timezone.localdate()
        # Created from the oldest to the newest, so the expected order is
        # not the insertion order.
        cls.transactions = [
            create_transaction(
                account, food, Decimal('10.00'),
                description=f'Compra de {days} dias atrás',
                date=today - datetime.timedelta(days=days),
            )
            for days in range(6, -1, -1)
        ]
        cls.transactions.reverse()

    def setUp(self):
        self.client.force_login(self.user)
        self.response = self.client.get(reverse('dashboard'))

    def test_lists_only_five_transactions_newest_first(self):
        self.assertQuerySetEqual(
            self.response.context['recent_transactions'],
            self.transactions[:5],
        )

    def test_older_transactions_are_not_rendered(self):
        self.assertContains(self.response, 'Compra de 0 dias atrás')
        self.assertContains(self.response, 'Compra de 4 dias atrás')
        self.assertNotContains(self.response, 'Compra de 5 dias atrás')
        self.assertNotContains(self.response, 'Compra de 6 dias atrás')

    def test_renders_link_to_all_transactions(self):
        self.assertContains(self.response, 'Ver todas as transações')
        self.assertNotContains(self.response, NO_TRANSACTIONS_MESSAGE)


class DashboardEmptyStateTests(TestCase):
    """PRD 9.6.3: a user without data sees zeros and the empty states."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('dashboard')
        cls.user = create_user()

    def setUp(self):
        self.client.force_login(self.user)

    def test_totals_are_decimal_zero(self):
        response = self.client.get(self.url)
        for key in (
            'total_balance', 'month_income', 'month_expense', 'month_result',
        ):
            with self.subTest(key=key):
                self.assertEqual(response.context[key], Decimal('0'))
                self.assertIsInstance(response.context[key], Decimal)

    def test_lists_are_empty(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context['accounts'], [])
        self.assertQuerySetEqual(response.context['recent_transactions'], [])

    def test_zero_values_are_rendered_without_sign(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'R$ 0,00', count=4)
        self.assertNotContains(response, '+R$')
        self.assertNotContains(response, '−R$')

    def test_empty_states_without_accounts(self):
        response = self.client.get(self.url)
        self.assertContains(response, NO_ACCOUNTS_MESSAGE)
        self.assertContains(response, NO_ACCOUNT_AND_CATEGORY_MESSAGE)
        self.assertNotContains(response, 'Gerenciar contas')
        self.assertNotContains(response, 'Ver todas as transações')

    def test_empty_state_with_account_and_no_category(self):
        create_account(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, NO_CATEGORY_MESSAGE)
        self.assertNotContains(response, NO_ACCOUNTS_MESSAGE)

    def test_empty_state_with_account_and_category(self):
        create_account(self.user, initial_balance=Decimal('75.00'))
        create_category(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, NO_TRANSACTIONS_MESSAGE)
        self.assertEqual(response.context['total_balance'], Decimal('75.00'))
        self.assertEqual(response.context['month_income'], Decimal('0'))


class DashboardIsolationTests(TestCase):
    """PRD 9.6.3: the dashboard only uses the logged-in user's data."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('dashboard')
        cls.user = create_user()
        cls.other_user = create_user(
            email='joao@example.com', first_name='João',
        )
        cls.newcomer = create_user(email='ana@example.com', first_name='Ana')
        cls.account = create_account(
            cls.user, 'Conta da Maria', initial_balance=Decimal('100.00'),
        )
        salary = create_category(cls.user, 'Salário', CategoryType.INCOME)
        food = create_category(cls.user, 'Alimentação', CategoryType.EXPENSE)
        cls.income = create_transaction(
            cls.account, salary, Decimal('1000.00'),
            description='Salário da Maria',
        )
        cls.expense = create_transaction(
            cls.account, food, Decimal('150.00'),
            description='Mercado da Maria',
        )
        cls.foreign_account = create_account(
            cls.other_user, 'Conta Secreta do João',
            bank_name='Banco Estrangeiro',
            initial_balance=Decimal('9999.00'),
        )
        foreign_salary = create_category(
            cls.other_user, 'Renda do João', CategoryType.INCOME,
        )
        foreign_food = create_category(
            cls.other_user, 'Gasto do João', CategoryType.EXPENSE,
        )
        cls.foreign_income = create_transaction(
            cls.foreign_account, foreign_salary, Decimal('7777.00'),
            description='Receita Secreta do João',
        )
        cls.foreign_expense = create_transaction(
            cls.foreign_account, foreign_food, Decimal('333.00'),
            description='Despesa Secreta do João',
        )

    def test_totals_only_count_own_data(self):
        self.client.force_login(self.user)
        context = self.client.get(self.url).context
        self.assertEqual(context['total_balance'], Decimal('950.00'))
        self.assertEqual(context['month_income'], Decimal('1000.00'))
        self.assertEqual(context['month_expense'], Decimal('150.00'))
        self.assertEqual(context['month_result'], Decimal('850.00'))

    def test_lists_only_have_own_data(self):
        self.client.force_login(self.user)
        context = self.client.get(self.url).context
        self.assertEqual(context['accounts'], [self.account])
        self.assertQuerySetEqual(
            context['recent_transactions'], [self.income, self.expense],
            ordered=False,
        )

    def test_other_users_data_is_not_rendered(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, 'Conta da Maria')
        self.assertContains(response, 'Salário da Maria')
        for text in (
            'Conta Secreta do João', 'Banco Estrangeiro',
            'Receita Secreta do João', 'Despesa Secreta do João',
            'Renda do João', 'Gasto do João', '7.777,00', '333,00',
        ):
            with self.subTest(text=text):
                self.assertNotContains(response, text)

    def test_other_user_sees_only_own_data(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.url)
        context = response.context
        self.assertEqual(context['accounts'], [self.foreign_account])
        self.assertEqual(context['total_balance'], Decimal('17443.00'))
        self.assertEqual(context['month_income'], Decimal('7777.00'))
        self.assertEqual(context['month_expense'], Decimal('333.00'))
        self.assertQuerySetEqual(
            context['recent_transactions'],
            [self.foreign_income, self.foreign_expense],
            ordered=False,
        )
        self.assertNotContains(response, 'Conta da Maria')
        self.assertNotContains(response, 'Salário da Maria')

    def test_user_without_data_sees_zeros_despite_other_users_data(self):
        self.client.force_login(self.newcomer)
        response = self.client.get(self.url)
        context = response.context
        self.assertEqual(context['accounts'], [])
        self.assertQuerySetEqual(context['recent_transactions'], [])
        self.assertEqual(context['total_balance'], Decimal('0'))
        self.assertEqual(context['month_income'], Decimal('0'))
        self.assertEqual(context['month_expense'], Decimal('0'))
        self.assertEqual(context['month_result'], Decimal('0'))
        self.assertContains(response, NO_ACCOUNTS_MESSAGE)
        self.assertNotContains(response, 'Conta da Maria')
        self.assertNotContains(response, 'Conta Secreta do João')


class StyledFormMixinTests(SimpleTestCase):
    """StyledFormMixin applies the design system classes (PRD 9.6)."""

    class SampleForm(StyledFormMixin, forms.Form):
        name = forms.CharField(
            widget=forms.TextInput(attrs={'class': 'w-full form-input'}),
        )
        is_active = forms.BooleanField(required=False)
        due_date = forms.DateField()
        custom_date = forms.DateField(
            widget=forms.DateInput(format='%d/%m/%Y'),
        )
        kind = forms.ChoiceField(
            choices=[('', '---------'), ('a', 'Opção A')], required=False,
        )
        fixed_kind = forms.ChoiceField(choices=[('a', 'Opção A')])

    def setUp(self):
        self.form = self.SampleForm()

    def widget_classes(self, name):
        return self.form.fields[name].widget.attrs['class'].split()

    def test_checkbox_gets_checkbox_class_instead_of_input_class(self):
        self.assertEqual(
            self.widget_classes('is_active'), CHECKBOX_CLASS.split(),
        )

    def test_existing_classes_are_kept_and_not_duplicated(self):
        self.assertEqual(self.widget_classes('name'), ['w-full', 'form-input'])

    def test_date_input_without_format_renders_as_html5_iso_date(self):
        widget = self.form.fields['due_date'].widget
        self.assertEqual(widget.input_type, 'date')
        self.assertEqual(
            widget.format_value(datetime.date(2026, 3, 5)), '2026-03-05',
        )

    def test_date_input_keeps_explicit_format(self):
        widget = self.form.fields['custom_date'].widget
        self.assertEqual(widget.input_type, 'date')
        self.assertEqual(widget.format, '%d/%m/%Y')

    def test_blank_choice_label_is_translated(self):
        self.assertEqual(
            list(self.form.fields['kind'].choices),
            [('', BLANK_CHOICE_LABEL), ('a', 'Opção A')],
        )

    def test_choices_without_blank_option_are_untouched(self):
        self.assertEqual(
            list(self.form.fields['fixed_kind'].choices), [('a', 'Opção A')],
        )
