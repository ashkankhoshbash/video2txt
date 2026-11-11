"""Build a portable desktop AppImage for Ubuntu x86-64."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]


def write_appimage(bundle, output, tool, runtime):
    """Package the frozen application as a Type 2 AppImage."""
    launcher = bundle / "AppRun"
    launcher.write_text(
        '#!/bin/sh\nexec "$(dirname -- "$0")/Video2Txt" "$@"\n',
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    (bundle / "video2txt.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Video2Txt\n"
        "Exec=Video2Txt\nIcon=video2txt\nCategories=AudioVideo;\n",
        encoding="utf-8",
    )
    shutil.copyfile(ROOT / "assets" / "video2txt.png", bundle / "video2txt.png")
    env = dict(os.environ, ARCH="x86_64", APPIMAGE_EXTRACT_AND_RUN="1")
    subprocess.run(
        [
            str(tool), "--runtime-file", str(runtime),
            "--mksquashfs-opt=-processors", "--mksquashfs-opt=4",
            str(bundle), str(output),
        ],
        env=env,
        check=True,
    )


def main():
    """Freeze the desktop app and add the complete offline model."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--appimagetool", type=Path, required=True)
    parser.add_argument("--runtime-file", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.error("Desktop builds are supported only on Linux.")
    if os.uname().machine != "x86_64":
        parser.error("The AppImage build targets x86-64.")
    if not os.access(args.appimagetool, os.X_OK):
        parser.error("Provide an executable appimagetool with --appimagetool.")
    if not args.runtime_file.is_file():
        parser.error("Provide the x86-64 Type 2 runtime with --runtime-file.")
    snapshot = args.model_dir or snapshot_download(
        "Systran/faster-whisper-large-v3",
        allow_patterns=["*.json", "model.bin", "README.md", "LICENSE*"],
    )
    snapshot = Path(snapshot)
    for filename in ("config.json", "model.bin", "tokenizer.json"):
        if not (snapshot / filename).is_file():
            parser.error(f"Missing model file: {snapshot / filename}")

    output = ROOT / "dist" / "Video2Txt-x86_64.AppImage"
    output.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
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
        image = staging / output.name
        write_appimage(
            bundle, image, args.appimagetool.resolve(), args.runtime_file.resolve()
        )
        image.replace(output)
    print(output)


if __name__ == "__main__":
    main()
