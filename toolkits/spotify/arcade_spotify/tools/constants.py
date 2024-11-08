SPOTIFY_BASE_URL = "https://api.spotify.com/v1"

ENDPOINTS = {
    "player_get_available_devices": "/me/player/devices",
    "player_get_playback_state": "/me/player",
    "player_get_currently_playing": "/me/player/currently-playing",
    "player_modify_playback": "/me/player/play",
    "player_pause_playback": "/me/player/pause",
    "player_skip_to_next": "/me/player/next",
    "player_skip_to_previous": "/me/player/previous",
    "player_seek_to_position": "/me/player/seek",
    "tracks_get_track": "/tracks/{track_id}",
    "tracks_get_recommendations": "/recommendations",
    "tracks_get_audio_features": "/audio-features",
    "search": "/search",
}
