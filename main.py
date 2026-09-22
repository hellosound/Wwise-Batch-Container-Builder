from __future__ import annotations

import sys

from waapi import WaapiClient

from src.models import ContainerType


DEFAULT_CONTAINER_TYPE = ContainerType.RANDOM

# Optional explicit rules for teams that want a configured default per group.
# The GUI still allows changing every group before applying the plan.
CONTAINER_OVERRIDES: dict[str, ContainerType] = {}


def get_container_type(group_name: str) -> ContainerType:
    return CONTAINER_OVERRIDES.get(group_name, DEFAULT_CONTAINER_TYPE)


def main() -> int:
    """Launch the GUI while keeping the WAAPI client alive for its lifetime."""
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        from src.ui.main_window import MainWindow
    except ImportError as exc:
        print(
            "PySide6 is required to run the GUI. "
            "Install dependencies with: python -m pip install -r requirements.txt"
        )
        print(f"Details: {exc}")
        return 1

    app = QApplication.instance() or QApplication(sys.argv)

    try:
        with WaapiClient() as client:
            window = MainWindow(client, get_container_type)
            window.show()
            return app.exec()
    except Exception as exc:
        QMessageBox.critical(
            None,
            "Could not connect to Wwise",
            f"The Wwise Authoring API connection failed:\n\n{exc}",
        )
        print("\n=== OPERATION FAILED ===")
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
