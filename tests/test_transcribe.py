from tpsermons.transcribe import PRIMARY_MODEL, RETRY_MODEL, ffmpeg_args


def test_downsamples_to_mono_16k_32kbps():
    # Keeps the longest sermon (68.5 min) at ~16.4 MB, under the 25 MB upload
    # cap -- which is why no chunking logic exists anywhere in this codebase.
    args = ffmpeg_args("in.mp3", "out.mp3")
    assert args[args.index("-ac") + 1] == "1"
    assert args[args.index("-ar") + 1] == "16000"
    assert args[args.index("-b:a") + 1] == "32k"


def test_overwrites_without_prompting():
    assert "-y" in ffmpeg_args("in.mp3", "out.mp3")


def test_retry_uses_a_different_model():
    # A model-specific fault should not be retried into the same wall.
    assert PRIMARY_MODEL != RETRY_MODEL
