---
name: music-production-agent
description: Plan and execute music transcription, lyric alignment, Synthesizer V vocals, arrangement, REAPER mixing, and workflow updates within the user's current scope.
---

# Music Production Agent

Use this skill for transcription, vocal production, music arrangement/mixing, or updates to the production workflow. Follow the user's current scope. Documentation and tool questions do not automatically start a song project or open a DAW.

## Workflow

1. Read the portable [workflow](../../docs/workflow.md). When continuing existing work, inspect the current revision and actual files; do not redo completed work because a tracking status is stale.
2. Identify separate sources of truth for structure/time, melody, lyrics/phonemes, and the current project. A lyric line or note count does not establish exact syllable alignment.
3. If planner/executor roles are available, have the planner make one bounded plan and let the executor continue authorized work. Model selection is controlled by the user's configuration; do not claim a model change based on prompting.
4. Keep one DAW/UI writer at a time, including project focus, plugin windows, clipboard, and export. Hand off the exact operation and write ownership when a tool cannot use the host UI.
5. Each analysis must answer a concrete question that changes the next production action. Use targeted waveform, spectrogram, F0, onset, phase, or envelope evidence only when it helps answer that question. Visual evidence is not listening and cannot prove naturalness or intelligibility.
6. Use [alignment guidance](../../docs/alignment-and-visual-diagnostics.md) to distinguish global offset, drift, and local lyric/note conflicts. Drums can anchor rhythm but cannot determine lead-vocal pitch or lyrics.
7. For SynthV, read the target group and its actual Vocal/Voice Part/modes, then follow [SV2 tuning](../../docs/synthv2-tuning.md). For REAPER, follow [REAPER production](../reaper-production/SKILL.md) and [vocal mixing](../../docs/vocal-mixing.md).
8. Continue reversible, authorized work without repeated approvals. Do not add full-project QA, planner rechecks, or user listening gates that the user did not request.

## Save and deliver

- Preserve originals; create a versioned working copy before modifying them.
- Save before loading a plugin that is new or has previously hung. The same failure without new evidence is not a reason to retry.
- A normal native save does not require closing and reopening. After an offline rewrite of an open native project, actually close it before reopening the edited file; invoking Open on the same path may leave the live project unchanged.
- Confirm required output files and their real format once. Report native renders and external recovery mixes separately when their processing differs.
- State what changed and any real limitations. If audio was not auditioned, say so; do not claim that it sounds natural, clear, or approved.
