"""
Helper methods for Bandcamp provider with cookie-based authentication.

Based on the LMS Bandcamp plugin's logic and adapted for MusicAssistant.
"""
"""Bandcamp API helpers for MusicAssistant Bandcamp provider."""
from __future__ import annotations

import json
import re
from typing import Any

import httpx
from music_assistant.common.models.media_items import (
    Album,
    Artist,
    MediaType,
    MediaItemType,
    Track,
)
from music_assistant.server.helpers.api import ApiHelper
from music_assistant.server.models.config_entries import ConfigEntry

BC_BASE = "https://bandcamp.com"
BC_API_BASE = "https://bandcamp.com/api"
BC_DAILY_URL = "https://daily.bandcamp.com/feed"  # Placeholder for Bandcamp Daily (if RSS parsing desired)


class BandcampAPI:
    def __init__(self, mass, instance_id: str, config: ConfigEntry):
        self.mass = mass
        self.instance_id = instance_id
        self.config = config
        self.session = httpx.AsyncClient()
        self.logged_in = False
        self.cookie = config.get_value("identity_cookie") or ""
        self.headers = {
            "User-Agent": "MusicAssistantBandcamp/1.0",
            "Cookie": f"identity={self.cookie}" if self.cookie else "",
        }

    async def close(self):
        await self.session.aclose()

    async def search(
        self, query: str, media_types: list[MediaType]
    ) -> dict[MediaType, list[MediaItemType]]:
        """Search Bandcamp."""
        result = {media_type: [] for media_type in media_types}
        async with self.session as client:
            search_url = f"{BC_BASE}/api/fuzzysearch/1/autocomplete?q={query}"
            resp = await client.get(search_url, headers=self.headers)
            if not resp.status_code == 200:
                return result
            data = resp.json()

            if MediaType.ARTIST in result and "auto" in data:
                for entry in data["auto"]:
                    if entry["type"] == "b":
                        result[MediaType.ARTIST].append(
                            Artist(
                                item_id=str(entry["id"]),
                                name=entry["name"],
                                provider=self.instance_id,
                            )
                        )
            return result

    async def get_artist(self, artist_id: str) -> Artist | None:
        url = f"{BC_API_BASE}/fancollection/1/collection_items_all?fan_id={artist_id}&count=1"
        async with self.session as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return Artist(
                item_id=artist_id,
                name=data.get("name") or "Unknown",
                provider=self.instance_id,
            )

    async def get_album(self, album_id: str) -> Album | None:
        url = f"{BC_API_BASE}/mobile/25/album_details?album_id={album_id}"
        async with self.session as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return self._parse_album(data)

    async def get_track(self, track_id: str) -> Track | None:
        url = f"{BC_API_BASE}/mobile/25/track_details?track_id={track_id}"
        async with self.session as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return self._parse_track(data)

    def _parse_album(self, data: dict[str, Any]) -> Album:
        artist = Artist(
            item_id=str(data["band_id"]),
            name=data.get("artist") or "Unknown",
            provider=self.instance_id,
        )
        return Album(
            item_id=str(data["album_id"]),
            name=data["title"],
            artist=artist,
            year=int(data["release_date"][:4]) if data.get("release_date") else None,
            provider=self.instance_id,
            tracks=[],
        )

    def _parse_track(self, data: dict[str, Any]) -> Track:
        album = None
        if "album_id" in data:
            album = Album(
                item_id=str(data["album_id"]),
                name=data.get("album_title") or "",
                provider=self.instance_id,
            )
        artist = Artist(
            item_id=str(data["band_id"]),
            name=data.get("artist") or "Unknown",
            provider=self.instance_id,
        )
        return Track(
            item_id=str(data["track_id"]),
            name=data["title"],
            duration=int(data["duration"]),
            provider=self.instance_id,
            artist=artist,
            album=album,
        )
