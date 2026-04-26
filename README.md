# polar-accesslink

`polar-accesslink` is a shared Polar AccessLink core with two adapters:
- `polar-mcp` for LLM and MCP-compatible clients
- `polar-cli` for cronjobs, exports, and simple automation

Current scope includes `activities`, `cardio-load`, and `exercises`.

## Architecture

- `polar_accesslink.service` and `polar_accesslink.client` contain the shared core.
- `polar_accesslink.mcp_server` exposes the core through MCP tools.
- `polar_accesslink.cli` exposes the same operations through a terminal command.

## Supported Operations

- `activities_range(from_date, to_date, include_samples=false)`
- `activity_by_date(date, include_samples=false)`
- `cardio_load_recent(days=30)`
- `cardio_load_by_date(date)`
- `exercises_recent(include_samples=false, include_zones=false, include_route=false, include_tcx_metadata=false)`
- `exercise_by_id(exercise_id, include_samples=false, include_zones=false, include_route=false, include_tcx_metadata=false)`

Both adapters return structured JSON envelopes:

- `status`: `ok` | `no_data` | `error`
- `query`
- `data`
- `meta.generated_at`
- `meta.source`
- `meta.rate_limit`

## Requirements

- Python `3.11+`
- Polar AccessLink `access_token`
- Polar AccessLink client credentials only if you use the one-time OAuth bootstrap helper

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
export POLAR_ACCESS_TOKEN="your-access-token"
```

### MCP

```bash
polar-mcp
```

Compatibility wrapper:

```bash
python3 run_polar_mcp.py
```

### CLI

```bash
polar-cli activities-range --from-date 2026-04-01 --to-date 2026-04-07 --pretty
polar-cli exercises-recent --output jsonl --out data/exercises.jsonl
```

## MCP Configuration Example

```json
{
  "mcpServers": {
    "polar": {
      "command": "python3",
      "args": ["/absolute/path/to/run_polar_mcp.py"],
      "env": {
        "POLAR_ACCESS_TOKEN": "your-access-token"
      }
    }
  }
}
```

## Cron Example

```bash
0 6 * * * cd /absolute/path/to/polar-accesslink && . .venv/bin/activate && POLAR_ACCESS_TOKEN=your-access-token polar-cli exercises-recent --output json --out data/exercises.json
```

## OAuth Bootstrap Helper

`polar_auth.py` is now a thin wrapper over `scripts/polar_auth.py`, which remains a standalone one-time helper to:

1. Start a callback server on `127.0.0.1:3000`
2. Open Polar auth URL
3. Exchange code for token
4. Optionally register user with `POST /v3/users`

Before running it, create a Polar AccessLink client and configure your redirect URL
using the official Polar docs:

- https://www.polar.com/accesslink-api/?srsltid=AfmBOorLohdyoKgJzuBTMkXHdaePysjJjcxexJQiq5ZH5UyDWFS_3aK8#authentication

Example:

```bash
export POLAR_CLIENT_ID='your-client-id'
export POLAR_CLIENT_SECRET='your-client-secret'
export POLAR_REDIRECT_URI='http://127.0.0.1:3000/auth/polar/callback'
export POLAR_MEMBER_ID='your-member-id'
python3 polar_auth.py
```

## Migration Notes

- Python package changed from `polar_mcp` to `polar_accesslink`.
- Distribution name changed from `polar-mcp` to `polar-accesslink`.
- `polar-mcp` stays as the MCP executable.
- `run_polar_mcp.py` stays as a compatibility wrapper, but now imports the renamed module.
- New automation entrypoint: `polar-cli`.
- If you have direct Python imports, cronjobs, or MCP configs pinned to old module paths, update them before upgrading.

## Privacy And Publishing

- Do not commit `.env` files or real Polar credentials.
- Do not post raw workout exports (`.tcx`, `.fit`, `.gpx`) publicly unless you are comfortable sharing that data.
- `exercise_by_id(..., include_tcx_metadata=true)` may surface workout titles and notes from your TCX export.

## Known Limitations

- `activities` are day-level summaries/samples, not workout-session objects.
- `cardio-load` is read-only load status/history data.
- `exercise` JSON does not expose workout `title`/`notes`.
- `include_tcx_metadata=true` makes an extra TCX request per exercise to enrich `title` and `notes`.
- **TCX `title` is limited to 15 characters** — the Garmin TCX XSD schema defines `Plan/Name` as `RestrictedToken_t` (`maxLength=15`). Polar truncates longer titles to comply with the spec. The `notes` field (`xsd:string`) has no length limit. If you need full exercise descriptions, put them in the Notes field in Polar Flow.
- `GPX` data is only available when an exercise has route data.

## TODO

- Add raw export helpers for `FIT` and `GPX` when needed.
