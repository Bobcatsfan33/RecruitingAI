# Sprint Status

Tracking what's complete, what's interface-only-pending-credentials, and what's deferred.

| Sprint | State | Notes |
|--------|-------|-------|
| 0 — Monorepo foundation | DONE | docker-compose, workspaces, Makefile, env template |
| 1 — Data Foundation | _in progress_ | |
| 2 — Domain Rules Engine | _pending_ | |
| 3 — Screening Agent | _pending_ | |
| 4 — Outreach + Close Protection | _pending_ | |
| 5 — Pipeline Orchestration | _pending_ | |
| 6 — Talent Command Center + Client Advisory | _pending_ | |
| 7 — Interview Agent | _pending_ | |
| 8 — Pre-Award Capture Intelligence | _pending_ | |
| 9 — Outcome Loops + Predictive Models | _pending_ | |
| 10 — Bench Management + Compliance | _pending_ | |
| 11 — Market Intelligence + Data Products | _pending_ | |
| 12 — Candidate Portal + Network Effects | _pending_ | |

## Integration adapter status

External services follow the adapter pattern: a `Protocol` interface plus a real-API implementation plus a `Mock*` implementation that returns deterministic data. Tests run against the mock; production wires the real one when credentials are configured.

| Integration | Adapter file | Status | Why not real today |
|-------------|--------------|--------|---------------------|
| Apollo (enrichment) | `services/.../enrichment/apollo.py` | mock | no free tier |
| ZoomInfo (enrichment) | `services/.../enrichment/zoominfo.py` | mock | no free tier |
| LinkedIn (sourcing + outreach) | `services/.../linkedin/` | mock | API restricted; partner programme required |
| GovWin / BGOV (federal contracts) | `services/capture/govwin/` | mock | no free tier |
| Vapi / Retell (voice AI) | `services/interview/voice/` | mock | no free tier |
| iCIMS (ATS) | `services/pipeline/ats/icims.py` | mock | enterprise contract required |
| Greenhouse Harvest API | `services/pipeline/ats/greenhouse.py` | shipped (free dev tier) | needs personal API key |
| SAP Fieldglass / Beeline (VMS) | `services/bench/vms/` | mock | enterprise contract |
| Sterling / HireRight (background) | `services/bench/background/` | mock | account required |
| DISS (clearance verification) | `services/bench/diss.py` | mock | federal access required |
| E-Verify | `services/bench/everify.py` | mock | employer enrollment required |
| Twilio (SMS) | `services/outreach/sms.py` | mock | no free tier |
| SendGrid (email) | `services/outreach/email/sendgrid.py` | shipped (free dev tier) | needs personal API key |
| SMTP / Mailpit (email) | `services/outreach/email/smtp.py` | shipped + working in dev | mailpit catcher in docker-compose |
| Stripe Connect (revenue split) | `services/market/billing.py` | shipped (test mode) | needs personal Stripe test keys |
| Anthropic Claude | `packages/py-llm/anthropic_client.py` | shipped | needs `ANTHROPIC_API_KEY` |
| Google Calendar (interview booking) | `services/interview/calendar/google.py` | shipped | OAuth — free |
| Clerk (auth) | `apps/.../auth/clerk.ts` | adapter shipped, `MockAuth` for dev | free tier available |

## "Will need real input to validate" list

Per the build constraint: we have no real placements, no real recruiters, no real clients to test against. The following acceptance metrics from the blueprint are **deferred until pilot**:

- Sprint 1: "90%+ resume parser accuracy on 50-resume test set" — code is correct; metric requires a labelled test set with real resumes.
- Sprint 3: "85%+ recruiter agreement on 50-candidate blind test" — replaced with the **employer-defined rubric** model (employer supplies pass criteria; agent passes if 85%+ of criteria met). Needs at least one client to define a rubric for end-to-end validation.
- Sprint 4: "25%+ outreach response rate" — requires real recipients.
- Sprint 7: "4+/5 candidate satisfaction on voice interview" — requires real candidates + Vapi/Retell credentials.
- Sprint 9: "predictive model 2x random on holdout" — model trained on synthetic data; real validation requires 50+ labelled placements.
- Sprint 11: "5+ paying intelligence subscribers" — go-to-market dependency.
