from collections.abc import Callable
from pathlib import Path

from waapi import WaapiClient

from src.grouping import (
    group_audio_files,
    sort_audio_files_by_index,
    sort_wwise_objects_by_index,
)
from src.models import (
    AudioFile,
    ContainerType,
    GroupPlan,
    PlanAction,
    WwiseObject,
)
from src.validation import (
    get_shared_parent_id,
    group_is_already_wrapped,
    validate_unique_object_ids,
)
from src.wwise.containers import validate_existing_container
from src.wwise.query import find_child_by_name, get_object_by_id


ContainerTypeResolver = Callable[[str], ContainerType]


def _join_wwise_path(parent_path: str, child_name: str) -> str:
    return f"{parent_path.rstrip(chr(92))}\\{child_name}"


def _ordered_objects(
    objects: list[WwiseObject],
    container_type: ContainerType,
) -> list[WwiseObject]:
    if container_type == ContainerType.SEQUENCE:
        return sort_wwise_objects_by_index(objects)
    return list(objects)


def _ordered_files(
    files: list[AudioFile],
    container_type: ContainerType,
) -> list[AudioFile]:
    if container_type == ContainerType.SEQUENCE:
        return sort_audio_files_by_index(files)
    return list(files)


def _validate_parent_for_skip(
    client: WaapiClient,
    group_name: str,
    parent_id: str,
    container_type: ContainerType,
) -> None:
    parent = get_object_by_id(client, parent_id)

    if parent is None:
        raise ValueError(
            f"Group '{group_name}' is already under a parent named "
            f"'{group_name}', but Wwise did not return that parent ({parent_id})."
        )

    validate_existing_container(parent, container_type)


def _validate_object_target_conflicts(
    client: WaapiClient,
    group_name: str,
    objects: list[WwiseObject],
    container_id: str,
) -> None:
    selected_ids = {obj.id for obj in objects}

    for obj in objects:
        existing = find_child_by_name(client, container_id, obj.name)

        if existing is not None and existing.get("id") not in selected_ids:
            raise ValueError(
                f"Group '{group_name}' cannot move '{obj.name}': the target "
                f"container already has a different child with that name."
            )


def _validate_file_target_conflicts(
    client: WaapiClient,
    group_name: str,
    files: list[AudioFile],
    container_id: str,
) -> None:
    for audio_file in files:
        existing = find_child_by_name(client, container_id, audio_file.name)

        if existing is not None:
            raise ValueError(
                f"Group '{group_name}' cannot import '{audio_file.name}': "
                "the target container already has a child with that name."
            )


def _existing_or_create(
    client: WaapiClient,
    parent_id: str,
    group_name: str,
    container_type: ContainerType,
) -> tuple[PlanAction, str | None, dict | None]:
    existing = find_child_by_name(client, parent_id, group_name)

    if existing is None:
        return PlanAction.CREATE, None, None

    validate_existing_container(existing, container_type)
    existing_id = existing.get("id")

    if not existing_id:
        raise ValueError(
            f"Existing container '{group_name}' has no Wwise GUID."
        )

    return PlanAction.REUSE, existing_id, existing


def build_operation_plan(
    client: WaapiClient,
    groups: dict[str, list[WwiseObject]],
    container_type_resolver: ContainerTypeResolver,
) -> list[GroupPlan]:
    """Analyze selected Wwise objects and return a validated write plan."""
    plan: list[GroupPlan] = []
    all_object_ids: set[str] = set()

    for group_name, objects in groups.items():
        validate_unique_object_ids(group_name, objects)
        overlapping_ids = all_object_ids.intersection(obj.id for obj in objects)
        if overlapping_ids:
            raise ValueError(
                f"Selected Wwise objects occur in more than one group: "
                f"{sorted(overlapping_ids)}"
            )
        all_object_ids.update(obj.id for obj in objects)
        parent_id = get_shared_parent_id(group_name, objects)
        container_type = container_type_resolver(group_name)

        if len(objects) < 2:
            plan.append(
                GroupPlan(
                    group_name=group_name,
                    parent_id=parent_id,
                    container_type=container_type,
                    action=PlanAction.SKIP,
                    objects=list(objects),
                    parent_name=objects[0].parent_name,
                    skip_reason="No variations; only one Sound is in this group.",
                )
            )
            continue

        ordered_objects = _ordered_objects(objects, container_type)

        if group_is_already_wrapped(group_name, objects):
            _validate_parent_for_skip(
                client,
                group_name,
                parent_id,
                container_type,
            )
            plan.append(
                GroupPlan(
                    group_name=group_name,
                    parent_id=parent_id,
                    container_type=container_type,
                    action=PlanAction.SKIP,
                    objects=ordered_objects,
                    parent_name=objects[0].parent_name,
                )
            )
            continue

        action, existing_id, existing = _existing_or_create(
            client,
            parent_id,
            group_name,
            container_type,
        )

        if action == PlanAction.REUSE and existing_id is not None:
            _validate_object_target_conflicts(
                client,
                group_name,
                objects,
                existing_id,
            )

        plan.append(
            GroupPlan(
                group_name=group_name,
                parent_id=parent_id,
                container_type=container_type,
                action=action,
                objects=ordered_objects,
                parent_name=objects[0].parent_name,
                existing_container_id=existing_id,
            )
        )

    return plan


