from datetime import datetime

from scripts.audio_pipeline import AudioPipeline


def test_audio_pipeline_writes_manifest_and_script_when_enabled(
    base_config,
    mock_logger,
    sample_a2_article,
    tmp_path,
):
    base_config.audio.enabled = True
    base_config.audio.output_path = str(tmp_path / "audio")
    base_config.audio.provider = "elevenlabs"
    base_config.audio.voice = "newsreader"

    pipeline = AudioPipeline(base_config, mock_logger)

    prepared_article = pipeline.prepare_for_publish(
        sample_a2_article,
        timestamp=datetime(2024, 1, 2, 12, 0, 0),
    )

    assert prepared_article.audio is not None
    assert prepared_article.audio.storage_key == (
        "articles/2024/01/espana-tiene-menos-contaminacion-a2/article.mp3"
    )
    assert prepared_article.audio.url is None

    script_path = (
        tmp_path
        / "audio"
        / "scripts"
        / "2024"
        / "01"
        / "espana-tiene-menos-contaminacion-a2.txt"
    )
    manifest_path = (
        tmp_path
        / "audio"
        / "manifests"
        / "2024"
        / "01"
        / "espana-tiene-menos-contaminacion-a2.json"
    )
    assert script_path.exists()
    assert manifest_path.exists()
    assert "Fin del artículo." in script_path.read_text(encoding="utf-8")


def test_audio_pipeline_sets_public_url_when_upload_enabled(
    base_config,
    mock_logger,
    sample_a2_article,
    tmp_path,
):
    base_config.audio.enabled = True
    base_config.audio.upload_enabled = True
    base_config.audio.output_path = str(tmp_path / "audio")
    base_config.audio.public_base_url = "https://media.spaili.com"

    pipeline = AudioPipeline(base_config, mock_logger)

    prepared_article = pipeline.prepare_for_publish(
        sample_a2_article,
        timestamp=datetime(2024, 1, 2, 12, 0, 0),
    )

    assert prepared_article.audio is not None
    assert (
        prepared_article.audio.url
        == "https://media.spaili.com/articles/2024/01/espana-tiene-menos-contaminacion-a2/article.mp3"
    )
