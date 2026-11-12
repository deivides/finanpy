from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.db import IntegrityError, transaction
from django.db.models import RestrictedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Account
from categories.forms import CategoryForm
from categories.models import Category, CategoryType
from transactions.models import Transaction

User = get_user_model()

PASSWORD = 'Sup3r-Segura-2026!'
CREATED_MESSAGE = 'Categoria criada com sucesso.'
UPDATED_MESSAGE = 'Categoria atualizada com sucesso.'
DELETED_MESSAGE = 'Categoria excluída com sucesso.'
DELETE_BLOCKED_MESSAGE = (
    'Esta categoria possui transações e não pode ser excluída.'
)
DUPLICATE_MESSAGE = 'Você já possui uma categoria com este nome e tipo.'
TYPE_CHANGE_IN_USE_MESSAGE = (
    'Não é possível alterar o tipo de uma categoria que possui transações.'
)
REQUIRED_MESSAGE = 'Este campo é obrigatório.'
EMPTY_INCOME_MESSAGE = 'Nenhuma categoria de entrada cadastrada.'
EMPTY_EXPENSE_MESSAGE = 'Nenhuma categoria de saída cadastrada.'


def create_user(email='maria@example.com', password=PASSWORD, **extra):
    extra.setdefault('first_name', 'Maria')
    extra.setdefault('last_name', 'Silva')
    return User.objects.create_user(email=email, password=password, **extra)


def create_category(user, name='Salário', category_type=CategoryType.INCOME):
    return Category.objects.create(
        user=user, name=name, category_type=category_type,
    )


def create_transaction(category, amount=Decimal('100.00'), **extra):
    account = Account.objects.create(user=category.user, name='Nubank')
    extra.setdefault('description', 'Lançamento')
    extra.setdefault('transaction_type', category.category_type)
    extra.setdefault('date', timezone.localdate())
    return Transaction.objects.create(
        user=category.user,
        account=account,
        category=category,
        amount=amount,
        **extra,
    )


def category_data(**overrides):
    data = {
        'name': 'Freelance',
        'category_type': CategoryType.INCOME,
    }
    data.update(overrides)
    return data


def message_texts(response):
    return [m.message for m in get_messages(response.wsgi_request)]


