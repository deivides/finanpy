import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.forms import AccountForm
from accounts.models import Account, AccountType
from categories.models import Category, CategoryType
from transactions.models import Transaction

User = get_user_model()

PASSWORD = 'Sup3r-Segura-2026!'
CREATED_MESSAGE = 'Conta criada com sucesso.'
UPDATED_MESSAGE = 'Conta atualizada com sucesso.'
DELETED_MESSAGE = 'Conta excluída com sucesso.'
EMPTY_LIST_MESSAGE = 'Você ainda não cadastrou nenhuma conta.'
REQUIRED_MESSAGE = 'Este campo é obrigatório.'


def create_user(email='maria@example.com', password=PASSWORD, **extra):
    extra.setdefault('first_name', 'Maria')
    extra.setdefault('last_name', 'Silva')
    return User.objects.create_user(email=email, password=password, **extra)


def create_account(user, name='Nubank', **extra):
    extra.setdefault('bank_name', 'Nu Pagamentos')
    extra.setdefault('account_type', AccountType.CHECKING)
    extra.setdefault('initial_balance', Decimal('0.00'))
    return Account.objects.create(user=user, name=name, **extra)


def create_category(user, name, category_type):
    return Category.objects.create(
        user=user, name=name, category_type=category_type,
    )


def create_transaction(account, category, amount, **extra):
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


def account_data(**overrides):
    data = {
        'name': 'Itaú Personnalité',
        'bank_name': 'Itaú',
        'account_type': AccountType.SAVINGS,
        'initial_balance': '1500.50',
    }
    data.update(overrides)
    return data


def message_texts(response):
    return [m.message for m in get_messages(response.wsgi_request)]


class AccountModelTests(TestCase):
    """Basic model behavior used by the views."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()

    def test_str_returns_name(self):
        account = create_account(self.user, name='Carteira')
        self.assertEqual(str(account), 'Carteira')

    def test_defaults(self):
        account = Account.objects.create(user=self.user, name='Conta')
        account.refresh_from_db()
        self.assertEqual(account.account_type, AccountType.CHECKING)
        self.assertEqual(account.initial_balance, Decimal('0.00'))
        self.assertEqual(account.bank_name, '')

    def test_default_ordering_is_by_name(self):
        create_account(self.user, name='Poupança')
        create_account(self.user, name='Banco do Brasil')
        create_account(self.user, name='Carteira')
        self.assertQuerySetEqual(
            Account.objects.filter(user=self.user),
            ['Banco do Brasil', 'Carteira', 'Poupança'],
            transform=str,
        )


class AccountBalanceWithoutTransactionsTests(TestCase):
    """PRD 9.3.1: balance without transactions equals initial_balance."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()

    def test_balance_with_zero_initial_balance(self):
        account = create_account(self.user, initial_balance=Decimal('0.00'))
        self.assertEqual(account.balance, Decimal('0.00'))

    def test_balance_with_positive_initial_balance(self):
        account = create_account(
            self.user, initial_balance=Decimal('1234.56'),
        )
        self.assertEqual(account.balance, Decimal('1234.56'))

    def test_balance_with_negative_initial_balance(self):
        account = create_account(self.user, initial_balance=Decimal('-80.15'))
        self.assertEqual(account.balance, Decimal('-80.15'))

    def test_balance_is_decimal(self):
        account = create_account(self.user, initial_balance=Decimal('10.00'))
        self.assertIsInstance(account.balance, Decimal)

    def test_balance_is_decimal_after_reload(self):
        create_account(self.user, initial_balance=Decimal('10.00'))
        account = Account.objects.get(user=self.user)
        self.assertIsInstance(account.balance, Decimal)
        self.assertEqual(account.balance, Decimal('10.00'))

    def test_balance_with_zero_initial_balance_is_decimal(self):
        account = create_account(self.user, initial_balance=Decimal('0'))
        self.assertIsInstance(account.balance, Decimal)


