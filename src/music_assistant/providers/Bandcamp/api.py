"""
Bandcamp support for MusicAssistant.
Copyright (C) 2025 Peter L Jones <peter@drealm.info>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

"""Bandcamp API client."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup

from music_assistant.common.models.errors import LoginFailed, MediaNotFoundError
from music_assistant.helpers.auth import AuthenticationHelper
from music_assistant.server.helpers.app_vars import app_var

from .const import BANDCAMP_API_URL, BANDCAMP_HTML_URL, DEFAULT_TIMEOUT
from .models import BandcampAlbum, BandcampArtist, BandcampTrack, BandcampUserIdentity

LOGGER = logging.getLogger(__name__)

# Regular expressions for parsing data
PLAY_INFO_REGEX = re.compile(r'data-tralbum="([^"]*)"')
PLAY_DATA_REGEX = re.compile(r"data-tralbum\s*:\s*({.*})")
USER_DATA_REGEX = re.compile(r"var UserData\s*=\s*({.*?});", re.DOTALL)


class BandcampApiClient:
    """Client to interact with Bandcamp's API and website, with support for multiple instances."""

    def __init__(self, domain: str, instance_id: str):
        """Initialize the API client."""
        self.domain = domain
        self.instance_id = instance_id
        self.session = aiohttp.ClientSession()
        self.user_identity = BandcampUserIdentity()
        self._authenticating = False
        self._auth_lock = asyncio.Lock()
        self.auth_helper = AuthenticationHelper()
        
        # Directory for storing instance-specific cookie file
        self.user_data_dir = os.path.join(app_var.USER_DATA_DIR, f"{self.domain}_{self.instance_id}")
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.cookie_file = os.path.join(self.user_data_dir, "cookies.json")

    async def authenticate_with_cookies(self, auth_token: Optional[str] = None) -> bool:
        """Authenticate with saved cookies or provided auth token using AuthenticationHelper."""
        try:
            async with self.auth_helper.start_session():
                if auth_token:
                    LOGGER.info("Using provided auth token for Bandcamp authentication")
                    self.auth_helper.set_cookie("identity", auth_token)
                else:
                    LOGGER.info("Trying to load cookies from file")
                    await self.auth_helper.load_cookies(self.cookie_file)

                # Verify login by checking user data
                user_data = await self.auth_helper.get_authenticated_user_data(self.session, BANDCAMP_HTML_URL)
                if user_data:
                    self.user_identity = BandcampUserIdentity.from_api_data(user_data)
                    await self.auth_helper.save_cookies(self.cookie_file)
                    LOGGER.info("Successfully authenticated with Bandcamp using cookies")
                    return True
                else:
                    LOGGER.warning("Failed to authenticate using cookies")
                    return False
        except Exception as exc:
            LOGGER.error("Authentication error with cookies: %s", str(exc))
            return False

    async def authenticate_with_credentials(self, username: str, password: str) -> bool:
        """Authenticate with username and password."""
        if self._authenticating or not username or not password:
            return False
        
        async with self._auth_lock:
        """Authenticate with username and password using AuthenticationHelper."""
        try:
            async with self.auth_helper.start_session():
                login_url = f"{BANDCAMP_HTML_URL}/login"
                LOGGER.info("Submitting user credentials to %s", login_url)

                # Submit credentials
                form_data = {
                    "user_session[login]": username,
                    "user_session[password]": password,
                    "user_session[remember_me]": "1",
                }
                user_data = await self.auth_helper.submit_form(self.session, login_url, form_data)
                if user_data:
                    self.user_identity = BandcampUserIdentity.from_api_data(user_data)
                    await self.auth_helper.save_cookies(self.cookie_file)
                    LOGGER.info("Successfully authenticated with Bandcamp using credentials")
                    return True
                else:
                    LOGGER.warning("Failed to authenticate using credentials")
                    return False
        except Exception as exc:
            LOGGER.error("Authentication error with credentials: %s", str(exc))
            return False

    async def close(self) -> None:
        """Close the API client and cleanup resources."""
        await self.session.close()

    async def get_collection_items(self) -> List[Dict[str, Any]]:
        """Get user's collection items."""
        if not self.user_identity.is_authenticated:
            return []
        
        fan_id = self.user_identity.fan_id
        if not fan_id:
            return []
        
        collection_url = f"{BANDCAMP_API_URL}/fan/{fan_id}/collection_items"
        items = []
        offset = 0
        
        try:
            while True:
                params = {
                    "fan_id": fan_id,
                    "older_than_token": offset,
                    "count": 100,
                }
                
                async with self.session.post(collection_url, json=params) as resp:
                    if resp.status != 200:
                        break
                    
                    data = await resp.json()
                    batch_items = data.get("items", [])
                    if not batch_items:
                        break
                    
                    items.extend(batch_items)
                    if len(batch_items) < 100:
                        break
                    
                    offset = data.get("last_token")
                    if not offset:
                        break
            
            return items
        
        except Exception as exc:
            LOGGER.error("Error getting collection: %s", str(exc))
            return []

    async def get_wishlist_items(self) -> List[Dict[str, Any]]:
        """Get user's wishlist items."""
        if not self.user_identity.is_authenticated:
            return []
        
        fan_id = self.user_identity.fan_id
        if not fan_id:
            return []
        
        wishlist_url = f"{BANDCAMP_API_URL}/fan/{fan_id}/wishlist_items"
        items = []
        offset = 0
        
        try:
            while True:
                params = {
                    "fan_id": fan_id,
                    "older_than_token": offset,
                    "count": 100,
                }
                
                async with self.session.post(wishlist_url, json=params) as resp:
                    if resp.status != 200:
                        break
                    
                    data = await resp.json()
                    batch_items = data.get("items", [])
                    if not batch_items:
                        break
                    
                    items.extend(batch_items)
                    if len(batch_items) < 100:
                        break
                    
                    offset = data.get("last_token")
                    if not offset:
                        break
            
            return items
        
        except Exception as exc:
            LOGGER.error("Error getting wishlist: %s", str(exc))
            return []

    async def get_followed_artists(self) -> List[Dict[str, Any]]:
        """Get user's followed artists."""
        if not self.user_identity.is_authenticated:
            return []
        
        fan_id = self.user_identity.fan_id
        if not fan_id:
            return []
        
        following_url = f"{BANDCAMP_API_URL}/fan/{fan_id}/following_bands"
        artists = []
        offset = 0
        
        try:
            while True:
                params = {
                    "fan_id": fan_id,
                    "older_than_token": offset,
                    "count": 100,
                }
                
                async with self.session.post(following_url, json=params) as resp:
                    if resp.status != 200:
                        break
                    
                    data = await resp.json()
                    batch_items = data.get("followeers", [])
                    if not batch_items:
                        break
                    
                    artists.extend(batch_items)
                    if len(batch_items) < 100:
                        break
                    
                    offset = data.get("last_token")
                    if not offset:
                        break
            
            return artists
        
        except Exception as exc:
            LOGGER.error("Error getting followed artists: %s", str(exc))
            return []

    async def search(self, query: str, limit: int = 10) -> Tuple[List[BandcampArtist], List[BandcampAlbum], List[BandcampTrack]]:
        """Search Bandcamp for artists, albums and tracks."""
        search_url = f"{BANDCAMP_HTML_URL}/search"
        params = {"q": query, "page": 1}
        
        artists = []
        albums = []
        tracks = []
        
        try:
            async with self.session.get(search_url, params=params) as resp:
                if resp.status != 200:
                    return [], [], []
                
                html = await resp.text()
            
            soup = BeautifulSoup(html, "html.parser")
            
            # Parse artists
            artists_section = soup.find("li", {"class": "band"})
            if artists_section:
                artist_items = artists_section.find_all("li", {"class": "searchresult"})
                for item in artist_items[:limit]:
                    try:
                        artist_name = item.find("div", {"class": "heading"}).find("a").text.strip()
                        artist_url = item.find("div", {"class": "heading"}).find("a")["href"]
                        artist_id = artist_url.split("/")[-1]
                        
                        artist = BandcampArtist(
                            artist_id=artist_id,
                            name=artist_name,
                            url=artist_url,
                        )
                        
                        # Check for image
                        img_tag = item.find("div", {"class": "art"}).find("img")
                        if img_tag and img_tag.get("src"):
                            artist.image_url = img_tag["src"]
                        
                        artists.append(artist)
                    except Exception as exc:
                        LOGGER.debug("Error parsing artist result: %s", exc)
            
            # Parse albums
            albums_section = soup.find("li", {"class": "album"})
            if albums_section:
                album_items = albums_section.find_all("li", {"class": "searchresult"})
                for item in album_items[:limit]:
                    try:
                        album_name = item.find("div", {"class": "heading"}).find("a").text.strip()
                        album_url = item.find("div", {"class": "heading"}).find("a")["href"]
                        album_id = album_url.split("/")[-1]
                        artist_name = item.find("div", {"class": "subhead"}).find("a").text.strip()
                        artist_url = item.find("div", {"class": "subhead"}).find("a")["href"]
                        artist_id = artist_url.split("/")[-1]
                        
                        album = BandcampAlbum(
                            album_id=album_id,
                            title=album_name,
                            artist_name=artist_name,
                            artist_id=artist_id,
                            url=album_url,
                        )
                        
                        # Check for image
                        img_tag = item.find("div", {"class": "art"}).find("img")
                        if img_tag and img_tag.get("src"):
                            album.image_url = img_tag["src"]
                        
                        albums.append(album)
                    except Exception as exc:
                        LOGGER.debug("Error parsing album result: %s", exc)
            
            # Parse tracks
            tracks_section = soup.find("li", {"class": "track"})
            if tracks_section:
                track_items = tracks_section.find_all("li", {"class": "searchresult"})
                for item in track_items[:limit]:
                    try:
                        track_name = item.find("div", {"class": "heading"}).find("a").text.strip()
                        track_url = item.find("div", {"class": "heading"}).find("a")["href"]
                        track_id = track_url.split("/")[-1]
                        artist_name = item.find("div", {"class": "subhead"}).find("a").text.strip()
                        artist_url = item.find("div", {"class": "subhead"}).find("a")["href"]
                        artist_id = artist_url.split("/")[-1]
                        
                        # Get album info if available
                        album_name = None
                        album_id = None
                        album_link = item.find("div", {"class": "itemsubtext"}).find("a")
                        if album_link:
                            album_name = album_link.text.strip()
                            album_url = album_link["href"]
                            album_id = album_url.split("/")[-1]
                        
                        track = BandcampTrack(
                            track_id=track_id,
                            title=track_name,
                            artist_name=artist_name,
                            artist_id=artist_id,
                            album_title=album_name,
                            album_id=album_id,
                            url=track_url,
                        )
                        
                        # Check for image
                        img_tag = item.find("div", {"class": "art"}).find("img")
                        if img_tag and img_tag.get("src"):
                            track.image_url = img_tag["src"]
                        
                        tracks.append(track)
                    except Exception as exc:
                        LOGGER.debug("Error parsing track result: %s", exc)
        
        except Exception as exc:
            LOGGER.error("Error during search: %s", str(exc))
        
        return artists, albums, tracks

    async def get_album(self, album_id: str) -> Optional[BandcampAlbum]:
        """Get album details from Bandcamp."""
        try:
            if "/" in album_id:
                parts = album_id.split("/")
                artist_slug = parts[0]
                album_slug = parts[1]
                album_url = f"https://{artist_slug}.bandcamp.com/album/{album_slug}"
            else:
                # Try to find the album URL
                artists, albums, _ = await self.search(album_id, limit=1)
                if albums:
                    album_url = albums[0].url
                else:
                    return None
            
            async with self.session.get(album_url) as resp:
                if resp.status != 200:
                    return None
                
                html = await resp.text()
            
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract album details
            album_name = soup.find("h2", {"class": "trackTitle"}).text.strip()
            artist_name = soup.find("span", {"itemprop": "byArtist"}).text.strip()
            artist_url = soup.find("span", {"itemprop": "byArtist"}).find("a")["href"]
            artist_id = artist_url.split("/")[-1]
            
            # Create the album
            album = BandcampAlbum(
                album_id=album_id,
                title=album_name,
                artist_name=artist_name,
                artist_id=artist_id,
                url=album_url,
            )
            
            # Get album art
            art_tag = soup.find("div", {"id": "tralbumArt"}).find("img")
            if art_tag and art_tag.get("src"):
                album.image_url = art_tag["src"]
            
            # Extract album tracks
            play_data_match = PLAY_DATA_REGEX.search(html)
            if play_data_match:
                play_data_str = play_data_match.group(1)
                play_data_str = play_data_str.replace("&quot;", '"').replace("\\&quot;", '\\"')
                play_data = json.loads(play_data_str)
                
                # Add release date if available
                if play_data.get("album_release_date"):
                    try:
                        release_date = datetime.fromtimestamp(play_data.get("album_release_date")).date()
                        album.release_date = release_date.isoformat()
                    except Exception:
                        pass
                
                # Get tracks
                tracks_info = play_data.get("trackinfo", [])
                
                # Parse tracks
                for idx, track_info in enumerate(tracks_info, 1):
                    track_id = f"{album_id}/{track_info.get('title', '').replace(' ', '-').lower()}"
                    track = BandcampTrack(
                        track_id=track_id,
                        title=track_info.get("title", ""),
                        artist_name=artist_name,
                        artist_id=artist_id,
                        album_id=album_id,
                        album_title=album_name,
                        url=f"{album_url}/track/{track_id.split('/')[-1]}",
                        track_number=idx,
                        duration=int(track_info.get("duration", 0) * 1000),  # Convert to ms
                    )
                    
                    if album.image_url:
                        track.image_url = album.image_url
                    
                    # Check if stream URL is available directly
                    file_info = track_info.get("file", {})
                    if file_info:
                        if file_info.get("mp3-v0"):
                            track.stream_url = file_info.get("mp3-v0")
                        elif file_info.get("mp3-320"):
                            track.stream_url = file_info.get("mp3-320")
                        elif file_info.get("mp3-128"):
                            track.stream_url = file_info.get("mp3-128")
                        elif file_info.get("flac"):
                            track.stream_url = file_info.get("flac")
                    
                    album.tracks.append(track)
            
            return album
        
        except Exception as exc:
            LOGGER.error("Error getting album: %s", str(exc))
            return None

    async def get_artist(self, artist_id: str) -> Optional[BandcampArtist]:
        """Get artist details from Bandcamp."""
        try:
            if "." in artist_id and "/" not in artist_id:
                artist_url = f"https://{artist_id}.bandcamp.com"
            else:
                # Try to find the artist URL from search
                artists, _, _ = await self.search(artist_id, limit=1)
                if artists:
                    artist_url = artists[0].url
                else:
                    return None
            
            async with self.session.get(artist_url) as resp:
                if resp.status != 200:
                    return None
                
                html = await resp.text()
            
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract artist details
            artist_name = soup.find("p", {"id": "band-name-location"}).find("span", {"class": "title"}).text.strip()
            
            # Create the artist
            artist = BandcampArtist(
                artist_id=artist_id,
                name=artist_name,
                url=artist_url,
            )
            
            # Get artist image
            art_tag = soup.find("div", {"id": "bio-container"}).find("img")
            if art_tag and art_tag.get("src"):
                artist.image_url = art_tag["src"]
            
            # Get artist bio
            bio_element = soup.find("div", {"class": "bio-text"})
            if bio_element:
                artist.bio = bio_element.text.strip()
            
            # Get artist location
            location_element = soup.find("p", {"id": "band-name-location"}).find("span", {"class": "location"})
            if location_element:
                artist.location = location_element.text.strip()
            
            return artist
        
        except Exception as exc:
            LOGGER.error("Error getting artist: %s", str(exc))
            return None

    async def get_artist_albums(self, artist_id: str) -> List[BandcampAlbum]:
        """Get albums for an artist."""
        try:
            if "." in artist_id and "/" not in artist_id:
                artist_url = f"https://{artist_id}.bandcamp.com"
            else:
                # Try to find the artist URL from search
                artists, _, _ = await self.search(artist_id, limit=1)
                if artists:
                    artist_url = artists[0].url
                else:
                    return []
            
            async with self.session.get(artist_url) as resp:
                if resp.status != 200:
                    return []
                
                html = await resp.text()
            
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract artist name
            artist_name = soup.find("p", {"id": "band-name-location"}).find("span", {"class": "title"}).text.strip()
            
            # Find all albums
            albums = []
            album_elements = soup.find_all("li", {"class": "music-grid-item"})
            
            for album_element in album_elements:
                try:
                    title_element = album_element.find("p", {"class": "title"})
                    if not title_element:
                        continue
                        
                    album_title = title_element.text.strip()
                    album_url = album_element.find("a")["href"]
                    album_id = album_url.split("/")[-1]
                    
                    album = BandcampAlbum(
                        album_id=album_id,
                        title=album_title,
                        artist_name=artist_name,
                        artist_id=artist_id,
                        url=album_url if album_url.startswith("http") else f"{artist_url}{album_url}",
                    )
                    
                    # Get album art
                    img_tag = album_element.find("div", {"class": "art"}).find("img")
                    if img_tag and img_tag.get("src"):
                        album.image_url = img_tag["src"]
                    
                    albums.append(album)
                except Exception as exc:
                    LOGGER.debug("Error parsing artist album: %s", exc)
            
            return albums
        
        except Exception as exc:
            LOGGER.error("Error getting artist albums: %s", str(exc))
            return []

    async def get_track_stream_url(self, track_id: str, track_url: Optional[str] = None) -> Optional[Tuple[str, str]]:
        """Get the stream URL for a track."""
        try:
            if not track_url:
                if "/" in track_id:
                    parts = track_id.split("/")
                    artist_slug = parts[0] 
                    track_slug = parts[-1]
                    # Determine if this is an album track or standalone track
                    if len(parts) == 3:  # artist/album/track format
                        album_slug = parts[1]
                        track_url = f"https://{artist_slug}.bandcamp.com/album/{album_slug}/track/{track_slug}"
                    else:  # artist/track format
                        track_url = f"https://{artist_slug}.bandcamp
