from dataclasses import asdict, dataclass, field
from enum import Enum


@dataclass
class PlaybackState:
    is_playing: bool | None = None
    progress_ms: int | None = (
        None  # Progress into the currently playing track or episode in milliseconds
    )
    device_name: str | None = None
    device_id: str | None = None
    currently_playing_type: str | None = None
    album_id: str | None = None
    album_name: str | None = None
    album_artists: list[str] = field(default_factory=list)
    album_spotify_url: str | None = None
    track_id: str | None = None
    track_name: str | None = None
    track_spotify_url: str | None = None
    track_artists: list[str] = field(default_factory=list)
    track_artists_ids: list[str] = field(default_factory=list)
    show_name: str | None = None
    show_id: str | None = None
    show_spotify_url: str | None = None
    episode_name: str | None = None
    episode_id: str | None = None
    episode_spotify_url: str | None = None
    message: str | None = None

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
