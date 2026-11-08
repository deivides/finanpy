from django import forms
from django.contrib.auth import get_user_model

from core.forms import StyledFormMixin

from .models import Profile


class UserNameForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name')
        labels = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('phone', 'birth_date')
        labels = {
            'phone': 'Telefone',
            'birth_date': 'Data de nascimento',
        }
        widgets = {
            'birth_date': forms.DateInput(
                attrs={'type': 'date'},
                format='%Y-%m-%d',
            ),
        }
