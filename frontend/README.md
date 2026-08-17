# GrACE-Demo frontend

Next.js 15 (App Router, TypeScript strict, Tailwind). Talks to the FastAPI backend
over JSON.

**Canonical install:** [../INSTALL.md](../INSTALL.md). End-user screens:
[../docs/USER_MANUAL.md](../docs/USER_MANUAL.md).

## Nav (this cut)

Chat · Inspector · Sources · Ingestion · Claims · Onboarding · Voice · Settings

There is **no graph viewer or Guided Review tab**. Those routes may still exist in
the tree; do not send students there.

## Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local   # if present; otherwise NEXT_PUBLIC_GRACE_API_BASE_URL defaults to http://localhost:8000
npm run dev
```

| Command | What it does |
|---|---|
| `npm run dev` | http://localhost:3000 |
| `npm run build` | Production build (strict TypeScript) |
| `npm test` | vitest |
| `npm run typecheck` | `tsc --noEmit` |

Dependencies are pinned exact (no carets).
