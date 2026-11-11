"""Decode local video audio and transcribe Persian speech."""

import av
import numpy as np


def transcribe(model, video):
    """Return Persian text from the video's first audio track."""
    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
    chunks = []
    with av.open(str(video)) as container:
        if not container.streams.audio:
            raise ValueError("The selected video has no audio track.")
        for frame in container.decode(audio=0):
            for converted in resampler.resample(frame):
                chunks.append(converted.to_ndarray().ravel())
        for converted in resampler.resample(None):
            chunks.append(converted.to_ndarray().ravel())

    if not chunks:
        return ""

    samples = np.concatenate(chunks).astype(np.float32) / 32768
    segments, _ = model.transcribe(samples, language="fa", vad_filter=True)
    return "\n".join(segment.text.strip() for segment in segments).strip()
