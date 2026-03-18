"""
Prepare website audio metadata and local manifests for approved articles.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from scripts.audio_script_builder import build_speech_script
from scripts.config import AppConfig
from scripts.models import AdaptedArticle, AudioAsset, AudioManifest
from scripts.text_utils import slugify_text


class AudioPipeline:
    """Build narration scripts and local manifests ahead of real TTS/upload steps."""

    def __init__(self, config: AppConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger.getChild("AudioPipeline")
        self.audio_config = config.audio
        self.output_dir = Path(self.audio_config.output_path)
        self.scripts_dir = self.output_dir / "scripts"
        self.manifests_dir = self.output_dir / "manifests"

        if self.audio_config.enabled:
            self.scripts_dir.mkdir(parents=True, exist_ok=True)
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
        script_path = self.scripts_dir / script_rel_path
        manifest_path = self.manifests_dir / manifest_rel_path
        script_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        script_path.write_text(script.narration, encoding="utf-8")

        storage_key = self._build_storage_key(timestamp, artifact_id)
        public_url = self._build_public_url(storage_key)
        asset = AudioAsset(
            url=public_url if self.audio_config.upload_enabled and public_url else None,
            storage_key=storage_key,
            provider=self.audio_config.provider,
            voice=self.audio_config.voice,
            format=self.audio_config.format,
            mime_type=self._mime_type_for_format(self.audio_config.format),
            local_script_path=str(script_path),
            manifest_path=str(manifest_path),
        )
        manifest = AudioManifest(
            article_slug=artifact_id,
            title=article.title,
            level=article.level,
            created_at=timestamp.isoformat(),
            status="ready" if asset.url else "pending",
            script=script,
            asset=asset,
        )
        manifest_path.write_text(
            json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if self.audio_config.upload_enabled:
            self.logger.warning(
                "Audio upload was requested but is not implemented yet; generated manifest only."
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

    def _build_public_url(self, storage_key: str) -> Optional[str]:
        if not self.audio_config.public_base_url:
            return None
        base_url = self.audio_config.public_base_url.rstrip("/")
        return f"{base_url}/{storage_key}"

    def _mime_type_for_format(self, format_name: str) -> str:
        return {
            "mp3": "audio/mpeg",
            "m4a": "audio/mp4",
            "wav": "audio/wav",
        }[format_name]