class CategoryModelTests(TestCase):
    """Basic model behavior used by the views."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()

    def test_str_returns_name(self):
        category = create_category(self.user, name='Alimentação')
        self.assertEqual(str(category), 'Alimentação')

    def test_default_ordering_is_by_type_and_name(self):
        create_category(self.user, 'Transporte', CategoryType.EXPENSE)
        create_category(self.user, 'Salário', CategoryType.INCOME)
        create_category(self.user, 'Alimentação', CategoryType.EXPENSE)
        create_category(self.user, 'Freelance', CategoryType.INCOME)
        # 'expense' sorts before 'income'.
        self.assertQuerySetEqual(
            Category.objects.filter(user=self.user),
            ['Alimentação', 'Transporte', 'Freelance', 'Salário'],
            transform=str,
        )

    def test_type_labels_are_in_portuguese(self):
        income = create_category(self.user, 'Salário', CategoryType.INCOME)
        expense = create_category(self.user, 'Lazer', CategoryType.EXPENSE)
        self.assertEqual(income.get_category_type_display(), 'Entrada')
        self.assertEqual(expense.get_category_type_display(), 'Saída')


class CategoryUniqueConstraintTests(TestCase):
    """PRD 9.4.1: database constraint on user + name + category_type."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        cls.other_user = create_user(email='joao@example.com')
        cls.category = create_category(
            cls.user, 'Salário', CategoryType.INCOME,
        )

    def test_constraint_is_declared_on_model(self):
        constraint = next(
            c for c in Category._meta.constraints
            if c.name == 'unique_user_category'
        )
        self.assertEqual(
            tuple(constraint.fields), ('user', 'name', 'category_type'),
        )

    def test_duplicate_user_name_type_raises_integrity_error(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                create_category(self.user, 'Salário', CategoryType.INCOME)
        self.assertEqual(Category.objects.filter(user=self.user).count(), 1)

    def test_same_name_with_different_type_is_allowed(self):
        create_category(self.user, 'Salário', CategoryType.EXPENSE)
        self.assertEqual(
            Category.objects.filter(user=self.user, name='Salário').count(),
            2,
        )

    def test_same_name_and_type_for_other_user_is_allowed(self):
        create_category(self.other_user, 'Salário', CategoryType.INCOME)
        self.assertEqual(
            Category.objects.filter(
                name='Salário', category_type=CategoryType.INCOME,
            ).count(),
            2,
        )

    def test_different_name_with_same_type_is_allowed(self):
        create_category(self.user, 'Freelance', CategoryType.INCOME)
        self.assertEqual(Category.objects.filter(user=self.user).count(), 2)

    def test_updating_into_duplicate_raises_integrity_error(self):
        other = create_category(self.user, 'Freelance', CategoryType.INCOME)
        other.name = 'Salário'
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                other.save()
        other.refresh_from_db()
        self.assertEqual(other.name, 'Freelance')


class CategoryFormDuplicateTests(TestCase):
    """PRD 9.4.1: CategoryForm rejects duplicates of the given user."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        cls.other_user = create_user(email='joao@example.com')
        cls.category = create_category(
            cls.user, 'Salário', CategoryType.INCOME,
        )

    def test_form_fields_do_not_expose_user(self):
        self.assertEqual(
            list(CategoryForm(user=self.user).fields),
            ['name', 'category_type'],
        )

    def test_new_category_is_valid(self):
        form = CategoryForm(data=category_data(), user=self.user)
        self.assertTrue(form.is_valid(), form.errors)

    def test_duplicate_is_rejected_with_portuguese_message(self):
        form = CategoryForm(
            data=category_data(name='Salário'), user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertFormError(form, None, DUPLICATE_MESSAGE)

    def test_duplicate_error_has_code(self):
        form = CategoryForm(
            data=category_data(name='Salário'), user=self.user,
        )
        self.assertTrue(form.has_error('__all__', code='duplicate_category'))

    def test_duplicate_with_surrounding_spaces_is_rejected(self):
        form = CategoryForm(
            data=category_data(name='  Salário  '), user=self.user,
        )
        self.assertFormError(form, None, DUPLICATE_MESSAGE)

    def test_same_name_with_different_type_is_valid(self):
        form = CategoryForm(
            data=category_data(
                name='Salário', category_type=CategoryType.EXPENSE,
            ),
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_same_name_and_type_for_other_user_is_valid(self):
        form = CategoryForm(
            data=category_data(name='Salário'), user=self.other_user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_editing_keeping_own_name_and_type_is_valid(self):
        form = CategoryForm(
            data=category_data(name='Salário'),
            instance=self.category,
            user=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_editing_into_another_own_category_is_rejected(self):
        other = create_category(self.user, 'Freelance', CategoryType.INCOME)
        form = CategoryForm(
            data=category_data(name='Salário'), instance=other, user=self.user,
        )
        self.assertFormError(form, None, DUPLICATE_MESSAGE)

    def test_name_is_required(self):
        form = CategoryForm(data=category_data(name=''), user=self.user)
        self.assertFormError(form, 'name', REQUIRED_MESSAGE)

    def test_category_type_is_required(self):
        form = CategoryForm(
            data=category_data(category_type=''), user=self.user,
        )
        self.assertFormError(form, 'category_type', REQUIRED_MESSAGE)

    def test_invalid_category_type_is_rejected(self):
        form = CategoryForm(
            data=category_data(category_type='transfer'), user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('category_type', form.errors)


class CategoryCreateViewDuplicateTests(TestCase):
    """PRD 9.4.1: the create view does not save a duplicate."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('category_create')
        cls.user = create_user()
        cls.other_user = create_user(email='joao@example.com')
        cls.category = create_category(
            cls.user, 'Salário', CategoryType.INCOME,
        )
        create_category(cls.other_user, 'Mesada', CategoryType.INCOME)

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_renders_empty_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'categories/category_form.html')
        self.assertIsInstance(response.context['form'], CategoryForm)
        self.assertFalse(response.context['form'].is_bound)
        self.assertContains(response, 'Nova categoria')

    def test_duplicate_post_rerenders_with_error(self):
        response = self.client.post(self.url, category_data(name='Salário'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'categories/category_form.html')
        self.assertFormError(
            response.context['form'], None, DUPLICATE_MESSAGE,
        )
        self.assertContains(response, DUPLICATE_MESSAGE)

    def test_duplicate_post_creates_nothing(self):
        self.client.post(self.url, category_data(name='Salário'))
        self.assertQuerySetEqual(
            Category.objects.filter(user=self.user), [self.category],
        )

    def test_duplicate_post_shows_no_success_message(self):
        response = self.client.post(self.url, category_data(name='Salário'))
        self.assertEqual(message_texts(response), [])

    def test_same_name_with_different_type_is_created(self):
        response = self.client.post(
            self.url,
            category_data(name='Salário', category_type=CategoryType.EXPENSE),
        )
        self.assertRedirects(response, reverse('category_list'))
        self.assertTrue(
            Category.objects.filter(
                user=self.user,
                name='Salário',
                category_type=CategoryType.EXPENSE,
            ).exists(),
        )

    def test_name_used_by_other_user_is_created(self):
        response = self.client.post(self.url, category_data(name='Mesada'))
        self.assertRedirects(response, reverse('category_list'))
        self.assertTrue(
            Category.objects.filter(user=self.user, name='Mesada').exists(),
        )
        self.assertEqual(Category.objects.filter(name='Mesada').count(), 2)

    def test_valid_post_shows_success_message(self):
        response = self.client.post(self.url, category_data())
        self.assertRedirects(response, reverse('category_list'))
        self.assertEqual(message_texts(response), [CREATED_MESSAGE])

    def test_success_message_rendered_after_redirect(self):
        response = self.client.post(self.url, category_data(), follow=True)
        self.assertContains(response, CREATED_MESSAGE)
        self.assertContains(response, 'Freelance')

    def test_missing_name_rerenders_with_error(self):
        response = self.client.post(self.url, category_data(name=''))
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], 'name', REQUIRED_MESSAGE,
        )
        self.assertEqual(Category.objects.filter(user=self.user).count(), 1)


