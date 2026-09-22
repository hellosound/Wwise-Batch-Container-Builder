# Wwise Batch Container Builder

Python + WAAPI + PySide6 tool for grouping existing Wwise `Sound` objects or external WAV files and placing them in Random, Sequence, Blend, or Actor-Mixer parents.

## Current architecture

```text
main.py
  -> src/ui/main_window.py
  -> src/grouping.py / src/planning.py
  -> src/executor.py
  -> src/wwise/*
  -> Wwise Authoring API
```

The application follows `READ -> ANALYZE -> PLAN -> PREVIEW -> EXECUTE`. The executor consumes a validated `GroupPlan`; it does not select container types or search for destinations again.

## Installation

On Windows, from this repository:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Open the Wwise project and enable **Project > User Preferences > Wwise Authoring API**. Wwise must remain open while using the tool.

Launch the GUI with:

```bat
python main.py
```

The application starts in **Use Current Wwise Selection** mode. It uses the current WAAPI selection and ignores non-Sound objects with a visible status message.

## Existing Wwise object workflow

1. Select multiple Sound objects in Wwise.
2. Launch `python main.py`, or use the command add-on described below.
3. Review the groups and current parent in the preview table.
4. Choose a container type independently for each group.
5. Press **Create** and confirm.

Objects are moved by their Wwise GUIDs. Existing containers are reused only when their Wwise type and Random/Sequence mode are compatible. A conflicting child name or parent type stops the plan before writes begin.

The naming engine removes only the final numeric suffix:

```text
sfx_attack_01       -> sfx_attack
sfx_attack-002      -> sfx_attack
robot2_attack_01    -> robot2_attack
weapon_v2_fire_002  -> weapon_v2_fire
```

Sequence groups require a numeric suffix and are sorted numerically (`1, 2, 10`).

## WAV import workflow

1. In Wwise, select exactly one destination parent object.
2. In the GUI, change **Input** to **Import WAV Files**.
3. Press **Select WAV Files** and select one or more `.wav` files.
4. Review groups, choose each container type, and press **Apply**.

The tool creates or reuses the group container, then imports each WAV as a Sound SFX directly below it through `ak.wwise.core.audio.import`. Sequence imports are planned in numeric order. Existing child-name conflicts are rejected before the write phase.

The **Open** button selects a folder and loads the `.wav` files directly inside that folder. Subfolders are not scanned in V1. A group containing only one WAV is shown as `Skip`, because it has no variation container to build.

Likewise, a single selected Sound with no variations is shown as `Skip` and does not block the other groups.

## Undo and safety

All writes in one Apply operation are enclosed in a Wwise Undo Group. On failure the group is closed with a failure label; the tool does not pretend that closing or cancelling a group is an automatic transactional rollback. Review the Wwise undo history after a partial failure.

The GUI always previews the plan and asks for confirmation. There is no `APPLY_CHANGES=True` command-line bypass.

## Wwise Command Add-on

Copy `wwise_addon/wwise_batch_container_builder.json` into the project's Wwise command add-ons directory, and make the repository available under the `Scripts/WwiseBatchContainerBuilder` path used by the template. Adjust the script path if your layout differs. In Wwise, reload command add-ons and launch **WAAPI > Wwise Batch Container Builder**.

The add-on starts the same GUI and reads the current Wwise selection through WAAPI. The command add-on template assumes `python` is on `PATH`; replace `program` with the absolute path to your Python executable if necessary.

## Development and tests

Run the tests without Wwise:

```bat
python -m unittest discover -s tests -v
```

The tests cover naming, grouping, numeric ordering, validation, CREATE/REUSE/SKIP planning, and WAV planning with a fake WAAPI client. A real Wwise instance is required to test WAAPI queries, container creation, moving, and audio import.

Compile/import smoke check:

```bat
python -m compileall -q src main.py
python -c "import main; print('import OK')"
```

## V1 limitations

Blend containers are created as basic `BlendContainer` objects; advanced Blend Track, RTPC, Switch Container, Event, recursive-folder, and naming-preset workflows are intentionally outside V1.
