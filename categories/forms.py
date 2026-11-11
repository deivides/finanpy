from django import forms

from core.forms import StyledFormMixin

from .models import Category

DUPLICATE_CATEGORY_MESSAGE = (
    'Você já possui uma categoria com este nome e tipo.'
)
TYPE_CHANGE_IN_USE_MESSAGE = (
    'Não é possível alterar o tipo de uma categoria que possui transações.'
)


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
        # The transaction type must match the category type (RF21), so a
        # category already in use cannot switch type. ModelForm only copies
        # cleaned_data to the instance after clean(), so instance still
        # holds the stored type here.
        if (
            self.instance.pk
            and category_type
            and category_type != self.instance.category_type
            and self.instance.transactions.exists()
        ):
            self.add_error(
                'category_type',
                forms.ValidationError(
                    TYPE_CHANGE_IN_USE_MESSAGE, code='category_in_use'
                ),
            )
        return cleaned_data
