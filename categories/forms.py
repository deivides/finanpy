from django import forms

from core.forms import StyledFormMixin

from .models import Category

DUPLICATE_CATEGORY_MESSAGE = 'Você já possui uma categoria com este nome e tipo.'


class CategoryForm(StyledFormMixin, forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        # `user` is keyword-only, so it never reaches ModelForm.__init__.
        self.user = user
        super().__init__(*args, **kwargs)

    class Meta:
        model = Category
        fields = ('name', 'category_type')
        labels = {
            'name': 'Nome',
            'category_type': 'Tipo',
        }

    def clean(self):
        # The model's UniqueConstraint includes `user`, which is not a form
        # field, so ModelForm skips it; without this check a duplicate would
        # only fail at the database with an IntegrityError.
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        category_type = cleaned_data.get('category_type')
        if name and category_type and self.user is not None:
            duplicates = Category.objects.filter(
                user=self.user, name=name, category_type=category_type
            ).exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise forms.ValidationError(
                    DUPLICATE_CATEGORY_MESSAGE, code='duplicate_category'
                )
        return cleaned_data
