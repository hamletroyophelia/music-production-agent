# Publishing without private material

This distribution contains generic workflow instructions, configuration templates, helper code and an integration patch. It excludes project sessions, lyrics, MIDI, audio, screenshots, local voicebank/plugin inventories, real machine paths, credentials, conversation logs and old Git history.

- Use a separate publication directory and an explicit file list; do not initialize Git in an existing music workspace and add everything.
- Generate machine-specific configuration locally. Keep it ignored by Git.
- Before committing, inspect the staged file list and scan for private paths, account details, token/private-key patterns and binary/music files. A regex scan reduces common mistakes but does not prove complete anonymization; review the actual publishing set.
- Keep third-party license/copyright attribution; an author's public credit is not a secret to redact.
- Credentials are used by the GitHub client/connector, never copied into this package. Use a GitHub no-reply address for Git commit metadata if appropriate.
- Diagnostics should report paths or finding categories without printing secret values.
