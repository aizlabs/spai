"""
Prepare website audio metadata and local manifests for approved articles.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from openai import OpenAI

from scripts.audio_script_builder import build_speech_script
from scripts.config import AppConfig
from scripts.models import AdaptedArticle, AudioAsset, AudioManifest
from scripts.text_utils import slugify_text

OPENAI_TTS_MODEL = "gpt-4o-mini-tts"


class AudioPipeline:
    """Build narration scripts and local manifests ahead of real TTS/upload steps."""

    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger,
        tts_client: Optional[Any] = None,
        s3_client: Optional[Any] = None,
    ):
        self.config = config
        self.logger = logger.getChild("AudioPipeline")
        self.audio_config = config.audio
        self.output_dir = Path(self.audio_config.output_path)
        self.scripts_dir = self.output_dir / "scripts"
        self.generated_dir = self.output_dir / "generated"
        self.manifests_dir = self.output_dir / "manifests"
        self.tts_client = tts_client
        self.s3_client = s3_client

        if self.audio_config.enabled:
            self.scripts_dir.mkdir(parents=True, exist_ok=True)
            self.generated_dir.mkdir(parents=True, exist_ok=True)
            self.manifests_dir.mkdir(parents=True, exist_ok=True)

    def prepare_for_publish(
        self,
        article: AdaptedArticle,
        timestamp: Optional[datetime] = None,
    ) -> AdaptedArticle:
        """Generate local audio preparation artifacts and attach metadata to the article."""
        if not self.audio_config.enabled:
            return article

        timestamp = timestamp or datetime.utcnow()
        slug = slugify_text(article.title)
        level = article.level.lower()
        year_month = timestamp.strftime("%Y/%m")
        artifact_id = self._build_artifact_id(timestamp, slug, level)
        script = build_speech_script(
            article,
            include_vocabulary=self.audio_config.include_vocabulary,
        )

        script_rel_path = Path(year_month) / f"{artifact_id}.txt"
        manifest_rel_path = Path(year_month) / f"{artifact_id}.json"
        audio_rel_path = Path(year_month) / artifact_id / f"article.{self.audio_config.format}"
        script_path = self.scripts_dir / script_rel_path
        manifest_path = self.manifests_dir / manifest_rel_path
        audio_path = self.generated_dir / audio_rel_path
        script_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.parent.mkdir(parents=True, exist_ok=True)

        script_path.write_text(script.narration, encoding="utf-8")
        self._synthesize_audio(script.narration, audio_path)

        storage_key = self._build_storage_key(timestamp, artifact_id)
        asset = AudioAsset(
            url=None,
            storage_key=storage_key,
            provider=self.audio_config.provider,
            voice=self.audio_config.voice,
            format=self.audio_config.format,
            mime_type=self._mime_type_for_format(self.audio_config.format),
            local_script_path=str(script_path),
            local_audio_path=str(audio_path),
            manifest_path=str(manifest_path),
        )

        if self.audio_config.upload_enabled:
            self._upload_audio_file(audio_path, storage_key, asset.mime_type)
            asset.url = self._build_public_url(storage_key)

        manifest = AudioManifest(
            article_slug=artifact_id,
            title=article.title,
            level=article.level,
            created_at=timestamp.isoformat(),
            status="ready",
            script=script,
            asset=asset,
        )
        manifest_path.write_text(
            json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self.logger.info(
            "Prepared audio manifest for '%s' at %s",
            article.title,
            manifest_path,
        )
        return article.model_copy(update={"audio": asset})

    def _build_artifact_id(self, timestamp: datetime, slug: str, level: str) -> str:
        timestamp_str = timestamp.strftime("%Y%m%d-%H%M%S")
        return f"{timestamp_str}-{slug}-{level}"

    def _build_storage_key(self, timestamp: datetime, artifact_id: str) -> str:
        prefix = self.audio_config.s3.prefix.strip("/")
        return "/".join(
            part
            for part in [
                prefix,
                timestamp.strftime("%Y"),
                timestamp.strftime("%m"),
                artifact_id,
                f"article.{self.audio_config.format}",
            ]
            if part
        )

    def _synthesize_audio(self, narration: str, audio_path: Path) -> None:
        provider = (self.audio_config.provider or "").strip().lower()
        if provider != "openai":
            raise ValueError(f"Unsupported audio provider: {self.audio_config.provider}")

        response = self._get_tts_client().audio.speech.create(
            input=narration,
            model=OPENAI_TTS_MODEL,
            voice=self.audio_config.voice or "alloy",
            response_format=self.audio_config.format,
        )
        response.write_to_file(audio_path)

    def _upload_audio_file(self, audio_path: Path, storage_key: str, mime_type: Optional[str]) -> None:
        bucket = self.audio_config.s3.bucket
        if not bucket:
            raise ValueError("Audio upload is enabled but audio.s3.bucket is not configured")

        public_base_url = self.audio_config.public_base_url
        if not public_base_url:
            raise ValueError("Audio upload is enabled but audio.public_base_url is not configured")

        extra_args = {"ContentType": mime_type or "application/octet-stream"}
        extra_args["CacheControl"] = "public, max-age=31536000, immutable"

        try:
            self._get_s3_client().upload_file(
                str(audio_path),
                bucket,
                storage_key,
                ExtraArgs=extra_args,
            )
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"Failed to upload audio to s3://{bucket}/{storage_key}") from exc

    def _build_public_url(self, storage_key: str) -> str:
        if not self.audio_config.public_base_url:
            raise ValueError("Audio public base URL is required to build a published audio URL")
        base_url = self.audio_config.public_base_url.rstrip("/")
        return f"{base_url}/{storage_key}"

    def _get_tts_client(self) -> Any:
        if self.tts_client is None:
            openai_api_key = self.config.llm.openai_api_key
            if not openai_api_key:
                raise ValueError("OpenAI TTS requires OPENAI_API_KEY to be configured")
            self.tts_client = OpenAI(api_key=openai_api_key)
        return self.tts_client

    def _get_s3_client(self) -> Any:
        if self.s3_client is None:
            region_name = self.audio_config.s3.region or None
            self.s3_client = boto3.client("s3", region_name=region_name)
        return self.s3_client

    def _mime_type_for_format(self, format_name: str) -> str:
        mime_types = {
            "mp3": "audio/mpeg",
            "m4a": "audio/mp4",
            "wav": "audio/wav",
        }
        try:
            return mime_types[format_name]
        except KeyError as exc:
            raise ValueError(f"Unsupported audio format for MIME type mapping: {format_name}") from exc
