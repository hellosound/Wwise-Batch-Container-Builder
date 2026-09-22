from waapi import WaapiClient

def move_object(
        client: WaapiClient,
        object_id: str,
        new_parent_id: str,
    )->dict:

    args = {
        "object": object_id,
        "parent": new_parent_id,
        "onNameConflict": "fail",
    }

    return client.call("ak.wwise.core.object.move", args,
                       )