class AccountBalanceWithTransactionsTests(TestCase):
    """PRD 9.3.2: balance = initial_balance + income - expenses."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        cls.other_user = create_user(email='joao@example.com')
        cls.salary = create_category(cls.user, 'Salário', CategoryType.INCOME)
        cls.food = create_category(
            cls.user, 'Alimentação', CategoryType.EXPENSE,
        )
        cls.other_salary = create_category(
            cls.other_user, 'Salário', CategoryType.INCOME,
        )
        cls.other_food = create_category(
            cls.other_user, 'Alimentação', CategoryType.EXPENSE,
        )

    def test_balance_with_only_income(self):
        account = create_account(self.user, initial_balance=Decimal('100.00'))
        create_transaction(account, self.salary, Decimal('50.25'))
        self.assertEqual(account.balance, Decimal('150.25'))

    def test_balance_with_only_expenses(self):
        account = create_account(self.user, initial_balance=Decimal('100.00'))
        create_transaction(account, self.food, Decimal('30.40'))
        self.assertEqual(account.balance, Decimal('69.60'))

    def test_balance_with_income_and_expenses(self):
        account = create_account(
            self.user, initial_balance=Decimal('1000.00'),
        )
        create_transaction(account, self.salary, Decimal('3500.00'))
        create_transaction(account, self.salary, Decimal('250.75'))
        create_transaction(account, self.food, Decimal('420.30'))
        create_transaction(account, self.food, Decimal('79.95'))
        # 1000.00 + 3500.00 + 250.75 - 420.30 - 79.95
        self.assertEqual(account.balance, Decimal('4250.50'))
        self.assertIsInstance(account.balance, Decimal)

    def test_balance_cents_are_exact(self):
        account = create_account(self.user, initial_balance=Decimal('0.00'))
        create_transaction(account, self.salary, Decimal('0.10'))
        create_transaction(account, self.salary, Decimal('0.20'))
        self.assertEqual(account.balance, Decimal('0.30'))

    def test_balance_cents_are_exact_with_expenses(self):
        account = create_account(self.user, initial_balance=Decimal('0.30'))
        create_transaction(account, self.food, Decimal('0.10'))
        create_transaction(account, self.food, Decimal('0.20'))
        self.assertEqual(account.balance, Decimal('0.00'))

    def test_balance_can_go_negative(self):
        account = create_account(self.user, initial_balance=Decimal('50.00'))
        create_transaction(account, self.salary, Decimal('20.00'))
        create_transaction(account, self.food, Decimal('100.01'))
        self.assertEqual(account.balance, Decimal('-30.01'))

    def test_balance_with_negative_initial_and_income(self):
        account = create_account(
            self.user, initial_balance=Decimal('-200.00'),
        )
        create_transaction(account, self.salary, Decimal('150.00'))
        self.assertEqual(account.balance, Decimal('-50.00'))

    def test_balance_counts_transactions_from_any_date(self):
        account = create_account(self.user, initial_balance=Decimal('0.00'))
        today = timezone.localdate()
        create_transaction(account, self.salary, Decimal('100.00'), date=today)
        create_transaction(
            account, self.salary, Decimal('200.00'),
            date=datetime.date(2020, 1, 15),
        )
        create_transaction(
            account, self.food, Decimal('30.00'),
            date=datetime.date(2019, 12, 31),
        )
        create_transaction(
            account, self.food, Decimal('20.00'),
            date=today + datetime.timedelta(days=40),
        )
        self.assertEqual(account.balance, Decimal('250.00'))

    def test_balance_ignores_other_account_of_same_user(self):
        account = create_account(self.user, initial_balance=Decimal('10.00'))
        other_account = create_account(
            self.user, name='Poupança', initial_balance=Decimal('500.00'),
        )
        create_transaction(account, self.salary, Decimal('5.00'))
        create_transaction(other_account, self.salary, Decimal('999.00'))
        create_transaction(other_account, self.food, Decimal('1.00'))
        self.assertEqual(account.balance, Decimal('15.00'))
        self.assertEqual(other_account.balance, Decimal('1498.00'))

    def test_balance_ignores_other_users_accounts(self):
        account = create_account(self.user, initial_balance=Decimal('10.00'))
        foreign_account = create_account(
            self.other_user, initial_balance=Decimal('10.00'),
        )
        create_transaction(foreign_account, self.other_salary, Decimal('700'))
        create_transaction(foreign_account, self.other_food, Decimal('3.00'))
        self.assertEqual(account.balance, Decimal('10.00'))
        self.assertEqual(foreign_account.balance, Decimal('707.00'))

    def test_balance_reflects_new_transactions(self):
        account = create_account(self.user, initial_balance=Decimal('10.00'))
        self.assertEqual(account.balance, Decimal('10.00'))
        create_transaction(account, self.food, Decimal('4.00'))
        self.assertEqual(account.balance, Decimal('6.00'))

    def test_balance_is_not_stored(self):
        # balance is computed; it is not a model field.
        field_names = {f.name for f in Account._meta.get_fields()}
        self.assertNotIn('balance', field_names)


class AnonymousAccessTests(TestCase):
    """PRD 9.3.3: every account URL requires login."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        cls.account = create_account(cls.user, name='Nubank')

    def assert_redirects_to_login(self, response, url):
        self.assertRedirects(response, f'{reverse("login")}?next={url}')

    def test_anonymous_list_redirects_to_login(self):
        url = reverse('account_list')
        self.assert_redirects_to_login(self.client.get(url), url)

    def test_anonymous_create_get_redirects_to_login(self):
        url = reverse('account_create')
        self.assert_redirects_to_login(self.client.get(url), url)

    def test_anonymous_create_post_redirects_and_creates_nothing(self):
        url = reverse('account_create')
        response = self.client.post(url, account_data())
        self.assert_redirects_to_login(response, url)
        self.assertEqual(Account.objects.count(), 1)

    def test_anonymous_update_get_redirects_to_login(self):
        url = reverse('account_update', args=[self.account.pk])
        self.assert_redirects_to_login(self.client.get(url), url)

    def test_anonymous_update_post_redirects_and_changes_nothing(self):
        url = reverse('account_update', args=[self.account.pk])
        response = self.client.post(url, account_data())
        self.assert_redirects_to_login(response, url)
        self.account.refresh_from_db()
        self.assertEqual(self.account.name, 'Nubank')

    def test_anonymous_delete_get_redirects_to_login(self):
        url = reverse('account_delete', args=[self.account.pk])
        self.assert_redirects_to_login(self.client.get(url), url)

    def test_anonymous_delete_post_redirects_and_deletes_nothing(self):
        url = reverse('account_delete', args=[self.account.pk])
        response = self.client.post(url)
        self.assert_redirects_to_login(response, url)
        self.assertTrue(Account.objects.filter(pk=self.account.pk).exists())


