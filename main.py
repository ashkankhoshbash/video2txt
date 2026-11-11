"""Generate Persian transcripts for local videos."""

import argparse
import os
import sys
from importlib.util import find_spec
from pathlib import Path

from faster_whisper import WhisperModel

from video2txt.transcription import transcribe


def configure_cuda_library_path():
    """Restart with the bundled CUDA libraries on the Linux loader path."""
    if sys.platform != "linux" or find_spec("nvidia") is None:
        return

    library_dirs = []
    for package in ("nvidia.cublas", "nvidia.cudnn"):
        spec = find_spec(package)
        if spec and spec.submodule_search_locations:
            for location in spec.submodule_search_locations:
                directory = Path(location) / "lib"
                if directory.is_dir():
                    library_dirs.append(str(directory))

    existing = os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep)
    existing = [directory for directory in existing if directory]
    missing = [
        directory for directory in library_dirs if directory not in existing
    ]
    if missing:
        # The Linux dynamic loader reads LD_LIBRARY_PATH at process startup.
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = os.pathsep.join(missing + existing)
        os.execve(sys.executable, [sys.executable, *sys.orig_argv[1:]], env)


def find_videos(video_dir):
    """Return the sorted list of visible files in the input directory."""
    if not video_dir.is_dir():
        raise RuntimeError(
            "Create a videos directory and put your video files in it."
        )
    videos = sorted(
        path for path in video_dir.iterdir()
        if path.is_file() and not path.name.startswith(".")
    )
    if not videos:
        raise RuntimeError("The videos directory is empty.")
    return videos


def main():
    """Parse CLI options and process the local video batch."""
    parser = argparse.ArgumentParser(description="Transcribe local videos.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("transcripts"),
        help="Directory for the generated transcripts",
    )
    args = parser.parse_args()

    videos = find_videos(Path("videos"))

    configure_cuda_library_path()
    model = WhisperModel("large-v3", device="cuda", compute_type="int8_float16")
    args.output.mkdir(parents=True, exist_ok=True)
    failures = 0

    for video in videos:
        try:
            transcript = transcribe(model, video)
            output = args.output / f"{video.name}.txt"
            text = f"{transcript}\n" if transcript else ""
            output.write_text(text, encoding="utf-8")
            print(output.resolve())
        except (OSError, ValueError, RuntimeError) as error:
            failures += 1
            print(f"Error processing {video.name}: {error}", file=sys.stderr)

    if failures:
        raise RuntimeError(
            f"Failed to transcribe {failures} of {len(videos)} files."
        )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        raise SystemExit(f"Error: {error}") from error
