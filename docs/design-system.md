# Design system

Visual guidelines defined in the [PRD](../PRD.md) (section 9). All templates in `templates/` follow these rules; keep new screens consistent with them.

## Principles

- **Dark by default**: near-black bluish background, layered surfaces.
- **Gradient as identity**: violet → indigo → cyan on highlight elements.
- **Color semantics**: emerald green for income, rose for expenses.
- **Consistency**: components defined once and reused across all screens.
- **Responsive** (mobile first).

## Palette

| Token | Usage | Tailwind class |
|---|---|---|
| `bg-app` | Application background | `bg-slate-950` |
| `bg-surface` | Cards, sidebar, modals | `bg-slate-900` |
| `bg-surface-2` | Inputs, row hover | `bg-slate-800` |
| `border` | Subtle borders | `border-slate-800` |
| `primary` | Main actions | `violet-500` / `violet-600` |
| `secondary` | Secondary highlights | `indigo-500` |
| `accent` | Details, links | `cyan-400` |
| `success` / income | Positive values | `emerald-400` |
| `danger` / expense | Negative values, deletion | `rose-500` |
| `warning` | Alerts | `amber-400` |
| `text-primary` | Main text | `text-slate-100` |
| `text-secondary` | Supporting text | `text-slate-400` |
| `text-muted` | Placeholders and disabled text | `text-slate-500` |

## Gradients

| Name | Classes |
|---|---|
| Main | `bg-gradient-to-r from-violet-600 via-indigo-600 to-cyan-700` (ends in `cyan-700` so white `btn-primary` text keeps AA contrast) |
| Text | `bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent` |
| Background glow | `bg-gradient-to-br from-violet-600/20 via-slate-950 to-cyan-500/10` |
| Balance card | `bg-gradient-to-br from-violet-600 to-indigo-700` |

## Typography

**Inter** font (400, 500, 600, 700) via Google Fonts.

| Element | Classes |
|---|---|
| H1 | `text-2xl md:text-3xl font-bold text-slate-100` |
| H2 | `text-xl font-semibold text-slate-100` |
| H3 (card) | `text-sm font-medium text-slate-400 uppercase tracking-wide` |
| Body | `text-sm md:text-base text-slate-300` |
| Caption | `text-xs text-slate-400` (`slate-500` fails AA contrast on the dark background) |
| Large monetary value | `text-3xl font-bold tabular-nums` |

## Components

Component classes, defined with `@apply` only once, in the `<style type="text/tailwindcss">` block of `templates/base.html`:

| Group | Classes |
|---|---|
| Buttons | `btn`, `btn-primary`, `btn-secondary`, `btn-ghost`, `btn-danger` |
| Forms | `form-label`, `form-input`, `form-error`, `form-help` |
| Cards | `card` |
| Badges | `badge`, `badge-income`, `badge-expense`, `badge-neutral` |
| Tables | `table` |
| Menu | `nav-link`, `nav-link-active` |

`<html>` in `base.html` carries `scheme-dark` (`color-scheme: dark`), so native controls (date picker icon, scrollbars, selects) render in dark mode globally; no per-field overrides.

The full definition of each class is in the PRD, section 9.4.

- **Badges**: `badge-income`/`badge-expense` for income/expense categories and types; `badge-neutral` (`bg-slate-800 text-slate-300 ring-1 ring-slate-700`) for labels with no income/expense meaning, such as the account type on the account list. Don't hand-build badges from loose utilities.
- **Invalid fields**: Django renders fields that have errors with `aria-invalid="true"` (and `aria-describedby` pointing to `<auto_id>_error`). `form-input` then gets a rose border and a rose focus ring: `aria-[invalid=true]:border-rose-500 aria-[invalid=true]:focus:border-rose-500 aria-[invalid=true]:focus:ring-rose-500/30`.
- **Favicon**: an inline SVG data URI in the `<head>` of `base.html` (`<`, `>`, `#` and spaces URL-encoded). It is a rounded square with the main gradient (`violet-600` → `indigo-600` → `cyan-700`) and a white "F" drawn as a `path`, so it does not depend on a font. There is no static file and no new dependency.

Tailwind v4 notes:

- `@apply` only accepts registered utilities. The base classes reused by other classes (`btn`, `badge`, `nav-link`) are declared with `@utility`. The rest live in `@layer components`, which allows nested selectors such as `.table th`.
- Tailwind v4 has no `placeholder-slate-500` class. Use `placeholder:text-slate-500` instead.
- Use `focus:outline-hidden`, not `focus:outline-none`, to hide the default focus outline. In v4, `outline-none` removes the outline in forced-colors (high contrast) mode as well.
- An unknown class inside `@apply` breaks the whole style block in the browser, so check every new class against Tailwind v4 before adding it.
- v4 has no built-in `aria-invalid` variant. The built-in ones are `aria-busy`, `aria-checked`, `aria-disabled`, `aria-expanded`, `aria-hidden`, `aria-pressed`, `aria-readonly`, `aria-required` and `aria-selected`. Use the arbitrary form `aria-[invalid=true]:`.

