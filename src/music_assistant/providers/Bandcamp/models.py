from __future__ import annotations

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

"""Bandcamp provider data models."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BandcampUserIdentity:
    """Represent Bandcamp user identity."""
    fan_id: Optional[int] = None
    username: Optional[str] = None
    name: Optional[str] = None
    image_id: Optional[str] = None
    url: Optional[str] = None
    is_authenticated: bool = False
    
    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> 'BandcampUserIdentity':
        """Create user identity from API data."""
        if not data:
            return cls()
        
        return cls(
            fan_id=data.get("fan_id"),
            username=data.get("username"),
            name=data.get("name"),
            image_id=data.get("image_id"),
            url=data.get("url"),
            is_authenticated=bool(data.get("fan_id"))
        )


@dataclass
class BandcampArtist:
    """Represent a Bandcamp artist."""
    artist_id: str
    name: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    
    
@dataclass
class BandcampAlbum:
    """Represent a Bandcamp album."""
    album_id: str
    title: str
    artist_name: str
    artist_id: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    release_date: Optional[str] = None
    tracks: List['BandcampTrack'] = field(default_factory=list)


@dataclass
class BandcampTrack:
    """Represent a Bandcamp track."""
    track_id: str
    title: str
    artist_name: str
    duration: int = 0  # In milliseconds
    artist_id: Optional[str] = None
    album_id: Optional[str] = None
    album_title: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    track_number: Optional[int] = None
    stream_url: Optional[str] = None


@dataclass
class BandcampPlaylist:
    """Represent a Bandcamp collection/wishlist as a playlist."""
    playlist_id: str
    name: str
    owner_name: str
    description: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    tracks: List[BandcampTrack] = field(default_factory=list)
