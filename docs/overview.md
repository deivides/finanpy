# Overview

**Finanpy** is a personal finance management web application built with **Python + Django full stack**. The project's premise is **simplicity and no over engineering**: native Django features and nothing beyond the scope described in the [PRD](../PRD.md).

## Stack

| Layer | Technology |
|---|---|
| Language | Python (virtual environment created with Python 3.14) |
| Framework | Django 6.1.2 |
| Database | SQLite (Django default, `db.sqlite3` file) |
| Frontend (defined in the PRD) | Django Template Language + TailwindCSS |

Installed dependencies (`requirements.txt`):

- `Django==6.1.2`
- `asgiref==3.13.0`
- `sqlparse==0.6.1`
- `tzdata==2026.6`

## Project apps

| App | Responsibility |
|---|---|
| `core` | Django project: global settings (`settings.py`) and root URLs |
| `users` | System user |
| `profiles` | User profile |
| `accounts` | Bank accounts |
| `categories` | Transaction categories |
| `transactions` | Income and expense transactions |

> Current state: the apps have been created and registered in `INSTALLED_APPS`, but they do not have models, views, URLs or templates yet. The only existing route is `admin/`.
