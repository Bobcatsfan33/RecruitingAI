rules:           uv run uvicorn services.rules.main:app --host 0.0.0.0 --port 8001 --reload
screening:       uv run uvicorn services.screening.main:app --host 0.0.0.0 --port 8002 --reload
outreach:        uv run uvicorn services.outreach.main:app --host 0.0.0.0 --port 8003 --reload
pipeline:        uv run uvicorn services.pipeline.main:app --host 0.0.0.0 --port 8004 --reload
client_advisory: uv run uvicorn services.client_advisory.main:app --host 0.0.0.0 --port 8005 --reload
interview:       uv run uvicorn services.interview.main:app --host 0.0.0.0 --port 8006 --reload
capture:         uv run uvicorn services.capture.main:app --host 0.0.0.0 --port 8007 --reload
outcomes:        uv run uvicorn services.outcomes.main:app --host 0.0.0.0 --port 8008 --reload
bench:           uv run uvicorn services.bench.main:app --host 0.0.0.0 --port 8009 --reload
market:          uv run uvicorn services.market.main:app --host 0.0.0.0 --port 8010 --reload
worker_pipeline: uv run python -m services.pipeline.worker
worker_outreach: uv run python -m services.outreach.worker
worker_close:    uv run python -m services.outreach.close_protection_worker
command_center:  pnpm --filter @wfi/command-center dev
candidate_portal: pnpm --filter @wfi/candidate-portal dev
