import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Account
from categories.models import Category, CategoryType
from transactions.forms import TransactionForm
from transactions.models import Transaction, TransactionType

User = get_user_model()

PASSWORD = 'Sup3r-Segura-2026!'
CREATED_MESSAGE = 'Transação criada com sucesso.'
UPDATED_MESSAGE = 'Transação atualizada com sucesso.'
DELETED_MESSAGE = 'Transação excluída com sucesso.'
CATEGORY_TYPE_MISMATCH_MESSAGE = (
    'A categoria selecionada não corresponde ao tipo da transação.'
)
EMPTY_LIST_MESSAGE = 'Você ainda não registrou nenhuma transação.'
EMPTY_FILTER_MESSAGE = (
    'Nenhuma transação encontrada para os filtros selecionados.'
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


def transaction_data(account, category, **overrides):
    data = {
        'description': 'Compra no mercado',
        'amount': '59.90',
        'transaction_type': category.category_type,
        'date': '2026-03-15',
        'account': account.pk,
        'category': category.pk,
    }
    data.update(overrides)
    return data


def message_texts(response):
    return [m.message for m in get_messages(response.wsgi_request)]


class TransactionAmountValidationTests(TestCase):
    """PRD 9.5.1: the form rejects an amount lower than or equal to zero."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('transaction_create')
        cls.user = create_user()
        cls.account = create_account(cls.user)
        cls.category = create_category(
            cls.user, 'Alimentação', CategoryType.EXPENSE,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def build_form(self, amount):
        return TransactionForm(
            data=transaction_data(self.account, self.category, amount=amount),
            user=self.user,
        )

    def test_zero_amount_is_rejected(self):
        form = self.build_form('0')
        self.assertFalse(form.is_valid())
        self.assertTrue(form.has_error('amount', code='min_value'))

    def test_negative_amount_is_rejected(self):
        form = self.build_form('-10.00')
        self.assertFalse(form.is_valid())
        self.assertTrue(form.has_error('amount', code='min_value'))

    def test_amount_error_is_only_on_amount_field(self):
        form = self.build_form('0')
        self.assertEqual(list(form.errors), ['amount'])

    def test_minimum_amount_is_accepted(self):
        form = self.build_form('0.01')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['amount'], Decimal('0.01'))

    def test_missing_amount_is_rejected(self):
        form = self.build_form('')
        self.assertTrue(form.has_error('amount', code='required'))

    def test_create_view_does_not_save_zero_amount(self):
        response = self.client.post(
            self.url,
            transaction_data(self.account, self.category, amount='0'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transactions/transaction_form.html')
        self.assertIn('amount', response.context['form'].errors)
        self.assertFalse(Transaction.objects.exists())
        self.assertEqual(message_texts(response), [])

    def test_create_view_does_not_save_negative_amount(self):
        response = self.client.post(
            self.url,
            transaction_data(self.account, self.category, amount='-0.01'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('amount', response.context['form'].errors)
        self.assertFalse(Transaction.objects.exists())

    def test_create_view_saves_minimum_amount(self):
        response = self.client.post(
            self.url,
            transaction_data(self.account, self.category, amount='0.01'),
        )
        self.assertRedirects(response, reverse('transaction_list'))
        self.assertEqual(Transaction.objects.get().amount, Decimal('0.01'))

    def test_update_view_does_not_save_zero_amount(self):
        transaction = create_transaction(
            self.account, self.category, Decimal('25.00'),
        )
        response = self.client.post(
            reverse('transaction_update', args=[transaction.pk]),
            transaction_data(self.account, self.category, amount='0'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('amount', response.context['form'].errors)
        transaction.refresh_from_db()
        self.assertEqual(transaction.amount, Decimal('25.00'))


class TransactionCategoryTypeTests(TestCase):
    """PRD 9.5.2: the category type must match the transaction type."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('transaction_create')
        cls.user = create_user()
        cls.account = create_account(cls.user)
        cls.salary = create_category(cls.user, 'Salário', CategoryType.INCOME)
        cls.food = create_category(
            cls.user, 'Alimentação', CategoryType.EXPENSE,
        )
        cls.transaction = create_transaction(
            cls.account, cls.food, Decimal('40.00'), description='Feira',
        )
        cls.update_url = reverse(
            'transaction_update', args=[cls.transaction.pk],
        )

    def setUp(self):
        self.client.force_login(self.user)

    def build_form(self, category, transaction_type):
        return TransactionForm(
            data=transaction_data(
                self.account, category, transaction_type=transaction_type,
            ),
            user=self.user,
        )

    def test_income_with_expense_category_is_rejected(self):
        form = self.build_form(self.food, TransactionType.INCOME)
        self.assertFalse(form.is_valid())
        self.assertFormError(form, 'category', CATEGORY_TYPE_MISMATCH_MESSAGE)

    def test_expense_with_income_category_is_rejected(self):
        form = self.build_form(self.salary, TransactionType.EXPENSE)
        self.assertFalse(form.is_valid())
        self.assertFormError(form, 'category', CATEGORY_TYPE_MISMATCH_MESSAGE)

    def test_mismatch_error_has_code_and_no_non_field_error(self):
        form = self.build_form(self.food, TransactionType.INCOME)
        self.assertTrue(
            form.has_error('category', code='category_type_mismatch'),
        )
        self.assertEqual(form.non_field_errors(), [])

    def test_income_with_income_category_is_valid(self):
        form = self.build_form(self.salary, TransactionType.INCOME)
        self.assertTrue(form.is_valid(), form.errors)

    def test_expense_with_expense_category_is_valid(self):
        form = self.build_form(self.food, TransactionType.EXPENSE)
        self.assertTrue(form.is_valid(), form.errors)

    def test_create_view_rejects_mismatch(self):
        response = self.client.post(
            self.url,
            transaction_data(
                self.account, self.food,
                transaction_type=TransactionType.INCOME,
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], 'category',
            CATEGORY_TYPE_MISMATCH_MESSAGE,
        )
        self.assertContains(response, CATEGORY_TYPE_MISMATCH_MESSAGE)
        self.assertQuerySetEqual(Transaction.objects.all(), [self.transaction])
        self.assertEqual(message_texts(response), [])

    def test_create_view_accepts_matching_category(self):
        response = self.client.post(
            self.url, transaction_data(self.account, self.salary),
        )
        self.assertRedirects(response, reverse('transaction_list'))
        created = Transaction.objects.exclude(pk=self.transaction.pk).get()
        self.assertEqual(created.category, self.salary)
        self.assertEqual(created.transaction_type, TransactionType.INCOME)

    def test_update_view_rejects_type_change_without_category_change(self):
        response = self.client.post(
            self.update_url,
            transaction_data(
                self.account, self.food,
                transaction_type=TransactionType.INCOME,
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], 'category',
            CATEGORY_TYPE_MISMATCH_MESSAGE,
        )
        self.transaction.refresh_from_db()
        self.assertEqual(
            self.transaction.transaction_type, TransactionType.EXPENSE,
        )
        self.assertEqual(self.transaction.description, 'Feira')

    def test_update_view_rejects_category_of_other_type(self):
        response = self.client.post(
            self.update_url,
            transaction_data(
                self.account, self.salary,
                transaction_type=TransactionType.EXPENSE,
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], 'category',
            CATEGORY_TYPE_MISMATCH_MESSAGE,
        )
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.category, self.food)

    def test_update_view_accepts_changing_type_and_category_together(self):
        response = self.client.post(
            self.update_url, transaction_data(self.account, self.salary),
        )
        self.assertRedirects(response, reverse('transaction_list'))
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.category, self.salary)
        self.assertEqual(
            self.transaction.transaction_type, TransactionType.INCOME,
        )


