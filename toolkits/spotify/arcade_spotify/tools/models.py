from dataclasses import asdict, dataclass, field
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
    track_artists: list[str] = field(default_factory=list)
    show_id: Optional[str] = None
    show_spotify_url: Optional[str] = None
    episode_name: Optional[str] = None
    episode_spotify_url: Optional[str] = None
    message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert the PlaybackState instance to a dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None and v != []}