class CategoryUpdateViewDuplicateTests(TestCase):
    """PRD 9.4.1: the update view keeps the duplicate rule."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        cls.category = create_category(
            cls.user, 'Salário', CategoryType.INCOME,
        )
        cls.other_category = create_category(
            cls.user, 'Freelance', CategoryType.INCOME,
        )
        cls.url = reverse('category_update', args=[cls.category.pk])

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_renders_prefilled_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'categories/category_form.html')
        self.assertEqual(response.context['form'].instance, self.category)
        self.assertContains(response, 'Editar categoria')
        self.assertContains(response, 'value="Salário"')

    def test_post_keeping_own_name_and_type_is_accepted(self):
        response = self.client.post(
            self.url,
            category_data(name='Salário', category_type=CategoryType.INCOME),
        )
        self.assertRedirects(response, reverse('category_list'))
        self.assertEqual(message_texts(response), [UPDATED_MESSAGE])
        self.assertEqual(Category.objects.count(), 2)

    def test_post_renaming_updates_category(self):
        response = self.client.post(
            self.url,
            category_data(name='Bônus', category_type=CategoryType.INCOME),
        )
        self.assertRedirects(response, reverse('category_list'))
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Bônus')
        self.assertEqual(self.category.user, self.user)

    def test_post_into_another_own_category_is_rejected(self):
        response = self.client.post(
            self.url,
            category_data(name='Freelance', category_type=CategoryType.INCOME),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], None, DUPLICATE_MESSAGE,
        )
        self.assertContains(response, DUPLICATE_MESSAGE)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Salário')
        self.assertEqual(message_texts(response), [])

    def test_changing_type_without_transactions_is_accepted(self):
        response = self.client.post(
            self.url,
            category_data(name='Salário', category_type=CategoryType.EXPENSE),
        )
        self.assertRedirects(response, reverse('category_list'))
        self.category.refresh_from_db()
        self.assertEqual(self.category.category_type, CategoryType.EXPENSE)

    def test_unknown_pk_returns_404(self):
        url = reverse('category_update', args=[self.category.pk + 1000])
        self.assertEqual(self.client.get(url).status_code, 404)


class CategoryDeleteWithTransactionsTests(TestCase):
    """PRD 9.4.2: a category with transactions cannot be deleted."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        cls.category = create_category(
            cls.user, 'Alimentação', CategoryType.EXPENSE,
        )
        cls.transaction = create_transaction(cls.category, Decimal('42.90'))
        cls.url = reverse('category_delete', args=[cls.category.pk])

    def setUp(self):
        self.client.force_login(self.user)

    def test_model_delete_raises_restricted_error(self):
        with self.assertRaises(RestrictedError):
            self.category.delete()
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_get_renders_confirmation_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'categories/category_confirm_delete.html',
        )
        self.assertContains(response, 'Alimentação')
        self.assertContains(
            response,
            'Categorias com transações vinculadas não podem ser excluídas.',
        )

    def test_post_does_not_delete_category(self):
        self.client.post(self.url)
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_post_keeps_transaction(self):
        self.client.post(self.url)
        self.transaction.refresh_from_db()
        self.assertEqual(self.transaction.category, self.category)
        self.assertEqual(self.transaction.amount, Decimal('42.90'))

    def test_post_redirects_to_list(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('category_list'))

    def test_post_shows_blocked_message_only(self):
        response = self.client.post(self.url)
        self.assertEqual(message_texts(response), [DELETE_BLOCKED_MESSAGE])

    def test_blocked_message_is_error_level(self):
        response = self.client.post(self.url)
        tags = [m.level_tag for m in get_messages(response.wsgi_request)]
        self.assertEqual(tags, ['error'])

    def test_blocked_message_rendered_after_redirect(self):
        response = self.client.post(self.url, follow=True)
        self.assertContains(response, DELETE_BLOCKED_MESSAGE)
        self.assertNotContains(response, DELETED_MESSAGE)
        self.assertQuerySetEqual(
            response.context['expense_categories'], [self.category],
        )

    def test_category_can_be_deleted_after_transactions_are_removed(self):
        self.transaction.delete()
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('category_list'))
        self.assertEqual(message_texts(response), [DELETED_MESSAGE])
        self.assertFalse(Category.objects.filter(pk=self.category.pk).exists())

    def test_type_change_is_rejected_while_in_use(self):
        response = self.client.post(
            reverse('category_update', args=[self.category.pk]),
            category_data(
                name='Alimentação', category_type=CategoryType.INCOME,
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], 'category_type',
            TYPE_CHANGE_IN_USE_MESSAGE,
        )
        self.category.refresh_from_db()
        self.assertEqual(self.category.category_type, CategoryType.EXPENSE)

    def test_rename_is_accepted_while_in_use(self):
        response = self.client.post(
            reverse('category_update', args=[self.category.pk]),
            category_data(name='Mercado', category_type=CategoryType.EXPENSE),
        )
        self.assertRedirects(response, reverse('category_list'))
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Mercado')

    def test_deleting_user_removes_category_and_transactions(self):
        # RESTRICT (unlike PROTECT) allows the delete when the transactions
        # are removed by the same cascade.
        self.user.delete()
        self.assertFalse(Category.objects.exists())
        self.assertFalse(Transaction.objects.exists())


