# Video2Txt Desktop

Video2Txt displays Persian transcripts from local videos using Whisper large-v3.
The portable x64 bundles include Python, Qt, PyAV with FFmpeg libraries, and
the model. Transcription runs offline on the CPU.

## Run a portable bundle

- Windows 10 (1809 or later) or Windows 11 x64. Extract `Video2Txt-windows-x64.zip` and open
  `Video2Txt/Video2Txt.exe`.
- Ubuntu 26.04 Desktop x64. Extract `Video2Txt-ubuntu-26.04-x64.tar.gz`
  with your archive manager or `tar -xzf Video2Txt-ubuntu-26.04-x64.tar.gz`.
  Open `Video2Txt/Video2Txt` or launch it from a terminal.

Keep the executable and its `_internal` folder together. Select **Choose
video…**, pick a file, then click **Transcribe**. The Persian text appears
in the window and can be selected and copied. Each archive includes roughly
3.1 GB of model files before compression.

## Build the bundles

For a local build, use a clean x64 environment on the target OS with Python 3.12
on Windows or Ubuntu 26.04’s system Python.
On the Ubuntu build machine, install `libxcb-cursor0`, `libegl1`, and
`libxkbcommon-x11-0` before building. Then run:

```sh
python -m pip install -r requirements-desktop.txt
python scripts/build_desktop.py
```

The build downloads the model and writes the portable application to
`dist/Video2Txt/`. To run from source with an already cached model, use
`python -m video2txt.desktop`.

### Rebuild offline

After installing the build dependencies and downloading the model once, pass
the path to the cached model snapshot to skip the download step:

```sh
HF_HUB_OFFLINE=1 python scripts/build_desktop.py --model-dir /path/to/model-snapshot
```

Use the snapshot directory that contains `config.json`, `model.bin`, and
`tokenizer.json`. On Ubuntu, look under
`~/.cache/huggingface/hub/models--Systran--faster-whisper-large-v3/snapshots/`.
The rebuilt application is written to `dist/Video2Txt/`.

## Project layout

- `video2txt/desktop.py` contains the desktop interface and its worker.
- `video2txt/transcription.py` contains the shared audio and speech pipeline.
- `main.py` remains the GPU batch CLI for the `videos/` directory.
- `scripts/build_desktop.py` builds an application for the current OS.
- `dist/` contains generated packages and is ignored by Git.
