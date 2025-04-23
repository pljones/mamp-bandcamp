"""
Bandcamp support for MusicAssistant with cookie-based login functionality.

Based on the LMS Bandcamp plugin (https://github.com/pljones/mamp-bandcamp/tree/main/herget.net/Bandcamp)
and the MusicAssistant YouTube plugin.
"""
"""MusicAssistant provider for Bandcamp."""

from __future__ import annotations

from typing import TYPE_CHECKING

from music_assistant.common.models.config_entry import ConfigEntry
from music_assistant.common.models.enums import ProviderType, MediaType, ProviderFeature
from music_assistant.common.models.media_items import (
    Album,
    Artist,
    Playlist,
    Track,
    SearchResults,
)
from music_assistant.server.models.music_provider import MusicProviderWithCapabilities

from .helpers import BandcampAPI

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class BandcampProvider(MusicProviderWithCapabilities):
    """MusicAssistant provider for Bandcamp."""

    _api: BandcampAPI

    async def setup(self, config: ConfigEntry) -> bool:
        self._api = BandcampAPI(config)
        return await self._api.setup()

    @property
    def name(self) -> str:
        return "Bandcamp"

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.MUSIC

    @property
    def supported_mediatypes(self) -> tuple[MediaType, ...]:
        return (
            MediaType.ARTIST,
            MediaType.ALBUM,
            MediaType.TRACK,
            MediaType.PLAYLIST,
        )

    @property
    def capabilities(self) -> set[ProviderFeature]:
        return {
            ProviderFeature.SEARCH,
            ProviderFeature.STREAM_DETAILS,
            ProviderFeature.LIBRARY_TRACKS,
            ProviderFeature.LIBRARY_ALBUMS,
            ProviderFeature.LIBRARY_ARTISTS,
            ProviderFeature.LIBRARY_PLAYLISTS,
            ProviderFeature.BROWSE,
        }

    async def search(self, search_query, media_types: list[MediaType]) -> SearchResults:
        return await self._api.search(search_query, media_types)

    async def get_track(self, prov_track_id: str) -> Track:
        return await self._api.get_track(prov_track_id)

    async def get_album(self, prov_album_id: str) -> Album:
        return await self._api.get_album(prov_album_id)

    async def get_artist(self, prov_artist_id: str) -> Artist:
        return await self._api.get_artist(prov_artist_id)

    async def get_playlist(self, prov_playlist_id: str) -> Playlist:
        return await self._api.get_playlist(prov_playlist_id)

    async def get_stream_details(self, item_id: str) -> Track:
        return await self._api.get_stream(item_id)

    async def library_tracks(self) -> AsyncGenerator[Track, None]:
        async for track in self._api.get_user_collection():
            yield track

    async def library_albums(self) -> AsyncGenerator[Album, None]:
        async for album in self._api.get_user_albums():
            yield album

    async def library_artists(self) -> AsyncGenerator[Artist, None]:
        async for artist in self._api.get_user_artists():
            yield artist

    async def library_playlists(self) -> AsyncGenerator[Playlist, None]:
        async for pl in self._api.get_user_playlists():
            yield pl

