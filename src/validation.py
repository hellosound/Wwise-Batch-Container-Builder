from src.models import WwiseObject


def get_shared_parent_id(
    group_name: str,
    objects: list[WwiseObject],
) -> str:

    if not objects:
        raise ValueError(
            f"Group '{group_name}' contains no objects."
        )

    if any(obj.parent_id is None for obj in objects):
        raise ValueError(
            f"Group '{group_name}' contains an object "
            "without a valid parent."
        )

    parent_ids = {
        obj.parent_id
        for obj in objects
    }

    if len(parent_ids) != 1:
        raise ValueError(
            f"Group '{group_name}' contains objects "
            "from multiple parents."
        )

    return next(iter(parent_ids))


def validate_unique_object_ids(
    group_name: str,
    objects: list[WwiseObject],
) -> None:
    ids = [obj.id for obj in objects]

    if len(ids) != len(set(ids)):
        raise ValueError(
            f"Group '{group_name}' contains duplicate Wwise object GUIDs."
        )


def group_is_already_wrapped(
    group_name: str,
    objects: list[WwiseObject],
) -> bool:

    if not objects:
        return False

    parent_names = {
        obj.parent_name
        for obj in objects
    }

    return parent_names == {
        group_name
    }
