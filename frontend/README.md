# Construction AI Platform — Frontend

Next.js (App Router) frontend for the Construction AI Platform backend.
Talks to the FastAPI backend at `NEXT_PUBLIC_API_URL` (browser) /
`API_URL_INTERNAL` (server, Docker-internal DNS) — see
[docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) in the repo root for the
overall system design.

## Stack

- **Next.js 16** App Router, TypeScript strict mode, Turbopack
- **shadcn/ui** (Base UI, not Radix) + Tailwind v4
- **recharts** for charts
- All API access goes through a single typed client: [src/lib/api.ts](src/lib/api.ts)

## Running

This project has no local Node.js requirement — everything runs through
Docker as part of the root `docker-compose.yml`.

```bash
# from the repo root, with the backend already running
docker compose up -d --build frontend
```

The app is served at [http://localhost:3000](http://localhost:3000).

To run it outside Docker (requires Node 22.13+ and pnpm):

```bash
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL, defaults to localhost:8000
pnpm install
pnpm dev
```

### Useful commands

```bash
pnpm dev              # dev server (Turbopack)
pnpm build             # production build
pnpm lint              # ESLint
npx tsc --noEmit       # type-check
pnpm dlx shadcn@latest add <name>   # add a shadcn/ui component
```

When developing inside the Docker container (bind-mounted volume),
Turbopack does not reliably pick up file changes written from the host —
restart the container after editing (`docker compose restart frontend`)
rather than relying on hot reload.

## Page inventory

| Route | Description |
|---|---|
| `/` | Dashboard: stat cards, 7-day activity chart, quick actions, recent runs, at-risk projects |
| `/chat` | Chat interface with inline agent result cards (meeting intelligence, supplier risk, weekly report) |
| `/projects` | Project list |
| `/projects/[id]` | Project detail — meetings, purchase orders, NCRs, safety events, weekly report action |
| `/suppliers` | Supplier list |
| `/suppliers/[id]` | Supplier detail — delivery/quality history, prior risk assessments, run-risk-assessment action |
| `/meetings` | Meeting browser with decisions |
| `/approvals` | Approval queue with approve/reject dialog |
| `/reports` | Weekly executive reports — generate new, browse previous |
| `/audit` | Paginated AI audit log with per-call detail (prompt, output, tool trace) |
| `/metrics` | Observability: LLM call/token/cost stats, calls-per-day, latency histogram, per-agent success rate, tool invocation table |

## Conventions

- Server components by default; `"use client"` only where interactivity/hooks are needed.
- All backend calls go through `src/lib/api.ts` — no scattered `fetch()` calls.
- Types in `src/lib/types.ts` mirror the backend's Pydantic schemas.
- shadcn/ui is built on Base UI here, not Radix — use `render={<Link .../>}` instead of `asChild`,
  and `onValueChange` handlers receive `string | null`.
- `src/app/error.tsx` / `not-found.tsx` / `loading.tsx` provide the shell-level error, 404, and
  loading states; most data pages additionally render their own empty states.
