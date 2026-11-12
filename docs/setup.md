# Development environment

## Prerequisites

- Python 3 installed (the project uses Python 3.14).
- Git.

## Installation

```bash
# clone the repository
git clone <repository-url> finanpy
cd finanpy

# create the virtual environment
python -m venv .venv

# activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# activate (Linux/macOS)
source .venv/bin/activate

# install dependencies
pip install -r requirements.txt
```

On Linux/macOS, use `python3` instead of `python` if `python` is not available.

## Running

```bash
# apply migrations
python manage.py migrate

# create an admin user (optional)
python manage.py createsuperuser

# start the development server
python manage.py runserver
```

The application is available at `http://127.0.0.1:8000/` and the admin at `http://127.0.0.1:8000/admin/`.

## Tests

```bash
python manage.py test                                   # all tests
python manage.py test accounts                          # one app
python manage.py test accounts.tests.SomeTest.test_x    # single test
```

### Coverage

`coverage` is a development tool and is not listed in `requirements.txt`. The configuration is in `.coveragerc` at the project root (branch coverage; `.venv`, migrations, `manage.py`, `core/asgi.py` and `core/wsgi.py` are omitted). The minimum coverage defined in the PRD is 80%.

```bash
pip install coverage
coverage run manage.py test
coverage report -m
```

## Lint (PEP 8)

`ruff` is a development tool and is not listed in `requirements.txt`. The configuration is in `ruff.toml` at the project root (line length 79, rules `E`, `W`, `F`, `I` and `Q` with single quotes).

```bash
pip install ruff
ruff check .
```

## Useful commands

| Command | Purpose |
|---|---|
| `python manage.py makemigrations <app>` | Generate migrations for an app |
| `python manage.py migrate` | Apply migrations |
| `python manage.py createsuperuser` | Create an admin user |
| `python manage.py test` | Run the automated tests |
| `coverage run manage.py test` | Run the tests and measure coverage |
| `coverage report -m` | Show the coverage report with the missing lines |
| `ruff check .` | Check PEP 8, imports and quotes |
| `pip freeze > requirements.txt` | Update the dependency list (do not include `ruff` or `coverage`) |

## Files ignored by git

The `.gitignore` already ignores, among others: `.venv/`, `__pycache__/`, `*.pyc`, `db.sqlite3`, `.env`, `.coverage` and `htmlcov/`.