class TransactionFormChoicesTests(TestCase):
    """PRD 9.5.3: the form only offers the user's accounts and categories."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('transaction_create')
        cls.user = create_user()
        cls.other_user = create_user(email='joao@example.com')
        cls.account = create_account(cls.user, 'Nubank')
        cls.wallet = create_account(cls.user, 'Carteira')
        cls.salary = create_category(cls.user, 'Salário', CategoryType.INCOME)
        cls.food = create_category(
            cls.user, 'Alimentação', CategoryType.EXPENSE,
        )
        cls.foreign_account = create_account(
            cls.other_user, 'Conta Secreta do João',
        )
        cls.foreign_category = create_category(
            cls.other_user, 'Gasto Secreto do João', CategoryType.EXPENSE,
        )
        cls.transaction = create_transaction(
            cls.account, cls.food, Decimal('40.00'), description='Feira',
        )
        cls.update_url = reverse(
            'transaction_update', args=[cls.transaction.pk],
        )

    def setUp(self):
        self.client.force_login(self.user)

    def assert_transaction_unchanged(self):
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.account, self.account)
        self.assertEqual(self.transaction.category, self.food)
        self.assertEqual(self.transaction.description, 'Feira')

    def test_form_fields_do_not_expose_user(self):
        self.assertEqual(
            list(TransactionForm(user=self.user).fields),
            [
                'description', 'amount', 'transaction_type', 'date',
                'account', 'category',
            ],
        )

    def test_account_queryset_has_only_own_accounts(self):
        form = TransactionForm(user=self.user)
        self.assertQuerySetEqual(
            form.fields['account'].queryset, [self.wallet, self.account],
        )

    def test_category_queryset_has_only_own_categories(self):
        form = TransactionForm(user=self.user)
        self.assertQuerySetEqual(
            form.fields['category'].queryset, [self.food, self.salary],
        )

    def test_querysets_follow_the_given_user(self):
        form = TransactionForm(user=self.other_user)
        self.assertQuerySetEqual(
            form.fields['account'].queryset, [self.foreign_account],
        )
        self.assertQuerySetEqual(
            form.fields['category'].queryset, [self.foreign_category],
        )

    def test_querysets_are_empty_without_user(self):
        form = TransactionForm()
        self.assertQuerySetEqual(form.fields['account'].queryset, [])
        self.assertQuerySetEqual(form.fields['category'].queryset, [])

    def test_category_label_shows_type(self):
        form = TransactionForm(user=self.user)
        labels = [label for _, label in form.fields['category'].choices]
        self.assertEqual(
            labels,
            [
                'Selecione uma categoria',
                'Alimentação (Saída)',
                'Salário (Entrada)',
            ],
        )

    def test_form_rejects_other_users_account(self):
        form = TransactionForm(
            data=transaction_data(self.foreign_account, self.food),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertTrue(form.has_error('account', code='invalid_choice'))

    def test_form_rejects_other_users_category(self):
        form = TransactionForm(
            data=transaction_data(self.account, self.foreign_category),
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertTrue(form.has_error('category', code='invalid_choice'))

    def test_create_view_renders_only_own_choices(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertQuerySetEqual(
            form.fields['account'].queryset, [self.wallet, self.account],
        )
        self.assertQuerySetEqual(
            form.fields['category'].queryset, [self.food, self.salary],
        )
        self.assertContains(response, 'Nubank')
        self.assertContains(response, 'Alimentação (Saída)')
        self.assertNotContains(response, 'Conta Secreta do João')
        self.assertNotContains(response, 'Gasto Secreto do João')

    def test_update_view_renders_only_own_choices(self):
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertQuerySetEqual(
            form.fields['account'].queryset, [self.wallet, self.account],
        )
        self.assertQuerySetEqual(
            form.fields['category'].queryset, [self.food, self.salary],
        )
        self.assertNotContains(response, 'Conta Secreta do João')
        self.assertNotContains(response, 'Gasto Secreto do João')

    def test_create_view_rejects_other_users_account(self):
        response = self.client.post(
            self.url, transaction_data(self.foreign_account, self.food),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('account', response.context['form'].errors)
        self.assertQuerySetEqual(Transaction.objects.all(), [self.transaction])
        self.assertEqual(message_texts(response), [])

    def test_create_view_rejects_other_users_category(self):
        response = self.client.post(
            self.url, transaction_data(self.account, self.foreign_category),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('category', response.context['form'].errors)
        self.assertQuerySetEqual(Transaction.objects.all(), [self.transaction])

    def test_update_view_rejects_other_users_account(self):
        response = self.client.post(
            self.update_url,
            transaction_data(self.foreign_account, self.food),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('account', response.context['form'].errors)
        self.assert_transaction_unchanged()

    def test_update_view_rejects_other_users_category(self):
        response = self.client.post(
            self.update_url,
            transaction_data(self.account, self.foreign_category),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('category', response.context['form'].errors)
        self.assert_transaction_unchanged()

    def test_user_without_accounts_and_categories_sees_prerequisites(self):
        newcomer = create_user(email='ana@example.com')
        self.client.force_login(newcomer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'Para registrar uma transação, você precisa de pelo menos uma '
            'conta e uma categoria.',
        )
        self.assertNotContains(response, 'Nubank')


class TransactionListFilterTests(TestCase):
    """PRD 9.5.4: month and type filters of the transaction list."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('transaction_list')
        cls.user = create_user()
        account = create_account(cls.user)
        salary = create_category(cls.user, 'Salário', CategoryType.INCOME)
        food = create_category(cls.user, 'Alimentação', CategoryType.EXPENSE)
        cls.jan_income = create_transaction(
            account, salary, Decimal('3000.00'),
            description='Salário de janeiro', date=datetime.date(2026, 1, 5),
        )
        cls.jan_expense = create_transaction(
            account, food, Decimal('120.50'),
            description='Mercado de janeiro', date=datetime.date(2026, 1, 10),
        )
        cls.jan_last_day = create_transaction(
            account, food, Decimal('79.50'),
            description='Jantar de janeiro', date=datetime.date(2026, 1, 31),
        )
        cls.feb_income = create_transaction(
            account, salary, Decimal('500.00'),
            description='Bônus de fevereiro', date=datetime.date(2026, 2, 1),
        )
        cls.feb_expense = create_transaction(
            account, food, Decimal('45.25'),
            description='Feira de fevereiro', date=datetime.date(2026, 2, 14),
        )
        cls.last_year = create_transaction(
            account, food, Decimal('10.00'),
            description='Lanche de 2025', date=datetime.date(2025, 1, 20),
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_without_filters_lists_everything_newest_first(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transactions/transaction_list.html')
        self.assertQuerySetEqual(
            response.context['transactions'],
            [
                self.feb_expense, self.feb_income, self.jan_last_day,
                self.jan_expense, self.jan_income, self.last_year,
            ],
        )
        self.assertEqual(response.context['current_month'], '')
        self.assertEqual(response.context['current_type'], '')
        self.assertEqual(response.context['total_income'], Decimal('3500.00'))
        self.assertEqual(response.context['total_expense'], Decimal('255.25'))

    def test_month_filter_returns_only_that_month(self):
        response = self.client.get(self.url, {'month': '2026-01'})
        self.assertQuerySetEqual(
            response.context['transactions'],
            [self.jan_last_day, self.jan_expense, self.jan_income],
        )
        self.assertNotContains(response, 'Bônus de fevereiro')
        self.assertNotContains(response, 'Lanche de 2025')

    def test_month_filter_context_and_totals(self):
        response = self.client.get(self.url, {'month': '2026-01'})
        self.assertEqual(response.context['current_month'], '2026-01')
        self.assertEqual(response.context['current_type'], '')
        self.assertEqual(response.context['total_income'], Decimal('3000.00'))
        self.assertEqual(response.context['total_expense'], Decimal('200.00'))
        self.assertContains(response, 'value="2026-01"')
        self.assertContains(response, '+R$ 3.000,00')
        self.assertContains(response, '−R$ 200,00')

    def test_month_filter_distinguishes_years(self):
        response = self.client.get(self.url, {'month': '2025-01'})
        self.assertQuerySetEqual(
            response.context['transactions'], [self.last_year],
        )
        self.assertEqual(response.context['total_income'], Decimal('0'))
        self.assertEqual(response.context['total_expense'], Decimal('10.00'))

    def test_type_filter_income(self):
        response = self.client.get(self.url, {'type': 'income'})
        self.assertQuerySetEqual(
            response.context['transactions'],
            [self.feb_income, self.jan_income],
        )
        self.assertEqual(response.context['current_type'], 'income')
        self.assertEqual(response.context['current_month'], '')
        self.assertEqual(response.context['total_income'], Decimal('3500.00'))
        self.assertEqual(response.context['total_expense'], Decimal('0'))
        self.assertContains(response, '<option value="income" selected>')

    def test_type_filter_expense(self):
        response = self.client.get(self.url, {'type': 'expense'})
        self.assertQuerySetEqual(
            response.context['transactions'],
            [
                self.feb_expense, self.jan_last_day, self.jan_expense,
                self.last_year,
            ],
        )
        self.assertEqual(response.context['current_type'], 'expense')
        self.assertEqual(response.context['total_income'], Decimal('0'))
        self.assertEqual(response.context['total_expense'], Decimal('255.25'))

    def test_month_and_type_filters_combined(self):
        response = self.client.get(
            self.url, {'month': '2026-01', 'type': 'expense'},
        )
        self.assertQuerySetEqual(
            response.context['transactions'],
            [self.jan_last_day, self.jan_expense],
        )
        self.assertEqual(response.context['current_month'], '2026-01')
        self.assertEqual(response.context['current_type'], 'expense')
        self.assertEqual(response.context['total_income'], Decimal('0'))
        self.assertEqual(response.context['total_expense'], Decimal('200.00'))

    def test_filter_without_results_shows_filtered_empty_state(self):
        response = self.client.get(self.url, {'month': '2024-06'})
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['transactions'], [])
        self.assertEqual(response.context['current_month'], '2024-06')
        self.assertEqual(response.context['total_income'], Decimal('0'))
        self.assertEqual(response.context['total_expense'], Decimal('0'))
        self.assertContains(response, EMPTY_FILTER_MESSAGE)
        self.assertNotContains(response, EMPTY_LIST_MESSAGE)

    def test_invalid_month_is_ignored(self):
        for month in ('abc', '2026-13', '2026', '01/2026'):
            with self.subTest(month=month):
                response = self.client.get(self.url, {'month': month})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['current_month'], '')
                self.assertEqual(len(response.context['transactions']), 6)

    def test_invalid_type_is_ignored(self):
        response = self.client.get(self.url, {'type': 'transfer'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_type'], '')
        self.assertEqual(len(response.context['transactions']), 6)
        self.assertEqual(response.context['total_income'], Decimal('3500.00'))

    def test_invalid_month_does_not_disable_valid_type(self):
        response = self.client.get(
            self.url, {'month': 'abc', 'type': 'income'},
        )
        self.assertEqual(response.context['current_month'], '')
        self.assertEqual(response.context['current_type'], 'income')
        self.assertQuerySetEqual(
            response.context['transactions'],
            [self.feb_income, self.jan_income],
        )

    def test_type_choices_are_in_context(self):
        response = self.client.get(self.url)
        self.assertEqual(
            response.context['type_choices'], TransactionType.choices,
        )


class TransactionListPaginationTests(TestCase):
    """PRD 9.5.4: pagination keeps the filters and totals cover all pages."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('transaction_list')
        cls.user = create_user()
        account = create_account(cls.user)
        salary = create_category(cls.user, 'Salário', CategoryType.INCOME)
        food = create_category(cls.user, 'Alimentação', CategoryType.EXPENSE)
        for day in range(1, 26):
            create_transaction(
                account, salary, Decimal('10.00'),
                date=datetime.date(2026, 3, day),
            )
        create_transaction(
            account, food, Decimal('7.00'), date=datetime.date(2026, 3, 30),
        )
        create_transaction(
            account, salary, Decimal('999.00'), date=datetime.date(2026, 4, 1),
        )
        cls.filters = {'month': '2026-03', 'type': 'income'}

    def setUp(self):
        self.client.force_login(self.user)

    def test_first_page_has_twenty_filtered_transactions(self):
        response = self.client.get(self.url, self.filters)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['transactions']), 20)
        self.assertEqual(response.context['paginator'].count, 25)

    def test_totals_cover_all_pages(self):
        response = self.client.get(self.url, self.filters)
        self.assertEqual(response.context['total_income'], Decimal('250.00'))
        self.assertEqual(response.context['total_expense'], Decimal('0'))

    def test_next_link_keeps_filters(self):
        response = self.client.get(self.url, self.filters)
        self.assertContains(
            response, 'href="?month=2026-03&amp;type=income&amp;page=2"',
        )

    def test_second_page_keeps_filters(self):
        response = self.client.get(self.url, {**self.filters, 'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['transactions']), 5)
        self.assertEqual(response.context['current_month'], '2026-03')
        self.assertEqual(response.context['current_type'], 'income')
        self.assertEqual(response.context['total_income'], Decimal('250.00'))
        self.assertContains(
            response, 'href="?month=2026-03&amp;type=income&amp;page=1"',
        )


class AnonymousAccessTests(TestCase):
    """PRD 9.5.5: every transaction URL requires login."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        cls.account = create_account(cls.user)
        cls.category = create_category(
            cls.user, 'Alimentação', CategoryType.EXPENSE,
        )
        cls.transaction = create_transaction(
            cls.account, cls.category, description='Feira',
        )

    def assert_redirects_to_login(self, response, url):
        self.assertRedirects(response, f'{reverse("login")}?next={url}')

    def test_anonymous_list_redirects_to_login(self):
        url = reverse('transaction_list')
        self.assert_redirects_to_login(self.client.get(url), url)

    def test_anonymous_create_get_redirects_to_login(self):
        url = reverse('transaction_create')
        self.assert_redirects_to_login(self.client.get(url), url)

    def test_anonymous_create_post_redirects_and_creates_nothing(self):
        url = reverse('transaction_create')
        response = self.client.post(
            url, transaction_data(self.account, self.category),
        )
        self.assert_redirects_to_login(response, url)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_anonymous_update_get_redirects_to_login(self):
        url = reverse('transaction_update', args=[self.transaction.pk])
        self.assert_redirects_to_login(self.client.get(url), url)

    def test_anonymous_update_post_redirects_and_changes_nothing(self):
        url = reverse('transaction_update', args=[self.transaction.pk])
        response = self.client.post(
            url, transaction_data(self.account, self.category),
        )
        self.assert_redirects_to_login(response, url)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.description, 'Feira')

    def test_anonymous_delete_get_redirects_to_login(self):
        url = reverse('transaction_delete', args=[self.transaction.pk])
        self.assert_redirects_to_login(self.client.get(url), url)

    def test_anonymous_delete_post_redirects_and_deletes_nothing(self):
        url = reverse('transaction_delete', args=[self.transaction.pk])
        response = self.client.post(url)
        self.assert_redirects_to_login(response, url)
        self.assertTrue(
            Transaction.objects.filter(pk=self.transaction.pk).exists(),
        )


class TransactionListIsolationTests(TestCase):
    """PRD 9.5.5: the list and its totals only use the user's own data."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('transaction_list')
        cls.user = create_user()
        cls.other_user = create_user(email='joao@example.com')
        cls.newcomer = create_user(email='ana@example.com')
        account = create_account(cls.user)
        salary = create_category(cls.user, 'Salário', CategoryType.INCOME)
        food = create_category(cls.user, 'Alimentação', CategoryType.EXPENSE)
        cls.income = create_transaction(
            account, salary, Decimal('1000.00'),
            description='Salário da Maria', date=datetime.date(2026, 1, 5),
        )
        cls.expense = create_transaction(
            account, food, Decimal('150.00'),
            description='Mercado da Maria', date=datetime.date(2026, 1, 10),
        )
        foreign_account = create_account(cls.other_user, 'Conta do João')
        foreign_salary = create_category(
            cls.other_user, 'Renda do João', CategoryType.INCOME,
        )
        foreign_food = create_category(
            cls.other_user, 'Gasto do João', CategoryType.EXPENSE,
        )
        cls.foreign_income = create_transaction(
            foreign_account, foreign_salary, Decimal('7777.00'),
            description='Receita Secreta do João',
            date=datetime.date(2026, 1, 6),
        )
        cls.foreign_expense = create_transaction(
            foreign_account, foreign_food, Decimal('333.00'),
            description='Despesa Secreta do João',
            date=datetime.date(2026, 1, 7),
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_lists_only_own_transactions(self):
        response = self.client.get(self.url)
        self.assertQuerySetEqual(
            response.context['transactions'], [self.expense, self.income],
        )

    def test_other_users_transactions_are_not_rendered(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Salário da Maria')
        self.assertNotContains(response, 'Receita Secreta do João')
        self.assertNotContains(response, 'Despesa Secreta do João')
        self.assertNotContains(response, 'Conta do João')
        self.assertNotContains(
            response,
            reverse('transaction_update', args=[self.foreign_income.pk]),
        )

    def test_totals_only_count_own_transactions(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context['total_income'], Decimal('1000.00'))
        self.assertEqual(response.context['total_expense'], Decimal('150.00'))

    def test_filters_do_not_reveal_other_users_transactions(self):
        response = self.client.get(
            self.url, {'month': '2026-01', 'type': 'income'},
        )
        self.assertQuerySetEqual(
            response.context['transactions'], [self.income],
        )
        self.assertEqual(response.context['total_income'], Decimal('1000.00'))

    def test_other_user_sees_only_own_transactions(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.url)
        self.assertQuerySetEqual(
            response.context['transactions'],
            [self.foreign_expense, self.foreign_income],
        )
        self.assertEqual(response.context['total_income'], Decimal('7777.00'))
        self.assertEqual(response.context['total_expense'], Decimal('333.00'))
        self.assertNotContains(response, 'Salário da Maria')

    def test_user_without_transactions_sees_empty_state(self):
        self.client.force_login(self.newcomer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['transactions'], [])
        self.assertEqual(response.context['total_income'], Decimal('0'))
        self.assertEqual(response.context['total_expense'], Decimal('0'))
        self.assertContains(response, EMPTY_LIST_MESSAGE)


class TransactionIsolationTests(TestCase):
    """PRD 9.5.5: another user's transaction returns 404, stays unchanged."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = create_user()
        cls.intruder = create_user(email='joao@example.com')
        cls.account = create_account(cls.owner, 'Conta da Maria')
        cls.category = create_category(
            cls.owner, 'Alimentação', CategoryType.EXPENSE,
        )
        cls.transaction = create_transaction(
            cls.account, cls.category, Decimal('88.80'),
            description='Transação da Maria', date=datetime.date(2026, 1, 10),
        )
        cls.update_url = reverse(
            'transaction_update', args=[cls.transaction.pk],
        )
        cls.delete_url = reverse(
            'transaction_delete', args=[cls.transaction.pk],
        )
        # Valid data for the intruder, so only the ownership check can fail.
        cls.intruder_account = create_account(cls.intruder, 'Conta do João')
        cls.intruder_category = create_category(
            cls.intruder, 'Lazer', CategoryType.EXPENSE,
        )

    def setUp(self):
        self.client.force_login(self.intruder)

    def intruder_data(self):
        return transaction_data(self.intruder_account, self.intruder_category)

    def assert_transaction_unchanged(self):
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.user, self.owner)
        self.assertEqual(self.transaction.account, self.account)
        self.assertEqual(self.transaction.category, self.category)
        self.assertEqual(self.transaction.description, 'Transação da Maria')
        self.assertEqual(self.transaction.amount, Decimal('88.80'))
        self.assertEqual(self.transaction.date, datetime.date(2026, 1, 10))

    def test_update_get_returns_404(self):
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 404)

    def test_update_post_returns_404_and_changes_nothing(self):
        response = self.client.post(self.update_url, self.intruder_data())
        self.assertEqual(response.status_code, 404)
        self.assert_transaction_unchanged()
        self.assertEqual(message_texts(response), [])

    def test_update_post_with_owner_data_returns_404(self):
        response = self.client.post(
            self.update_url,
            transaction_data(self.account, self.category, amount='1.00'),
        )
        self.assertEqual(response.status_code, 404)
        self.assert_transaction_unchanged()

    def test_delete_get_returns_404(self):
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 404)

    def test_delete_post_returns_404_and_deletes_nothing(self):
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 404)
        self.assert_transaction_unchanged()
        self.assertEqual(message_texts(response), [])

    def test_404_page_does_not_leak_transaction_data(self):
        response = self.client.get(self.update_url)
        self.assertNotContains(response, 'Transação da Maria', status_code=404)

    def test_list_does_not_show_other_users_transaction(self):
        response = self.client.get(reverse('transaction_list'))
        self.assertQuerySetEqual(response.context['transactions'], [])
        self.assertNotContains(response, 'Transação da Maria')
        self.assertNotContains(response, self.update_url)

    def test_owner_still_has_access(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.update_url).status_code, 200)
        self.assertEqual(self.client.get(self.delete_url).status_code, 200)


