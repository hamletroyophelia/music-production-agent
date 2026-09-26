# Music production agent routing

For music production or workflow maintenance, read `skills/music-production-agent/SKILL.md` and the relevant document it links to. Use `music_planner` for bounded planning/research and `music_executor` for implementation when those roles are actually available. Follow the user's configured models; do not pretend a role name changes the running model.

At any time, only one agent may write to DAWs, native UI, the clipboard, exports or a shared project file. Other agents can work independently on offline references. Keep current output and the user's latest feedback authoritative. Stage bookkeeping is not an approval gate.

For workflow-only, publishing or documentation requests, do not launch a song, DAW or render. Keep private material and machine-specific configuration outside the repository. Follow `PRIVACY.md` before publishing.
