# Antigravity telemetry hook

The `googlecloudtools.datacloud_telemetry` PreToolUse hook is disabled locally.

It blocked Antigravity headless tool calls on 2026-09-21 because its command
resolved `telemetry_hook_bundle.js` with invalid quoting. The hook is telemetry
only; it is not a Solo-Code Harness permission, locking, scope, or verification
control.

Configuration:

```text
C:\\Users\\Giang_PC\\.gemini\\config\\plugins\\googlecloudtools.datacloud_telemetry\\hooks.json
```

The plugin remains installed. Its `enabled` field is set to `false`, so GUI and
headless Antigravity keep their normal tools while this telemetry hook does not
run.

After updating Antigravity or its Google Cloud Tools plugins, check that field.
If an update turns it back on, first test a read-only headless request. Re-enable
the hook only after its command runs successfully without blocking `view_file`
or `run_command`.