class CategoryDeleteWithoutTransactionsTests(TestCase):
    """PRD 9.4.2: a category without transactions is deleted normally."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        cls.category = create_category(
            cls.user, 'Lazer', CategoryType.EXPENSE,
        )
        cls.used_category = create_category(
            cls.user, 'Alimentação', CategoryType.EXPENSE,
        )
        cls.transaction = create_transaction(cls.used_category)
        cls.url = reverse('category_delete', args=[cls.category.pk])

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_does_not_delete(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_post_deletes_category(self):
        self.client.post(self.url)
        self.assertFalse(Category.objects.filter(pk=self.category.pk).exists())

    def test_post_keeps_other_categories_and_transactions(self):
        self.client.post(self.url)
        self.assertQuerySetEqual(
            Category.objects.filter(user=self.user), [self.used_category],
        )
        self.assertQuerySetEqual(
            Transaction.objects.all(), [self.transaction],
        )

    def test_post_redirects_to_list(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('category_list'))

    def test_post_shows_success_message_only(self):
        response = self.client.post(self.url)
        self.assertEqual(message_texts(response), [DELETED_MESSAGE])

    def test_success_message_rendered_after_redirect(self):
        response = self.client.post(self.url, follow=True)
        self.assertContains(response, DELETED_MESSAGE)
        self.assertNotContains(response, DELETE_BLOCKED_MESSAGE)

    def test_unknown_pk_returns_404(self):
        url = reverse('category_delete', args=[self.category.pk + 1000])
        self.assertEqual(self.client.post(url).status_code, 404)


class AnonymousAccessTests(TestCase):
    """PRD 9.4.3: every category URL requires login."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        cls.category = create_category(
            cls.user, 'Salário', CategoryType.INCOME,
        )

    def assert_redirects_to_login(self, response, url):
        self.assertRedirects(response, f'{reverse("login")}?next={url}')

    def test_anonymous_list_redirects_to_login(self):
        url = reverse('category_list')
        self.assert_redirects_to_login(self.client.get(url), url)

    def test_anonymous_create_get_redirects_to_login(self):
        url = reverse('category_create')
        self.assert_redirects_to_login(self.client.get(url), url)

    def test_anonymous_create_post_redirects_and_creates_nothing(self):
        url = reverse('category_create')
        response = self.client.post(url, category_data())
        self.assert_redirects_to_login(response, url)
        self.assertEqual(Category.objects.count(), 1)

    def test_anonymous_update_get_redirects_to_login(self):
        url = reverse('category_update', args=[self.category.pk])
        self.assert_redirects_to_login(self.client.get(url), url)

    def test_anonymous_update_post_redirects_and_changes_nothing(self):
        url = reverse('category_update', args=[self.category.pk])
        response = self.client.post(url, category_data())
        self.assert_redirects_to_login(response, url)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Salário')

    def test_anonymous_delete_get_redirects_to_login(self):
        url = reverse('category_delete', args=[self.category.pk])
        self.assert_redirects_to_login(self.client.get(url), url)

    def test_anonymous_delete_post_redirects_and_deletes_nothing(self):
        url = reverse('category_delete', args=[self.category.pk])
        response = self.client.post(url)
        self.assert_redirects_to_login(response, url)
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())


