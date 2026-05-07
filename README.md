# Workforce Intelligence & Deployment Platform

AI-native recruiting operating system targeting GSI/FSI cleared contract staffing and enterprise sales/SE recruiting.

> **Status:** under active construction. Built from `~/.openclaw/agents/sapor/memory/PLATFORM-BLUEPRINT.md` (the canonical product spec). See `docs/SPRINT-STATUS.md` for what is done, what is stubbed, and what requires real third-party credentials to enable.

## Repository layout

```
services/        Python FastAPI services + Temporal workers (one dir per agent / domain)
  rules/           Sprint 2 — OPA-backed rules engine API
  screening/       Sprint 3 — screening agent
  outreach/        Sprint 4 — outreach + close protection
  pipeline/        Sprint 5 — Temporal pipeline orchestration
  client-advisory/ Sprint 6 — client advisory + client development
  interview/       Sprint 7 — voice/chat interview agent
  capture/         Sprint 8 — pre-award capture intelligence
  outcomes/        Sprint 9 — outcome loops + predictive ML
  bench/           Sprint 10 — bench management + compliance
  market/          Sprint 11 — market intelligence + data products

packages/        Shared libraries
  schemas/         Pydantic + TypeScript shared schema definitions
  rules-sdk/       Client SDK for the rules service
  audit/           Audit-log writer (ClickHouse)
  events/          Kafka/Redpanda event publisher + consumer helpers
  llm/             Model router + prompt-cached Anthropic client

apps/
  command-center/  Sprint 6 — Next.js client/internal dashboard
  candidate-portal/ Sprint 12 — Next.js candidate-facing portal

infrastructure/
  docker/          docker-compose.yml for local dev (PG+pgvector, ClickHouse, Redis, Temporal)
  terraform/       AWS production stack (RDS, ElastiCache, ECS Fargate, ALB, Secrets, alarms)
  k8s/             Kubernetes manifests (alternative deployment)
  migrations/      SQL migrations for ClickHouse
  schema/          Prisma schema (PostgreSQL operational DB)

rules/           OPA policy bundle (.rego files + tests)

docs/            Architecture decisions, sprint status, runbooks
```

## Getting started

### Prerequisites

- Node 20+, pnpm 9+
- Python 3.12+, [uv](https://github.com/astral-sh/uv)
- Docker + Docker Compose
- (For OPA dev) `opa` CLI: `brew install opa`

### One-command bootstrap

```bash
make bootstrap     # installs all deps, brings infra up, runs migrations, generates clients
make test          # runs all test suites
make dev           # starts every service in dev mode (uses overmind/foreman)
```

### Individual services

Each `services/<name>` and `apps/<name>` has its own `pyproject.toml` / `package.json` and can be run standalone. Run `make help` for the catalogue.

## Tech stack at a glance

| Layer | Tech |
|-------|------|
| Operational DB | PostgreSQL 15 + `pgvector` |
| Analytical DB | ClickHouse |
| Workflow | Temporal |
| Streaming | Redpanda (Kafka-compatible) |
| Rules | Open Policy Agent (OPA) |
| Backend | Python 3.12 / FastAPI |
| Frontend | Next.js 14 + React 18 + Tailwind |
| ML | scikit-learn (Sprint 9), Feast (feature store) |
| LLM | Anthropic Claude (model router: Opus / Sonnet / Haiku) with prompt caching |
| Auth | Clerk-shaped adapter (works with Clerk; mock for dev) |
| Email | SMTP (free) primary, SendGrid adapter for production |
| SMS | Twilio adapter (no free tier — interface only by default) |
| Voice AI | Vapi/Retell adapter interface (no free tier — see `docs/INTEGRATIONS.md`) |
| Object storage | S3-compatible (MinIO in dev) |

## Regulatory invariants enforced in code

1. **Every AI decision is audit-logged** to ClickHouse with input summary, decision, reasoning, model, confidence — see `packages/audit`.
2. **Rules engine handles process; LLMs handle judgment.** Every endpoint that calls an LLM first runs deterministic guards. See `services/rules`.
3. **Candidate ownership** (exclusivity, RTR, DNC, non-compete) is enforced before any submission action — `services/rules` ownership policies.
4. **Human escalation triggers are first-class** — VP+ candidates, $350K+ comp, mixed signals, etc. — never silenced.
5. **EEOC/OFCCP traceability**: every screen / submit / offer recommendation has a permanent reasoning record.

## Build status

See [`docs/SPRINT-STATUS.md`](./docs/SPRINT-STATUS.md) for per-sprint completion + what requires real credentials to graduate from interface-only to production.
