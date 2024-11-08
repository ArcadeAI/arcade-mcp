from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional


@dataclass
class PlaybackState:
    is_playing: Optional[bool] = None
    progress_ms: Optional[int] = (
        None  # Progress into the currently playing track or episode in milliseconds
    )
    device_name: Optional[str] = None
    device_id: Optional[str] = None
    currently_playing_type: Optional[str] = None
    album_id: Optional[str] = None
    album_name: Optional[str] = None
    album_artists: list[str] = field(default_factory=list)
    album_spotify_url: Optional[str] = None
    track_id: Optional[str] = None
    track_name: Optional[str] = None
    track_spotify_url: Optional[str] = None
    track_artists: list[str] = field(default_factory=list)
    track_artists_ids: list[str] = field(default_factory=list)
    show_id: Optional[str] = None
    show_spotify_url: Optional[str] = None
    episode_name: Optional[str] = None
    episode_spotify_url: Optional[str] = None
    message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert the PlaybackState instance to a dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None and v != []}


@dataclass
class Device:
    id: str
    is_active: bool
    is_private_session: bool
    is_restricted: bool
    name: str
    type: str
    volume_percent: int
    supports_volume: bool

    def to_dict(self) -> dict:
        """Convert the Device instance to a dictionary."""
        return asdict(self)


class SearchType(str, Enum):
    ALBUM = "album"
    ARTIST = "artist"
    PLAYLIST = "playlist"
    TRACK = "track"
    SHOW = "show"
    EPISODE = "episode"
    AUDIOBOOK = "audiobook"
