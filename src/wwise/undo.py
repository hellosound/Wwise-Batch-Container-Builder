from waapi import WaapiClient


def begin_undo_group(client: WaapiClient,) -> None:

    client.call(
        "ak.wwise.core.undo.beginGroup"
    )


def end_undo_group(client: WaapiClient,display_name: str,) -> None:

    client.call(
        "ak.wwise.core.undo.endGroup",
        {
            "displayName": display_name
        },
    )