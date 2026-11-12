import datetime

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.db.models.signals import post_save
from django.test import TestCase
from django.urls import reverse

from profiles.forms import ProfileForm, UserNameForm
from profiles.models import Profile

User = get_user_model()

PASSWORD = 'Sup3r-Segura-2026!'
SUCCESS_MESSAGE = 'Perfil atualizado com sucesso.'
REQUIRED_MESSAGE = 'Este campo é obrigatório.'
INVALID_DATE_MESSAGE = 'Informe uma data válida.'


def create_user(email='maria@example.com', password=PASSWORD, **extra):
    extra.setdefault('first_name', 'Maria')
    extra.setdefault('last_name', 'Silva')
    return User.objects.create_user(email=email, password=password, **extra)


def profile_data(**overrides):
    data = {
        'first_name': 'Mariana',
        'last_name': 'Souza',
        'phone': '(11) 98888-7777',
        'birth_date': '1990-05-20',
    }
    data.update(overrides)
    return data


class ProfileSignalTests(TestCase):
    """PRD 9.2.1: the post_save signal creates the Profile."""

    def test_create_user_creates_profile(self):
        user = create_user()
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_create_user_creates_exactly_one_profile(self):
        user = create_user()
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)

    def test_create_superuser_creates_profile(self):
        admin = User.objects.create_superuser(
            email='admin@example.com', password=PASSWORD,
        )
        self.assertEqual(Profile.objects.filter(user=admin).count(), 1)

    def test_new_profile_has_empty_phone_and_birth_date(self):
        profile = create_user().profile
        self.assertEqual(profile.phone, '')
        self.assertIsNone(profile.birth_date)

    def test_profile_is_reachable_through_related_name(self):
        user = create_user()
        self.assertEqual(user.profile, Profile.objects.get(user=user))

    def test_saving_existing_user_does_not_create_second_profile(self):
        user = create_user()
        profile_id = user.profile.pk
        user.first_name = 'Mariana'
        user.save()
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)
        self.assertEqual(Profile.objects.get(user=user).pk, profile_id)

    def test_saving_existing_user_keeps_profile_data(self):
        user = create_user()
        Profile.objects.filter(user=user).update(phone='11999990000')
        user.last_name = 'Oliveira'
        user.save()
        self.assertEqual(Profile.objects.get(user=user).phone, '11999990000')

    def test_each_user_gets_own_profile(self):
        create_user()
        create_user(email='joao@example.com')
        self.assertEqual(Profile.objects.count(), 2)
        self.assertEqual(User.objects.count(), 2)

    def test_raw_save_does_not_create_profile(self):
        # loaddata sends post_save with raw=True; the fixture is expected
        # to carry its own Profile rows, so the signal must skip them.
        user = create_user()
        user.profile.delete()
        post_save.send(sender=User, instance=user, created=True, raw=True)
        self.assertFalse(Profile.objects.filter(user=user).exists())

    def test_deleting_user_deletes_profile(self):
        user = create_user()
        user.delete()
        self.assertEqual(Profile.objects.count(), 0)

    def test_signup_view_creates_profile(self):
        response = self.client.post(reverse('signup'), {
            'first_name': 'João',
            'last_name': 'Souza',
            'email': 'joao@example.com',
            'password1': PASSWORD,
            'password2': PASSWORD,
        })
        self.assertRedirects(response, reverse('dashboard'))
        user = User.objects.get(email='joao@example.com')
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)

    def test_str_mentions_user(self):
        profile = create_user().profile
        self.assertEqual(str(profile), 'Perfil de maria@example.com')


class ProfileFormTests(TestCase):
    """PRD 9.2.2: form rules used by the profile page."""

    def test_user_name_form_requires_first_name(self):
        form = UserNameForm(data={'first_name': '', 'last_name': 'Silva'})
        self.assertFormError(form, 'first_name', REQUIRED_MESSAGE)

    def test_user_name_form_requires_last_name(self):
        form = UserNameForm(data={'first_name': 'Maria', 'last_name': ''})
        self.assertFormError(form, 'last_name', REQUIRED_MESSAGE)

    def test_user_name_form_does_not_expose_email(self):
        self.assertEqual(
            list(UserNameForm().fields), ['first_name', 'last_name'],
        )

    def test_profile_form_fields_are_optional(self):
        form = ProfileForm(data={'phone': '', 'birth_date': ''})
        self.assertTrue(form.is_valid(), form.errors)

    def test_profile_form_does_not_expose_user(self):
        self.assertEqual(list(ProfileForm().fields), ['phone', 'birth_date'])

    def test_profile_form_rejects_invalid_date(self):
        form = ProfileForm(data={'phone': '', 'birth_date': '2023-02-30'})
        self.assertFormError(form, 'birth_date', INVALID_DATE_MESSAGE)

    def test_birth_date_widget_is_html5_date(self):
        form = ProfileForm(
            instance=Profile(birth_date=datetime.date(1990, 5, 20)),
        )
        html = str(form['birth_date'])
        self.assertIn('type="date"', html)
        self.assertIn('value="1990-05-20"', html)