class CategoryListIsolationTests(TestCase):
    """PRD 9.4.3: the list shows only the logged-in user's categories."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('category_list')
        cls.user = create_user()
        cls.other_user = create_user(email='joao@example.com')
        cls.newcomer = create_user(email='ana@example.com')
        cls.salary = create_category(cls.user, 'Salário', CategoryType.INCOME)
        cls.freelance = create_category(
            cls.user, 'Freelance', CategoryType.INCOME,
        )
        cls.food = create_category(
            cls.user, 'Alimentação', CategoryType.EXPENSE,
        )
        cls.foreign_income = create_category(
            cls.other_user, 'Renda Secreta do João', CategoryType.INCOME,
        )
        cls.foreign_expense = create_category(
            cls.other_user, 'Gasto Secreto do João', CategoryType.EXPENSE,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_returns_200_with_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'categories/category_list.html')

    def test_categories_context_has_only_own_categories(self):
        response = self.client.get(self.url)
        self.assertQuerySetEqual(
            response.context['categories'],
            [self.food, self.freelance, self.salary],
        )

    def test_income_context_has_only_own_income_categories(self):
        response = self.client.get(self.url)
        self.assertQuerySetEqual(
            response.context['income_categories'],
            [self.freelance, self.salary],
        )

    def test_expense_context_has_only_own_expense_categories(self):
        response = self.client.get(self.url)
        self.assertQuerySetEqual(
            response.context['expense_categories'], [self.food],
        )

    def test_renders_own_categories_with_actions(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Salário')
        self.assertContains(response, 'Freelance')
        self.assertContains(response, 'Alimentação')
        self.assertContains(
            response, reverse('category_update', args=[self.salary.pk]),
        )
        self.assertContains(
            response, reverse('category_delete', args=[self.salary.pk]),
        )

    def test_other_users_categories_are_not_rendered(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, 'Renda Secreta do João')
        self.assertNotContains(response, 'Gasto Secreto do João')
        self.assertNotContains(
            response,
            reverse('category_update', args=[self.foreign_income.pk]),
        )
        self.assertNotContains(
            response,
            reverse('category_delete', args=[self.foreign_expense.pk]),
        )

    def test_other_user_sees_only_own_categories(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.url)
        self.assertQuerySetEqual(
            response.context['income_categories'], [self.foreign_income],
        )
        self.assertQuerySetEqual(
            response.context['expense_categories'], [self.foreign_expense],
        )
        self.assertNotContains(response, 'Freelance')
        self.assertNotContains(response, 'Alimentação')

    def test_user_without_categories_sees_empty_states(self):
        self.client.force_login(self.newcomer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['categories'], [])
        self.assertQuerySetEqual(response.context['income_categories'], [])
        self.assertQuerySetEqual(response.context['expense_categories'], [])
        self.assertContains(response, EMPTY_INCOME_MESSAGE)
        self.assertContains(response, EMPTY_EXPENSE_MESSAGE)
        self.assertNotContains(response, 'Renda Secreta do João')


class CategoryCreateOwnershipTests(TestCase):
    """PRD 9.4.3: the create view assigns the logged-in user."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('category_create')
        cls.user = create_user()
        cls.other_user = create_user(email='joao@example.com')

    def setUp(self):
        self.client.force_login(self.user)

    def test_valid_post_creates_category(self):
        response = self.client.post(
            self.url,
            category_data(name='Moradia', category_type=CategoryType.EXPENSE),
        )
        self.assertRedirects(response, reverse('category_list'))
        category = Category.objects.get()
        self.assertEqual(category.name, 'Moradia')
        self.assertEqual(category.category_type, CategoryType.EXPENSE)

    def test_valid_post_assigns_request_user(self):
        self.client.post(self.url, category_data())
        self.assertEqual(Category.objects.get().user, self.user)

    def test_posted_user_field_is_ignored(self):
        self.client.post(
            self.url,
            category_data(user=self.other_user.pk, user_id=self.other_user.pk),
        )
        self.assertEqual(Category.objects.get().user, self.user)
        self.assertFalse(
            Category.objects.filter(user=self.other_user).exists(),
        )

    def test_each_user_creates_own_category(self):
        self.client.post(self.url, category_data())
        self.client.force_login(self.other_user)
        self.client.post(self.url, category_data())
        self.assertEqual(
            Category.objects.filter(user=self.user, name='Freelance').count(),
            1,
        )
        self.assertEqual(
            Category.objects.filter(
                user=self.other_user, name='Freelance',
            ).count(),
            1,
        )


