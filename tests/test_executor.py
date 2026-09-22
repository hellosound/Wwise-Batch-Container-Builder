import unittest
from unittest.mock import patch

from src.executor import execute_operation_plan
from src.models import AudioFile, ContainerType, GroupPlan, PlanAction, WwiseObject


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict | None]] = []

    def call(self, uri: str, args: dict | None = None, options: dict | None = None) -> dict:
        self.calls.append((uri, args))
        return {}


class ExecutorTests(unittest.TestCase):
    def test_executor_moves_existing_objects_from_plan(self) -> None:
        client = RecordingClient()
        obj = WwiseObject(
            id="sound-guid",
            name="sfx_attack_01",
            type="Sound",
            path="\\Root\\sfx_attack_01",
            parent_id="root",
            parent_name="Root",
        )
        plan = [
            GroupPlan(
                group_name="sfx_attack",
                parent_id="root",
                container_type=ContainerType.RANDOM,
                action=PlanAction.CREATE,
                objects=[obj],
            )
        ]

        with patch(
            "src.executor.create_container",
            return_value={"id": "container-guid"},
        ) as create, patch("src.executor.move_object") as move:
            execute_operation_plan(client, plan)

        create.assert_called_once()
        move.assert_called_once_with(client, "sound-guid", "container-guid")
        self.assertEqual(
            [uri for uri, _args in client.calls],
            [
                "ak.wwise.core.undo.beginGroup",
                "ak.wwise.core.undo.endGroup",
            ],
        )

    def test_executor_imports_wav_from_plan(self) -> None:
        client = RecordingClient()
        audio_file = AudioFile("C:/audio/sfx_attack_01.wav")
        plan = [
            GroupPlan(
                group_name="sfx_attack",
                parent_id="root",
                container_type=ContainerType.RANDOM,
                action=PlanAction.REUSE,
                files=[audio_file],
                parent_path="\\Root\\sfx_attack",
                existing_container_id="container-guid",
            )
        ]

        with patch("src.executor.import_audio_file") as import_file:
            execute_operation_plan(client, plan)

        import_file.assert_called_once_with(
            client,
            audio_file,
            "\\Root\\sfx_attack",
        )


if __name__ == "__main__":
    unittest.main()
