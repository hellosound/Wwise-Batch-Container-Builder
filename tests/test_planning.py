import unittest
from pathlib import Path
from unittest.mock import patch

from src.models import AudioFile, ContainerType, PlanAction, WwiseObject
from src.planning import build_operation_plan, build_wav_operation_plan


class FakeWaapiClient:
    def __init__(self) -> None:
        self.children: dict[str, list[dict]] = {}
        self.objects: dict[str, dict] = {}

    def call(self, uri: str, args: dict | None = None, options: dict | None = None) -> dict:
        self.assert_uri(uri)
        waql = (args or {}).get("waql", "")
        object_id = waql.split('"')[1] if '"' in waql else ""

        if "select children" in waql:
            return {"return": self.children.get(object_id, [])}
        if object_id in self.objects:
            return {"return": [self.objects[object_id]]}
        return {"return": []}

    @staticmethod
    def assert_uri(uri: str) -> None:
        if uri != "ak.wwise.core.object.get":
            raise AssertionError(f"Unexpected URI in planning test: {uri}")


def sound(
    name: str,
    object_id: str,
    parent_id: str = "parent",
    parent_name: str = "Root",
) -> WwiseObject:
    return WwiseObject(
        id=object_id,
        name=name,
        type="Sound",
        path=f"\\Root\\{name}",
        parent_id=parent_id,
        parent_name=parent_name,
    )


class PlanningTests(unittest.TestCase):
    def test_existing_objects_create_plan(self) -> None:
        client = FakeWaapiClient()
        objects = [sound("sfx_attack_01", "one"), sound("sfx_attack_02", "two")]

        plan = build_operation_plan(
            client,
            {"sfx_attack": objects},
            lambda _group: ContainerType.RANDOM,
        )

        self.assertEqual(plan[0].action, PlanAction.CREATE)
        self.assertEqual(plan[0].objects, objects)

    def test_existing_compatible_container_reuses(self) -> None:
        client = FakeWaapiClient()
        client.children["parent"] = [
            {
                "id": "container",
                "name": "sfx_attack",
                "type": "RandomSequenceContainer",
                "path": "\\Root\\sfx_attack",
                "@RandomOrSequence": 1,
            }
        ]
        objects = [
            sound("sfx_attack_01", "one"),
            sound("sfx_attack_02", "two"),
        ]

        plan = build_operation_plan(
            client,
            {"sfx_attack": objects},
            lambda _group: ContainerType.RANDOM,
        )

        self.assertEqual(plan[0].action, PlanAction.REUSE)
        self.assertEqual(plan[0].existing_container_id, "container")

    def test_already_wrapped_plan_skips_after_type_validation(self) -> None:
        client = FakeWaapiClient()
        client.objects["container"] = {
            "id": "container",
            "name": "sfx_attack",
            "type": "RandomSequenceContainer",
            "path": "\\Root\\sfx_attack",
            "@RandomOrSequence": 1,
        }
        objects = [
            sound(
                "sfx_attack_01",
                "one",
                parent_id="container",
                parent_name="sfx_attack",
            ),
            sound(
                "sfx_attack_02",
                "two",
                parent_id="container",
                parent_name="sfx_attack",
            ),
        ]

        plan = build_operation_plan(
            client,
            {"sfx_attack": objects},
            lambda _group: ContainerType.RANDOM,
        )

        self.assertEqual(plan[0].action, PlanAction.SKIP)

    def test_single_sound_is_skipped_without_querying_for_a_container(self) -> None:
        client = FakeWaapiClient()
        objects = [sound("sfx_fish_idle_lp", "single")]

        plan = build_operation_plan(
            client,
            {"sfx_fish_idle_lp": objects},
            lambda _group: ContainerType.RANDOM,
        )

        self.assertEqual(plan[0].action, PlanAction.SKIP)
        self.assertIn("only one Sound", plan[0].skip_reason or "")

    def test_wav_plan_uses_same_grouping_and_numeric_order(self) -> None:
        client = FakeWaapiClient()
        paths = [
            AudioFile(str(Path(name)))
            for name in ("sound_10.wav", "sound_2.wav", "sound_1.wav")
        ]
        with patch("src.planning.Path.is_file", return_value=True):
            plan = build_wav_operation_plan(
                client,
                paths,
                "parent",
                "\\Actor-Mixer Hierarchy\\Default Work Unit",
                lambda _group: ContainerType.SEQUENCE,
            )

        self.assertEqual(plan[0].action, PlanAction.CREATE)
        self.assertEqual(
            [item.name for item in plan[0].files],
            ["sound_1", "sound_2", "sound_10"],
        )

    def test_wav_plan_rejects_missing_file(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not exist"):
            build_wav_operation_plan(
                FakeWaapiClient(),
                [AudioFile("missing.wav")],
                "parent",
                "\\Root",
                lambda _group: ContainerType.RANDOM,
            )

    def test_single_wav_is_skipped_as_non_variation(self) -> None:
        with patch("src.planning.Path.is_file", return_value=True):
            plan = build_wav_operation_plan(
                FakeWaapiClient(),
                [AudioFile("single.wav")],
                "parent",
                "\\Root",
                lambda _group: ContainerType.RANDOM,
            )

        self.assertEqual(plan[0].action, PlanAction.SKIP)
        self.assertIn("only one WAV", plan[0].skip_reason or "")


if __name__ == "__main__":
    unittest.main()
