from waapi import WaapiClient

from src.models import GroupPlan, PlanAction
from src.wwise.containers import create_container, import_audio_file
from src.wwise.mover import move_object
from src.wwise.undo import begin_undo_group, end_undo_group


def _container_path(result: dict, planned_path: str | None) -> str | None:
    actual_path = result.get("path")
    if isinstance(actual_path, str) and actual_path:
        return actual_path
    return planned_path


def execute_operation_plan(
    client: WaapiClient,
    plan: list[GroupPlan],
) -> None:
    """Execute a previously validated plan without making new decisions."""
    actionable = [item for item in plan if item.action != PlanAction.SKIP]
    if not actionable:
        return

    begin_undo_group(client)

    try:
        for item in actionable:
            if item.action == PlanAction.CREATE:
                result = create_container(
                    client,
                    item.parent_id,
                    item.group_name,
                    item.container_type,
                )
                container_id = result["id"]
                container_path = _container_path(result, item.parent_path)
            elif item.action == PlanAction.REUSE:
                if item.existing_container_id is None:
                    raise ValueError(
                        f"Group '{item.group_name}' was marked for reuse but "
                        "has no existing container ID."
                    )
                container_id = item.existing_container_id
                container_path = item.parent_path
            else:
                raise ValueError(f"Unsupported plan action: {item.action}")

            if item.files:
                if not container_path:
                    raise ValueError(
                        f"Group '{item.group_name}' has no Wwise path for WAV import."
                    )

                for audio_file in item.files:
                    try:
                        import_audio_file(client, audio_file, container_path)
                    except Exception as exc:
                        raise RuntimeError(
                            f"Failed importing '{audio_file.path}' for group "
                            f"'{item.group_name}': {exc}"
                        ) from exc

            for obj in item.objects:
                try:
                    move_object(client, obj.id, container_id)
                except Exception as exc:
                    raise RuntimeError(
                        f"Failed moving Wwise object '{obj.name}' ({obj.id}) "
                        f"for group '{item.group_name}': {exc}"
                    ) from exc

    except Exception:
        end_undo_group(client, "Batch Container Builder - Failed")
        raise
    else:
        end_undo_group(client, "Batch Container Builder")
