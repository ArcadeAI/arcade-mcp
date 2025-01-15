from unittest.mock import MagicMock

import pytest

from arcade_spotify.tools.models import PlaybackState
from arcade_spotify.tools.utils import convert_to_playback_state, send_spotify_request


@pytest.mark.asyncio
async def test_send_spotify_request(tool_context, mock_httpx_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx_client.request.return_value = mock_response

    response = await send_spotify_request(
        tool_context,
        "GET",
        "https://api.spotify.com/v1/me/player",
        params={"param": "value"},
        json_data={"data": "value"},
    )
    assert response == mock_response
    mock_httpx_client.request.assert_called_once_with(
        "GET",
        "https://api.spotify.com/v1/me/player",
        headers={"Authorization": "Bearer test_token"},
        params={"param": "value"},
        json={"data": "value"},
    )


def test_convert_to_playback_state():
    player_get_playback_state_response = {
        "timestamp": 1734651060828,
        "context": {
            "external_urls": {
                "spotify": "https://open.spotify.com/playlist/37i9dQZF1EYkqdzj48dyYq"
            },
            "href": "https://api.spotify.com/v1/playlists/37i9dQZF1EYkqdzj48dyYq",
            "type": "playlist",
            "uri": "spotify:playlist:37i9dQZF1EYkqdzj48dyYq",
        },
        "progress_ms": 261652,
        "item": {
            "album": {
                "album_type": "album",
                "artists": [
                    {
                        "external_urls": {
                            "spotify": "https://open.spotify.com/artist/3GBPw9NK25X1Wt2OUvOwY3"
                        },
                        "href": "https://api.spotify.com/v1/artists/3GBPw9NK25X1Wt2OUvOwY3",
                        "id": "3GBPw9NK25X1Wt2OUvOwY3",
                        "name": "Jack Johnson",
                        "type": "artist",
                        "uri": "spotify:artist:3GBPw9NK25X1Wt2OUvOwY3",
                    }
                ],
                "available_markets": [
                    "AR",
                    "XK",
                ],
                "external_urls": {
                    "spotify": "https://open.spotify.com/album/23BBbqDGMhloT6f2YBecSr"
                },
                "href": "https://api.spotify.com/v1/albums/23BBbqDGMhloT6f2YBecSr",
                "id": "23BBbqDGMhloT6f2YBecSr",
                "images": [
                    {
                        "height": 640,
                        "url": "https://i.scdn.co/image/ab67616d0000b2732bd026ab797a3de9605d9cb3",
                        "width": 640,
                    },
                    {
                        "height": 300,
                        "url": "https://i.scdn.co/image/ab67616d00001e022bd026ab797a3de9605d9cb3",
                        "width": 300,
                    },
                    {
                        "height": 64,
                        "url": "https://i.scdn.co/image/ab67616d000048512bd026ab797a3de9605d9cb3",
                        "width": 64,
                    },
                ],
                "name": "Brushfire Fairytales [Remastered (Bonus Version)]",
                "release_date": "2011-04-12",
                "release_date_precision": "day",
                "total_tracks": 15,
                "type": "album",
                "uri": "spotify:album:23BBbqDGMhloT6f2YBecSr",
            },
            "artists": [
                {
                    "external_urls": {
                        "spotify": "https://open.spotify.com/artist/3GBPw9NK25X1Wt2OUvOwY3"
                    },
                    "href": "https://api.spotify.com/v1/artists/3GBPw9NK25X1Wt2OUvOwY3",
                    "id": "3GBPw9NK25X1Wt2OUvOwY3",
                    "name": "Jack Johnson",
                    "type": "artist",
                    "uri": "spotify:artist:3GBPw9NK25X1Wt2OUvOwY3",
                }
            ],
            "available_markets": [
                "AR",
                "XK",
            ],
            "disc_number": 1,
            "duration_ms": 281749,
            "explicit": False,
            "external_ids": {"isrc": "USER81100105"},
            "external_urls": {"spotify": "https://open.spotify.com/track/54S3uCvfZauNw8lVCHZYYo"},
            "href": "https://api.spotify.com/v1/tracks/54S3uCvfZauNw8lVCHZYYo",
            "id": "54S3uCvfZauNw8lVCHZYYo",
            "is_local": False,
            "name": "Flake",
            "popularity": 59,
            "preview_url": "https://p.scdn.co/mp3-preview/7094898f5aa76222b06349e4ec26489ca80b5e4f?cid=26913f34d26f4c16a15d5a93e309a1dc",
            "track_number": 5,
            "type": "track",
            "uri": "spotify:track:54S3uCvfZauNw8lVCHZYYo",
        },
        "currently_playing_type": "track",
        "actions": {
            "disallows": {
                "resuming": True,
                "toggling_repeat_context": True,
                "toggling_repeat_track": True,
                "toggling_shuffle": True,
            }
        },
        "is_playing": True,
    }

    expected_playback_state = PlaybackState(
        device_name=None,
        device_id=None,
        currently_playing_type="track",
        is_playing=True,
        progress_ms=261652,
        message=None,
        album_name="Brushfire Fairytales [Remastered (Bonus Version)]",
        album_id="23BBbqDGMhloT6f2YBecSr",
        album_artists=["Jack Johnson"],
        album_spotify_url="https://open.spotify.com/album/23BBbqDGMhloT6f2YBecSr",
        track_name="Flake",
        track_id="54S3uCvfZauNw8lVCHZYYo",
        track_spotify_url="https://open.spotify.com/track/54S3uCvfZauNw8lVCHZYYo",
        track_artists=["Jack Johnson"],
        track_artists_ids=["3GBPw9NK25X1Wt2OUvOwY3"],
    )

    playback_state = convert_to_playback_state(player_get_playback_state_response)

    assert playback_state == expected_playback_state