def build_wav_operation_plan(
    client: WaapiClient,
    files: list[AudioFile],
    destination_parent_id: str,
    destination_parent_path: str,
    container_type_resolver: ContainerTypeResolver,
    destination_parent_name: str | None = None,
) -> list[GroupPlan]:
    """Analyze external WAVs using the same grouping/planning rules."""
    if not destination_parent_id or not destination_parent_path:
        raise ValueError(
            "A Wwise destination parent with both a GUID and path is required."
        )

    if not files:
        return []

    seen_paths: set[str] = set()
    for audio_file in files:
        normalized_path = str(Path(audio_file.path).resolve()).casefold()

        if normalized_path in seen_paths:
            raise ValueError(f"The WAV file was selected more than once: {audio_file.path}")
        seen_paths.add(normalized_path)

        if Path(audio_file.path).suffix.casefold() != ".wav":
            raise ValueError(f"Only .wav files are supported: {audio_file.path}")
        if not Path(audio_file.path).is_file():
            raise ValueError(f"The WAV file does not exist: {audio_file.path}")

    plan: list[GroupPlan] = []

    for group_name, group_files in group_audio_files(files).items():
        container_type = container_type_resolver(group_name)

        if len(group_files) < 2:
            plan.append(
                GroupPlan(
                    group_name=group_name,
                    parent_id=destination_parent_id,
                    container_type=container_type,
                    action=PlanAction.SKIP,
                    files=list(group_files),
                    parent_name=destination_parent_name,
                    parent_path=destination_parent_path,
                    skip_reason="No variations; only one WAV is in this group.",
                )
            )
            continue

        ordered_files = _ordered_files(group_files, container_type)
        action, existing_id, existing = _existing_or_create(
            client,
            destination_parent_id,
            group_name,
            container_type,
        )

        if action == PlanAction.REUSE and existing_id is not None:
            _validate_file_target_conflicts(
                client,
                group_name,
                ordered_files,
                existing_id,
            )

        container_path = (
            existing.get("path")
            if existing is not None
            else _join_wwise_path(destination_parent_path, group_name)
        )

        if not container_path:
            raise ValueError(
                f"Wwise did not return a path for existing container "
                f"'{group_name}'."
            )

        plan.append(
            GroupPlan(
                group_name=group_name,
                parent_id=destination_parent_id,
                container_type=container_type,
                action=action,
                files=ordered_files,
                parent_name=destination_parent_name,
                parent_path=container_path,
                existing_container_id=existing_id,
            )
        )

    return plan


def print_operation_plan(plan: list[GroupPlan]) -> None:
    print("\n=== OPERATION PLAN ===")

    for item in plan:
        parent = item.parent_id
        if item.parent_name:
            parent = f"{item.parent_name} ({item.parent_id})"
        print(
            f"\n{item.group_name}"
            f"\n  Objects/Files: {item.count}"
            f"\n  Container: {item.container_type.value}"
            f"\n  Parent: {parent}"
            f"\n  Action: {item.action.value}"
            f"{f' ({item.skip_reason})' if item.skip_reason else ''}"
        )

        for obj in item.objects:
            print(f"    {obj.name} -> {obj.id}")
        for audio_file in item.files:
            print(f"    {audio_file.name} <- {audio_file.path}")
