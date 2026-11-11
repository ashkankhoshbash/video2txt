# Video2Txt Desktop

Video2Txt displays Persian transcripts from local videos using Whisper large-v3.
The single-file Linux x64 executable includes Python, Qt, PyAV with FFmpeg libraries, and
the model. Transcription runs offline on the CPU.

## Build on Linux

For a local build, start in the project root on Ubuntu 26.04 Desktop x64.
Install the system dependencies on the Ubuntu build machine:

```sh
sudo apt update
sudo apt install python3-venv libxcb-cursor0 libegl1 libxkbcommon-x11-0
```

Then install the Python dependencies and build the application:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/build_desktop.py
```

The build downloads the model and writes the portable application to
`dist/Video2Txt.run`.

### Rebuild offline

After installing the build dependencies and downloading the model once, pass
the path to the cached model snapshot to skip the download step:

```sh
HF_HUB_OFFLINE=1 python scripts/build_desktop.py --model-dir /path/to/model-snapshot
```

Use the snapshot directory that contains `config.json`, `model.bin`, and
`tokenizer.json`. On Ubuntu, look under
`~/.cache/huggingface/hub/models--Systran--faster-whisper-large-v3/snapshots/`.
The rebuilt application is written to `dist/Video2Txt.run`.

## Run the built application

From the project root, launch the executable:

```sh
./dist/Video2Txt.run
```

Select **Choose video…**, pick a file, then click **Transcribe**. The Persian
text appears in the window and can be selected and copied.

To use the app on another Ubuntu 26.04 Desktop x64 machine, copy
`Video2Txt.run` and run it there. It contains the model and the application
dependencies. At each launch it unpacks into a temporary directory, so allow
about 4 GB of free space there. The temporary files are removed on normal exit.

## Project layout

- `video2txt/desktop.py` contains the desktop interface and its worker.
- `video2txt/transcription.py` contains the shared audio and speech pipeline.
- `scripts/build_desktop.py` builds the portable Linux application.
- `dist/` contains generated packages and is ignored by Git.
