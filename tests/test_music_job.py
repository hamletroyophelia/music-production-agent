"""Unit tests for the music job status and handoff helper."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import music_job


class MusicJobTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source.wav"
        self.source.write_text("source content must not be copied", encoding="utf-8")
        self.evidence = self.root / "proof.txt"
        self.evidence.write_text("evidence", encoding="utf-8")
        self.output = self.root / "job"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def call(self, *argv: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = music_job.main(list(argv))
        return result, stdout.getvalue(), stderr.getvalue()

    def init_args(self, output: Path | None = None, source: str | None = None) -> tuple[str, ...]:
        return (
            "init",
            "--title", "Example song",
            "--output", str(output if output is not None else self.output),
            "--source", source if source is not None else str(self.source),
            "--scope", "Transcribe melody and prepare a vocal arrangement.",
            "--deliverable", "MIDI file",
            "--deliverable", "Final mix",
        )

    def make_job(self) -> Path:
        result, _, error = self.call(*self.init_args())
        self.assertEqual(result, 0, error)
        return self.output / "job.json"

    def update(self, job: Path, stage: str, status: str, *extra: str) -> tuple[int, str, str]:
        return self.call("update", "--job", str(job), "--stage", stage,
                         "--status", status, *extra)

    def test_init_records_paths_without_reading_source_and_refuses_overwrite(self) -> None:
        env_keys = (
            "MUSIC_AGENT_PLANNER_MODEL",
            "MUSIC_AGENT_PLANNER_REASONING_EFFORT",
            "MUSIC_AGENT_EXECUTOR_MODEL",
            "MUSIC_AGENT_EXECUTOR_REASONING_EFFORT",
        )
        with mock.patch.dict(os.environ, {key: "" for key in env_keys}):
            result, _, error = self.call(*self.init_args())
        self.assertEqual(result, 0, error)
        job_path = self.output / "job.json"
        plan_path = self.output / "PLAN.md"
        original_job = job_path.read_bytes()
        original_plan = plan_path.read_bytes()
        job = json.loads(original_job)
        self.assertEqual(job["inputs"], [str(self.source.resolve())])
        self.assertNotIn("source content must not be copied", original_job.decode("utf-8"))
        self.assertIn("job.json` is the status source", original_plan.decode("utf-8"))
        inherited = {
            "configuration_source": "inherited",
            "runtime_selection_confirmed": False,
        }
        self.assertEqual(job["models"]["planner"], inherited)
        self.assertEqual(job["models"]["executor"], inherited)
        self.assertEqual(list(job["stages"]), list(music_job.STAGES))
        self.assertTrue(all(stage["status"] == "pending" for stage in job["stages"].values()))
        self.assertEqual(job["revision"], 1)
        self.assertEqual(job["revision_history"], [])
        self.assertEqual(job["dependencies"], music_job.DEFAULT_DEPENDENCIES)
        self.assertEqual(job["analysis_policy"], {
            "mode": "visual_targeted",
            "subjective_listening": False,
        })
        self.assertIn("not mean subjective audio quality passed", original_plan.decode("utf-8"))
        self.assertIn("active model is not inspected", original_plan.decode("utf-8"))

        result, _, error = self.call(*self.init_args())
        self.assertEqual(result, 2)
        self.assertIn("refusing to overwrite", error)
        self.assertEqual(job_path.read_bytes(), original_job)
        self.assertEqual(plan_path.read_bytes(), original_plan)

    def test_model_environment_values_are_metadata_not_runtime_selection(self) -> None:
        with mock.patch.dict(os.environ, {
            "MUSIC_AGENT_PLANNER_MODEL": "example-model",
            "MUSIC_AGENT_PLANNER_REASONING_EFFORT": "high",
            "MUSIC_AGENT_EXECUTOR_MODEL": "",
            "MUSIC_AGENT_EXECUTOR_REASONING_EFFORT": "",
        }):
            job = music_job._new_job(
                "Example", self.output, [str(self.source)], "Test scope", ["Artifact"]
            )

        self.assertEqual(job["models"]["planner"], {
            "configuration_source": "environment",
            "runtime_selection_confirmed": False,
            "requested_model": "example-model",
            "requested_reasoning_effort": "high",
        })
        self.assertEqual(job["models"]["executor"]["configuration_source"], "inherited")
        plan = music_job._plan_text(job)
        self.assertIn("environment metadata only", plan)
        self.assertIn("runtime selection is not verified", plan)

    def test_empty_and_missing_paths_are_rejected(self) -> None:
        result, _, error = self.call(*self.init_args(source=""))
        self.assertEqual(result, 2)
        self.assertIn("source path must not be empty", error)

        missing = self.root / "missing.wav"
        result, _, error = self.call(*self.init_args(source=str(missing)))
        self.assertEqual(result, 2)
        self.assertIn("source does not exist", error)

        empty_output_args = list(self.init_args())
        empty_output_args[empty_output_args.index("--output") + 1] = ""
        result, _, error = self.call(*empty_output_args)
        self.assertEqual(result, 2)
        self.assertIn("output directory path must not be empty", error)

    def test_done_requires_existing_evidence(self) -> None:
        job = self.make_job()
        result, _, error = self.update(job, "intake", "done")
        self.assertEqual(result, 2)
        self.assertIn("without at least one existing evidence file", error)
        self.assertEqual(json.loads(job.read_text(encoding="utf-8"))["stages"]["intake"]["status"], "pending")

    def test_running_is_unblocked_but_done_uses_actual_dependencies(self) -> None:
        job = self.make_job()
        result, _, error = self.update(job, "mix", "running")
        self.assertEqual(result, 0, error)

        result, _, error = self.update(job, "arrangement", "done", "--evidence", str(self.evidence))
        self.assertEqual(result, 2)
        self.assertIn("dependencies are done or skipped: transcription", error)

        result, _, error = self.update(job, "intake", "done", "--evidence", str(self.evidence))
        self.assertEqual(result, 0, error)
        result, _, error = self.update(job, "transcription", "done", "--evidence", str(self.evidence))
        self.assertEqual(result, 0, error)
        # Arrangement depends on transcription, not the intervening lyrics/vocal stages.
        result, _, error = self.update(job, "arrangement", "done", "--evidence", str(self.evidence))
        self.assertEqual(result, 0, error)

    def test_legacy_job_uses_default_dependencies_and_custom_overrides_are_validated(self) -> None:
        job = self.make_job()
        data = json.loads(job.read_text(encoding="utf-8"))
        data.pop("dependencies")
        job.write_text(json.dumps(data), encoding="utf-8")
        result, _, error = self.update(job, "arrangement", "done", "--evidence", str(self.evidence))
        self.assertEqual(result, 2)
        self.assertIn("transcription", error)

        data = json.loads(job.read_text(encoding="utf-8"))
        data["dependencies"] = {"arrangement": [], "mix": ["vocal"]}
        job.write_text(json.dumps(data), encoding="utf-8")
        result, _, error = self.update(job, "arrangement", "done", "--evidence", str(self.evidence))
        self.assertEqual(result, 0, error)

        data = json.loads(job.read_text(encoding="utf-8"))
        data["dependencies"] = {"intake": ["delivery"]}
        job.write_text(json.dumps(data), encoding="utf-8")
        result, _, error = self.call("status", "--job", str(job))
        self.assertEqual(result, 2)
        self.assertIn("dependency cycle", error)

        data["dependencies"] = {"vocal": ["unlisted-stage"]}
        job.write_text(json.dumps(data), encoding="utf-8")
        result, _, error = self.call("status", "--job", str(job))
        self.assertEqual(result, 2)
        self.assertIn("unknown dependency", error)

    def test_legal_serial_updates_and_done_stage_is_immutable(self) -> None:
        job = self.make_job()
        result, _, error = self.update(job, "intake", "done", "--evidence", str(self.evidence))
        self.assertEqual(result, 0, error)
        result, _, error = self.update(job, "transcription", "running")
        self.assertEqual(result, 0, error)
        result, _, error = self.update(job, "transcription", "done", "--evidence", str(self.evidence))
        self.assertEqual(result, 0, error)

        current = job.read_bytes()
        data = json.loads(current)
        self.assertEqual(data["stages"]["intake"]["accepted"], True)
        self.assertEqual(data["stages"]["transcription"]["status"], "done")
        self.assertEqual(data["stages"]["transcription"]["evidence"], [str(self.evidence.resolve())])
        result, _, error = self.update(job, "transcription", "blocked", "--note", "Needs revision")
        self.assertEqual(result, 2)
        self.assertIn("already done and cannot be modified", error)
        self.assertEqual(job.read_bytes(), current)

    def test_skipped_requires_note_and_delivery_can_complete_scoped_job(self) -> None:
        job = self.make_job()
        for stage in music_job.STAGES[:-1]:
            if stage == "intake":
                result, _, error = self.update(job, stage, "done", "--evidence", str(self.evidence))
            else:
                result, _, error = self.update(job, stage, "skipped", "--note", f"Not in scope: {stage}")
            self.assertEqual(result, 0, error)

        result, _, error = self.update(job, "delivery", "done", "--evidence", str(self.evidence))
        self.assertEqual(result, 0, error)

        result, output, error = self.call("status", "--job", str(job))
        self.assertEqual(result, 0, error)
        self.assertIn("Overall: done (scoped; skipped stages not accepted)", output)
        self.assertIn("transcription: skipped (not accepted)", output)
        data = json.loads(job.read_text(encoding="utf-8"))
        self.assertFalse(data["stages"]["transcription"]["accepted"])
        self.assertTrue(data["stages"]["delivery"]["accepted"])

        data["stages"]["delivery"]["status"] = "skipped"
        self.assertEqual(music_job._overall_status(data["stages"]), "incomplete (delivery stage is not done)")

    def test_blocked_stage_can_resume_after_dependencies_recover_and_running_can_be_cancelled(self) -> None:
        job = self.make_job()
        result, _, error = self.update(job, "arrangement", "blocked", "--note", "Waiting for transcription")
        self.assertEqual(result, 0, error)
        result, _, error = self.update(job, "arrangement", "running")
        self.assertEqual(result, 0, error)
        result, _, error = self.update(job, "arrangement", "done", "--evidence", str(self.evidence))
        self.assertEqual(result, 2)
        self.assertIn("transcription", error)

        result, _, error = self.update(job, "intake", "done", "--evidence", str(self.evidence))
        self.assertEqual(result, 0, error)
        result, _, error = self.update(job, "transcription", "done", "--evidence", str(self.evidence))
        self.assertEqual(result, 0, error)
        result, _, error = self.update(job, "arrangement", "done", "--evidence", str(self.evidence))
        self.assertEqual(result, 0, error)

        result, _, error = self.update(job, "vocal", "running")
        self.assertEqual(result, 0, error)
        result, _, error = self.update(job, "vocal", "skipped")
        self.assertEqual(result, 2)
        self.assertIn("without a non-empty --note", error)
        result, _, error = self.update(job, "vocal", "skipped", "--note", "Cancelled by user")
        self.assertEqual(result, 0, error)
        updated = json.loads(job.read_text(encoding="utf-8"))
        self.assertEqual(updated["stages"]["vocal"]["status"], "skipped")
        self.assertFalse(updated["stages"]["vocal"]["accepted"])

    def test_revise_archives_old_stage_states_and_resets_only_named_stages(self) -> None:
        job = self.make_job()
        for stage in ("intake", "transcription", "lyrics"):
            result, _, error = self.update(job, stage, "done", "--evidence", str(self.evidence))
            self.assertEqual(result, 0, error)
        result, _, error = self.update(job, "vocal", "running", "--note", "Current work")
        self.assertEqual(result, 0, error)
        before = json.loads(job.read_text(encoding="utf-8"))

        result, output, error = self.call(
            "revise", "--job", str(job), "--stage", "transcription",
            "--stage", "vocal", "--stage", "vocal", "--note", "Correct source alignment",
        )
        self.assertEqual(result, 0, error)
        self.assertIn("revision 2", output)
        revised = json.loads(job.read_text(encoding="utf-8"))
        self.assertEqual(revised["revision"], 2)
        self.assertEqual(len(revised["revision_history"]), 1)
        history = revised["revision_history"][0]
        self.assertEqual(history["stages"]["transcription"], before["stages"]["transcription"])
        self.assertEqual(history["stages"]["vocal"], before["stages"]["vocal"])
        for stage in ("transcription", "vocal"):
            self.assertEqual(revised["stages"][stage]["status"], "running")
            self.assertFalse(revised["stages"][stage]["accepted"])
            self.assertEqual(revised["stages"][stage]["evidence"], [])
            self.assertEqual(revised["stages"][stage]["note"], "Correct source alignment")
        self.assertEqual(revised["stages"]["intake"], before["stages"]["intake"])
        self.assertEqual(revised["stages"]["lyrics"], before["stages"]["lyrics"])
        history_file = job.parent / "revision_history" / "revision-0002.json"
        self.assertEqual(json.loads(history_file.read_text(encoding="utf-8")), history)

        first_history = history_file.read_bytes()
        result, _, error = self.call(
            "revise", "--job", str(job), "--stage", "lyrics", "--note", "Update lyric mapping",
        )
        self.assertEqual(result, 0, error)
        self.assertEqual(history_file.read_bytes(), first_history)
        self.assertTrue((job.parent / "revision_history" / "revision-0003.json").is_file())
        self.assertEqual(json.loads(job.read_text(encoding="utf-8"))["revision"], 3)

    def test_revise_refuses_to_overwrite_an_existing_history_file(self) -> None:
        job = self.make_job()
        history_dir = job.parent / "revision_history"
        history_dir.mkdir()
        history_file = history_dir / "revision-0002.json"
        history_file.write_text("preserve this", encoding="utf-8")
        before = job.read_bytes()

        result, _, error = self.call(
            "revise", "--job", str(job), "--stage", "intake", "--note", "Retry intake",
        )
        self.assertEqual(result, 2)
        self.assertIn("refusing to overwrite", error)
        self.assertEqual(job.read_bytes(), before)
        self.assertEqual(history_file.read_text(encoding="utf-8"), "preserve this")

    def test_removed_registered_evidence_blocks_done(self) -> None:
        job = self.make_job()
        result, _, error = self.update(job, "intake", "running", "--evidence", str(self.evidence))
        self.assertEqual(result, 0, error)
        self.evidence.unlink()
        before = job.read_bytes()
        result, _, error = self.update(job, "intake", "done")
        self.assertEqual(result, 2)
        self.assertIn("evidence no longer exists", error)
        self.assertEqual(job.read_bytes(), before)

    def test_failed_atomic_replace_preserves_original_job(self) -> None:
        job = self.make_job()
        before = job.read_bytes()
        with mock.patch.object(music_job.os, "replace", side_effect=OSError("simulated replace failure")):
            result, _, error = self.update(job, "intake", "running")
        self.assertEqual(result, 2)
        self.assertIn("filesystem operation failed", error)
        self.assertEqual(job.read_bytes(), before)
        self.assertEqual(list(self.output.glob(".job.json.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
