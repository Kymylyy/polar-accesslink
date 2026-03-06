# polar-mcp

`polar-mcp` is a read-only MCP server for Polar AccessLink.
V1 scope includes `activities` and `cardio-load`.

## Features

- `activities_range(from_date, to_date, include_samples=false)`
- `activity_by_date(date, include_samples=false)`
- `cardio_load_recent(days=30)`
- `cardio_load_by_date(date)`

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

Example:

```bash
export POLAR_CLIENT_ID='your-client-id'
export POLAR_CLIENT_SECRET='your-client-secret'
export POLAR_REDIRECT_URI='http://127.0.0.1:3000/auth/polar/callback'
export POLAR_MEMBER_ID='kymyly-main'
python3 polar_auth.py
```

## Known Limitations

- `activities` are day-level summaries/samples, not workout-session objects.
- `cardio-load` is read-only load status/history data.
- `exercises` are intentionally not implemented in v1.

## TODO

- Add `exercises` tool family after live payloads become available.
- Consider optional TCX-based enrichment (`name`/`notes`) for session views after `exercises` rollout.