class ProfileUpdateViewTests(TestCase):
    """PRD 9.2.2: editing the profile updates User and Profile."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        Profile.objects.filter(user=cls.user).update(
            phone='(11) 91111-2222',
            birth_date=datetime.date(1985, 1, 15),
        )
        cls.other = create_user(
            email='joao@example.com', first_name='João', last_name='Souza',
        )
        Profile.objects.filter(user=cls.other).update(
            phone='(21) 93333-4444',
            birth_date=datetime.date(1970, 12, 31),
        )
        cls.url = reverse('profile')

    def setUp(self):
        self.client.force_login(self.user)

    def assert_user_unchanged(self):
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Maria')
        self.assertEqual(self.user.last_name, 'Silva')
        self.assertEqual(self.user.email, 'maria@example.com')

    def assert_profile_unchanged(self):
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.phone, '(11) 91111-2222')
        self.assertEqual(profile.birth_date, datetime.date(1985, 1, 15))

    # Access control -------------------------------------------------------

    def test_anonymous_get_redirects_to_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(
            response, f'{reverse("login")}?next={self.url}',
        )

    def test_anonymous_post_redirects_to_login_and_changes_nothing(self):
        self.client.logout()
        response = self.client.post(self.url, profile_data())
        self.assertRedirects(
            response, f'{reverse("login")}?next={self.url}',
        )
        self.assert_user_unchanged()
        self.assert_profile_unchanged()

    # GET ------------------------------------------------------------------

    def test_get_returns_200_with_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profiles/profile_form.html')

    def test_get_context_has_both_forms_bound_to_current_user(self):
        response = self.client.get(self.url)
        user_form = response.context['user_form']
        profile_form = response.context['profile_form']
        self.assertIsInstance(user_form, UserNameForm)
        self.assertIsInstance(profile_form, ProfileForm)
        self.assertEqual(user_form.instance, self.user)
        self.assertEqual(profile_form.instance, self.user.profile)

    def test_get_renders_current_data(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'value="Maria"')
        self.assertContains(response, 'value="Silva"')
        self.assertContains(response, 'value="(11) 91111-2222"')
        self.assertContains(response, 'value="1985-01-15"')

    def test_get_does_not_render_other_user_data(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, 'joao@example.com')
        self.assertNotContains(response, '(21) 93333-4444')
        self.assertNotContains(response, '1970-12-31')

    def test_get_shows_email_read_only_without_name(self):
        response = self.client.get(self.url)
        self.assertContains(
            response,
            '<input type="email" id="profile-email" '
            'value="maria@example.com" '
            'class="form-input cursor-not-allowed text-slate-400" readonly '
            'aria-describedby="profile-email_helptext">',
            html=True,
        )
        self.assertNotContains(response, 'name="email"')
        self.assertContains(
            response, 'O e-mail é usado para entrar e não pode ser alterado.',
        )

    # Valid POST -----------------------------------------------------------

    def test_valid_post_redirects_to_profile_page(self):
        response = self.client.post(self.url, profile_data())
        self.assertRedirects(response, self.url)

    def test_valid_post_updates_user_names(self):
        self.client.post(self.url, profile_data())
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Mariana')
        self.assertEqual(self.user.last_name, 'Souza')

    def test_valid_post_updates_profile(self):
        self.client.post(self.url, profile_data())
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.phone, '(11) 98888-7777')
        self.assertEqual(profile.birth_date, datetime.date(1990, 5, 20))

    def test_valid_post_shows_success_message(self):
        response = self.client.post(self.url, profile_data())
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertEqual(messages, [SUCCESS_MESSAGE])

    def test_valid_post_message_rendered_after_redirect(self):
        response = self.client.post(self.url, profile_data(), follow=True)
        self.assertContains(response, SUCCESS_MESSAGE)

    def test_valid_post_can_clear_optional_profile_fields(self):
        self.client.post(self.url, profile_data(phone='', birth_date=''))
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.phone, '')
        self.assertIsNone(profile.birth_date)

    def test_valid_post_does_not_create_extra_profile(self):
        self.client.post(self.url, profile_data())
        self.assertEqual(Profile.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Profile.objects.count(), 2)

    def test_post_ignores_email_field(self):
        response = self.client.post(
            self.url, profile_data(email='hacker@example.com'),
        )
        self.assertRedirects(response, self.url)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'maria@example.com')
        self.assertFalse(
            User.objects.filter(email='hacker@example.com').exists(),
        )

    def test_post_ignores_privilege_fields(self):
        self.client.post(
            self.url,
            profile_data(is_staff='on', is_superuser='on', is_active=''),
        )
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertTrue(self.user.is_active)

    # Isolation ------------------------------------------------------------

    def test_post_only_edits_request_user(self):
        self.client.post(self.url, profile_data())
        self.other.refresh_from_db()
        other_profile = Profile.objects.get(user=self.other)
        self.assertEqual(self.other.first_name, 'João')
        self.assertEqual(self.other.last_name, 'Souza')
        self.assertEqual(other_profile.phone, '(21) 93333-4444')
        self.assertEqual(other_profile.birth_date, datetime.date(1970, 12, 31))

    def test_post_with_foreign_ids_cannot_touch_other_user(self):
        other_profile = Profile.objects.get(user=self.other)
        self.client.post(
            self.url,
            profile_data(
                id=other_profile.pk,
                user=self.other.pk,
                user_id=self.other.pk,
            ),
        )
        other_profile.refresh_from_db()
        self.assertEqual(other_profile.user, self.other)
        self.assertEqual(other_profile.phone, '(21) 93333-4444')
        own_profile = Profile.objects.get(user=self.user)
        self.assertEqual(own_profile.phone, '(11) 98888-7777')
        self.assertEqual(Profile.objects.count(), 2)

    def test_logged_in_as_other_user_edits_only_their_profile(self):
        self.client.force_login(self.other)
        self.client.post(self.url, profile_data(first_name='Joana'))
        self.other.refresh_from_db()
        self.assertEqual(self.other.first_name, 'Joana')
        self.assert_user_unchanged()
        self.assert_profile_unchanged()

    # Invalid POST ---------------------------------------------------------

    def test_empty_first_name_rerenders_with_error(self):
        response = self.client.post(self.url, profile_data(first_name=''))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profiles/profile_form.html')
        self.assertFormError(
            response.context['user_form'], 'first_name', REQUIRED_MESSAGE,
        )
        self.assertContains(response, REQUIRED_MESSAGE)

    def test_empty_first_name_saves_neither_form(self):
        self.client.post(self.url, profile_data(first_name=''))
        self.assert_user_unchanged()
        self.assert_profile_unchanged()

    def test_empty_last_name_saves_neither_form(self):
        response = self.client.post(self.url, profile_data(last_name=''))
        self.assertFormError(
            response.context['user_form'], 'last_name', REQUIRED_MESSAGE,
        )
        self.assert_user_unchanged()
        self.assert_profile_unchanged()

    def test_invalid_date_rerenders_with_error(self):
        response = self.client.post(
            self.url, profile_data(birth_date='2023-02-30'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['profile_form'], 'birth_date',
            INVALID_DATE_MESSAGE,
        )
        self.assertContains(response, INVALID_DATE_MESSAGE)

    def test_invalid_date_saves_neither_form(self):
        self.client.post(self.url, profile_data(birth_date='não é data'))
        self.assert_user_unchanged()
        self.assert_profile_unchanged()

    def test_phone_too_long_saves_neither_form(self):
        response = self.client.post(self.url, profile_data(phone='9' * 21))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['profile_form'].errors['phone'])
        self.assert_user_unchanged()
        self.assert_profile_unchanged()

    def test_both_forms_invalid_reports_both_errors(self):
        response = self.client.post(
            self.url, profile_data(first_name='', birth_date='31/02/2023'),
        )
        self.assertFormError(
            response.context['user_form'], 'first_name', REQUIRED_MESSAGE,
        )
        self.assertFormError(
            response.context['profile_form'], 'birth_date',
            INVALID_DATE_MESSAGE,
        )
        self.assert_user_unchanged()
        self.assert_profile_unchanged()

    def test_invalid_post_keeps_submitted_values(self):
        response = self.client.post(
            self.url, profile_data(first_name='', phone='(11) 95555-0000'),
        )
        self.assertContains(response, 'value="(11) 95555-0000"')
        self.assertContains(response, 'value="Souza"')

    def test_invalid_post_shows_no_success_message(self):
        response = self.client.post(self.url, profile_data(first_name=''))
        self.assertEqual(list(get_messages(response.wsgi_request)), [])


class ProfileUpdateViewMissingProfileTests(TestCase):
    """PRD 9.2.2: the view recreates a missing Profile (get_or_create)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = create_user()
        Profile.objects.filter(user=cls.user).delete()
        cls.url = reverse('profile')

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_creates_missing_profile(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Profile.objects.filter(user=self.user).count(), 1)

    def test_valid_post_creates_and_fills_missing_profile(self):
        response = self.client.post(self.url, profile_data())
        self.assertRedirects(response, self.url)
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.phone, '(11) 98888-7777')
        self.assertEqual(profile.birth_date, datetime.date(1990, 5, 20))

    def test_repeated_get_keeps_single_profile(self):
        self.client.get(self.url)
        self.client.get(self.url)
        self.assertEqual(Profile.objects.filter(user=self.user).count(), 1)