## Button usage

| Variant | Usage |
|---|---|
| `btn-primary` | Main action of the screen (Save, Log in, Sign up) |
| `btn-secondary` | Secondary actions (Cancel, Back, Filter) |
| `btn-ghost` | Subtle actions (Edit, menu items) |
| `btn-danger` | Destructive actions (Delete) |

Rule: at most **one** `btn-primary` per screen/form. Navigation bars (public navbar and sidebar) never use `btn-primary`, so they don't compete with the page's main action. On list pages, the create `btn-primary` ("Nova conta", "Nova transação"...) lives in the page header and is always visible, even when the list is empty. Empty states never use `btn-primary` (see Empty states).

## Focus

Every interactive element has a visible keyboard focus ring: a solid `focus-visible:ring-2 focus-visible:ring-violet-400` with `ring-offset-2` in the background color (`ring-offset-slate-950` on the page, `ring-offset-slate-900` in the sidebar and inside cards). This keeps at least 3:1 contrast, including on `btn-primary`, `btn-danger` and `nav-link-active`.

- `btn` (offset `slate-950`) and `nav-link` (offset `slate-900`, since it only lives in the sidebar) include it. The sidebar close button adds `focus-visible:ring-offset-slate-900`. Buttons inside a `.card` switch to the `slate-900` offset through a `.card :is(.btn-primary, .btn-secondary, .btn-ghost, .btn-danger)` rule in `base.html`.
- Standalone links (logos, the footer links on login/sign up) use `rounded-lg focus:outline-hidden` plus the same ring.
- `form-input` keeps its own focus style (`focus:border-violet-500 focus:ring-2 focus:ring-violet-500/30`), which turns rose on invalid fields (see Components).
- While the mobile sidebar is open, the content column gets `inert`, so Tab stays inside the menu.

## Empty states

`components/_empty_state.html` renders an icon, a text and, optionally (`button_label` + `button_url`), a `btn-secondary` call to action. List pages pass no button, because the header already has the same action. The button label matches the header/shortcut action: "Nova conta", "Nova categoria", "Nova transação". On the dashboard, the transactions block offers "Nova transação" when the user has accounts and categories, "Nova categoria" when they have accounts but no category (the transaction form would be unusable), and only text when they have no account (the "Minhas contas" block already offers "Nova conta").

## Missing prerequisites

When a required select has no options (for example, "Nova transação" with no account or no category), the form shows a box at the top: `rounded-xl bg-amber-500/10 p-3 text-sm text-amber-300 ring-1 ring-amber-500/30`. The box links to "Nova conta" and/or "Nova categoria". These are plain underlined links with the standard focus ring, not buttons, so the screen keeps a single `btn-primary`.

## Navigation

- **Public navbar** (`components/_navbar_public.html`): gradient logo on the left; "Entrar" (`btn-ghost`) and "Cadastre-se" (`btn-secondary`) on the right. Logged-in users see only "Ir para o dashboard" (`btn-secondary`).
- **Sidebar** (`components/_sidebar.html`): menu items use `nav-link`; the current page uses `nav-link-active`, based on `request.resolver_match.url_name`. "Sair" is a POST form at the bottom.

## Messages

Colors follow `message.level_tag`:

| Level | Classes |
|---|---|
| Success | `bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-500/30` |
| Error | `bg-rose-500/10 text-rose-300 ring-1 ring-rose-500/30` |
| Warning | `bg-amber-500/10 text-amber-300 ring-1 ring-amber-500/30` |
| Info | `bg-cyan-500/10 text-cyan-300 ring-1 ring-cyan-500/30` |

## Layout

| Context | Classes |
|---|---|
| Page container | `mx-auto w-full max-w-7xl px-4 md:px-8 py-6 md:py-8` |
| Summary cards grid | `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6` |
| Two-block content | `grid grid-cols-1 lg:grid-cols-3 gap-6` (main `lg:col-span-2`) |
| Page header | `flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6` |
| Tables on mobile | `overflow-x-auto` inside a `card` |
| User text (names, descriptions) | `wrap-anywhere`, never `truncate` or `whitespace-nowrap` (in tables, `break-words` does not shrink a cell's minimum width) |

## Monetary values

- Income in `text-emerald-400` with a `+` prefix.
- Expenses in `text-rose-400` with a `−` prefix.
- Always `tabular-nums`.
- A total that is exactly zero (month income/expenses, filtered totals, month result) is neutral: `R$ 0,00` with no sign, in `text-slate-100` (or the inherited white on the balance card). Negative values keep the `−` prefix via `cut:"-"`.
- A "Ver todas" action above a table is a compact `btn-ghost` (`px-3 py-1.5`) with `-mr-3`, so its text lines up with the right edge of the "Valor" column while the focus ring stays whole.
