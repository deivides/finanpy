# Design system

Visual guidelines defined in the [PRD](../PRD.md) (section 9). There are no templates in the project yet; follow these rules when creating them.

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
| Badges | `badge`, `badge-income`, `badge-expense` |
| Tables | `table` |
| Menu | `nav-link`, `nav-link-active` |

`<html>` in `base.html` carries `scheme-dark` (`color-scheme: dark`), so native controls (date picker icon, scrollbars, selects) render in dark mode globally; no per-field overrides.

The full definition of each class is in the PRD, section 9.4.

Tailwind v4 notes:

- `@apply` only accepts registered utilities. The base classes reused by other classes (`btn`, `badge`, `nav-link`) are declared with `@utility`. The rest live in `@layer components`, which allows nested selectors such as `.table th`.
- Tailwind v4 has no `placeholder-slate-500` class. Use `placeholder:text-slate-500` instead.
- An unknown class inside `@apply` breaks the whole style block in the browser, so check every new class against Tailwind v4 before adding it.

## Button usage

| Variant | Usage |
|---|---|
| `btn-primary` | Main action of the screen (Save, Log in, Sign up) |
| `btn-secondary` | Secondary actions (Cancel, Back, Filter) |
| `btn-ghost` | Subtle actions (Edit, menu items) |
| `btn-danger` | Destructive actions (Delete) |

Rule: at most **one** `btn-primary` per screen/form. Navigation bars (public navbar and sidebar) never use `btn-primary`, so they don't compete with the page's main action.

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

## Monetary values

- Income in `text-emerald-400` with a `+` prefix.
- Expenses in `text-rose-400` with a `−` prefix.
- Always `tabular-nums`.
