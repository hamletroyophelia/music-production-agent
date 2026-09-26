#!/usr/bin/env python3
"""Create and track music production jobs.

This is a local status and handoff helper. It does not call models, operate a
DAW, or inspect the contents of source files.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


STAGES = (
    "intake",
    "transcription",
    "lyrics",
    "vocal",
    "arrangement",
    "mix",
    "delivery",
)
STATUSES = ("pending", "running", "blocked", "done", "skipped")
JOB_VERSION = 1
DEFAULT_DEPENDENCIES = {
    "intake": [],
    "transcription": ["intake"],
    "lyrics": ["transcription"],
    "vocal": ["lyrics"],
    "arrangement": ["transcription"],
    "mix": ["vocal", "arrangement"],
    "delivery": ["mix"],
}


class JobError(Exception):
    """An invalid job request or job file."""


def _nonempty_text(value: str | None, label: str) -> str:
    if value is None or not value.strip():
        raise JobError(f"{label} must not be empty")
    return value.strip()


def _absolute_existing_file(raw_path: str, label: str) -> str:
    if not raw_path or not raw_path.strip():
        raise JobError(f"{label} path must not be empty")
    path = Path(raw_path).expanduser()
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise JobError(f"{label} does not exist: {raw_path}") from exc
    if not resolved.is_file():
        raise JobError(f"{label} must be a file: {raw_path}")
    return str(resolved)


def _absolute_output_dir(raw_path: str) -> Path:
    if not raw_path or not raw_path.strip():
        raise JobError("output directory path must not be empty")
    return Path(raw_path).expanduser().resolve(strict=False)


def _model_metadata(role: str) -> dict[str, Any]:
    """Record optional model requests without claiming to select a runtime model."""
    prefix = f"MUSIC_AGENT_{role.upper()}"
    requested_model = os.environ.get(f"{prefix}_MODEL", "").strip()
    requested_effort = os.environ.get(f"{prefix}_REASONING_EFFORT", "").strip()
    if not requested_model and not requested_effort:
        return {
            "configuration_source": "inherited",
            "runtime_selection_confirmed": False,
        }

    record: dict[str, Any] = {
        "configuration_source": "environment",
        "runtime_selection_confirmed": False,
    }
    if requested_model:
        record["requested_model"] = requested_model
    if requested_effort:
        record["requested_reasoning_effort"] = requested_effort
    return record


def _model_summary(record: dict[str, Any]) -> str:
    if record.get("configuration_source") == "inherited":
        return "inherited from the runtime; active model is not inspected by this tool"
    requests = [f"requested model: {record['requested_model']}"] if record.get("requested_model") else []
    if record.get("requested_reasoning_effort"):
        requests.append(f"requested reasoning effort: {record['requested_reasoning_effort']}")
    detail = "; ".join(requests) if requests else "no request values"
    return f"environment metadata only ({detail}); runtime selection is not verified"


def _new_job(title: str, output_dir: Path, sources: list[str], scope: str,
             deliverables: list[str]) -> dict[str, Any]:
    return {
        "version": JOB_VERSION,
        "id": str(uuid.uuid4()),
        "revision": 1,
        "revision_history": [],
        "title": title,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "output_dir": str(output_dir),
        "models": {
            "planner": _model_metadata("planner"),
            "executor": _model_metadata("executor"),
        },
        "inputs": sources,
        "scope": scope,
        "deliverables": deliverables,
        "dependencies": {stage: list(dependencies)
                          for stage, dependencies in DEFAULT_DEPENDENCIES.items()},
        "analysis_policy": {
            "mode": "visual_targeted",
            "subjective_listening": False,
        },
        "stages": {
            stage: {
                "status": "pending",
                "evidence": [],
                "note": "",
                "accepted": False,
            }
            for stage in STAGES
        },
    }


def _plan_text(job: dict[str, Any]) -> str:
    lines = [
        f"# {job['title']}",
        "",
        f"- Job ID: `{job['id']}`",
        f"- Created: {job['created_at']}",
        f"- Planner model metadata: {_model_summary(job['models']['planner'])}",
        f"- Executor model metadata: {_model_summary(job['models']['executor'])}",
        "",
        "## Scope",
        "",
        job["scope"],
        "",
        "## Sources",
        "",
    ]
    lines.extend(f"- `{source}`" for source in job["inputs"])
    lines.extend(["", "## Deliverables", ""])
    lines.extend(f"- {item}" for item in job["deliverables"])
    lines.extend([
        "",
        "## Workflow",
        "",
        "Stages may run as soon as work begins; they do not wait for every earlier stage.",
        "Completion dependencies are stored in `job.json` and may be overridden per job.",
        "`done` means the authorized scoped work is complete; it does not mean subjective audio quality passed.",
    ])
    lines.extend(["", "## Stages", ""])
    lines.extend(f"- [ ] **{stage}** — pending" for stage in STAGES)
    lines.extend([
        "",
        "`job.json` is the status source; these checkboxes are an initial planning template.",
        "",
        "Update stage status and evidence with `music_job.py update`. A skipped",
        "stage is recorded as not accepted. Use `music_job.py revise` to reopen",
        "only the specified stage or stages; later stages are not reset automatically.",
        "",
    ])
    return "\n".join(lines)


def _write_new_files(output_dir: Path, files: dict[str, str]) -> None:
    """Create a set of new files without overwriting existing files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    destinations = [output_dir / name for name in files]
    present = [str(path) for path in destinations if path.exists()]
    if present:
        raise JobError("refusing to overwrite existing job file(s): " + ", ".join(present))

    temporary_paths: list[Path] = []
    created_paths: list[Path] = []
    try:
        for name, contents in files.items():
            fd, temporary_name = tempfile.mkstemp(prefix=f".{name}.", suffix=".tmp", dir=output_dir)
            temporary = Path(temporary_name)
            temporary_paths.append(temporary)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(contents)
                stream.flush()
                os.fsync(stream.fileno())

        # Hard-link creation is atomic and fails if another process created a
        # destination after the initial existence check.
        for temporary, destination in zip(temporary_paths, destinations):
            os.link(temporary, destination)
            created_paths.append(destination)
    except Exception:
        for destination in created_paths:
            try:
                destination.unlink()
            except OSError:
                pass
        raise
    finally:
        for temporary in temporary_paths:
            try:
                temporary.unlink()
            except OSError:
                pass


