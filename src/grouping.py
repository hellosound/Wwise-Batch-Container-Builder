from collections import defaultdict
from pathlib import Path
import re

from src.models import AudioFile, WwiseObject


NUMERIC_SUFFIX = re.compile(r"[_-]?\d+$")
NUMERIC_INDEX = re.compile(r"(\d+)$")
AUDIO_EXTENSIONS = {".wav", ".wave", ".aif", ".aiff", ".flac", ".ogg"}


def _name_stem(name_or_path: str) -> str:
    candidate = Path(name_or_path)

    if candidate.suffix.casefold() in AUDIO_EXTENSIONS:
        return candidate.stem

    return candidate.name or name_or_path


def get_group_name(name_or_path: str) -> str:
    return NUMERIC_SUFFIX.sub("", _name_stem(name_or_path))


def group_audio_files(
    items: list[AudioFile],
) -> dict[str, list[AudioFile]]:
    """Group external audio files with the same naming engine as Wwise objects."""

    groups: dict[str, list[AudioFile]] = defaultdict(list)

    for item in items:
        groups[get_group_name(item.name)].append(item)

    return dict(groups)


def group_wwise_objects(
    items: list[WwiseObject],
) -> dict[str, list[WwiseObject]]:

    groups: dict[str, list[WwiseObject]] = defaultdict(list)

    for item in items:
        group_name = get_group_name(item.name)
        groups[group_name].append(item)

    return dict(groups)

def get_numeric_index(name: str) -> int | None:
    match = NUMERIC_INDEX.search(_name_stem(name))

    if match is None:
        return None

    return int(match.group(1))

def sort_wwise_objects_by_index(
    objects: list[WwiseObject],
) -> list[WwiseObject]:

    def sort_key(obj: WwiseObject) -> int:
        index = get_numeric_index(obj.name)

        if index is None:
            raise ValueError(
                f"Object '{obj.name}' "
                "has no numeric suffix."
            )

        return index

    return sorted(
        objects,
        key=sort_key,
    )


def sort_audio_files_by_index(
    files: list[AudioFile],
) -> list[AudioFile]:
    """Return WAV files in numeric suffix order for a Sequence container."""

    def sort_key(audio_file: AudioFile) -> int:
        index = get_numeric_index(audio_file.name)

        if index is None:
            raise ValueError(
                f"File '{audio_file.path}' has no numeric suffix."
            )

        return index

    return sorted(files, key=sort_key)
