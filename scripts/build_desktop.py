"""Build a portable desktop bundle for Linux."""

import argparse
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]


LAUNCHER = """#!/bin/sh
set -eu
work=$(mktemp -d "${TMPDIR:-/tmp}/video2txt.XXXXXXXX")
trap 'rm -rf -- "$work"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
tail -n +PAYLOAD_LINE -- "$0" | tar -xf - -C "$work"
"$work/Video2Txt/Video2Txt" "$@"
exit $?
"""


def write_executable(bundle, output):
    """Append the bundled app to a launcher and publish it atomically."""
    header = LAUNCHER.replace(
        "PAYLOAD_LINE", str(LAUNCHER.count("\n") + 1)
    ).encode("utf-8")
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        executable = Path(temporary) / output.name
        with executable.open("wb") as stream:
            stream.write(header)
            with tarfile.open(fileobj=stream, mode="w|") as archive:
                archive.add(bundle, arcname="Video2Txt")
        executable.chmod(0o755)
        executable.replace(output)


def main():
    """Freeze the desktop app and add the complete offline model."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path)
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("Desktop builds are supported only on Linux.")
    snapshot = args.model_dir or snapshot_download(
        "Systran/faster-whisper-large-v3",
        allow_patterns=["*.json", "model.bin", "README.md", "LICENSE*"],
    )
    snapshot = Path(snapshot)
    for filename in ("config.json", "model.bin", "tokenizer.json"):
        if not (snapshot / filename).is_file():
            parser.error(f"Missing model file: {snapshot / filename}")

    output = ROOT / "dist" / "Video2Txt.run"
    output.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="video2txt-build-") as temporary:
        staging = Path(temporary)
        subprocess.run(
            [
                sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                "--distpath", str(staging / "dist"),
                "--workpath", str(staging / "build"),
                "--specpath", str(staging),
                "--onedir", "--name", "Video2Txt",
                "--collect-data", "faster_whisper",
                "--collect-binaries", "ctranslate2",
                "--collect-binaries", "onnxruntime",
                "--paths", str(ROOT),
                "video2txt/desktop.py",
            ],
            cwd=ROOT,
            check=True,
        )
        bundle = staging / "dist" / "Video2Txt"
        shutil.copytree(snapshot, bundle / "_internal" / "model")
        write_executable(bundle, output)
    print(output)


if __name__ == "__main__":
    main()
