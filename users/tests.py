from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import TestCase
from django.urls import reverse

from users.forms import LoginForm, SignUpForm

User = get_user_model()

PASSWORD = 'Sup3r-Segura-2026!'
DUPLICATE_EMAIL_MESSAGE = 'Já existe um usuário com este e-mail.'
INVALID_LOGIN_MESSAGE = (
    'E-mail ou senha inválidos. Verifique os dados e tente novamente.'
)
REQUIRED_MESSAGE = 'Este campo é obrigatório.'


def create_user(email='maria@example.com', password=PASSWORD, **extra):
    extra.setdefault('first_name', 'Maria')
    extra.setdefault('last_name', 'Silva')
    return User.objects.create_user(email=email, password=password, **extra)


def signup_data(**overrides):
    data = {
        'first_name': 'João',
        'last_name': 'Souza',
        'email': 'joao@example.com',
        'password1': PASSWORD,
        'password2': PASSWORD,
    }
    data.update(overrides)
    return data


class UserManagerCreateUserTests(TestCase):
    """PRD 9.1.1 and 9.1.2: UserManager.create_user."""

    def test_create_user_lowercases_email_domain(self):
        user = create_user(email='maria@EXAMPLE.COM')
        self.assertEqual(user.email, 'maria@example.com')

    def test_create_user_lowercases_email_local_part(self):
        # The manager calls normalize_email() and then .lower() on the
        # whole address, so the local part is lowercased as well.
        user = create_user(email='Maria.Silva@Example.com')
        self.assertEqual(user.email, 'maria.silva@example.com')

    def test_create_user_hashes_password(self):
        user = create_user()
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.check_password('senha-errada'))

    def test_create_user_without_password_has_unusable_password(self):
        user = create_user(password=None)
        self.assertFalse(user.has_usable_password())

    def test_create_user_is_not_staff_nor_superuser(self):
        user = create_user()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_user_has_no_username(self):
        user = create_user()
        self.assertIsNone(getattr(user, 'username', None))
        self.assertEqual(User.USERNAME_FIELD, 'email')
        self.assertEqual(user.get_username(), 'maria@example.com')

    def test_create_user_persists_names(self):
        user = create_user()
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Maria')
        self.assertEqual(user.last_name, 'Silva')

    def test_str_returns_email(self):
        user = create_user()
        self.assertEqual(str(user), 'maria@example.com')

    def test_create_user_with_none_email_raises_value_error(self):
        with self.assertRaisesMessage(ValueError, 'O e-mail é obrigatório.'):
            User.objects.create_user(email=None, password=PASSWORD)
        self.assertFalse(User.objects.exists())

    def test_create_user_with_empty_email_raises_value_error(self):
        with self.assertRaisesMessage(ValueError, 'O e-mail é obrigatório.'):
            User.objects.create_user(email='', password=PASSWORD)
        self.assertFalse(User.objects.exists())


class UserManagerCreateSuperuserTests(TestCase):
    """PRD 9.1.3: UserManager.create_superuser."""

    def test_create_superuser_sets_staff_and_superuser_flags(self):
        admin = User.objects.create_superuser(
            email='Admin@Example.com', password=PASSWORD,
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)
        self.assertEqual(admin.email, 'admin@example.com')
        self.assertTrue(admin.check_password(PASSWORD))

    def test_create_superuser_with_is_staff_false_raises_value_error(self):
        with self.assertRaisesMessage(
            ValueError, 'O superusuário precisa ter is_staff=True.',
        ):
            User.objects.create_superuser(
                email='admin@example.com', password=PASSWORD, is_staff=False,
            )
        self.assertFalse(User.objects.exists())

    def test_create_superuser_with_is_superuser_false_raises_value_error(
        self,
    ):
        with self.assertRaisesMessage(
            ValueError, 'O superusuário precisa ter is_superuser=True.',
        ):
            User.objects.create_superuser(
                email='admin@example.com',
                password=PASSWORD,
                is_superuser=False,
            )
        self.assertFalse(User.objects.exists())


