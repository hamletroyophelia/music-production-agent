---
name: reaper-production
description: Work in REAPER on arrangement, MIDI, audio routing, effects, mixing, and exports; use targeted diagnostics and preserve a single host writer.
---

# REAPER Production

Use an available REAPER MCP or scripting integration only when connected. Discover the current tool schema and host state before writing; an MCP process being present does not prove that REAPER is connected.

1. At task start, read the current project, target tracks/time range, relevant media, routing, and effect instances. Do not scan the whole project for every small change.
2. Preserve the source project and edit a versioned copy. Only one agent may write to REAPER, the open project, UI focus, plugin windows, clipboard, or exports at a time.
3. MIDI/audio timing depends on tempo map, meter/pickup, project zero, item position/source offset/playrate, and MIDI PPQ. Use [alignment guidance](../../docs/alignment-and-visual-diagnostics.md); drum pitch cannot establish vocal pitch.
4. Verify a plugin's current instance, parameters, units, and load state before relying on it. Installation or scanning does not establish authorization or successful loading. Save before loading an untried or previously unstable plugin.
5. Start with static fader/pan and arrangement balance. Add EQ, dynamics, bass/kick ducking, de-essing, width, delay, or reverb only to solve an observed problem. Use [vocal mixing guidance](../../docs/vocal-mixing.md).
6. If a vocal is absent or too low, compare the vocal stem with its matching source at the same processing/gain stage, then inspect item/take trim, envelope, fader, mute, FX, and routing. Confirm the actual master vocal contribution only after the vocal path is known. Do not compare a pre-master vocal stem with a post-master instrumental and do not raise Master first to mask a missing vocal.
7. For volume envelopes, `points_added` is not proof of correct gain. Use the active tool contract: linear `Volume` input should be converted internally using the envelope scaling mode, with raw/scaling details in the response. If those details are absent, treat the integration as old/unclear and do not write guessed values. See the envelope notes in [vocal mixing](../../docs/vocal-mixing.md).
8. Native saves do not need routine reopen cycles. After editing the project file offline while it is open, close it and open the modified file from disk once; reopening the same path may not reload it.
9. Make one issue-specific confirmation after a targeted repair. Do not add full-project tests, repeated write handoffs, or planner approval gates without a concrete reason.

Report the actual output format and provenance. If an external recovery mix uses a different chain from the `.rpp`, do not present it as a reproducible native render. Visual diagnostics cannot substitute for listening or prove vocal naturalness.