class TransactionCreateOwnershipTests(TestCase):
    """PRD 9.5.5: the create view assigns the logged-in user."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('transaction_create')
        cls.user = create_user()
        cls.other_user = create_user(email='joao@example.com')
        cls.account = create_account(cls.user)
        cls.category = create_category(
            cls.user, 'Alimentação', CategoryType.EXPENSE,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_renders_empty_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transactions/transaction_form.html')
        self.assertIsInstance(response.context['form'], TransactionForm)
        self.assertFalse(response.context['form'].is_bound)
        self.assertContains(response, 'Nova transação')

    def test_valid_post_creates_transaction_for_request_user(self):
        response = self.client.post(
            self.url, transaction_data(self.account, self.category),
        )
        self.assertRedirects(response, reverse('transaction_list'))
        transaction = Transaction.objects.get()
        self.assertEqual(transaction.user, self.user)
        self.assertEqual(transaction.account, self.account)
        self.assertEqual(transaction.category, self.category)
        self.assertEqual(transaction.description, 'Compra no mercado')
        self.assertEqual(transaction.amount, Decimal('59.90'))
        self.assertEqual(transaction.transaction_type, TransactionType.EXPENSE)
        self.assertEqual(transaction.date, datetime.date(2026, 3, 15))

    def test_posted_user_field_is_ignored(self):
        self.client.post(
            self.url,
            transaction_data(
                self.account, self.category,
                user=self.other_user.pk, user_id=self.other_user.pk,
            ),
        )
        self.assertEqual(Transaction.objects.get().user, self.user)

    def test_valid_post_shows_success_message(self):
        response = self.client.post(
            self.url, transaction_data(self.account, self.category),
        )
        self.assertEqual(message_texts(response), [CREATED_MESSAGE])

    def test_success_message_rendered_after_redirect(self):
        response = self.client.post(
            self.url,
            transaction_data(self.account, self.category),
            follow=True,
        )
        self.assertContains(response, CREATED_MESSAGE)
        self.assertContains(response, 'Compra no mercado')


class TransactionModelTests(TestCase):
    """Basic model behavior used by the views."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        cls.account = create_account(cls.user)
        cls.salary = create_category(cls.user, 'Salário', CategoryType.INCOME)
        cls.food = create_category(
            cls.user, 'Alimentação', CategoryType.EXPENSE,
        )

    def test_str_returns_description_and_amount(self):
        transaction = create_transaction(
            self.account, self.food, Decimal('42.90'), description='Feira',
        )
        self.assertEqual(str(transaction), 'Feira - 42.90')

    def test_date_defaults_to_today(self):
        transaction = Transaction.objects.create(
            user=self.user,
            account=self.account,
            category=self.food,
            description='Feira',
            amount=Decimal('10.00'),
            transaction_type=TransactionType.EXPENSE,
        )
        self.assertEqual(transaction.date, timezone.localdate())

    def test_default_ordering_is_newest_date_then_newest_created(self):
        older = create_transaction(
            self.account, self.food, date=datetime.date(2026, 1, 1),
        )
        first_of_day = create_transaction(
            self.account, self.food, date=datetime.date(2026, 1, 2),
        )
        second_of_day = create_transaction(
            self.account, self.salary, date=datetime.date(2026, 1, 2),
        )
        # created_at is set explicitly so the tie-break is deterministic.
        base = timezone.now()
        Transaction.objects.filter(pk=first_of_day.pk).update(
            created_at=base - datetime.timedelta(minutes=5),
        )
        Transaction.objects.filter(pk=second_of_day.pk).update(
            created_at=base,
        )
        self.assertQuerySetEqual(
            Transaction.objects.all(), [second_of_day, first_of_day, older],
        )

    def test_type_labels_are_in_portuguese(self):
        income = create_transaction(self.account, self.salary)
        expense = create_transaction(self.account, self.food)
        self.assertEqual(income.get_transaction_type_display(), 'Entrada')
        self.assertEqual(expense.get_transaction_type_display(), 'Saída')

    def test_deleting_account_cascades_to_transactions(self):
        create_transaction(self.account, self.food)
        self.account.delete()
        self.assertFalse(Transaction.objects.exists())