class AccountListViewTests(TestCase):
    """PRD 9.3.3 and 9.3.4: account list."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('account_list')
        cls.user = create_user()
        cls.other_user = create_user(email='joao@example.com')
        cls.wallet = create_account(
            cls.user, name='Carteira', bank_name='',
            account_type=AccountType.WALLET,
            initial_balance=Decimal('1234.56'),
        )
        cls.bank = create_account(
            cls.user, name='Banco Inter', bank_name='Inter',
            initial_balance=Decimal('-50.00'),
        )
        cls.savings = create_account(
            cls.user, name='Reserva', bank_name='Caixa Econômica',
            account_type=AccountType.SAVINGS,
        )
        cls.foreign = create_account(
            cls.other_user, name='Conta Secreta do João',
            bank_name='Banco Estrangeiro',
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_returns_200_with_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/account_list.html')

    def test_lists_only_own_accounts_ordered_by_name(self):
        response = self.client.get(self.url)
        self.assertQuerySetEqual(
            response.context['accounts'],
            [self.bank, self.wallet, self.savings],
        )

    def test_other_users_accounts_are_not_rendered(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, 'Conta Secreta do João')
        self.assertNotContains(response, 'Banco Estrangeiro')
        self.assertNotContains(
            response, reverse('account_update', args=[self.foreign.pk]),
        )

    def test_renders_names_bank_and_type(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Banco Inter')
        self.assertContains(response, 'Caixa Econômica')
        # Type labels: 'Poupança' and 'Conta corrente' are not account names.
        self.assertContains(response, 'Poupança')
        self.assertContains(response, 'Conta corrente')

    def test_renders_balance_in_brazilian_format(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'R$ 1.234,56')

    def test_renders_negative_balance_with_minus_sign(self):
        response = self.client.get(self.url)
        self.assertContains(response, '−R$ 50,00')

    def test_renders_edit_and_delete_links(self):
        response = self.client.get(self.url)
        self.assertContains(
            response, reverse('account_update', args=[self.wallet.pk]),
        )
        self.assertContains(
            response, reverse('account_delete', args=[self.wallet.pk]),
        )

    def test_does_not_show_empty_state_when_has_accounts(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, EMPTY_LIST_MESSAGE)

    def test_other_user_sees_only_own_account(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.url)
        self.assertQuerySetEqual(response.context['accounts'], [self.foreign])
        self.assertNotContains(response, 'Caixa Econômica')


class AccountListEmptyStateTests(TestCase):
    """PRD 9.3.3: empty state of the account list."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        cls.other_user = create_user(email='joao@example.com')
        create_account(cls.other_user, name='Conta do João')

    def test_empty_list_shows_empty_state(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('account_list'))
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['accounts'], [])
        self.assertContains(response, EMPTY_LIST_MESSAGE)
        self.assertNotContains(response, 'Conta do João')


