import unittest

from src.models import AudioFile, ContainerType
from src.wwise.containers import import_audio_file, validate_existing_container
from src.wwise.query import get_children


class RecordingClient:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls: list[tuple[str, dict, dict | None]] = []

    def call(self, uri: str, args: dict | None = None, options: dict | None = None) -> dict:
        self.calls.append((uri, args or {}, options))
        return self.response


class WwiseApiTests(unittest.TestCase):
    def test_get_children_uses_children_waql(self) -> None:
        client = RecordingClient({"return": [{"id": "child", "name": "x"}]})

        result = get_children(client, "{parent-guid}")

        self.assertEqual(result[0]["id"], "child")
        self.assertEqual(client.calls[0][0], "ak.wwise.core.object.get")
        self.assertEqual(
            client.calls[0][1]["waql"],
            '$ "{parent-guid}" select children',
        )

    def test_import_audio_file_targets_sound_sfx_path(self) -> None:
        client = RecordingClient({"log": [], "objects": [{"id": "sound"}]})
        audio_file = AudioFile("C:/audio/attack_01.wav")

        import_audio_file(client, audio_file, "\\Root\\attack")

        uri, args, _options = client.calls[0]
        self.assertEqual(uri, "ak.wwise.core.audio.import")
        self.assertEqual(
            args["imports"][0]["objectPath"],
            "\\Root\\attack\\<Sound SFX>attack_01",
        )

    def test_random_and_sequence_modes_are_distinct(self) -> None:
        existing = {
            "name": "attack",
            "type": "RandomSequenceContainer",
            "@RandomOrSequence": 1,
        }
        validate_existing_container(existing, ContainerType.RANDOM)
        with self.assertRaises(ValueError):
            validate_existing_container(existing, ContainerType.SEQUENCE)


if __name__ == "__main__":
    unittest.main()
