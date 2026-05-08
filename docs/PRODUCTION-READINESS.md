# Production-Readiness Review

12-sprint build complete. This document captures: what was built, what is real vs adapter-only, what blocks a production launch, and where the architecture should pivot before the platform sees real traffic.

## Build summary

| Metric | Value |
|--------|-------|
| Sprints completed | 12 of 12 |
| Backend services | 9 (rules, candidates, screening, outreach, pipeline, client-advisory, interview, capture, outcomes, bench, market) |
| Frontend apps | 2 (command-center, candidate-portal) — Salesforce-meets-macOS |
| Shared Python packages | 6 (schemas, audit, events, llm, rules-sdk, data) |
| OPA policies | 11 |
| Unit tests | **177 passing** |
| Approximate LOC | **~12,800** |
| Database tables | 9 PG (candidates, clients, requisitions, submissions, RTR, DNC, non-competes, non-solicits, silver_medalists, pipeline_events) + 2 ClickHouse (interaction_events, audit_log + daily MV) |

## What's real, end-to-end

These flows work today against the local stack (`make bootstrap`):

1. **Resume → candidate record.** PDF or DOCX uploaded → text extracted → LLM-based structured extraction → embedding generated → candidate row written → ownership records correctly initialised.
2. **Semantic search.** Query → embedding → pgvector ANN against candidate corpus → ranked results with structured filters (clearance, motion, metro).
3. **Rules engine.** OPA policy bundle answers comp / timeline / ownership / margin / non-compete / req-mode / LCAT / approachability / counteroffer / fiscal-year / co-employment questions; the rules SDK gives every other service a typed surface.
4. **Screening agent.** Ownership pre-check → deterministic rubric predicates → LLM judgment block → 85%-of-employer-rubric pass test → audit log row → calibration harness comparing against employer-supplied labelled examples.
5. **Outreach + Close Protection.** Sequence engine, three preset cadences, A/B framework with two-proportion z-test, response classifier (heuristic + LLM fallback), counteroffer detection that emits a `candidate_falloff` event for silver-medalist promotion.
6. **Pipeline orchestration.** State machine with all transitions, SLA evaluator, multi-req routing, silver-medalist pool with promote-and-renumber, submission-package generator, Greenhouse Harvest ATS adapter.
7. **Talent Command Center.** Salesforce-meets-macOS Next.js app with vibrancy chrome, ⌘K command palette, dark/light, dashboard + candidates + reqs + pipeline + audit + capture + bench routes.
8. **Client Advisory.** Feasibility report (rolls up rule verdicts + builds relaxation options), stalled-pipeline diagnosis weighted by absolute lost candidates.
9. **Interview agent.** Three role-specific rubrics, chat flow stepping through dimensions, transcript evaluation routed to frontier-tier (Opus) for high-stakes judgment, high-value-interview escalation, mixed-signals escalation.
10. **Capture.** Feasibility analyzer, heat-map builder, comp estimator (location + clearance + poly multipliers), LOI workflow with acceptance-rate + expiry.
11. **Outcomes ML.** scikit-learn LogisticRegression for placement_success + offer_acceptance, trains on synthetic 1500/1200-row datasets at startup, AUC > 0.7 on held-out, predict_proba + per-feature explanation, hot-reload from disk.
12. **Bench + compliance.** Contract-end + clearance-expiration alert ladder, co-employment risk + conversion fee + utilisation calculators, compliance adapter interfaces with mock implementations.
13. **Market intelligence.** Comp percentiles (p25/50/75/90, w2-only filter, min sample 3), hiring velocity with skill momentum, competitive agency intelligence, API-key-gated data API with three-tier rate limit table.
14. **Candidate portal.** Self-service profile, market percentiles, alerts, post-placement referral submission.

## Adapter status (what would need credentials to flip from mock to live)

