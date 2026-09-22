from waapi import WaapiClient

from src.models import AudioFile, ContainerType


def _build_container_args(
    parent_id: str,
    name: str,
    container_type: ContainerType,
) -> dict:
    args = {
        "parent": parent_id,
        "name": name,
        "onNameConflict": "fail",
    }

    if container_type == ContainerType.RANDOM:
        args["type"] = "RandomSequenceContainer"
        args["@RandomOrSequence"] = 1
    elif container_type == ContainerType.SEQUENCE:
        args["type"] = "RandomSequenceContainer"
        args["@RandomOrSequence"] = 0
    elif container_type == ContainerType.BLEND:
        args["type"] = "BlendContainer"
    elif container_type == ContainerType.ACTOR_MIXER:
        args["type"] = "ActorMixer"
    else:
        raise ValueError(f"Unsupported container type: {container_type}")

    return args


def create_container(
    client: WaapiClient,
    parent_id: str,
    name: str,
    container_type: ContainerType,
) -> dict:
    result = client.call(
        "ak.wwise.core.object.create",
        _build_container_args(parent_id, name, container_type),
    )

    if not isinstance(result, dict) or not result.get("id"):
        raise RuntimeError(
            f"Wwise did not return a valid ID while creating "
            f"container '{name}'."
        )

    return result


def get_expected_wwise_type(container_type: ContainerType) -> str:
    if container_type in (ContainerType.RANDOM, ContainerType.SEQUENCE):
        return "RandomSequenceContainer"
    if container_type == ContainerType.BLEND:
        return "BlendContainer"
    if container_type == ContainerType.ACTOR_MIXER:
        return "ActorMixer"
    raise ValueError(f"Unsupported container type: {container_type}")


def validate_existing_container(
    existing: dict,
    requested_type: ContainerType,
) -> None:
    expected_type = get_expected_wwise_type(requested_type)
    actual_type = existing.get("type")

    if actual_type != expected_type:
        raise ValueError(
            f"Existing object '{existing.get('name')}' is "
            f"'{actual_type}', but '{requested_type.value}' was requested."
        )

    if requested_type in (ContainerType.RANDOM, ContainerType.SEQUENCE):
        expected_mode = 1 if requested_type == ContainerType.RANDOM else 0
        actual_mode = existing.get("@RandomOrSequence")

        if actual_mode != expected_mode:
            raise ValueError(
                f"Existing container '{existing.get('name')}' has the wrong "
                "Random/Sequence mode."
            )


def import_audio_file(
    client: WaapiClient,
    audio_file: AudioFile,
    container_path: str,
) -> dict:
    """Import one WAV as a Sound SFX directly below a Wwise container."""
    object_path = (
        f"{container_path.rstrip(chr(92))}"
        f"\\<Sound SFX>{audio_file.name}"
    )

    result = client.call(
        "ak.wwise.core.audio.import",
        {
            "importOperation": "useExisting",
            "default": {"importLanguage": "SFX"},
            "imports": [
                {
                    "audioFile": audio_file.path,
                    "objectPath": object_path,
                }
            ],
        },
    )

    if not isinstance(result, dict):
        raise RuntimeError(
            f"Wwise returned an invalid response importing '{audio_file.path}'."
        )

    log = result.get("log", [])
    errors = [
        entry
        for entry in log
        if isinstance(entry, dict)
        and str(entry.get("severity", "")).casefold() in {"error", "fatal"}
    ] if isinstance(log, list) else []

    if errors:
        raise RuntimeError(
            f"Wwise reported an import error for '{audio_file.path}': {errors}"
        )

    imported_objects = result.get("objects")
    if imported_objects is not None and not isinstance(imported_objects, list):
        raise RuntimeError(
            f"Wwise returned an invalid object list importing '{audio_file.path}'."
        )

    return result