class CategoryIsolationTests(TestCase):
    """PRD 9.4.3: another user's category returns 404 and stays unchanged."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = create_user()
        cls.intruder = create_user(email='joao@example.com')
        cls.category = create_category(
            cls.owner, 'Categoria da Maria', CategoryType.INCOME,
        )
        cls.update_url = reverse('category_update', args=[cls.category.pk])
        cls.delete_url = reverse('category_delete', args=[cls.category.pk])

    def setUp(self):
        self.client.force_login(self.intruder)

    def assert_category_unchanged(self):
        self.category.refresh_from_db()
        self.assertEqual(self.category.user, self.owner)
        self.assertEqual(self.category.name, 'Categoria da Maria')
        self.assertEqual(self.category.category_type, CategoryType.INCOME)

    def test_update_get_returns_404(self):
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 404)

    def test_update_post_returns_404_and_changes_nothing(self):
        response = self.client.post(self.update_url, category_data())
        self.assertEqual(response.status_code, 404)
        self.assert_category_unchanged()

    def test_update_post_shows_no_message(self):
        response = self.client.post(self.update_url, category_data())
        self.assertEqual(message_texts(response), [])

    def test_delete_get_returns_404(self):
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 404)

    def test_delete_post_returns_404_and_deletes_nothing(self):
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 404)
        self.assert_category_unchanged()

    def test_delete_post_shows_no_message(self):
        response = self.client.post(self.delete_url)
        self.assertEqual(message_texts(response), [])

    def test_delete_post_with_transactions_returns_404(self):
        # 404 comes before the RESTRICT check, so the intruder cannot tell
        # whether the category is in use.
        create_transaction(self.category)
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(message_texts(response), [])
        self.assert_category_unchanged()

    def test_404_page_does_not_leak_category_data(self):
        response = self.client.get(self.update_url)
        self.assertNotContains(response, 'Categoria da Maria', status_code=404)

    def test_list_does_not_show_other_users_category(self):
        response = self.client.get(reverse('category_list'))
        self.assertQuerySetEqual(response.context['categories'], [])
        self.assertNotContains(response, 'Categoria da Maria')
        self.assertNotContains(response, self.update_url)

    def test_intruder_can_reuse_owner_category_name(self):
        response = self.client.post(
            reverse('category_create'),
            category_data(name='Categoria da Maria'),
        )
        self.assertRedirects(response, reverse('category_list'))
        self.assertEqual(
            Category.objects.get(user=self.intruder).name,
            'Categoria da Maria',
        )
        self.assert_category_unchanged()

    def test_owner_still_has_access(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.update_url).status_code, 200)
        self.assertEqual(self.client.get(self.delete_url).status_code, 200)
