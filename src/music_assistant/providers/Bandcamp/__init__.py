"""
Bandcamp support for MusicAssistant with cookie-based login functionality.

Based on the LMS Bandcamp plugin (https://github.com/pljones/mamp-bandcamp/tree/main/herget.net/Bandcamp)
and the MusicAssistant YouTube plugin.
"""
"""MusicAssistant provider for Bandcamp."""

from __future__ import annotations

from typing import TYPE_CHECKING
from music_assistant.common.models.enums import ProviderFeature, MediaType
from music_assistant.common.models.config_entries import ConfigEntry, ConfigValueType
from music_assistant.common.models.media_items import (  # noqa: F401
    MediaItemType,
    BrowseFolder,
    Album,
    Track,
    SearchResults,
)
from music_assistant.server.models.provider import MusicProvider
from .helpers import BandcampAPI

if TYPE_CHECKING:
    from music_assistant.server.models.mass import Mass


class BandcampProvider(MusicProvider):
    _api: BandcampAPI

    async def setup(self, mass: Mass, config: ConfigEntry) -> None:
        await super().setup(mass, config)
        self._api = BandcampAPI(self.mass, self.instance_id, config)
        await self._api.setup()

    async def close(self) -> None:
        await self._api.close()

    async def get_library_albums(self) -> list[Album]:
        return await self._api.get_user_collection()

    async def get_album(self, album_id: str) -> Album:
        return await self._api.get_album(album_id)

    async def get_track(self, track_id: str) -> Track:
        return await self._api.get_track(track_id)

    async def get_album_tracks(self, album_id: str) -> list[Track]:
        return await self._api.get_album_tracks(album_id)

    async def get_stream_details(self, item_id: str) -> Track:
        return await self._api.get_stream_details(item_id)

    async def search(self, search_query: str, media_types: list[MediaType], limit: int = 25) -> SearchResults:
        return await self._api.search(search_query, media_types, limit)

    async def browse(self, path: str | None = None) -> BrowseFolder:
        if not path:
            return BrowseFolder(
                item_id="bandcamp_root",
                provider=self.instance_id,
                children=[
                    BrowseFolder(item_id="new_notable", name="New & Notable", provider=self.instance_id),
                    BrowseFolder(item_id="genres", name="Genres", provider=self.instance_id),
                    BrowseFolder(item_id="tags", name="Tags", provider=self.instance_id),
                    BrowseFolder(item_id="best_selling", name="Best-Selling", provider=self.instance_id),
                    BrowseFolder(item_id="staff_picks", name="Staff Picks", provider=self.instance_id),
                    BrowseFolder(item_id="discover", name="Discover", provider=self.instance_id),
                    BrowseFolder(item_id="daily", name="Bandcamp Daily", provider=self.instance_id),
                    BrowseFolder(item_id="collection", name="My Collection", provider=self.instance_id),
                    BrowseFolder(item_id="location", name="By Location", provider=self.instance_id),
                    BrowseFolder(item_id="format", name="By Format (Vinyl, Cassette, etc.)", provider=self.instance_id),
                ]
            )

        if path == "genres":
            genres = await self._api.get_genres()
            return BrowseFolder(
                item_id="genres",
                provider=self.instance_id,
                children=[
                    BrowseFolder(item_id=f"genre:{g['slug']}", name=g['name'], provider=self.instance_id)
                    for g in genres
                ]
            )

        if path.startswith("genre:"):
            slug = path.split(":", 1)[1]
            albums = await self._api.get_albums_by_genre(slug)
            return BrowseFolder(
                item_id=path,
                provider=self.instance_id,
                children=[Album.from_dict(album.to_dict()) for album in albums]
            )

        if path == "tags":
            tags = await self._api.get_tags()
            return BrowseFolder(
                item_id="tags",
                provider=self.instance_id,
                children=[
                    BrowseFolder(item_id=f"tag:{t['slug']}", name=t['name'], provider=self.instance_id)
                    for t in tags
                ]
            )

        if path.startswith("tag:"):
            slug = path.split(":", 1)[1]
            albums = await self._api.get_albums_by_tag(slug)
            return BrowseFolder(
                item_id=path,
                provider=self.instance_id,
                children=[Album.from_dict(album.to_dict()) for album in albums]
            )

        if path == "new_notable":
            albums = await self._api.get_new_and_notable()
            return BrowseFolder(
                item_id=path,
                provider=self.instance_id,
                children=[Album.from_dict(album.to_dict()) for album in albums]
            )

        if path == "best_selling":
            albums = await self._api.get_best_selling()
            return BrowseFolder(
                item_id=path,
                provider=self.instance_id,
                children=[Album.from_dict(album.to_dict()) for album in albums]
            )

        if path == "staff_picks":
            albums = await self._api.get_staff_picks()
            return BrowseFolder(
                item_id=path,
                provider=self.instance_id,
                children=[Album.from_dict(album.to_dict()) for album in albums]
            )

        if path == "discover":
            albums = await self._api.get_discover()
            return BrowseFolder(
                item_id=path,
                provider=self.instance_id,
                children=[Album.from_dict(album.to_dict()) for album in albums]
            )

        if path == "daily":
            posts = await self._api.get_bandcamp_daily()
            return BrowseFolder(
                item_id=path,
                provider=self.instance_id,
                children=[BrowseFolder(item_id=f"daily:{p['slug']}", name=p['title'], provider=self.instance_id) for p in posts]
            )

        if path.startswith("daily:"):
            slug = path.split(":", 1)[1]
            albums = await self._api.get_albums_from_daily(slug)
            return BrowseFolder(
                item_id=path,
                provider=self.instance_id,
                children=[Album.from_dict(album.to_dict()) for album in albums]
            )

        if path == "collection":
            albums = await self._api.get_user_collection()
            return BrowseFolder(
                item_id=path,
                provider=self.instance_id,
                children=[Album.from_dict(album.to_dict()) for album in albums]
            )

        if path == "location":
            locations = await self._api.get_locations()
            return BrowseFolder(
                item_id="location",
                provider=self.instance_id,
                children=[
                    BrowseFolder(item_id=f"location:{loc['slug']}", name=loc['name'], provider=self.instance_id)
                    for loc in locations
                ]
            )

        if path.startswith("location:"):
            slug = path.split(":", 1)[1]
            albums = await self._api.get_albums_by_location(slug)
            return BrowseFolder(
                item_id=path,
                provider=self.instance_id,
                children=[Album.from_dict(album.to_dict()) for album in albums]
            )

        if path == "format":
            formats = await self._api.get_formats()
            return BrowseFolder(
                item_id="format",
                provider=self.instance_id,
                children=[
                    BrowseFolder(item_id=f"format:{f['slug']}", name=f['name'], provider=self.instance_id)
                    for f in formats
                ]
            )

        if path.startswith("format:"):
            slug = path.split(":", 1)[1]
            albums = await self._api.get_albums_by_format(slug)
            return BrowseFolder(
                item_id=path,
                provider=self.instance_id,
                children=[Album.from_dict(album.to_dict()) for album in albums]
            )

        return BrowseFolder(item_id=path, provider=self.instance_id, children=[])

    @property
    def supported_features(self) -> set[ProviderFeature]:
        return {
            ProviderFeature.BROWSE,
            ProviderFeature.SEARCH,
            ProviderFeature.STREAM,
            ProviderFeature.LIBRARY_ALBUMS,
            ProviderFeature.ALBUMS,
            ProviderFeature.TRACKS,
        }
