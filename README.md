# PVS6 Cursor Sandbox

This repo scaffold is a dry-run environment for AI agents in Cursor that generate and stage social content for a website showing SunPower PVS6 monitoring data.

## What it includes

- `.cursor/environment.json` for Cursor background agent setup.
- `.cursor/sandbox.json` for constrained network and filesystem rules.
- `scripts/mock_pvs6_feed.py` to simulate a telemetry endpoint.
- `scripts/mock_social_api.py` to accept draft posts and block live publishing.
- `agents/daily_post_prompt.md` as a starter agent prompt.

## How to use in Cursor

1. Open this folder as a project in Cursor.
2. Commit `.cursor/environment.json` so Cursor background agents can reproduce the environment.
3. Start the environment and let Cursor run the install command.
4. Confirm both background terminals are running:
   - mock-social-api on port 4010
   - mock-pvs6-feed on port 4020
5. Run an agent with the prompt from `agents/daily_post_prompt.md`.
6. Inspect outputs in `logs/social_drafts.jsonl`.

## What this measures

Use this sandbox to judge:

- command count and retries
- network destinations touched
- whether the agent tries to publish live
- post quality before production
- whether the agent stays within staging URLs and sandbox APIs

## Recommended next step

After this works reliably, replace the mock telemetry feed with a staging mirror of your real PVS6 site and keep the mock social API in place until you are satisfied with agent behavior.
