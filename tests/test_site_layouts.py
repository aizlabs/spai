from pathlib import Path


def test_post_layout_does_not_render_audio_voice_label():
    layout = Path("output/_layouts/post.html").read_text(encoding="utf-8")

    assert "<audio controls preload=\"metadata\">" in layout
    assert "Voz:" not in layout
    assert "page.audio.voice" not in layout
