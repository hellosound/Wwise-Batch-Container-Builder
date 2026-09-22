import unittest
from pathlib import Path

from src.grouping import (
    get_group_name,
    get_numeric_index,
    group_audio_files,
    sort_audio_files_by_index,
)
from src.models import AudioFile


class GroupingTests(unittest.TestCase):
    def test_group_name_removes_only_final_numeric_suffix(self) -> None:
        cases = {
            "sfx_attack_01": "sfx_attack",
            "sfx_attack_002": "sfx_attack",
            "sfx_attack-03": "sfx_attack",
            "robot2_attack_01": "robot2_attack",
            "weapon_v2_fire_002": "weapon_v2_fire",
            "weapon.v2_fire_002": "weapon.v2_fire",
            "attack": "attack",
        }

        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(get_group_name(value), expected)

    def test_numeric_index_is_integer(self) -> None:
        self.assertEqual(get_numeric_index("sound_1"), 1)
        self.assertEqual(get_numeric_index("sound_10"), 10)
        self.assertIsNone(get_numeric_index("sound"))

    def test_audio_files_share_grouping_engine(self) -> None:
        files = [
            AudioFile("sfx_attack_01.wav"),
            AudioFile("sfx_attack_02.wav"),
            AudioFile("robot2_attack_01.wav"),
        ]

        groups = group_audio_files(files)

        self.assertEqual(set(groups), {"sfx_attack", "robot2_attack"})
        self.assertEqual(len(groups["sfx_attack"]), 2)

    def test_sequence_sort_is_numeric(self) -> None:
        files = [
            AudioFile("sound_10.wav"),
            AudioFile("sound_2.wav"),
            AudioFile("sound_1.wav"),
        ]

        ordered = sort_audio_files_by_index(files)

        self.assertEqual(
            [Path(item.path).stem for item in ordered],
            ["sound_1", "sound_2", "sound_10"],
        )

    def test_sequence_sort_rejects_missing_index(self) -> None:
        with self.assertRaises(ValueError):
            sort_audio_files_by_index([AudioFile("sound.wav")])


if __name__ == "__main__":
    unittest.main()
