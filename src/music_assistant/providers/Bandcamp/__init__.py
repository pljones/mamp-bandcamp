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

Based on the LMS Bandcamp plugin (https://github.com/pljones/mamp-bandcamp/tree/main/herget.net/Bandcamp)
and partly on the MusicAssistant YouTube plugin, refactoring in line with current MusicAssistant
best practice and a structured coding approach proposed by Anthropic Claude.
"""

"""MusicAssistant Bandcamp Provider entry points."""

from .const import DOMAIN
from .provider import BandcampProvider

__all__ = ["DOMAIN", "BandcampProvider"]