class AccountCreateViewTests(TestCase):
    """PRD 9.3.3: account creation."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('account_create')
        cls.user = create_user()
        cls.other_user = create_user(email='joao@example.com')

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_renders_empty_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/account_form.html')
        self.assertIsInstance(response.context['form'], AccountForm)
        self.assertFalse(response.context['form'].is_bound)
        self.assertContains(response, 'Nova conta')

    def test_form_does_not_expose_user_field(self):
        self.assertEqual(
            list(AccountForm().fields),
            ['name', 'bank_name', 'account_type', 'initial_balance'],
        )

    def test_valid_post_creates_account(self):
        self.client.post(self.url, account_data())
        account = Account.objects.get()
        self.assertEqual(account.name, 'Itaú Personnalité')
        self.assertEqual(account.bank_name, 'Itaú')
        self.assertEqual(account.account_type, AccountType.SAVINGS)
        self.assertEqual(account.initial_balance, Decimal('1500.50'))

    def test_valid_post_assigns_request_user(self):
        self.client.post(self.url, account_data())
        self.assertEqual(Account.objects.get().user, self.user)

    def test_posted_user_field_is_ignored(self):
        self.client.post(
            self.url,
            account_data(user=self.other_user.pk, user_id=self.other_user.pk),
        )
        account = Account.objects.get()
        self.assertEqual(account.user, self.user)
        self.assertFalse(Account.objects.filter(user=self.other_user).exists())

    def test_valid_post_redirects_to_list(self):
        response = self.client.post(self.url, account_data())
        self.assertRedirects(response, reverse('account_list'))

    def test_valid_post_shows_success_message(self):
        response = self.client.post(self.url, account_data())
        self.assertEqual(message_texts(response), [CREATED_MESSAGE])

    def test_success_message_rendered_after_redirect(self):
        response = self.client.post(self.url, account_data(), follow=True)
        self.assertContains(response, CREATED_MESSAGE)
        self.assertContains(response, 'Itaú Personnalité')

    def test_bank_name_is_optional(self):
        response = self.client.post(self.url, account_data(bank_name=''))
        self.assertRedirects(response, reverse('account_list'))
        self.assertEqual(Account.objects.get().bank_name, '')

    def test_negative_initial_balance_is_accepted(self):
        self.client.post(self.url, account_data(initial_balance='-250.75'))
        self.assertEqual(
            Account.objects.get().initial_balance, Decimal('-250.75'),
        )

    def test_missing_name_rerenders_with_error(self):
        response = self.client.post(self.url, account_data(name=''))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/account_form.html')
        self.assertFormError(
            response.context['form'], 'name', REQUIRED_MESSAGE,
        )
        self.assertContains(response, REQUIRED_MESSAGE)
        self.assertFalse(Account.objects.exists())

    def test_missing_initial_balance_is_rejected(self):
        response = self.client.post(
            self.url, account_data(initial_balance=''),
        )
        self.assertFormError(
            response.context['form'], 'initial_balance', REQUIRED_MESSAGE,
        )
        self.assertFalse(Account.objects.exists())

    def test_invalid_account_type_is_rejected(self):
        response = self.client.post(
            self.url, account_data(account_type='crypto'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('account_type', response.context['form'].errors)
        self.assertFalse(Account.objects.exists())

    def test_initial_balance_with_three_decimals_is_rejected(self):
        response = self.client.post(
            self.url, account_data(initial_balance='10.123'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('initial_balance', response.context['form'].errors)
        self.assertFalse(Account.objects.exists())

    def test_invalid_post_keeps_submitted_values(self):
        response = self.client.post(
            self.url, account_data(name='', bank_name='Banco Teste'),
        )
        self.assertContains(response, 'value="Banco Teste"')

    def test_invalid_post_shows_no_success_message(self):
        response = self.client.post(self.url, account_data(name=''))
        self.assertEqual(message_texts(response), [])


class AccountUpdateViewTests(TestCase):
    """PRD 9.3.3: account update."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        cls.other_user = create_user(email='joao@example.com')
        cls.account = create_account(
            cls.user, name='Nubank', bank_name='Nu Pagamentos',
            account_type=AccountType.CHECKING,
            initial_balance=Decimal('100.00'),
        )
        cls.url = reverse('account_update', args=[cls.account.pk])

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_renders_prefilled_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/account_form.html')
        self.assertEqual(response.context['form'].instance, self.account)
        self.assertContains(response, 'Editar conta')
        self.assertContains(response, 'value="Nubank"')
        self.assertContains(response, 'value="Nu Pagamentos"')
        self.assertContains(response, 'value="100.00"')

    def test_valid_post_updates_account(self):
        self.client.post(self.url, account_data())
        self.account.refresh_from_db()
        self.assertEqual(self.account.name, 'Itaú Personnalité')
        self.assertEqual(self.account.bank_name, 'Itaú')
        self.assertEqual(self.account.account_type, AccountType.SAVINGS)
        self.assertEqual(self.account.initial_balance, Decimal('1500.50'))

    def test_valid_post_does_not_create_new_account(self):
        self.client.post(self.url, account_data())
        self.assertEqual(Account.objects.count(), 1)

    def test_valid_post_redirects_to_list(self):
        response = self.client.post(self.url, account_data())
        self.assertRedirects(response, reverse('account_list'))

    def test_valid_post_shows_success_message(self):
        response = self.client.post(self.url, account_data())
        self.assertEqual(message_texts(response), [UPDATED_MESSAGE])

    def test_posted_user_field_does_not_change_owner(self):
        self.client.post(self.url, account_data(user=self.other_user.pk))
        self.account.refresh_from_db()
        self.assertEqual(self.account.user, self.user)

    def test_missing_name_rerenders_with_error_and_keeps_data(self):
        response = self.client.post(self.url, account_data(name=''))
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], 'name', REQUIRED_MESSAGE,
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.name, 'Nubank')
        self.assertEqual(self.account.initial_balance, Decimal('100.00'))
        self.assertEqual(message_texts(response), [])

    def test_unknown_pk_returns_404(self):
        url = reverse('account_update', args=[self.account.pk + 1000])
        self.assertEqual(self.client.get(url).status_code, 404)


