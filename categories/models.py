from django.conf import settings
from django.db import models


class CategoryType(models.TextChoices):
    INCOME = 'income', 'Entrada'
    EXPENSE = 'expense', 'Saída'


class Category(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='categories',
        verbose_name='usuário',
    )
    name = models.CharField('nome', max_length=100)
    category_type = models.CharField(
        'tipo',
        max_length=10,
        choices=CategoryType.choices,
    )
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        ordering = ['category_type', 'name']
        verbose_name = 'categoria'
        verbose_name_plural = 'categorias'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name', 'category_type'],
                name='unique_user_category',
            ),
        ]

    def __str__(self):
        return self.name
