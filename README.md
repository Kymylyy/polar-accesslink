# polar-mcp

`polar-mcp` is a read-only MCP server for Polar AccessLink.
Current scope includes `activities`, `cardio-load`, and `exercises`.

It is designed for personal data access through an LLM or MCP-compatible client.

## Features

- `activities_range(from_date, to_date, include_samples=false)`
- `activity_by_date(date, include_samples=false)`
- `cardio_load_recent(days=30)`
- `cardio_load_by_date(date)`
- `exercises_recent(include_samples=false, include_zones=false, include_route=false, include_tcx_metadata=false)`
- `exercise_by_id(exercise_id, include_samples=false, include_zones=false, include_route=false, include_tcx_metadata=false)`

All tools return structured JSON envelopes:

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
polar-mcp
```

You can also run:

```bash
python3 run_polar_mcp.py
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

## Privacy And Publishing

- Do not commit `.env` files or real Polar credentials.
- Do not post raw workout exports (`.tcx`, `.fit`, `.gpx`) publicly unless you are comfortable sharing that data.
- `exercise_by_id(..., include_tcx_metadata=true)` may surface workout titles and notes from your TCX export.

## Known Limitations

- `activities` are day-level summaries/samples, not workout-session objects.
- `cardio-load` is read-only load status/history data.
- `exercise` JSON does not expose workout `title`/`notes`.
- `include_tcx_metadata=true` makes an extra TCX request per exercise to enrich `title` and `notes`.
- `GPX` data is only available when an exercise has route data.

## TODO

- Add raw export helpers for `FIT` and `GPX` when needed.
- Consider richer TCX parsing beyond `title`/`notes` if session views need laps or trackpoints.
