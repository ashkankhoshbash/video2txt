"""Build a portable desktop bundle on the target platform."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]


def main():
    """Freeze the desktop app and add the complete offline model."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path)
    args = parser.parse_args()
    snapshot = args.model_dir or snapshot_download(
        "Systran/faster-whisper-large-v3",
        allow_patterns=["*.json", "model.bin", "README.md", "LICENSE*"],
    )
    snapshot = Path(snapshot)
    for filename in ("config.json", "model.bin", "tokenizer.json"):
        if not (snapshot / filename).is_file():
            parser.error(f"Missing model file: {snapshot / filename}")

    subprocess.run(
        [
            sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
            "--onedir", "--windowed", "--name", "Video2Txt",
            "--collect-data", "faster_whisper",
            "--collect-binaries", "ctranslate2",
            "--collect-binaries", "onnxruntime",
            "--paths", str(ROOT),
            "video2txt/desktop.py",
        ],
        cwd=ROOT,
        check=True,
    )
    model = ROOT / "dist" / "Video2Txt" / "_internal" / "model"
    shutil.copytree(snapshot, model, symlinks=False)


if __name__ == "__main__":
    main()