class TransactionUpdateViewTests(TestCase):
    """Update flow of the owner's transaction."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        cls.account = create_account(cls.user)
        cls.wallet = create_account(cls.user, 'Carteira')
        cls.food = create_category(
            cls.user, 'Alimentação', CategoryType.EXPENSE,
        )
        cls.leisure = create_category(cls.user, 'Lazer', CategoryType.EXPENSE)
        cls.transaction = create_transaction(
            cls.account, cls.food, Decimal('40.00'),
            description='Feira', date=datetime.date(2026, 1, 10),
        )
        cls.url = reverse('transaction_update', args=[cls.transaction.pk])

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_renders_prefilled_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transactions/transaction_form.html')
        self.assertEqual(response.context['form'].instance, self.transaction)
        self.assertContains(response, 'Editar transação')
        self.assertContains(response, 'value="Feira"')
        self.assertContains(response, 'value="2026-01-10"')

    def test_valid_post_updates_transaction(self):
        response = self.client.post(
            self.url,
            transaction_data(
                self.wallet, self.leisure,
                description='Cinema', amount='32.00', date='2026-02-20',
            ),
        )
        self.assertRedirects(response, reverse('transaction_list'))
        self.assertEqual(message_texts(response), [UPDATED_MESSAGE])
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.description, 'Cinema')
        self.assertEqual(self.transaction.amount, Decimal('32.00'))
        self.assertEqual(self.transaction.date, datetime.date(2026, 2, 20))
        self.assertEqual(self.transaction.account, self.wallet)
        self.assertEqual(self.transaction.category, self.leisure)
        self.assertEqual(self.transaction.user, self.user)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_unknown_pk_returns_404(self):
        url = reverse('transaction_update', args=[self.transaction.pk + 1000])
        self.assertEqual(self.client.get(url).status_code, 404)


class TransactionDeleteViewTests(TestCase):
    """Delete flow of the owner's transaction."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        cls.account = create_account(
            cls.user, initial_balance=Decimal('100.00'),
        )
        cls.food = create_category(
            cls.user, 'Alimentação', CategoryType.EXPENSE,
        )
        cls.transaction = create_transaction(
            cls.account, cls.food, Decimal('40.00'), description='Feira',
        )
        cls.kept = create_transaction(
            cls.account, cls.food, Decimal('15.00'), description='Padaria',
        )
        cls.url = reverse('transaction_delete', args=[cls.transaction.pk])

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_renders_confirmation_page_without_deleting(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'transactions/transaction_confirm_delete.html',
        )
        self.assertContains(response, 'Feira')
        self.assertTrue(
            Transaction.objects.filter(pk=self.transaction.pk).exists(),
        )

    def test_post_deletes_only_that_transaction(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('transaction_list'))
        self.assertQuerySetEqual(Transaction.objects.all(), [self.kept])

    def test_post_shows_success_message(self):
        response = self.client.post(self.url)
        self.assertEqual(message_texts(response), [DELETED_MESSAGE])

    def test_post_updates_account_balance(self):
        self.assertEqual(self.account.balance, Decimal('45.00'))
        self.client.post(self.url)
        self.assertEqual(self.account.balance, Decimal('85.00'))

    def test_unknown_pk_returns_404(self):
        url = reverse('transaction_delete', args=[self.transaction.pk + 1000])
        self.assertEqual(self.client.post(url).status_code, 404)
