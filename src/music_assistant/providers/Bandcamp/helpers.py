"""
Helper methods for Bandcamp provider with cookie-based authentication.

Based on the LMS Bandcamp plugin's logic and adapted for MusicAssistant.
"""

import aiohttp
from music_assistant_models.errors import LoginFailed
from music_assistant_models.media_items import Album, Artist, Playlist, Track


class BandcampAPI:
    """Class to interact with Bandcamp."""

    API_BASE_URL = "https://bandcamp.com"
    TEST_URL = "https://bandcamp.com/api/account/current"

    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.authenticated = False

    async def authenticate(self, cookie: str) -> bool:
        """Authenticate with Bandcamp using a session cookie."""
        headers = {"Cookie": cookie}
        async with self.session.get(self.TEST_URL, headers=headers) as response:
            if response.status == 200:
                self.authenticated = True
                return True
            raise LoginFailed("Failed to authenticate with Bandcamp. Invalid session cookie.")

    async def get_library_artists(self) -> list[Artist]:
        """Retrieve library artists."""
        if not self.authenticated:
            raise LoginFailed("Not authenticated")
        async with self.session.get(f"{self.API_BASE_URL}/library_artists") as resp:
            data = await resp.json()
            return [
                Artist(
                    item_id=artist["id"],
                    name=artist["name"],
                    provider="bandcamp",
                )
                for artist in data.get("artists", [])
            ]

    async def get_library_albums(self) -> list[Album]:
        """Retrieve library albums."""
        if not self.authenticated:
            raise LoginFailed("Not authenticated")
        async with self.session.get(f"{self.API_BASE_URL}/library_albums") as resp:
            data = await resp.json()
            return [
                Album(
                    item_id=album["id"],
                    name=album["title"],
                    artists=[Artist(item_id=album["artist_id"], name=album["artist"])],
                    provider="bandcamp",
                )
                for album in data.get("albums", [])
            ]

    async def get_library_tracks(self) -> list[Track]:
        """Retrieve library tracks."""
        if not self.authenticated:
            raise LoginFailed("Not authenticated")
        async with self.session.get(f"{self.API_BASE_URL}/library_tracks") as resp:
            data = await resp.json()
            return [
                Track(
                    item_id=track["id"],
                    name=track["title"],
                    album=Album(item_id=track["album_id"], name=track["album"]),
                    artists=[Artist(item_id=track["artist_id"], name=track["artist"])],
                    provider="bandcamp",
                )
                for track in data.get("tracks", [])
            ]

    async def get_daily_shows(self) -> list[Playlist]:
        """Retrieve Bandcamp Daily shows."""
        async with self.session.get(f"{self.API_BASE_URL}/daily") as resp:
            data = await resp.json()
            return [
                Playlist(
                    item_id=show["id"],
                    name=show["name"],
                    provider="bandcamp",
                )
                for show in data.get("daily_list", [])
            ]

    async def get_daily_show(self, show_id: str) -> dict[str, list]:
        """Retrieve details of a specific Bandcamp Daily show."""
        async with self.session.get(f"{self.API_BASE_URL}/daily/{show_id}") as resp:
            data = await resp.json()
            return {
                "tracks": [
                    Track(
                        item_id=track["id"],
                        name=track["title"],
                        album=Album(item_id=track["album_id"], name=track["album"]),
                        artists=[Artist(item_id=track["artist_id"], name=track["artist"])],
                        provider="bandcamp",
                    )
                    for track in data.get("tracks", [])
                ],
                "albums": data.get("albums", []),
            }
