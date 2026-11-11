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

Development tool (not in `requirements.txt`): `ruff`, the PEP 8 linter configured in `ruff.toml`.

## Project apps

| App | Responsibility |
|---|---|
| `core` | Django project: global settings (`settings.py`) and root URLs |
| `users` | System user |
| `profiles` | User profile |
| `accounts` | Bank accounts |
| `categories` | Transaction categories |
| `transactions` | Income and expense transactions |

> Current state: Sprints 0–7 are implemented: custom user, profile, bank accounts (with computed balance), categories and transactions (CRUD, month/type filters, filtered totals, pagination). Sprint 8 is done: dashboard (total balance, month income/expenses/result, latest transactions, accounts), design system review and code review (`ruff check .` clean). Automated tests (Sprint 9) and Docker (Sprint 10) are pending.
