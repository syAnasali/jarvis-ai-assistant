"""ExportTelemetryDialog modal dialog for exporting telemetry to JSON, CSV, and Markdown."""

from typing import Optional
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ExportTelemetryDialog(QDialog):
    """Modal dialog prompting user for telemetry format and export destination path."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export Observability Telemetry")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        lbl_fmt = QLabel("Export Format:")
        layout.addWidget(lbl_fmt)

        self.cmb_format = QComboBox()
        self.cmb_format.addItems(["JSON Snapshot (.json)", "CSV Spreadsheet (.csv)", "Markdown Report (.md)"])
        layout.addWidget(self.cmb_format)

        lbl_path = QLabel("Export Destination Path:")
        layout.addWidget(lbl_path)

        path_layout = QHBoxLayout()
        self.txt_path = QLineEdit("exports/telemetry_report.json")
        path_layout.addWidget(self.txt_path)

        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self._browse_destination)
        path_layout.addWidget(self.btn_browse)
        layout.addLayout(path_layout)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.cmb_format.currentIndexChanged.connect(self._update_extension)

    def _update_extension(self, idx: int) -> None:
        exts = [".json", ".csv", ".md"]
        curr = self.txt_path.text()
        base = curr.rsplit(".", 1)[0]
        self.txt_path.setText(f"{base}{exts[idx]}")

    def _browse_destination(self) -> None:
        idx = self.cmb_format.currentIndex()
        filters = ["JSON Files (*.json)", "CSV Files (*.csv)", "Markdown Files (*.md)"]
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Telemetry", self.txt_path.text(), filters[idx])
        if file_path:
            self.txt_path.setText(file_path)

    def get_export_info(self) -> tuple[str, str]:
        """Returns tuple of (format, file_path)."""
        fmt_map = {0: "json", 1: "csv", 2: "markdown"}
        fmt = fmt_map.get(self.cmb_format.currentIndex(), "json")
        return fmt, self.txt_path.text().strip()
