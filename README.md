# Finanpy

Aplicação web de gestão de finanças pessoais construída com Django full stack (templates DTL + TailwindCSS). O escopo, o modelo de dados e o planejamento estão no [PRD](PRD.md). A documentação técnica está em [docs/](docs/README.md).

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/macOS
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/`.

## Convenções de código

| Regra | Detalhe |
|---|---|
| Idioma do código | Inglês: variáveis, classes, funções, models e URLs |
| Idioma da interface | Português brasileiro: labels, mensagens, `verbose_name` e templates |
| Estilo | PEP 8 |
| Aspas | Aspas simples sempre que possível. As exceções são docstrings (`"""`) e strings que contêm apóstrofo |
| Views | Prefira Class Based Views e recursos nativos do Django |
| Models | Todo model tem `created_at` e `updated_at`. Valores monetários usam `DecimalField` |
| Escopo | Nada de dependências ou funcionalidades fora do PRD |

Os detalhes estão em [docs/coding-standards.md](docs/coding-standards.md).
