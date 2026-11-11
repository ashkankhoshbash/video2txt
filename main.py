"""Generate Persian transcripts for local videos."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from importlib.util import find_spec
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel


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


def transcribe_video(model, video, audio):
    """Extract the first audio track and return its Persian transcript."""
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
         "-y", "-i", str(video), "-map", "0:a:0", "-ac", "1",
         "-ar", "16000", "-c:a", "pcm_s16le", str(audio)],
        check=True,
    )
    with wave.open(str(audio), "rb") as wav_file:
        pcm = wav_file.readframes(wav_file.getnframes())
    samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32)
    samples /= 32768.0
    segments, _ = model.transcribe(samples, language="fa", vad_filter=True)
    return "\n".join(segment.text.strip() for segment in segments).strip()


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
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("Install FFmpeg and make sure it is on PATH.")

    configure_cuda_library_path()
    model = WhisperModel("small", device="cuda", compute_type="int8_float16")
    args.output.mkdir(parents=True, exist_ok=True)
    failures = 0

    with tempfile.TemporaryDirectory() as temp_dir:
        audio = Path(temp_dir) / "audio.wav"
        for video in videos:
            try:
                transcript = transcribe_video(model, video, audio)
                output = args.output / f"{video.name}.txt"
                text = f"{transcript}\n" if transcript else ""
                output.write_text(text, encoding="utf-8")
                print(output.resolve())
            except (
                OSError,
                ValueError,
                RuntimeError,
                wave.Error,
                subprocess.CalledProcessError,
            ) as error:
                failures += 1
                print(
                    f"Error processing {video.name}: {error}", file=sys.stderr
                )

    if failures:
        raise RuntimeError(
            f"Failed to transcribe {failures} of {len(videos)} files."
        )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        raise SystemExit(f"Error: {error}") from error
