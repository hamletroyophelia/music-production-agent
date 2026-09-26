# Volume-envelope scaling fix

The Python tool advertises linear Volume amplitudes (1.0 = 0 dB), but the upstream Lua writer at the pinned revision inserts values directly into a potentially fader-scaled envelope. This can create near-zero/silent automation.

The patch keeps Volume inputs/outputs linear by default and converts using `GetEnvelopeScalingMode`, `ScaleToEnvelopeMode` and `ScaleFromEnvelopeMode`. Responses include native coordinates and scaling mode. Explicit `value_mode="raw"` bypasses conversion. Other envelope types retain their existing units.

Apply in a separate checkout, preserving your existing installation:

```sh
git clone https://github.com/xDarkzx/Reaper-MCP.git reaper-mcp
cd reaper-mcp
git checkout 78b57fc5f9bd10ae523b7c419c8f36ffb4c38e38
git apply --check /path/to/music-production-agent/integrations/reaper/envelope-scaling.patch
git apply /path/to/music-production-agent/integrations/reaper/envelope-scaling.patch
```

`/path/to/music-production-agent` is a placeholder for your checkout. Follow the upstream installation instructions, then reload both the Python MCP service and the Lua script in REAPER when next using the bridge. Already running services do not reload because files changed. Read `value_mode`/`scaling_mode` in the response before relying on the new contract. Do not apply the patch blindly to a different upstream version.

This patch does not fix points already written incorrectly into an existing project. Repair those from known intended gains, preserving timing; after an offline RPP edit, close and reopen the project once so the host loads disk state. Confirm the affected signal path, not just the master peak. See [vocal mixing](../../docs/vocal-mixing.md).
