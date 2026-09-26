---
name: synthv-bridge
description: Inspect and edit the Synthesizer V Studio project currently open through a connected SynthV Agent Bridge or compatible scripting adapter.
---

# SynthV Agent Bridge

Use this skill when the task changes Synthesizer V notes, lyrics, phonemes, pitch curves, automation, Vocal Modes, tracks, Note Groups, selection, or playback. The connected bridge acts on the project currently open in Synthesizer V; it does not edit an `.svp` file on disk unless its current schema explicitly says otherwise.

## Discover current tools

Tool names and schemas can differ by adapter version. When available, use `sv_status` to inspect connection/session state, `sv_describe` to fetch an unfamiliar action schema, `sv_query` for bounded reads, `sv_command` for guarded writes, and `sv_ui` for native UI actions. `sv_review` may expose a read-only runtime panel. If those names are not exposed, use the tools actually supplied by the current integration rather than assuming these methods exist.

## Read → write discipline

1. Read only the target track/Group/range needed for the change, using the adapter's fresh write-intent context when supported.
2. Build the write from that context and submit it once. Do not reuse a context across turns or across a changed session.
3. On stale context, session change, or unknown context, read the target again deliberately. Never blindly resend the old payload.
4. Respect one-based indices at the protocol boundary when the adapter uses them. A SynthV quarter note is 705,600,000 blicks; MIDI pitch is an integer where 60 is C4.
5. Shared Note Groups can affect multiple References. Confirm the intended scope before editing shared content. If the current adapter marks a capability disabled or unstable, do not bypass it with unguarded file editing.

A note commonly includes local Group `onset`, `duration`, MIDI `pitch`, `lyrics`, optional `phonemes`, `detune`, and adapter-specific identity/fingerprint fields. Automation commonly uses a parameter name, interpolation mode, and position/value points. Read the current schema and parameter `range`/`defaultValue` before writing; do not assume units or supported parameters.

## Vocal identity and modes

Track defaults and a Note Group's actual Vocal can differ. The scripting API may not expose current Vocal identity or modes that remain at default values. An empty API result is not proof that a voice has no modes.

Use available native UI automation to inspect the target Group, Vocal/Voice Part, and full Voice Panel mode state. Record exact mode names, Pitch/Timbre/Pronunciation values, units, and ranges. Re-read after changing Group or Vocal. Consult [SV2 tuning guidance](../../docs/synthv2-tuning.md) and the relevant generation's official documentation; never guess names or parameter indices from another voicebank.

If a child agent cannot use the native UI, hand the bounded UI observation/action to the current host writer. Ask the user for missing identity information only if available UI and tools cannot supply it. Do not request screenshots by default.

## Errors and scope

| Result | Response |
| --- | --- |
| Stale target/context or session changed | Read the intended target again; never reuse the old write payload. |
| Shared Group write | Confirm that the edit is intended for all linked References before proceeding. |
| Query too large | Narrow the range, page size, or returned fields. |
| Host postcondition failure | Follow the adapter's reported undo/recovery instruction, then read the target again. |
| Build/protocol mismatch | Consult the connected adapter's setup instructions; stop writes until versions are coherent. |

Suggest a working copy before the first write. State the target and intended change once, then complete already-authorized reversible edits without repeated approval requests. Do not alter lyrics, points outside the target range, or other Groups unless the user authorized it. A metadata guard is not subjective audio QA; do one bounded target confirmation where needed, not a repeated full-project scan.
