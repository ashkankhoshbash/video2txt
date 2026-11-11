# Video2Txt Desktop

Video2Txt displays Persian transcripts from local videos using Whisper large-v3.
The single-file Linux x64 executable includes Python, Qt, PyAV with FFmpeg libraries, and
the model. Transcription runs offline on the CPU.

## Build on Linux

From the project root on Ubuntu 26.04 Desktop x86-64, install the build
dependencies:

```sh
sudo apt update
sudo apt install curl python3-venv libxcb-cursor0 libegl1 libxkbcommon-x11-0
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Download the AppImage builder and its Type 2 runtime once:

```sh
mkdir -p build
curl -fL https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage -o build/appimagetool.AppImage
curl -fL https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64 -o build/runtime-x86_64
chmod +x build/appimagetool.AppImage
```

Build the application. The first build downloads the Whisper model:

```sh
python scripts/build_desktop.py \
  --appimagetool build/appimagetool.AppImage \
  --runtime-file build/runtime-x86_64
```

### Rebuild offline

Reuse the downloaded build tools and point the build at a local model
snapshot containing `config.json`, `model.bin`, and `tokenizer.json`:

```sh
HF_HUB_OFFLINE=1 python scripts/build_desktop.py \
  --appimagetool build/appimagetool.AppImage \
  --runtime-file build/runtime-x86_64 \
  --model-dir /path/to/model-snapshot
```

On Ubuntu, look for the model under
`~/.cache/huggingface/hub/models--Systran--faster-whisper-large-v3/snapshots/`.

## Run the built application

The build produces one file, `dist/Video2Txt-x86_64.AppImage`. Copy it as
needed. Python, Qt, FFmpeg libraries, and the Whisper model are bundled.

```sh
./dist/Video2Txt-x86_64.AppImage
```

If FUSE mounts are unavailable, use the built-in extraction mode. It needs
about 4 GB of free space in the temporary directory:

```sh
./dist/Video2Txt-x86_64.AppImage --appimage-extract-and-run
```

Select **Choose video…** or paste an Aparat video link. Optionally enter
specialized terms in **Hot words**, separated by commas, then click
**Transcribe**. Click **کپی** to copy the full transcript. Aparat links
require internet access. Downloaded media is removed when processing ends.

## Project layout

- `video2txt/desktop.py` contains the desktop interface and its worker.
- `video2txt/transcription.py` contains the shared audio and speech pipeline.
- `scripts/build_desktop.py` builds the portable Linux application.
- `dist/` contains generated packages and is ignored by Git.
