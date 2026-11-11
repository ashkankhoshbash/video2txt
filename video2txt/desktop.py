"""Desktop interface for offline Persian video transcription."""

import argparse
import multiprocessing
import sys
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from video2txt.download import download_audio
from video2txt.transcription import transcribe

MODEL_PATH = Path(getattr(sys, "_MEIPASS", Path(__file__).parents[1])) / "model"


def load_model():
    """Load the packaged Whisper model without accessing the network."""
    model = str(MODEL_PATH)
    if not getattr(sys, "frozen", False) and not MODEL_PATH.is_dir():
        model = "large-v3"
    try:
        return WhisperModel(
            model,
            device="cuda",
            compute_type="int8_float16",
            local_files_only=True,
        )
    except RuntimeError as error:
        raise RuntimeError(
            f"Could not load Whisper on the NVIDIA GPU: {error}"
        ) from error


class TranscriptionWorker(QThread):
    """Keep model loading and transcription off the interface thread."""

    result = Signal(str)
    failed = Signal(str)
    phase = Signal(str)

    def __init__(self, parent):
        """Initialize an idle worker with a reusable model."""
        super().__init__(parent)
        self.video = None
        self.model = None
        self.url = ""
        self.hotwords = None

    def run(self):
        """Transcribe the selected video and report the result."""
        try:
            if self.url:
                self.phase.emit("Downloading media…")
                with tempfile.TemporaryDirectory(prefix="video2txt-media-") as temp:
                    video = download_audio(self.url, Path(temp))
                    text = self.transcribe_video(video)
            else:
                text = self.transcribe_video(self.video)
            self.result.emit(text)
        except Exception as error:
            self.failed.emit(str(error))


    def transcribe_video(self, video):
        """Load the model once and transcribe the input."""
        self.phase.emit("Transcribing…")
        if self.model is None:
            self.model = load_model()
        return transcribe(self.model, video, hotwords=self.hotwords)


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
        layout.addWidget(QLabel("Persian transcription"))
        self.url = QLineEdit()
        self.url.setAccessibleName("Aparat video link")
        self.url.setPlaceholderText("Paste an Aparat video link")
        self.url.setClearButtonEnabled(True)
        self.url.textChanged.connect(self.update_source)
        layout.addWidget(self.url)

        self.hotwords = QLineEdit()
        self.hotwords.setPlaceholderText("e.g. داتیس، تشخیص چهره، WDR")
        self.hotwords.setClearButtonEnabled(True)
        hotwords_label = QLabel("&Hot words (optional)")
        hotwords_label.setBuddy(self.hotwords)
        layout.addWidget(hotwords_label)
        layout.addWidget(self.hotwords)

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
        transcript_header = QHBoxLayout()
        transcript_header.addWidget(QLabel("Transcript"))
        transcript_header.addStretch()
        self.copy = QPushButton("کپی")
        self.copy.setEnabled(False)
        self.copy.clicked.connect(self.copy_transcript)
        transcript_header.addWidget(self.copy)
        layout.addLayout(transcript_header)
        self.output = QTextEdit(readOnly=True)
        self.output.setAccessibleName("Persian transcript")
        self.output.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(self.output, stretch=1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.status = QLabel("Choose a video or paste a link.")
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.worker.phase.connect(self.status.setText)
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
            self.url.clear()
            self.update_source()

    def update_source(self):
        """Update the active input and clear the previous transcript."""
        url = self.url.text().strip()
        if url:
            self.video = None
        self.filename.setText(
            "Video link selected" if url else
            self.video.name if self.video else "No video selected"
        )
        self.output.clear()
        self.copy.setEnabled(False)
        ready = bool(url or self.video)
        self.start.setEnabled(ready)
        self.status.setText(
            "Ready to transcribe." if ready else "Choose a video or paste a link."
        )

    def start_work(self):
        """Start processing and show progress."""
        self.choose.setEnabled(False)
        self.url.setEnabled(False)
        self.hotwords.setEnabled(False)
        self.start.setEnabled(False)
        self.copy.setEnabled(False)
        self.output.clear()
        self.status.setText("Preparing…")
        self.progress.show()
        self.worker.video = self.video
        self.worker.url = self.url.text().strip()
        self.worker.hotwords = self.hotwords.text().strip() or None
        self.worker.start()

    def copy_transcript(self):
        """Copy the entire transcript to the system clipboard."""
        QApplication.clipboard().setText(self.output.toPlainText())
        self.status.setText("Transcript copied.")

    def show_result(self, text):
        """Display selectable Persian text inside the window."""
        self.output.setPlainText(text)
        self.copy.setEnabled(bool(text))
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
        self.url.setEnabled(True)
        self.hotwords.setEnabled(True)
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
