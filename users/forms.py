from django import forms
from django.contrib.auth.forms import (
    AdminUserCreationForm,
    AuthenticationForm,
    UserChangeForm,
    UserCreationForm,
)

from core.forms import StyledFormMixin

from .models import User


class UserAdminCreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ('email', 'first_name', 'last_name')
        field_classes = {}

    def clean_email(self):
        email = self.cleaned_data.get('email')
        return email.strip().lower() if email else email


class UserAdminChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'
        field_classes = {}

    def clean_email(self):
        email = self.cleaned_data.get('email')
        return email.strip().lower() if email else email


class SignUpForm(StyledFormMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('first_name', 'last_name', 'email')
        field_classes = {}
        labels = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'email': 'E-mail',
        }
        error_messages = {
            'email': {
                'unique': 'Já existe uma conta com este e-mail.',
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['first_name'].widget.attrs['autofocus'] = True
        self.fields['email'].widget.attrs.pop('autofocus', None)
        self.fields['password1'].label = 'Senha'
        self.fields['password2'].label = 'Confirmação de senha'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        return email.strip().lower() if email else email


class LoginForm(StyledFormMixin, AuthenticationForm):
    username = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(
            attrs={'autofocus': True, 'autocomplete': 'email'},
        ),
    )
    password = forms.CharField(
        label='Senha',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )

    error_messages = {
        'invalid_login': (
            'E-mail ou senha inválidos. Verifique os dados e tente novamente.'
        ),
        'inactive': 'Esta conta está inativa.',
    }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        return username.strip().lower() if username else username
