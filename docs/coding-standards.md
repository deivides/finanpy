# Coding standards

Standards defined in the [PRD](../PRD.md) that all project code must follow.

## Principles

- Simplicity, no over engineering.
- Prefer native Django features.
- Do not add dependencies or features outside the PRD scope.

## Style

- Code follows **PEP 8**.
- Use **single quotes** whenever possible.

```python
# correct
LANGUAGE_CODE = 'pt-br'

# avoid
LANGUAGE_CODE = "pt-br"
```

## Language

| Where | Language |
|---|---|
| Code (variables, classes, functions, models, URLs) | English |
| User-facing text (labels, messages, templates) | Brazilian Portuguese |

## Models

- Every model must have the audit fields:

```python
created_at = models.DateTimeField(auto_now_add=True)
updated_at = models.DateTimeField(auto_now=True)
```

- Monetary values always use `DecimalField`, never `float`.
- `verbose_name` in Portuguese.

## Views

- Prefer **Class Based Views**.
- Internal pages require authentication (`LoginRequiredMixin`).
- Data isolation: every query for user data must be filtered by `request.user`. List/Detail/Update/Delete views use `LoginRequiredMixin` + `UserQuerySetMixin` (`core/views.py`), in that order, so another user's pk returns 404. Create views set `form.instance.user = self.request.user` in `form_valid`.

## Signals

- Signals live in `signals.py` inside the corresponding app and are imported in the `ready()` method of the app's `AppConfig`.

## Security

- CSRF protection on all forms (`{% csrf_token %}`).
- Passwords validated by the native `AUTH_PASSWORD_VALIDATORS`.

## Frontend

- Templates with Django Template Language; no frontend JavaScript frameworks.
- Styling exclusively with TailwindCSS, following the [design system](design-system.md).

## Database

- Django's default SQLite.
- Generate migrations per app (`makemigrations <app>`) whenever a model changes.