def init_job(args: argparse.Namespace) -> int:
    title = _nonempty_text(args.title, "title")
    scope = _nonempty_text(args.scope, "scope")
    deliverables = [_nonempty_text(value, "deliverable") for value in args.deliverable]
    if not deliverables:
        raise JobError("at least one --deliverable is required")
    if not args.source:
        raise JobError("at least one --source is required")
    sources = [_absolute_existing_file(value, "source") for value in args.source]
    output_dir = _absolute_output_dir(args.output)
    job = _new_job(title, output_dir, sources, scope, deliverables)
    json_text = json.dumps(job, ensure_ascii=False, indent=2) + "\n"
    _write_new_files(output_dir, {"job.json": json_text, "PLAN.md": _plan_text(job)})
    print(f"Created job: {output_dir / 'job.json'}")
    return 0


def _load_job(path_value: str) -> tuple[Path, dict[str, Any]]:
    if not path_value or not path_value.strip():
        raise JobError("job path must not be empty")
    path = Path(path_value).expanduser().resolve(strict=False)
    try:
        with path.open("r", encoding="utf-8") as stream:
            job = json.load(stream)
    except FileNotFoundError as exc:
        raise JobError(f"job file does not exist: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise JobError(f"cannot read job file {path}: {exc}") from exc
    if not isinstance(job, dict) or job.get("version") != JOB_VERSION:
        raise JobError(f"unsupported or invalid job file: {path}")
    stages = job.get("stages")
    if not isinstance(stages, dict) or any(stage not in stages for stage in STAGES):
        raise JobError(f"job file is missing required stages: {path}")
    for stage in STAGES:
        record = stages[stage]
        if not isinstance(record, dict) or record.get("status") not in STATUSES:
            raise JobError(f"invalid state for stage {stage!r} in {path}")
    revision = job.get("revision", 1)
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise JobError(f"invalid revision number in {path}")
    if not isinstance(job.get("revision_history", []), list):
        raise JobError(f"invalid revision_history in {path}")
    _resolve_dependencies(job)
    return path, job


def _overall_status(stages: dict[str, dict[str, Any]]) -> str:
    values = [stages[stage]["status"] for stage in STAGES]
    if all(value == "done" for value in values):
        return "done"
    if "blocked" in values:
        return "blocked"
    if "running" in values:
        return "running"
    if (all(value in ("done", "skipped") for value in values)
            and stages["delivery"]["status"] == "done"):
        return "done (scoped; skipped stages not accepted)"
    if all(value in ("done", "skipped") for value in values):
        return "incomplete (delivery stage is not done)"
    return "pending"


def status_job(args: argparse.Namespace) -> int:
    _, job = _load_job(args.job)
    print(f"Job: {job.get('title', '(untitled)')}")
    print(f"Overall: {_overall_status(job['stages'])}")
    for stage in STAGES:
        record = job["stages"][stage]
        suffix = " (not accepted)" if record["status"] == "skipped" else ""
        print(f"  {stage}: {record['status']}{suffix}")
    return 0


def _resolve_dependencies(job: dict[str, Any]) -> dict[str, list[str]]:
    """Merge per-job overrides onto the default graph and reject invalid graphs."""
    overrides = job.get("dependencies", DEFAULT_DEPENDENCIES)
    if not isinstance(overrides, dict):
        raise JobError("dependencies must be an object mapping stages to stage lists")

    unknown_stages = [stage for stage in overrides if stage not in STAGES]
    if unknown_stages:
        raise JobError("unknown dependency stage(s): " + ", ".join(map(str, unknown_stages)))

    graph = {stage: list(dependencies)
             for stage, dependencies in DEFAULT_DEPENDENCIES.items()}
    for stage, dependencies in overrides.items():
        if not isinstance(dependencies, list):
            raise JobError(f"dependencies for {stage!r} must be a list")
        checked: list[str] = []
        for dependency in dependencies:
            if not isinstance(dependency, str) or dependency not in STAGES:
                raise JobError(f"unknown dependency {dependency!r} for stage {stage!r}")
            if dependency == stage:
                raise JobError(f"stage {stage!r} cannot depend on itself")
            if dependency in checked:
                raise JobError(f"duplicate dependency {dependency!r} for stage {stage!r}")
            checked.append(dependency)
        graph[stage] = checked

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(stage: str) -> None:
        if stage in visiting:
            raise JobError(f"dependency cycle includes stage {stage!r}")
        if stage in visited:
            return
        visiting.add(stage)
        for dependency in graph[stage]:
            visit(dependency)
        visiting.remove(stage)
        visited.add(stage)

    for stage in STAGES:
        visit(stage)
    return graph


def _unfinished_dependencies(job: dict[str, Any], stage: str) -> list[str]:
    graph = _resolve_dependencies(job)
    return [dependency for dependency in graph[stage]
            if job["stages"][dependency]["status"] not in ("done", "skipped")]


ALLOWED_TRANSITIONS = {
    "pending": {"pending", "running", "blocked", "done", "skipped"},
    "running": {"running", "blocked", "done", "skipped"},
    "blocked": {"blocked", "pending", "running", "done"},
    "skipped": {"skipped"},
    "done": set(),
}


def update_job(args: argparse.Namespace) -> int:
    path, job = _load_job(args.job)
    stage = args.stage
    target_status = args.status
    record = job["stages"][stage]
    current_status = record["status"]
    if current_status == "done":
        raise JobError(f"stage {stage!r} is already done and cannot be modified; start a new job version")
    if target_status not in ALLOWED_TRANSITIONS[current_status]:
        raise JobError(f"invalid transition for {stage}: {current_status} -> {target_status}")

    evidence = list(record.get("evidence", []))
    for raw_path in args.evidence:
        resolved = _absolute_existing_file(raw_path, "evidence")
        if resolved not in evidence:
            evidence.append(resolved)
    note = record.get("note", "")
    if args.note is not None:
        note = args.note.strip()

    if target_status == "done":
        unfinished = _unfinished_dependencies(job, stage)
        if unfinished:
            raise JobError(
                f"cannot mark {stage!r} done before dependencies are done or skipped: "
                + ", ".join(unfinished)
            )
        if not evidence:
            raise JobError(f"cannot mark {stage!r} done without at least one existing evidence file")
        for evidence_path in evidence:
            if not Path(evidence_path).is_file():
                raise JobError(f"cannot mark {stage!r} done because evidence no longer exists: {evidence_path}")
    if target_status == "skipped" and not note:
        raise JobError(f"cannot skip {stage!r} without a non-empty --note explaining why")

    record["status"] = target_status
    record["evidence"] = evidence
    record["note"] = note
    record["accepted"] = target_status == "done"
    _atomic_write_json(path, job)
    acceptance = " (not accepted)" if target_status == "skipped" else ""
    print(f"Updated {stage}: {target_status}{acceptance}")
    return 0


def revise_job(args: argparse.Namespace) -> int:
    path, job = _load_job(args.job)
    note = _nonempty_text(args.note, "note")
    stages = list(dict.fromkeys(args.stage))
    if not stages:
        raise JobError("at least one --stage is required")

    current_revision = job.get("revision", 1)
    next_revision = current_revision + 1
    old_states = {stage: copy.deepcopy(job["stages"][stage]) for stage in stages}
    history_path = path.parent / "revision_history" / f"revision-{next_revision:04d}.json"
    entry = {
        "revision": next_revision,
        "from_revision": current_revision,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": note,
        "stages": old_states,
        "history_file": str(history_path),
    }
    history_file_record = json.dumps(entry, ensure_ascii=False, indent=2) + "\n"
    _write_new_files(history_path.parent, {history_path.name: history_file_record})

    job["revision"] = next_revision
    job.setdefault("revision_history", []).append(entry)
    for stage in stages:
        record = job["stages"][stage]
        record["status"] = "running"
        record["accepted"] = False
        record["evidence"] = []
        record["note"] = note
    try:
        _atomic_write_json(path, job)
    except Exception:
        try:
            history_path.unlink()
        except OSError:
            pass
        raise

    print(f"Revised revision {next_revision}: " + ", ".join(stages))
    print(f"History: {history_path}")
    return 0


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    """Replace one JSON file atomically using a temporary file beside it."""
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create and track music production job files. This is a status and handoff "
            "tool only: it does not schedule models, operate a DAW, or read source contents."
        ),
        epilog=(
            "Running records work that has started; completion uses the job dependency graph and existing evidence. "
            "Done means scoped work is complete, not an audio-quality pass. Use revise to reopen only named stages."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create a new job.json and PLAN.md")
    init_parser.add_argument("--title", required=True, help="job title")
    init_parser.add_argument("--output", required=True, metavar="DIR", help="new job directory")
    init_parser.add_argument("--source", required=True, action="append", metavar="PATH",
                             help="source file path; repeat for multiple files")
    init_parser.add_argument("--scope", required=True, help="work scope")
    init_parser.add_argument("--deliverable", required=True, action="append", metavar="TEXT",
                             help="expected deliverable; repeat for multiple deliverables")
    init_parser.set_defaults(func=init_job)

    status_parser = subparsers.add_parser("status", help="show job and stage status")
    status_parser.add_argument("--job", required=True, metavar="PATH", help="path to job.json")
    status_parser.set_defaults(func=status_job)

    update_parser = subparsers.add_parser("update", help="update one stage and its handoff evidence")
    update_parser.add_argument("--job", required=True, metavar="PATH", help="path to job.json")
    update_parser.add_argument("--stage", required=True, choices=STAGES)
    update_parser.add_argument("--status", required=True, choices=STATUSES)
    update_parser.add_argument("--evidence", action="append", default=[], metavar="PATH",
                               help="existing evidence file; repeat for multiple files")
    update_parser.add_argument("--note", help="stage note; required when setting skipped")
    update_parser.set_defaults(func=update_job)

    revise_parser = subparsers.add_parser("revise", help="reopen specific stages for a new revision")
    revise_parser.add_argument("--job", required=True, metavar="PATH", help="path to job.json")
    revise_parser.add_argument("--stage", required=True, action="append", choices=STAGES,
                               help="stage to reopen; repeat for multiple stages")
    revise_parser.add_argument("--note", required=True, help="required reason for the revision")
    revise_parser.set_defaults(func=revise_job)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except JobError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: filesystem operation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
