# UI Design Direction — "Salesforce meets macOS"

**Decision:** Both the Talent Command Center (Sprint 6, internal/client portal) and the Candidate Portal (Sprint 12) follow a **"Salesforce-meets-macOS"** visual language.

## What that means concretely

**From Salesforce — the data-density vocabulary**
- Dense list views with sortable columns, inline status pills, kanban toggle.
- "Record" pages with header + tabbed sections + related-list rails.
- Universal global search (`⌘K`) with object-typed results (Candidates · Reqs · Clients · Audit).
- Right-rail "Activity" feed with avatars + event icons.
- Persistent left nav with object icons + collapsible app launcher (the Salesforce "waffle").
- Stage-based pipeline visualisation across the top of req records.

**From macOS — the surface treatment + interaction grammar**
- Translucent / vibrancy-style sidebars and toolbars (`backdrop-blur` + thin borders).
- Sharp 8/12/16 grid; generous whitespace inside dense data; subtle shadows.
- SF-Pro-inspired type stack: `-apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", system-ui`.
- Traffic-light close pattern in window-style modals (informational; we keep modals single-action).
- Native-feeling segmented controls + popover menus + spotlight-style command palette.
- Dark mode is the default; light mode toggles via `⌘+Shift+L`.
- Motion: spring-based, 200-280ms, subtle; never bouncy.

## Component primitives we ship in `apps/command-center/components/ui`

- `<Sidebar>` — left nav, vibrancy backdrop, collapsible, `⌘+\` to toggle.
- `<Toolbar>` — translucent top bar, breadcrumb, global search, notification stack.
- `<DataTable>` — sortable, filterable, sticky-header, keyboard nav.
- `<Pill>` — status pills with semantic colours (open / submitted / hired / cancelled).
- `<Pipeline>` — horizontal stage strip with counts + drag-to-reorder.
- `<RecordPage>` — header + tabs + related-list rail layout.
- `<CommandPalette>` — `⌘K` spotlight; types over Candidate/Req/Client/Audit.
- `<Card>` — soft shadow, rounded, subtle border.
- `<Badge>` — denser variant of `<Pill>` for inline metadata.

## Colour + tokens

Defined as CSS custom properties on `:root`; both modes share the same names.

| Role | Light | Dark |
|------|-------|------|
| `--bg-canvas` | `#f5f5f7` | `#0b0b0f` |
| `--bg-surface` | `#ffffff` | `#15151b` |
| `--bg-elevated` | `#ffffff` | `#1d1d24` |
| `--bg-vibrancy` | `rgba(255,255,255,0.7)` | `rgba(20,20,26,0.7)` |
| `--border-subtle` | `#e5e5ea` | `#2a2a33` |
| `--text-primary` | `#1d1d1f` | `#f2f2f7` |
| `--text-secondary` | `#6e6e73` | `#a1a1a6` |
| `--accent` | `#0a84ff` (sf blue) | `#0a84ff` |
| `--success` | `#30d158` | `#30d158` |
| `--warning` | `#ff9f0a` | `#ff9f0a` |
| `--danger`  | `#ff453a` | `#ff453a` |
| `--brand-salesforce` | `#0070d2` | `#0070d2` |

Where to find the canonical implementation: `apps/command-center/styles/tokens.css` once Sprint 6 lands.
