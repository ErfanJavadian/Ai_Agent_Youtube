"""Integration tests for project persistence and workflow transitions."""
import tempfile
import unittest
from pathlib import Path

from ai_yas.storage import ProjectStore
from ai_yas.workflow import (
    InvalidTransitionError,
    Stage,
    WorkflowEngine,
    WorkflowStatus,
)


class WorkflowEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.engine = WorkflowEngine(ProjectStore(Path(self.temp.name)))

    def create(self):
        return self.engine.create_project(
            project_id="demo-video",
            title="The Future of AI",
            target_audience="Curious general audience",
            topic="How AI may change science",
        )

    def advance_to_approval(self):
        self.create()
        for _ in range(10):
            self.engine.start("demo-video")
            self.engine.complete_current_stage("demo-video")

    def test_create_and_reload_project(self):
        created = self.create()
        loaded = self.engine.snapshot("demo-video")
        self.assertEqual(created["workflow"]["current_stage"], Stage.INTAKE.value)
        self.assertEqual(loaded["project"]["title"], "The Future of AI")
        self.assertEqual(loaded["workflow"]["status"], WorkflowStatus.READY.value)

    def test_full_lifecycle_requires_explicit_approval(self):
        self.advance_to_approval()
        before = self.engine.snapshot("demo-video")["workflow"]
        self.assertEqual(before["current_stage"], Stage.APPROVAL.value)
        self.assertEqual(before["status"], WorkflowStatus.READY.value)

        with self.assertRaises(InvalidTransitionError):
            self.engine.start("demo-video")
            # If start succeeds, completing approval without approval must fail.
            self.engine.complete_current_stage("demo-video")

    def test_approval_gate_and_completion(self):
        self.advance_to_approval()
        self.engine.request_approval("demo-video")
        pending = self.engine.snapshot("demo-video")["workflow"]
        self.assertEqual(pending["status"], WorkflowStatus.WAITING_FOR_HUMAN.value)

        self.engine.resolve_approval("demo-video", approved=True, note="Reviewed")
        finished = self.engine.complete_current_stage("demo-video")
        self.assertEqual(finished["workflow"]["current_stage"], Stage.COMPLETE.value)
        self.assertEqual(finished["workflow"]["status"], WorkflowStatus.COMPLETED.value)
        self.assertEqual(finished["project"]["status"], "completed")

    def test_rejected_approval_blocks_and_can_be_retried(self):
        self.advance_to_approval()
        self.engine.request_approval("demo-video")
        rejected = self.engine.resolve_approval("demo-video", approved=False, note="Fix citations")
        self.assertEqual(rejected["workflow"]["status"], WorkflowStatus.BLOCKED.value)
        self.assertEqual(rejected["workflow"]["blocked_reason"], "Fix citations")
        retried = self.engine.retry("demo-video")
        self.assertEqual(retried["workflow"]["status"], WorkflowStatus.READY.value)
        self.assertEqual(retried["workflow"]["human_approval"], "not_requested")

    def test_failure_can_be_retried_and_attempt_is_counted(self):
        self.create()
        started = self.engine.start("demo-video")
        self.assertEqual(started["workflow"]["attempt"], 1)
        failed = self.engine.fail("demo-video", "temporary render failure")
        self.assertEqual(failed["workflow"]["status"], WorkflowStatus.FAILED.value)
        retried = self.engine.retry("demo-video")
        self.assertEqual(retried["workflow"]["status"], WorkflowStatus.READY.value)
        self.assertEqual(self.engine.start("demo-video")["workflow"]["attempt"], 2)

    def test_invalid_project_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.create_project("../escape", "Bad", "Audience")

    def test_duplicate_project_is_rejected(self):
        self.create()
        with self.assertRaises(FileExistsError):
            self.create()

    def test_cannot_complete_when_not_running(self):
        self.create()
        with self.assertRaises(InvalidTransitionError):
            self.engine.complete_current_stage("demo-video")


if __name__ == "__main__":
    unittest.main()