class SignUpViewTests(TestCase):
    """PRD 9.1.4 and 9.1.5: sign up view."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('signup')
        cls.existing_user = create_user()

    def test_get_renders_signup_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/signup.html')
        self.assertIsInstance(response.context['form'], SignUpForm)

    def test_valid_signup_creates_user(self):
        self.client.post(self.url, signup_data())
        user = User.objects.get(email='joao@example.com')
        self.assertEqual(user.first_name, 'João')
        self.assertEqual(user.last_name, 'Souza')
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.is_staff)

    def test_valid_signup_redirects_to_dashboard(self):
        response = self.client.post(self.url, signup_data())
        self.assertRedirects(response, reverse('dashboard'))

    def test_valid_signup_logs_user_in(self):
        response = self.client.post(self.url, signup_data(), follow=True)
        user = User.objects.get(email='joao@example.com')
        self.assertEqual(int(self.client.session[SESSION_KEY]), user.pk)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user, user)

    def test_valid_signup_normalizes_email_to_lowercase(self):
        self.client.post(
            self.url, signup_data(email='  Joao.Souza@Example.COM  '),
        )
        self.assertTrue(
            User.objects.filter(email='joao.souza@example.com').exists(),
        )

    def test_authenticated_user_is_redirected_to_dashboard(self):
        self.client.force_login(self.existing_user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('dashboard'))

    def test_authenticated_user_post_does_not_create_user(self):
        self.client.force_login(self.existing_user)
        response = self.client.post(self.url, signup_data())
        self.assertRedirects(response, reverse('dashboard'))
        self.assertFalse(User.objects.filter(email='joao@example.com').exists())

    def test_first_name_is_required(self):
        response = self.client.post(self.url, signup_data(first_name=''))
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], 'first_name', REQUIRED_MESSAGE,
        )
        self.assertFalse(User.objects.filter(email='joao@example.com').exists())

    def test_last_name_is_required(self):
        response = self.client.post(self.url, signup_data(last_name=''))
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], 'last_name', REQUIRED_MESSAGE,
        )
        self.assertFalse(User.objects.filter(email='joao@example.com').exists())

    def test_password_mismatch_is_rejected(self):
        response = self.client.post(
            self.url, signup_data(password2='Outra-Senha-2026!'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('password2', response.context['form'].errors)
        self.assertFalse(User.objects.filter(email='joao@example.com').exists())
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_duplicate_email_is_rejected(self):
        response = self.client.post(
            self.url, signup_data(email='maria@example.com'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], 'email', DUPLICATE_EMAIL_MESSAGE,
        )
        self.assertContains(response, DUPLICATE_EMAIL_MESSAGE)
        self.assertEqual(User.objects.count(), 1)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_duplicate_email_with_different_case_is_rejected(self):
        response = self.client.post(
            self.url, signup_data(email='MARIA@Example.COM'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], 'email', DUPLICATE_EMAIL_MESSAGE,
        )
        self.assertEqual(User.objects.count(), 1)
        self.assertNotIn(SESSION_KEY, self.client.session)


class LoginViewTests(TestCase):
    """PRD 9.1.6: login by e-mail."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('login')
        cls.user = create_user()

    def test_get_renders_login_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/login.html')
        self.assertIsInstance(response.context['form'], LoginForm)

    def test_login_with_email_redirects_to_dashboard(self):
        response = self.client.post(
            self.url, {'username': 'maria@example.com', 'password': PASSWORD},
        )
        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)

    def test_login_email_is_case_insensitive(self):
        response = self.client.post(
            self.url,
            {'username': '  MARIA@Example.COM ', 'password': PASSWORD},
        )
        self.assertRedirects(response, reverse('dashboard'))
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)

    def test_login_with_wrong_password_shows_error(self):
        response = self.client.post(
            self.url,
            {'username': 'maria@example.com', 'password': 'senha-errada'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], None, INVALID_LOGIN_MESSAGE,
        )
        self.assertContains(response, INVALID_LOGIN_MESSAGE)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_login_with_unknown_email_shows_error(self):
        response = self.client.post(
            self.url,
            {'username': 'ninguem@example.com', 'password': PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'], None, INVALID_LOGIN_MESSAGE,
        )
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_with_inactive_user_fails(self):
        create_user(email='inativo@example.com', is_active=False)
        response = self.client.post(
            self.url,
            {'username': 'inativo@example.com', 'password': PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_authenticated_user_is_redirected_to_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse('dashboard'))


class LogoutViewTests(TestCase):
    """PRD 9.1.7: logout via POST."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('logout')
        cls.user = create_user()

    def setUp(self):
        self.client.force_login(self.user)

    def test_logout_post_redirects_to_home(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('home'))

    def test_logout_post_ends_session(self):
        self.client.post(self.url)
        self.assertNotIn(SESSION_KEY, self.client.session)
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(
            response, f'{reverse("login")}?next={reverse("dashboard")}',
        )

    def test_logout_get_is_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.user.pk)


class UserAdminEmailNormalizationTests(TestCase):
    """Users saved through the admin keep the lowercase e-mail rule."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password=PASSWORD,
            first_name='Ana',
            last_name='Admin',
        )
        cls.user = create_user()

    def setUp(self):
        self.client.force_login(self.admin_user)

    def test_admin_add_form_lowercases_email(self):
        response = self.client.post(
            reverse('admin:users_user_add'),
            {
                'email': '  Joao.Souza@EXAMPLE.com ',
                'first_name': 'João',
                'last_name': 'Souza',
                'usable_password': 'true',
                'password1': PASSWORD,
                'password2': PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            User.objects.filter(email='joao.souza@example.com').exists(),
        )

    def test_user_created_in_admin_can_log_in_with_lowercase_email(self):
        self.client.post(
            reverse('admin:users_user_add'),
            {
                'email': 'Joao@Example.COM',
                'first_name': 'João',
                'last_name': 'Souza',
                'usable_password': 'true',
                'password1': PASSWORD,
                'password2': PASSWORD,
            },
        )
        self.client.logout()
        response = self.client.post(
            reverse('login'),
            {'username': 'joao@example.com', 'password': PASSWORD},
        )
        self.assertRedirects(response, reverse('dashboard'))

    def test_admin_change_form_lowercases_email(self):
        response = self.client.post(
            reverse('admin:users_user_change', args=[self.user.pk]),
            {
                'email': 'Maria.Nova@EXAMPLE.com',
                'first_name': 'Maria',
                'last_name': 'Silva',
                'is_active': 'on',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'maria.nova@example.com')

    def test_admin_change_form_rejects_duplicate_email_in_other_case(self):
        response = self.client.post(
            reverse('admin:users_user_change', args=[self.user.pk]),
            {
                'email': 'ADMIN@example.com',
                'first_name': 'Maria',
                'last_name': 'Silva',
                'is_active': 'on',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['adminform'].form.is_valid())
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'maria@example.com')
