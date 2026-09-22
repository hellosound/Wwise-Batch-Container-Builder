from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from waapi import WaapiClient

from src.executor import execute_operation_plan
from src.grouping import group_wwise_objects
from src.models import AudioFile, ContainerType, GroupPlan, WwiseObject
from src.planning import build_operation_plan, build_wav_operation_plan
from src.wwise.selection import get_selected_objects


class MainWindow(QMainWindow):
    """Preview and apply plans for Wwise selections or external WAV files."""

    COLUMNS = [
        "Group",
        "Count",
        "Current / Destination Parent",
        "Container Type",
        "Planned Action",
    ]

    def __init__(
        self,
        client: WaapiClient,
        container_type_resolver: Callable[[str], ContainerType],
    ) -> None:
        super().__init__()
        self.client = client
        self.container_type_resolver = container_type_resolver
        self.mode = "selection"
        self.selected_objects: list[WwiseObject] = []
        self.audio_files: list[AudioFile] = []
        self.destination_parent: WwiseObject | None = None
        self.plan: list[GroupPlan] = []
        self.container_choices: dict[str, ContainerType] = {}
        self._updating_table = False

        self.setWindowTitle("Wwise Batch Container Builder")
        self.resize(980, 560)
        self._build_ui()
        self._load_selection()

    def _build_ui(self) -> None:
        root = QWidget(self)
        layout = QVBoxLayout(root)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Input:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Use Current Wwise Selection", "selection")
        self.mode_combo.addItem("Import WAV Files", "wav")
        self.mode_combo.currentIndexChanged.connect(self._mode_changed)
        controls.addWidget(self.mode_combo)

        self.refresh_button = QPushButton("Refresh Wwise Selection")
        self.refresh_button.clicked.connect(self._load_selection)
        controls.addWidget(self.refresh_button)

        self.wav_button = QPushButton("Open")
        self.wav_button.clicked.connect(self._open_wav_folder)
        self.wav_button.setEnabled(False)
        controls.addWidget(self.wav_button)
        controls.addStretch()
        layout.addLayout(controls)

        self.destination_label = QLabel(
            "Selection mode: select Sound objects in Wwise."
        )
        layout.addWidget(self.destination_label)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        footer = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)
        footer.addWidget(self.status_label, 1)
        self.apply_button = QPushButton("Create")
        self.apply_button.clicked.connect(self._create)
        self.apply_button.setEnabled(False)
        footer.addWidget(self.apply_button)
        layout.addLayout(footer)

        self.setCentralWidget(root)

    def _mode_changed(self, index: int) -> None:
        self.mode = str(self.mode_combo.itemData(index))
        is_wav = self.mode == "wav"
        self.refresh_button.setEnabled(not is_wav)
        self.wav_button.setEnabled(is_wav)
        self.audio_files = []
        self.destination_parent = None
        self.plan = []
        self.table.setRowCount(0)
        self.apply_button.setEnabled(False)

        if is_wav:
            self.destination_label.setText(
                "Select one Wwise parent object, then choose WAV files."
            )
            self.status_label.setText(
                "Waiting for WAV files and a destination parent."
            )
        else:
            self.destination_label.setText(
                "Selection mode: select Sound objects in Wwise."
            )
            self._load_selection()

    def _load_selection(self) -> None:
        if self.mode != "selection":
            return

        try:
            selected = get_selected_objects(self.client)
            self.selected_objects = [
                obj for obj in selected if obj.type == "Sound"
            ]
            ignored = len(selected) - len(self.selected_objects)

            if not self.selected_objects:
                raise ValueError("No Sound objects are selected in Wwise.")

            self._rebuild_selection_plan()
            suffix = (
                f" Ignored {ignored} non-Sound object(s)."
                if ignored
                else ""
            )
            self.status_label.setText(
                f"Loaded {len(self.selected_objects)} Sound object(s).{suffix}"
            )
        except Exception as exc:
            self._show_error("Could not read the Wwise selection", exc)

    def _open_wav_folder(self) -> None:
        if self.mode != "wav":
            return

        try:
            selected = get_selected_objects(self.client)
            if len(selected) != 1:
                raise ValueError(
                    "Select exactly one Wwise destination parent before choosing WAV files."
                )
            if selected[0].type == "Sound":
                raise ValueError(
                    "A Sound object cannot be used as the destination parent."
                )

            folder = QFileDialog.getExistingDirectory(
                self,
                "Open folder containing WAV files",
                "",
            )
            if not folder:
                return

            paths = sorted(
                path
                for path in Path(folder).iterdir()
                if path.is_file() and path.suffix.casefold() == ".wav"
            )
            if not paths:
                raise ValueError(
                    f"No WAV files were found directly inside '{folder}'."
                )

            self.destination_parent = selected[0]
            self.audio_files = [AudioFile(str(path)) for path in paths]
            self.destination_label.setText(
                f"Destination: {self.destination_parent.path}"
            )
            self._rebuild_wav_plan()
            self.status_label.setText(
                f"Loaded {len(self.audio_files)} WAV file(s) from '{folder}'."
            )
        except Exception as exc:
            self._show_error("Could not prepare WAV files", exc)

    def _resolver(self, group_name: str) -> ContainerType:
        if group_name in self.container_choices:
            return self.container_choices[group_name]
        return self.container_type_resolver(group_name)

    def _rebuild_selection_plan(self) -> None:
        groups = group_wwise_objects(self.selected_objects)
        self.plan = build_operation_plan(
            self.client,
            groups,
            self._resolver,
        )
        self._render_plan()

    def _rebuild_wav_plan(self) -> None:
        if self.destination_parent is None:
            return

        self.plan = build_wav_operation_plan(
            self.client,
            self.audio_files,
            self.destination_parent.id,
            self.destination_parent.path,
            self._resolver,
            self.destination_parent.name,
        )
        self._render_plan()

    def _render_plan(self) -> None:
        self._updating_table = True
        try:
            self.table.setRowCount(len(self.plan))
            for row, item in enumerate(self.plan):
                self.table.setItem(row, 0, QTableWidgetItem(item.group_name))
                self.table.setItem(row, 1, QTableWidgetItem(str(item.count)))
                parent = item.parent_id
                if item.parent_name:
                    parent = f"{item.parent_name} ({item.parent_id})"
                self.table.setItem(row, 2, QTableWidgetItem(parent))

                combo = QComboBox()
                for container_type in ContainerType:
                    combo.addItem(container_type.value, container_type)
                combo.setCurrentIndex(combo.findData(item.container_type))
                combo.currentIndexChanged.connect(
                    lambda _index, group=item.group_name: self._container_changed(group)
                )
                self.table.setCellWidget(row, 3, combo)
                action = item.action.value
                if item.skip_reason:
                    action = f"{action}: {item.skip_reason}"
                self.table.setItem(row, 4, QTableWidgetItem(action))

                for column in range(self.table.columnCount()):
                    cell = self.table.item(row, column)
                    if cell is not None:
                        cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
        finally:
            self._updating_table = False

        self.apply_button.setEnabled(
            any(item.action.value != "Skip" for item in self.plan)
        )
        self.table.resizeColumnsToContents()

    def _container_changed(self, group_name: str) -> None:
        if self._updating_table:
            return

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is None or item.text() != group_name:
                continue
            combo = self.table.cellWidget(row, 3)
            if isinstance(combo, QComboBox):
                self.container_choices[group_name] = combo.currentData()
            break

        try:
            if self.mode == "selection":
                self._rebuild_selection_plan()
            else:
                self._rebuild_wav_plan()
        except Exception as exc:
            self._show_error(f"Cannot update group '{group_name}'", exc)

    def _create(self) -> None:
        if not self.plan:
            return

        answer = QMessageBox.question(
            self,
            "Confirm Wwise changes",
            "Apply this operation plan to Wwise? This will create, import, and/or move objects.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        try:
            execute_operation_plan(self.client, self.plan)
            QMessageBox.information(
                self,
                "Completed",
                "The operation completed successfully.",
            )
            self.apply_button.setEnabled(False)
            self.status_label.setText("Operation completed.")
        except Exception as exc:
            self._show_error("The operation failed", exc)

    def _show_error(self, title: str, exc: Exception) -> None:
        self.apply_button.setEnabled(False)
        self.status_label.setText(str(exc))
        QMessageBox.critical(self, title, str(exc))
