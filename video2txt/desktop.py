"""Desktop interface for offline Persian video transcription."""

import argparse
import multiprocessing
import sys
from pathlib import Path

from faster_whisper import WhisperModel
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from video2txt.transcription import transcribe

MODEL_PATH = Path(getattr(sys, "_MEIPASS", Path(__file__).parents[1])) / "model"


def load_model():
    """Load the packaged Whisper model without accessing the network."""
    model = str(MODEL_PATH)
    if not getattr(sys, "frozen", False) and not MODEL_PATH.is_dir():
        model = "large-v3"
    return WhisperModel(
        model,
        device="cpu",
        compute_type="int8",
        local_files_only=True,
    )


class TranscriptionWorker(QThread):
    """Keep model loading and transcription off the interface thread."""

    result = Signal(str)
    failed = Signal(str)

    def __init__(self, parent):
        """Initialize an idle worker with a reusable model."""
        super().__init__(parent)
        self.video = None
        self.model = None

    def run(self):
        """Transcribe the selected video and report the result."""
        try:
            if self.model is None:
                self.model = load_model()
            self.result.emit(transcribe(self.model, self.video))
        except Exception as error:
            self.failed.emit(str(error))


class Desktop(QWidget):
    """Select a local video and display its Persian transcript."""

    def __init__(self):
        """Build the interface and connect its actions."""
        super().__init__()
        self.video = None
        self.worker = TranscriptionWorker(self)
        self.setWindowTitle("Video2Txt")
        self.resize(780, 560)
        self.setMinimumSize(460, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        title = QLabel("Video2Txt")
        font = title.font()
        font.setPointSize(22)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        layout.addWidget(QLabel("Offline Persian transcription"))

        controls = QHBoxLayout()
        self.choose = QPushButton("Choose video…")
        self.choose.clicked.connect(self.pick)
        self.start = QPushButton("Transcribe")
        self.start.setEnabled(False)
        self.start.clicked.connect(self.start_work)
        controls.addWidget(self.choose)
        controls.addStretch()
        controls.addWidget(self.start)
        layout.addLayout(controls)

        self.filename = QLabel("No video selected")
        self.filename.setTextFormat(Qt.TextFormat.PlainText)
        self.filename.setWordWrap(True)
        layout.addWidget(self.filename)
        layout.addWidget(QLabel("Transcript"))
        self.output = QTextEdit(readOnly=True)
        self.output.setAccessibleName("Persian transcript")
        self.output.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(self.output, stretch=1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.status = QLabel("Choose a video to get started.")
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.worker.result.connect(self.show_result)
        self.worker.failed.connect(self.show_error)
        self.worker.finished.connect(self.finish_work)

    def pick(self):
        """Choose a video using the platform file dialog."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Choose a video", "",
            "Video files (*.mp4 *.mkv *.mov *.avi *.webm *.m4v);;"
            "All files (*)",
        )
        if filename:
            self.video = Path(filename)
            self.filename.setText(self.video.name)
            self.output.clear()
            self.status.setText("Ready to transcribe.")
            self.start.setEnabled(True)

    def start_work(self):
        """Start processing and show progress."""
        self.choose.setEnabled(False)
        self.start.setEnabled(False)
        self.output.clear()
        self.status.setText("Transcribing…")
        self.progress.show()
        self.worker.video = self.video
        self.worker.start()

    def show_result(self, text):
        """Display selectable Persian text inside the window."""
        self.output.setPlainText(text)
        self.status.setText(
            "Transcription complete." if text else "No speech detected."
        )

    def show_error(self, error):
        """Show the processing error in the window."""
        self.status.setText(f"Transcription failed. {error}")

    def finish_work(self):
        """Restore the controls after processing."""
        self.progress.hide()
        self.choose.setEnabled(True)
        self.start.setEnabled(True)

    def closeEvent(self, event):
        """Keep the worker alive until the current transcription ends."""
        if self.worker.isRunning():
            self.status.setText("Wait for transcription to finish.")
            event.ignore()
        else:
            super().closeEvent(event)


def main():
    """Open the desktop app or verify a packaged transcription."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-test", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    app = QApplication([sys.argv[0]])
    window = Desktop()
    if args.smoke_test:
        window.show_result(transcribe(load_model(), args.smoke_test))
        return 0
    window.show()
    return app.exec()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
