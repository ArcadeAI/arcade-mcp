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
    "search": "/search",
}

RESPONSE_MSGS = {
    "artist_not_found": "Artist '{artist_name}' not found",
    "track_not_found": "Track '{track_name}' not found",
    "no_track_to_adjust_position": "No track to adjust position",
    "playback_position_adjusted": "Playback position adjusted",
    "no_track_to_go_back_to": "No track to go back to",
    "playback_skipped_to_previous_track": "Playback skipped to previous track",
    "no_track_to_skip": "No track to skip",
    "playback_skipped_to_next_track": "Playback skipped to next track",
    "playback_paused": "Playback paused",
    "playback_resumed": "Playback resumed",
    "no_track_to_resume": "No track to resume",
    "no_track_to_pause": "No track to pause",
    "no_track_to_play": "No track to play",
    "no_available_devices": "No available devices",
    "track_is_already_paused": "Track is already paused",
    "track_is_already_playing": "Track is already playing",
    "playback_started": "Playback started",
    "no_active_device": "Cannot start playback because no active device is available",
}
