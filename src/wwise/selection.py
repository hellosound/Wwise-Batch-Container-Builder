from waapi import WaapiClient

from src.models import WwiseObject


SELECTION_RETURN_FIELDS = [
    "id",
    "name",
    "type",
    "path",
    "parent",
]


def _to_wwise_object(data: dict) -> WwiseObject:
    parent = data.get("parent")
    if not isinstance(parent, dict):
        parent = {}

    return WwiseObject(
        id=data["id"],
        name=data["name"],
        type=data["type"],
        path=data["path"],
        parent_id=parent.get("id"),
        parent_name=parent.get("name"),
    )


def get_selected_objects(client: WaapiClient,) -> list[WwiseObject]:

    options = {
        "return": SELECTION_RETURN_FIELDS
    }

    result = client.call(
        "ak.wwise.ui.getSelectedObjects",
        options=options,
    )

    if not isinstance(result, dict):
        return []

    raw_objects = result.get("objects", [])
    if not isinstance(raw_objects, list):
        return []

    selected: list[WwiseObject] = []
    for index, data in enumerate(raw_objects):
        if not isinstance(data, dict):
            continue
        try:
            selected.append(_to_wwise_object(data))
        except KeyError as exc:
            raise ValueError(
                f"Wwise returned an incomplete selected object at index "
                f"{index}; missing field: {exc.args[0]}"
            ) from exc

    return selected