class AccountDeleteViewTests(TestCase):
    """PRD 9.3.3: account deletion."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        cls.account = create_account(cls.user, name='Nubank')
        cls.other_account = create_account(cls.user, name='Carteira')
        cls.url = reverse('account_delete', args=[cls.account.pk])
        salary = create_category(cls.user, 'Salário', CategoryType.INCOME)
        food = create_category(cls.user, 'Alimentação', CategoryType.EXPENSE)
        create_transaction(cls.account, salary, Decimal('100.00'))
        create_transaction(cls.account, food, Decimal('40.00'))
        cls.kept_transaction = create_transaction(
            cls.other_account, food, Decimal('15.00'),
        )
        cls.salary = salary

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_renders_confirmation_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'accounts/account_confirm_delete.html',
        )
        self.assertContains(response, 'Nubank')
        self.assertContains(
            response,
            'Todas as transações vinculadas a esta conta também serão '
            'excluídas.',
        )

    def test_get_does_not_delete(self):
        self.client.get(self.url)
        self.assertTrue(Account.objects.filter(pk=self.account.pk).exists())

    def test_post_deletes_account(self):
        self.client.post(self.url)
        self.assertFalse(Account.objects.filter(pk=self.account.pk).exists())
        self.assertTrue(
            Account.objects.filter(pk=self.other_account.pk).exists(),
        )

    def test_post_redirects_to_list(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('account_list'))

    def test_post_shows_success_message(self):
        response = self.client.post(self.url)
        self.assertEqual(message_texts(response), [DELETED_MESSAGE])

    def test_success_message_rendered_after_redirect(self):
        response = self.client.post(self.url, follow=True)
        self.assertContains(response, DELETED_MESSAGE)

    def test_post_cascades_account_transactions(self):
        self.client.post(self.url)
        self.assertFalse(
            Transaction.objects.filter(account_id=self.account.pk).exists(),
        )

    def test_post_keeps_transactions_of_other_accounts(self):
        self.client.post(self.url)
        self.assertQuerySetEqual(
            Transaction.objects.all(), [self.kept_transaction],
        )

    def test_post_keeps_categories(self):
        # Category uses RESTRICT, but the cascade through Account removes
        # the transactions in the same operation, so deletion succeeds and
        # the categories stay.
        self.client.post(self.url)
        self.assertTrue(Category.objects.filter(pk=self.salary.pk).exists())
        self.assertEqual(Category.objects.filter(user=self.user).count(), 2)

    def test_unknown_pk_returns_404(self):
        url = reverse('account_delete', args=[self.account.pk + 1000])
        self.assertEqual(self.client.post(url).status_code, 404)


class AccountIsolationTests(TestCase):
    """PRD 9.3.4: another user's account returns 404 and stays unchanged."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = create_user()
        cls.intruder = create_user(email='joao@example.com')
        cls.account = create_account(
            cls.owner, name='Conta da Maria', bank_name='Banco da Maria',
            account_type=AccountType.CHECKING,
            initial_balance=Decimal('900.00'),
        )
        cls.update_url = reverse('account_update', args=[cls.account.pk])
        cls.delete_url = reverse('account_delete', args=[cls.account.pk])
        category = create_category(cls.owner, 'Salário', CategoryType.INCOME)
        cls.transaction = create_transaction(
            cls.account, category, Decimal('100.00'),
        )

    def setUp(self):
        self.client.force_login(self.intruder)

    def assert_account_unchanged(self):
        self.account.refresh_from_db()
        self.assertEqual(self.account.user, self.owner)
        self.assertEqual(self.account.name, 'Conta da Maria')
        self.assertEqual(self.account.bank_name, 'Banco da Maria')
        self.assertEqual(self.account.account_type, AccountType.CHECKING)
        self.assertEqual(self.account.initial_balance, Decimal('900.00'))

    def test_update_get_returns_404(self):
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 404)

    def test_update_post_returns_404_and_changes_nothing(self):
        response = self.client.post(self.update_url, account_data())
        self.assertEqual(response.status_code, 404)
        self.assert_account_unchanged()

    def test_update_post_shows_no_message(self):
        response = self.client.post(self.update_url, account_data())
        self.assertEqual(message_texts(response), [])

    def test_delete_get_returns_404(self):
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 404)

    def test_delete_post_returns_404_and_deletes_nothing(self):
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 404)
        self.assert_account_unchanged()
        self.assertTrue(
            Transaction.objects.filter(pk=self.transaction.pk).exists(),
        )

    def test_delete_post_shows_no_message(self):
        response = self.client.post(self.delete_url)
        self.assertEqual(message_texts(response), [])

    def test_404_page_does_not_leak_account_data(self):
        response = self.client.get(self.update_url)
        self.assertNotContains(response, 'Conta da Maria', status_code=404)

    def test_list_does_not_show_other_users_account(self):
        response = self.client.get(reverse('account_list'))
        self.assertQuerySetEqual(response.context['accounts'], [])
        self.assertNotContains(response, 'Conta da Maria')
        self.assertNotContains(response, self.update_url)
        self.assertContains(response, EMPTY_LIST_MESSAGE)

    def test_owner_still_has_access(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.update_url).status_code, 200)
        self.assertEqual(self.client.get(self.delete_url).status_code, 200)