| Integration | Status | Why |
|-------------|--------|-----|
| Anthropic Claude | **real** | needs `ANTHROPIC_API_KEY` |
| Voyage AI embeddings | **real** | needs `VOYAGE_API_KEY` |
| SendGrid email | **real** (free dev tier) | needs `SENDGRID_API_KEY` |
| SMTP / Mailpit | **real, working in dev** | mailpit is in docker-compose |
| Greenhouse Harvest ATS | **real** (free dev tier) | needs `GREENHOUSE_HARVEST_API_KEY` |
| Google Calendar | **real** (free OAuth) | needs `GOOGLE_OAUTH_CLIENT_ID` + secret |
| Apollo enrichment | adapter shipped | no free tier — Apollo trial credits only |
| Twilio SMS | adapter shipped | no free tier |
| Vapi voice AI | adapter shipped | no free tier |
| LinkedIn outbound | mock | partner programme required |
| GovWin / BGOV | not built | enterprise contract required |
| iCIMS ATS | not built | enterprise contract required |
| SAP Fieldglass / Beeline VMS | not built | enterprise contract required |
| Sterling / HireRight | adapter shipped (mock) | account required |
| DISS clearance verification | adapter shipped (mock) | federal employer enrollment required |
| E-Verify | adapter shipped (mock) | DHS enrollment required |
| Stripe Connect (marketplace billing) | not built | Sprint 11 ships API-key gating; Stripe wiring is a bolt-on |

## Where I have real concerns about viability

These are honest production-readiness gaps. Some were called out earlier in the build; others surfaced as the surface area grew.

### 1. Synthetic training data is structurally weak

Sprint 9 trains placement-success and offer-acceptance models on synthetic data because the platform has no real placements. The synthesizer encodes plausible relationships (motion match → success, comp gap → acceptance, etc.), which means **the model learns the synthesizer's biases, not real-world signal**. AUC > 0.7 on the synthetic holdout is real signal-on-the-distribution-we-built, not on actual recruiting outcomes. Until real placements accumulate, these models should be considered **decision-support theatre at best**. They are useful for:

- Smoke-testing the ML pipeline (predict_proba round-trip, feature explanations).
- Exercising the explainability surface for client demos.
- Establishing the feature contract that real data will replace.

They are **not safe** for go/no-go decisions. **Pivot recommendation:** disable `/v1/predict/*` from production gating until at least 50 real placements label the dataset and the production AUC clears 0.7 on a real holdout. The retraining endpoint already accepts a custom dataset — wire it to the real Signal table when data exists.

### 2. The "85% rubric agreement" calibration is an unverified contract

We replaced the original "85% recruiter agreement on 50-candidate blind test" with the employer-rubric model: the employer supplies pass criteria, and we score the agent against them. This is **operationally cleaner** but technically untested. We have not run the calibration endpoint against any real labelled set. **Pivot recommendation:** before client #1 goes live, run the calibration harness against at least one client's labelled 30-candidate set. If the agreement rate is < 85%, the screening agent's LLM prompt and / or default rubric synthesis need adjustment — both are localised changes.

### 3. Clearance + polygraph parsing has zero ground truth

The resume parser regex is reasonable for the obvious cases ("TS/SCI", "Lifestyle Polygraph") but the field hasn't been validated against a real labelled corpus of cleared resumes. Production candidate intake **will** misclassify clearance levels until this is calibrated, and clearance is the field most expensive to be wrong about. **Pivot recommendation:** the first 200 candidate records ingested in production should be sampled into a manual review queue keyed by clearance + polygraph. If accuracy < 95% on that sample, layer a second LLM pass specifically on the clearance section.

### 4. Multi-tenant boundaries don't exist yet

Every service treats data as global. There is no `tenant_id` column, no row-level security, no per-client data isolation. This is fine for an internal-tools deployment serving one staffing agency, but **dangerous** the moment two agencies share the platform — they will see each other's candidates. **Pivot recommendation before commercial pilot:** add `tenant_id` to every primary table, every event envelope, and every audit row; add Postgres RLS policies; gate every route on tenant context derived from the auth claim. This is ~2 weeks of focused work and should happen *before* the first paying customer, not after.

### 5. Stripe / billing is unbuilt

Sprint 11's data API has tier-based rate limits but no actual billing. There's no `Subscription` table, no Stripe webhook ingest, no enforcement that an expired subscription drops the X-Api-Key. **Pivot recommendation:** before announcing pricing, port the Stripe Connect integration pattern from the signal-marketplace work (`packages/api/src/services/stripe.service.ts` — webhook idempotency, subscription model, tier checkout). Reusable in ~1 week.

### 6. Compliance adapters are all mocked

DISS, E-Verify, Sterling, HireRight — all required for federal hiring — exist only as `Mock*` implementations. We **cannot do compliance-clean federal placements** today. **Pivot recommendation:** a federal-cleared launch is gated on building real Sterling + DISS + E-Verify integrations. Each requires an enterprise contract. The interfaces are correct; the work is procurement + a few hundred lines of HTTP client code per provider.

