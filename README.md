# Finanpy

Aplicação web de gestão de finanças pessoais construída com Django full stack (templates DTL + TailwindCSS). O escopo, o modelo de dados e o planejamento estão no [PRD](PRD.md). A documentação técnica está em [docs/](docs/README.md).

## Requisitos

- Python 3.14
- Git

## Instalação e execução

### Windows (PowerShell)

```powershell
git clone <url-do-repositorio> finanpy
cd finanpy
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Se o PowerShell bloquear o script de ativação, libere scripts locais para o usuário atual com `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e ative o ambiente de novo.

### Linux/macOS

```bash
git clone <url-do-repositorio> finanpy
cd finanpy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

O `createsuperuser` é opcional e pede e-mail, nome, sobrenome e senha (o login é feito por e-mail).

### Endereços

| Página | URL |
|---|---|
| Página inicial | `http://127.0.0.1:8000/` |
| Admin do Django | `http://127.0.0.1:8000/admin/` |

### Testes

Com o ambiente virtual ativado:

```bash
python manage.py test                 # todos os testes
python manage.py test accounts        # testes de um app
```

### Cobertura de testes

O `coverage` é uma ferramenta de desenvolvimento e não faz parte do `requirements.txt`. A configuração está em `.coveragerc` e a cobertura mínima definida no PRD é de 80%.

```bash
pip install coverage
coverage run manage.py test
coverage report -m
```

### Lint (PEP 8)

O `ruff` é uma ferramenta de desenvolvimento e não faz parte do `requirements.txt`. A configuração está em `ruff.toml` (linhas de até 79 caracteres, ordem de imports e aspas simples).

```bash
pip install ruff
ruff check .
```

Mais detalhes em [docs/setup.md](docs/setup.md).

## Convenções de código

| Regra | Detalhe |
|---|---|
| Idioma do código | Inglês: variáveis, classes, funções, models e URLs |
| Idioma da interface | Português brasileiro: labels, mensagens, `verbose_name` e templates |
| Estilo | PEP 8, verificado com `ruff check .` |
| Aspas | Aspas simples sempre que possível. As exceções são docstrings (`"""`) e strings que contêm apóstrofo |
| Views | Prefira Class Based Views e recursos nativos do Django |
| Models | Todo model tem `created_at` e `updated_at`. Valores monetários usam `DecimalField` |
| Escopo | Nada de dependências ou funcionalidades fora do PRD |

### Isolamento de dados

Toda view que acessa dados do usuário usa `LoginRequiredMixin` + `UserQuerySetMixin` (`core/views.py`), nessa ordem. O mixin filtra `get_queryset()` por `request.user`, então um objeto de outro usuário retorna 404.

```python
class AccountListView(LoginRequiredMixin, UserQuerySetMixin, ListView):
    model = Account
```

Views de criação definem o dono no `form_valid`:

```python
def form_valid(self, form):
    form.instance.user = self.request.user
    return super().form_valid(form)
```

Formulários que precisam do usuário (checagem de duplicidade, querysets por usuário) recebem `user` via `UserFormKwargsMixin` (`core/views.py`), usado nas views de criação e edição.

Os detalhes estão em [docs/coding-standards.md](docs/coding-standards.md).
