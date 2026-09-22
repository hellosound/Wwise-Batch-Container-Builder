from waapi import WaapiClient


OBJECT_RETURN_FIELDS = [
    "id",
    "name",
    "type",
    "path",
    "parent",
    "@RandomOrSequence",
]


def get_children(
    client: WaapiClient,
    parent_id: str,
) -> list[dict]:
    args = {
        "waql": f'$ "{parent_id}" select children',
    }

    options = {
        "return": [
            "id",
            "name",
            "type",
            "path",
            "@RandomOrSequence",
        ]
    }

    result = client.call(
        "ak.wwise.core.object.get",
        args,
        options=options,
    )

    if not isinstance(result, dict):
        return []

    objects = result.get("return", [])
    if not isinstance(objects, list):
        return []

    return [
        child
        for child in objects
        if isinstance(child, dict)
    ]


def get_object_by_id(
    client: WaapiClient,
    object_id: str,
) -> dict | None:
    result = client.call(
        "ak.wwise.core.object.get",
        {"waql": f'$ "{object_id}"'},
        options={"return": OBJECT_RETURN_FIELDS},
    )

    if not isinstance(result, dict):
        return None

    objects = result.get("return", [])
    if not isinstance(objects, list) or not objects:
        return None

    first = objects[0]
    return first if isinstance(first, dict) else None


def find_child_by_name(
    client: WaapiClient,
    parent_id: str,
    name: str,
) -> dict | None:
    children = get_children(client, parent_id)

    matches = [
        child
        for child in children
        if child.get("name") == name
    ]

    if not matches:
        return None

    if len(matches) > 1:
        raise ValueError(
            f"More than one child named '{name}' exists "
            f"under parent '{parent_id}'."
        )

    return matches[0]
