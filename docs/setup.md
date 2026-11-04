# Development environment

## Prerequisites

- Python 3 installed.

## Installation

```bash
# create the virtual environment
python -m venv .venv

# activate (Windows)
.venv\Scripts\activate

# activate (Linux/macOS)
source .venv/bin/activate

# install dependencies
pip install -r requirements.txt
```

## Running

```bash
# apply migrations
python manage.py migrate

# start the development server
python manage.py runserver
```

The application is available at `http://127.0.0.1:8000/` and the admin at `http://127.0.0.1:8000/admin/`.

## Useful commands

| Command | Purpose |
|---|---|
| `python manage.py makemigrations <app>` | Generate migrations for an app |
| `python manage.py migrate` | Apply migrations |
| `python manage.py createsuperuser` | Create an admin user |
| `pip freeze > requirements.txt` | Update the dependency list |

## Files ignored by git

The `.gitignore` already ignores, among others: `.venv/`, `__pycache__/`, `*.pyc`, `db.sqlite3` and `.env`.
