# UI Workflow Contract: Modernized HMS UI

## Navigation Contract

- Successful login routes users to the dashboard, not directly to POS.
- Global side navigation exposes: Dashboard, POS, Inventory, Billing, Reports, Kitchen, AI Agent, and Logout.
- Kitchen display does not use the shared standard header; all other operational screens do.
- Quick actions on the dashboard must deep-link directly to the relevant target screen.

## Role Visibility Contract

- All roles may log in through the redesigned login screen.
- POS discount action is visible only to `MANAGER`, `CASHIER`, and `ADMIN`.
- POS void action is visible only to `MANAGER` and `ADMIN`.
- Restricted actions are hidden or non-actionable without removing the user's ability to view the rest of the screen.

## Screen Behavior Contract

### Login

- Role must be selected before PIN submission.
- PIN feedback is shown as masked progressive dots.
- Offline-ready state is always visible.

### Dashboard

- Must show greeting, date, four summary cards, quick actions, active order list, recent activity, and payment breakdown.
- Missing data is rendered as intentional placeholders rather than blank panels.

### POS

- Menu is rendered as a three-column card grid with category filtering.
- Out-of-stock items are visibly disabled and cannot be added.
- Current order summary remains visible while menu browsing.
- Existing keyboard shortcuts remain active.

### Inventory

- Alert sidebar remains visible independently from the main stock table.
- Stock health is expressed through consistent badges and proportional bars.
- Ledger history is visible in the same screen context.

### Billing

- Payment method is selectable through card-like choices.
- Change due updates immediately from the entered amount.
- Receipt preview remains visible before confirming print or follow-up actions.

### Reports

- All visual summaries use built-in Flet layout primitives only.
- Date switching and CSV export remain available from the top control row.

### Kitchen

- Tickets are displayed in a dense grid suitable for standing-distance reading.
- Kitchen urgency uses time-driven visual states.
- Individual item completion and whole-order readiness are separate actions.

### AI Agent

- Screen is split into agent status, interaction panel, and live event activity.
- Interaction modes are explicit and switchable.
- Ambiguous commands present explicit clarification chips rather than silent guesses.
- Every command response can expose a step-by-step trace.

## Empty, Error, and Refresh Contract

- Each screen has a deliberate empty state message when no live data is available.
- Read failures degrade to safe placeholder values or readable inline errors instead of crashing the screen.
- Periodic refresh is limited to lightweight operational panels such as kitchen timers and audit/event activity.