### 7. The audit log isn't queryable by clients yet

Every agent decision lands in ClickHouse, but no client-facing surface exposes it. The blueprint and `docs/COMPLIANCE.md` (carried over from signal-marketplace pattern) call out 7-year retention + EEOC/OFCCP traceability, but that promise is only kept by ClickHouse durability. **Pivot recommendation:** build `/v1/audit/candidate/{id}` returning the redacted decision history. The `wfi_audit.AuditLogger.for_candidate()` reader exists; wire it to a route + UI before the first client signs a data-handling contract.

### 8. No CI yet

Every sprint shipped tests. None of them runs automatically. The next person to add a feature will silently break the full suite. **Pivot recommendation:** add `.github/workflows/ci.yml` (Python tests + ruff + Prisma-equivalent migration validation + Next.js typecheck) before the first non-author PR lands. ~1 day.

### 9. Temporal workflows exist as stubs only

Sprint 5 ships a state machine + an in-process silver-medalist pool. The blueprint specified Temporal workflows for durable, retried, sagaed pipeline orchestration. We never wrote the actual `@workflow.defn` definitions. **Pivot recommendation:** when production traffic exists, the silver-medalist pool's "promote within 48 hours of falloff" SLA cannot be guaranteed by an in-memory dict. Convert to real Temporal workflows: `PipelineWorkflow`, `CloseProtectionWorkflow`, `ScreeningWorkflow`. ~3-5 days.

### 10. Observability is missing

Prometheus + Grafana are in docker-compose for the development illusion, but no service exports metrics. Pino-equivalent structured logging exists everywhere; metrics + tracing don't. **Pivot recommendation:** before launch, instrument the screening + outreach + pipeline services with Prometheus counters (decisions/sec, cost-per-decision, pipeline stage transitions, SLA-breach count) and OpenTelemetry traces across the rules-SDK call path. ~1 week.

## What the build is actually good for today

Despite the gaps above, the platform **is** in a state where it can:

- Demo the full agent flow end-to-end against synthetic data.
- Onboard a single internal staffing team (no multi-tenant gap blocker).
- Accept resume uploads, parse them, and surface meaningful matches against semantic queries.
- Run a controlled pilot with one friendly client willing to supply a labelled rubric for calibration.
- Generate verifiable cost telemetry on every LLM call (cost_usd is logged on every audit row).

What it is **not** ready for:

- Multi-tenant SaaS deployment.
- Federal cleared placements.
- Public marketing of "predictive placement-success scoring" — the synthetic-data caveat needs to be honest.
- Selling subscriptions to the data API — billing isn't wired.

## Recommended pivot sequence

If I were ranking what to do next:

1. **Multi-tenant boundary** (P0, ~2 weeks) — gates everything else commercial.
2. **CI workflow** (P0, ~1 day) — gates safe iteration.
3. **Stripe billing port from signal-marketplace pattern** (P1, ~1 week) — gates the data API revenue line.
4. **Real ML training when 50+ placements exist** (P1, ~1 day of work + months of data accumulation).
5. **Audit log read API + UI** (P1, ~3 days) — gates the EEOC/OFCCP compliance promise.
6. **Temporal workflows** (P2, ~1 week) — gates the silver-medalist SLA at scale.
7. **Real compliance adapters (Sterling / DISS / E-Verify)** (P2, ~2 weeks per provider) — gates federal placements.
8. **Observability (Prometheus + OTel)** (P2, ~1 week) — gates production debuggability.
9. **LinkedIn / GovWin partner integrations** (P3, gated on procurement).

Total to commercial-pilot-ready: roughly 4-6 weeks of focused work plus ~3-6 months of real-world data accumulation before the ML piece is anything other than scaffold.

## Final test counts

Across 12 sprints + sprint 0:

```
177 passing tests across:
  packages/py-schemas:    6
  packages/py-data:      16
  services/candidates:    6
  services/rules:         6
  services/screening:    23
  services/outreach:     30
  services/pipeline:     22
  services/client-advisory: 9
  services/interview:    16
  services/capture:      11
  services/outcomes:      9
  services/bench:        16
  services/market:        8
```

Approximately **12,800 lines** across services, packages, and the two Next.js apps. Every commit pushed to https://github.com/Bobcatsfan33/RecruitingAI/.
