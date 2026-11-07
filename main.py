import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

CATALOG = "https://datisint.com/academy/videos"
VIDEO_PATH = "/academy/videos/37e023454f874aca"


def fetch(url):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser(description="Transcribe a short Datis Academy sample.")
    parser.add_argument("--output", type=Path, default=Path("transcript.txt"))
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None:
        raise RuntimeError("Install FFmpeg and make sure it is on PATH.")

    if VIDEO_PATH not in fetch(CATALOG):
        raise RuntimeError("The selected tutorial is no longer linked from the Datis catalog.")

    page = fetch("https://datisint.com" + VIDEO_PATH)
    match = re.search(r'aparat\.com/(?:video/video/embed/videohash/|v/)([a-zA-Z0-9]+)', page)
    if not match:
        raise RuntimeError("Could not find the Aparat player on the tutorial page.")

    media_url = subprocess.check_output(
        [sys.executable, "-m", "yt_dlp", "--no-playlist", "-f", "ba/w",
         "--get-url", f"https://www.aparat.com/v/{match[1]}"],
        text=True,
    ).strip()

    from faster_whisper import WhisperModel

    with tempfile.TemporaryDirectory() as temp_dir:
        audio = Path(temp_dir) / "sample.wav"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
             "-rw_timeout", "30000000", "-i", media_url, "-t", "60",
             "-map", "0:a:0", "-ac", "1", "-ar", "16000",
             "-c:a", "pcm_s16le", str(audio)],
            check=True,
        )
        model = WhisperModel("small", device="cuda", compute_type="int8_float16")
        segments, _ = model.transcribe(str(audio), language="fa", vad_filter=True)
        transcript = "\n".join(segment.text.strip() for segment in segments).strip()

    if not transcript:
        raise RuntimeError("No speech was detected in the first 60 seconds.")
    args.output.write_text(transcript + "\n", encoding="utf-8")
    print(args.output.resolve())


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"Error: {error}") from error
