# Worker Dispatch: worker_m3_frontend

## 2026-08-29T11:52:28Z

Mission: Build the complete production-grade Next.js 14 Developer Dashboard in `frontend/` (App Router + Tailwind CSS + Lucide Icons + Radix/Shadcn UI primitives + `next-themes`).

### Target Architecture:
- Root Layout with ThemeProvider, Dark/Light/System theme toggler, Zero hydration flash, Command palette (Cmd+K), Navbar with live counters, Footer, Toaster.
- Faceted Issue Explorer with debounced search (/ shortcut), domain pills, difficulty tags, time-to-solve filter, tech stack multi-select, bounty slider, Grid / Table / Compact view togglers.
- AI Issue Workbench Drawer (Sheet) with 4 tabs: Root Cause, AST Localized Files (with Graphify launcher), Repro Sandbox (with 1-click copy and CLI run command), CONTRIBUTING.md Fix Checklist (with localStorage persistence).
- Hourly ROI Calculator Widget with interactive slider.
- Deep-linkable standalone Issue Workbench page `/issues/[id]` with dynamic SEO and JSON-LD schema.
- Dedicated full-screen `/graph` Graphify Knowledge Graph explorer.
- Dedicated Pro & Team `/pricing` page with Dodo Payments / Lemon Squeezy checkout triggers.
- Modals: Notification Modal (Telegram pairing, Discord webhook tester, Resend email digest), Pricing Modal, Share Modal.
- Full typing, custom hooks, API client with resilient backend connection and offline demo fallback.
- SEO: `sitemap.ts`, `robots.ts`, OpenGraph metadata, JSON-LD structured data (`TechArticle`, `SoftwareApplication`).
- Zero TypeScript compiler errors and clean production build.
