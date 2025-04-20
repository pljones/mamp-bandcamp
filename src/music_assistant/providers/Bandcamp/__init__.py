"""
Bandcamp support for MusicAssistant with cookie-based login functionality.

Based on the LMS Bandcamp plugin (https://github.com/pljones/mamp-bandcamp/tree/main/herget.net/Bandcamp)
and the MusicAssistant YouTube plugin.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator, TYPE_CHECKING

from music_assistant.models.music_provider import MusicProvider
from music_assistant.models.config_entries import ConfigEntry, ConfigValueType
from music_assistant.models.enums import ConfigEntryType, ProviderFeature
from music_assistant.models.errors import LoginFailed
from music_assistant.models.media_items import (
    Album,
    Artist,
    MediaItemType,
    Playlist,
    SearchResults,
    Track,
)
from .helpers import BandcampAPI

if TYPE_CHECKING:
    from music_assistant import MusicAssistant
    from music_assistant.models import ProviderInstanceType
    from music_assistant.models.provider import ProviderManifest
    from music_assistant.models.config_entries import ProviderConfig


CONF_COOKIE = "cookie"

SUPPORTED_FEATURES = {
    ProviderFeature.LIBRARY_ARTISTS,
    ProviderFeature.LIBRARY_ALBUMS,
    ProviderFeature.LIBRARY_TRACKS,
    ProviderFeature.SEARCH,
    ProviderFeature.BROWSE,
}


async def setup(mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig) -> ProviderInstanceType:
    """Initialize Bandcamp provider with given configuration."""
    return BandcampProvider(mass, manifest, config)


async def get_config_entries(
    mass: MusicAssistant, instance_id: str | None = None, action: str | None = None, values: dict[str, ConfigValueType] | None = None
) -> tuple[ConfigEntry, ...]:
    """Return Config entries to setup this provider."""
    return (
        ConfigEntry(
            key=CONF_COOKIE,
            type=ConfigEntryType.SECURE_STRING,
            label="Bandcamp Session Cookie",
            required=True,
        ),
    )


class BandcampProvider(MusicProvider):
    """Provider for Bandcamp."""

    def __init__(self, mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig):
        """Initialize Bandcamp provider."""
        super().__init__(mass, manifest, config)
        self.api = BandcampAPI()
        self.cookie = config.get_value(CONF_COOKIE)
        self.logger = logging.getLogger(__name__)
        self.authenticated = False

    @property
    def supported_features(self) -> set[ProviderFeature]:
        """Return the features supported by this provider."""
        return SUPPORTED_FEATURES

    async def login(self) -> None:
        """Authenticate with Bandcamp using a session cookie."""
        self.logger.info("Authenticating to Bandcamp with provided session cookie...")
        try:
            self.authenticated = await self.api.authenticate(self.cookie)
            self.logger.info("Successfully authenticated to Bandcamp.")
        except LoginFailed as err:
            self.logger.error("Failed to authenticate to Bandcamp: %s", str(err))
            raise LoginFailed("Invalid Bandcamp session cookie") from err

    async def search(self, search_query: str, media_types: list[MediaItemType], limit: int = 5) -> SearchResults:
        """Perform search on Bandcamp."""
        await self._ensure_authenticated()
        results = await self.api.search(search_query, media_types, limit)
        return results

    async def get_library_artists(self) -> AsyncGenerator[Artist, None]:
        """Retrieve all library artists from Bandcamp."""
        await self._ensure_authenticated()
        artists = await self.api.get_library_artists()
        for artist in artists:
            yield artist

    async def get_library_albums(self) -> AsyncGenerator[Album, None]:
        """Retrieve all library albums from Bandcamp."""
        await self._ensure_authenticated()
        albums = await self.api.get_library_albums()
        for album in albums:
            yield album

    async def get_library_tracks(self) -> AsyncGenerator[Track, None]:
        """Retrieve all library tracks from Bandcamp."""
        await self._ensure_authenticated()
        tracks = await self.api.get_library_tracks()
        for track in tracks:
            yield track

    async def get_bandcamp_daily(self) -> list[Playlist]:
        """Fetch Bandcamp Daily as playlists."""
        await self._ensure_authenticated()
        return await self.api.get_daily_shows()

    async def get_bandcamp_daily_details(self, show_id: str) -> dict[str, list]:
        """Fetch details of a specific Bandcamp Daily show."""
        await self._ensure_authenticated()
        return await self.api.get_daily_show(show_id)

    async def _ensure_authenticated(self) -> None:
        """Ensure the user is authenticated before making API calls."""
        if not self.authenticated:
            await self.login()
