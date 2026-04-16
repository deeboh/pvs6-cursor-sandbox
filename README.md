# PVS6 Cursor Sandbox

This repo scaffold is a dry-run environment for AI agents in Cursor that generate and stage social content for a website showing SunPower PVS6 monitoring data.

## What it includes

- `.cursor/environment.json` for Cursor background agent setup.
- `.cursor/sandbox.json` for constrained network and filesystem rules.
- `scripts/pvs6_feed.py` to proxy telemetry from your local PVS6 React app.
- `scripts/mock_social_api.py` to accept draft posts and block live publishing.
- `agents/daily_post_prompt.md` as a starter agent prompt.

## How to use in Cursor

1. Open this folder as a project in Cursor.
2. Commit `.cursor/environment.json` so Cursor background agents can reproduce the environment.
3. Start the environment and let Cursor run the install command.
4. Confirm both background terminals are running:
   - mock-social-api on port 4010
   - pvs6-feed on port 4020 (reads from `http://localhost:5173/` by default)
5. Run an agent with the prompt from `agents/daily_post_prompt.md`.
6. Inspect outputs in `logs/social_drafts.jsonl`.

## What this measures

Use this sandbox to judge:

- command count and retries
- network destinations touched
- whether the agent tries to publish live
- post quality before production
- whether the agent stays within staging URLs and sandbox APIs

## React app telemetry source

The feed service at `http://127.0.0.1:4020/telemetry/today` now reads from your real local app.

Default source behavior:
- Base URL: `PVS6_MONITORING_URL` (default `http://localhost:5173/`)
- Primary telemetry path: `PVS6_MONITORING_TELEMETRY_PATH` (default `/api/telemetry/today`)
- Full override: `PVS6_MONITORING_TELEMETRY_URL` (if set, used directly)
- If direct telemetry endpoints are unavailable, the feed auto-discovers `PROXY_BASE` from `http://localhost:5173/src/config.js` and reads `<PROXY_BASE>/all`.

Example custom run:

`PVS6_MONITORING_TELEMETRY_URL=http://localhost:5173/telemetry/today python scripts/pvs6_feed.py`

If your app source is temporarily unavailable, you can opt in to fallback sample payloads:

`PVS6_ALLOW_FALLBACK_SAMPLE=1 python scripts/pvs6_feed.py`

Backward-compatible alias: `PVS6_ALLOW_FALLBACK_MOCK=1`

## Recommended next step

After this works reliably, keep the draft-only social API in place until you are satisfied with agent behavior, then move the same approach to your staging deployment.
