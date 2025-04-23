"""
Helper methods for Bandcamp provider with cookie-based authentication.

Based on the LMS Bandcamp plugin's logic and adapted for MusicAssistant.
"""
"""Bandcamp API helpers for MusicAssistant Bandcamp provider."""
from __future__ import annotations

import aiohttp
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import quote
from typing import AsyncGenerator

from music_assistant.common.models.enums import MediaType
from music_assistant.common.models.media_items import (
    Album,
    Artist,
    Playlist,
    Track,
    SearchResults,
)

BANDCAMP_BASE = "https://bandcamp.com"


class BandcampAPI:
    """Bandcamp API wrapper for MusicAssistant."""

    def __init__(self, config):
        self.session = aiohttp.ClientSession()
        self.username = config.get_value("username")
        self.cookie = config.get_value("cookie")
        self.headers = {
            "User-Agent": "MusicAssistantBandcamp",
            "Cookie": self.cookie or "",
        }

    async def setup(self) -> bool:
        return True

    async def _fetch_html(self, url: str) -> BeautifulSoup:
        async with self.session.get(url, headers=self.headers) as resp:
            text = await resp.text()
            return BeautifulSoup(text, "html.parser")

    async def search(self, query: str, media_types: list[MediaType]) -> SearchResults:
        url = f"{BANDCAMP_BASE}/search?q={quote(query)}"
        soup = await self._fetch_html(url)
        results = SearchResults()

        for item in soup.select("li.searchresult"):
            item_type = item.get("data-searchtype")
            title = item.select_one(".heading").get_text(strip=True)
            link = item.select_one("a")["href"]

            if item_type == "t" and MediaType.TRACK in media_types:
                results.tracks.append(Track(name=title, provider="bandcamp", provider_mappings={"bandcamp": link}))
            elif item_type == "a" and MediaType.ALBUM in media_types:
                results.albums.append(Album(name=title, provider="bandcamp", provider_mappings={"bandcamp": link}))
            elif item_type == "b" and MediaType.ARTIST in media_types:
                results.artists.append(Artist(name=title, provider="bandcamp", provider_mappings={"bandcamp": link}))

        return results

    async def get_album(self, url: str) -> Album:
        soup = await self._fetch_html(url)
        title = soup.find("h2", class_="trackTitle").get_text(strip=True)
        artist = await self.get_artist(soup.find("a", href=re.compile("/music$"))["href"])
        tracks = []
        trackinfo_match = re.search(r"trackinfo\s*:\s*(\[{.*?}\])", soup.text, re.DOTALL)
        if trackinfo_match:
            trackinfo = json.loads(trackinfo_match.group(1))
            for track in trackinfo:
                tracks.append(Track(name=track.get("title", "Track"), media_url=track["file"]["mp3-128"], provider="bandcamp"))
        return Album(name=title, artist=artist, tracks=tracks, provider="bandcamp", provider_mappings={"bandcamp": url})

    async def get_track(self, url: str) -> Track:
        soup = await self._fetch_html(url)
        title = soup.find("h2", class_="trackTitle").get_text(strip=True)
        artist_link = soup.find("a", href=re.compile("/music$"))
        artist = await self.get_artist(artist_link["href"]) if artist_link else None
        stream = await self.get_stream(url)
        return Track(name=title, artist=artist, media_url=stream.media_url, provider="bandcamp", provider_mappings={"bandcamp": url})

    async def get_artist(self, url: str) -> Artist:
        soup = await self._fetch_html(url)
        title = soup.title.string.strip().split("|")[0].strip()
        return Artist(name=title, provider="bandcamp", provider_mappings={"bandcamp": url})

    async def get_playlist(self, playlist_id: str) -> Playlist:
        if "wishlist" in playlist_id:
            return Playlist(name="Wishlist", provider="bandcamp", provider_mappings={"bandcamp": playlist_id})
        return Playlist(name="Collection", provider="bandcamp", provider_mappings={"bandcamp": playlist_id})

    async def get_stream(self, url: str) -> Track:
        soup = await self._fetch_html(url)
        match = re.search(r"trackinfo\s*:\s*(\[{.*?}\])", soup.text, re.DOTALL)
        if not match:
            raise ValueError("No stream found")
        info = json.loads(match.group(1))[0]
        return Track(name=info.get("title", "Track"), media_url=info["file"]["mp3-128"], provider="bandcamp")

    async def _fan_page(self) -> str:
        fan_url = f"https://bandcamp.com/{self.username}"
        soup = await self._fetch_html(fan_url)
        return soup

    async def get_user_collection(self) -> AsyncGenerator[Track, None]:
        soup = await self._fan_page()
        for item in soup.select("li.collection-item-container"):
            link = item.find("a", href=True)
            if "/track/" in link["href"]:
                yield await self.get_track(link["href"])

    async def get_user_albums(self) -> AsyncGenerator[Album, None]:
        soup = await self._fan_page()
        for item in soup.select("li.collection-item-container"):
            link = item.find("a", href=True)
            if "/album/" in link["href"]:
                yield await self.get_album(link["href"])

    async def get_user_artists(self) -> AsyncGenerator[Artist, None]:
        soup = await self._fan_page()
        for item in soup.select("div.fan-collection-artist-name"):
            link = item.find("a", href=True)
            yield await self.get_artist(link["href"])

    async def get_user_playlists(self) -> AsyncGenerator[Playlist, None]:
        if not self.username:
            return
        yield Playlist(name="Wishlist", provider="bandcamp", provider_mappings={"bandcamp": f"https://bandcamp.com/{self.username}/wishlist"})
        yield Playlist(name="Collection", provider="bandcamp", provider_mappings={"bandcamp": f"https://bandcamp.com/{self.username}"})

