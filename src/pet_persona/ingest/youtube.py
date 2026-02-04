"""YouTube ingestion pipeline."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pet_persona.config import get_settings
from pet_persona.db.models import SourceDoc, TraitScore
from pet_persona.ingest.cache import FileCache
from pet_persona.ingest.models import YOUTUBE_SEARCH_PATTERNS
from pet_persona.ingest.rate_limit import RateLimiterRegistry
from pet_persona.traits import score_traits
from pet_persona.utils.logging import get_logger
from pet_persona.utils.text import clean_text

logger = get_logger(__name__)


class YouTubeIngester:
    """Ingest breed information from YouTube using the Data API."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.youtube_api_key
        self.cache = FileCache()
        self.rate_limiter = RateLimiterRegistry.get(
            "youtube",
            max_requests=settings.youtube_rate_limit_requests,
            period_seconds=settings.youtube_rate_limit_period,
        )
        self.output_dir = settings.raw_youtube_dir

        if not self.api_key:
            logger.warning(
                "YouTube API key not configured. "
                "Set YOUTUBE_API_KEY in .env file to enable YouTube ingestion."
            )

    def _get_youtube_service(self):
        """Get YouTube API service client."""
        if not self.api_key:
            raise ValueError("YouTube API key not configured")

        try:
            from googleapiclient.discovery import build

            return build("youtube", "v3", developerKey=self.api_key)
        except ImportError:
            raise ImportError(
                "google-api-python-client not installed. "
                "Install with: pip install google-api-python-client"
            )

    def _search_videos(
        self, query: str, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for videos matching a query.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of video metadata dicts
        """
        cache_key = f"youtube_search:{query}:{max_results}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        if not self.api_key:
            logger.warning("YouTube API key not set, skipping search")
            return []

        self.rate_limiter.acquire()

        try:
            youtube = self._get_youtube_service()

            # Search for videos
            search_response = (
                youtube.search()
                .list(
                    q=query,
                    part="id,snippet",
                    type="video",
                    maxResults=max_results,
                    relevanceLanguage="en",
                    safeSearch="moderate",
                )
                .execute()
            )

            videos = []
            for item in search_response.get("items", []):
                video_id = item["id"]["videoId"]
                snippet = item["snippet"]

                videos.append(
                    {
                        "video_id": video_id,
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", ""),
                        "channel_title": snippet.get("channelTitle", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "thumbnail_url": snippet.get("thumbnails", {})
                        .get("medium", {})
                        .get("url", ""),
                    }
                )

            self.cache.set(cache_key, videos)
            logger.debug(f"Found {len(videos)} videos for query: {query}")
            return videos

        except Exception as e:
            logger.error(f"YouTube search error for '{query}':{e}")
            return []

    def _get_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a video.

        Args:
            video_id: YouTube video ID

        Returns:
            Video details dict or None
        """
        cache_key = f"youtube_video:{video_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        if not self.api_key:
            return None

        self.rate_limiter.acquire()

        try:
            youtube = self._get_youtube_service()

            response = (
                youtube.videos()
                .list(part="snippet,contentDetails,statistics", id=video_id)
                .execute()
            )

            items = response.get("items", [])
            if not items:
                return None

            item = items[0]
            snippet = item["snippet"]
            content_details = item.get("contentDetails", {})
            statistics = item.get("statistics", {})

            result = {
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "channel_id": snippet.get("channelId", ""),
                "published_at": snippet.get("publishedAt", ""),
                "duration": content_details.get("duration", ""),
                "view_count": statistics.get("viewCount", "0"),
                "like_count": statistics.get("likeCount", "0"),
                "tags": snippet.get("tags", []),
            }

            self.cache.set(cache_key, result)
            return result

        except Exception as e:
            logger.error(f"YouTube video details error for '{video_id}': {e}")
            return None

    def _get_transcript(self, video_id: str) -> Optional[str]:
        """
        Attempt to get transcript for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            Transcript text or None if unavailable
        """
        cache_key = f"youtube_transcript:{video_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(
                    video_id, languages=["en", "en-US", "en-GB"]
                )

                # Combine transcript segments
                transcript_text = " ".join(
                    segment["text"] for segment in transcript_list
                )

                self.cache.set(cache_key, transcript_text)
                logger.debug(f"Retrieved transcript for video:{video_id}")
                return transcript_text

            except (TranscriptsDisabled, NoTranscriptFound):
                logger.debug(f"No transcript available for video: {video_id}")
                return None

        except ImportError:
            logger.debug(
                "youtube-transcript-api not installed, skipping transcript retrieval"
            )
            return None

    def ingest_breed(
        self,
        breed: str,
        species: Literal["dog", "cat"],
        max_results: int = 10,
    ) -> List[SourceDoc]:
        """
        Ingest breed-related YouTube content.

        Args:
            breed: Breed name
            species: 'dog' or 'cat'
            max_results: Maximum videos to fetch per query

        Returns:
            List of SourceDoc objects
        """
        if not self.api_key:
            logger.warning(
                "YouTube API key not configured. Skipping YouTube ingestion."
            )
            return []

        logger.info(f"Ingesting YouTube data for {species}: {breed}")

        all_videos = []
        seen_ids = set()

        # Search using multiple query patterns
        for pattern in YOUTUBE_SEARCH_PATTERNS:
            query = pattern.format(breed=breed)
            videos = self._search_videos(query, max_results=max_results // 2)

            for video in videos:
                video_id = video["video_id"]
                if video_id not in seen_ids:
                    seen_ids.add(video_id)
                    all_videos.append(video)

            # Stop if we have enough videos
            if len(all_videos) >= max_results:
                break

        # Limit to max_results
        all_videos = all_videos[:max_results]

        # Enrich with details and transcripts
        source_docs = []
        for video in all_videos:
            video_id = video["video_id"]

            # Get full details
            details = self._get_video_details(video_id)
            if details:
                video.update(details)

            # Try to get transcript
            transcript = self._get_transcript(video_id)

            # Build content from available data
            content_parts = []
            if video.get("title"):
                content_parts.append(f"Title: {video['title']}")
            if video.get("description"):
                content_parts.append(f"Description: {video['description']}")
            if transcript:
                content_parts.append(f"Transcript: {transcript}")
            if video.get("tags"):
                content_parts.append(f"Tags: {', '.join(video['tags'][:20])}")

            content = clean_text("\n\n".join(content_parts))

            source_doc = SourceDoc(
                source_type="youtube",
                source_id=video_id,
                title=video.get("title", ""),
                url=f"https://www.youtube.com/watch?v={video_id}",
                content=content,
                metadata={
                    "species": species,
                    "breed": breed,
                    "channel": video.get("channel_title", ""),
                    "view_count": video.get("view_count", "0"),
                    "has_transcript": transcript is not None,
                },
            )
            source_docs.append(source_doc)

        # Save raw data
        raw_path = self.output_dir / f"{species}_{breed.replace(' ', '_')}_youtube.json"
        with open(raw_path, "w") as f:
            json.dump(
                {
                    "breed": breed,
                    "species": species,
                    "fetched_at": datetime.utcnow().isoformat(),
                    "videos": all_videos,
                    "source_docs": [sd.model_dump(mode="json")for sd in source_docs],
                },
                f,
                indent=2,
                default=str,
            )
        logger.info(
            f"Saved {len(source_docs)} YouTube sources for {breed} to: {raw_path}"
        )

        return source_docs

    def score_sources(self, source_docs: List[SourceDoc]) -> Dict[str, TraitScore]:
        """
        Score traits from YouTube source documents.

        Args:
            source_docs: List of SourceDoc objects

        Returns:
            Dict mapping trait_id to TraitScore
        """
        texts = [doc.content for doc in source_docs if doc.content]
        return score_traits(texts)
