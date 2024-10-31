from arcade_spotify.tools.tracks import (
    get_recommendations,
    get_track_from_id,
    get_tracks_audio_features,
)

from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    tool_eval,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_tool(get_track_from_id, "Spotify")
catalog.add_tool(get_recommendations, "Spotify")
catalog.add_tool(get_tracks_audio_features, "Spotify")

# This history is a conversation where the user asks for the currently playing song, and then asks for information about it.
history = [
    {"role": "user", "content": "what song is playing rn"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_fqZHT1DNcil1pbIv6UbOWVq9",
                "type": "function",
                "function": {"name": "Spotify_GetCurrentlyPlaying", "arguments": "{}"},
            }
        ],
    },
    {
        "role": "tool",
        "content": '{"album_artists":["Gajaka"],"album_id":"7b5h7MJ70KC92FrwSvRaQi","album_name":"Aerial","album_spotify_url":"https://open.spotify.com/album/7b5h7MJ70KC92FrwSvRaQi","currently_playing_type":"track","is_playing":true,"progress_ms":96962,"track_artists":["Gajaka"],"track_id":"03gaqN3aWm9TQxuHay0G8R","track_name":"Aerial"}',
        "tool_call_id": "call_fqZHT1DNcil1pbIv6UbOWVq9",
        "name": "Spotify_GetCurrentlyPlaying",
    },
    {
        "role": "assistant",
        "content": 'The song currently playing is "Aerial" by Gajaka. You can listen to it on Spotify [here](https://open.spotify.com/album/7b5h7MJ70KC92FrwSvRaQi).',
    },
]

# This history is a conversation where the user asks for the currently playing song, and then asks to skip to the next song, and then asks for information about the new song.
history_2 = [
    {"role": "user", "content": "what song is playing right now?"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_u2nS7hd7ETdbjElHW4mrFphd",
                "type": "function",
                "function": {"name": "Spotify_GetCurrentlyPlaying", "arguments": "{}"},
            }
        ],
    },
    {
        "role": "tool",
        "content": '{"album_artists":["The Dawning"],"album_id":"2dmrP48hhdCIoxeYJFMSVO","album_name":"summer breeze","album_spotify_url":"https://open.spotify.com/album/2dmrP48hhdCIoxeYJFMSVO","currently_playing_type":"track","is_playing":true,"progress_ms":144092,"track_artists":["The Dawning"],"track_id":"14CQdqVFygEls6szbfwuTL","track_name":"summer breeze"}',
        "tool_call_id": "call_u2nS7hd7ETdbjElHW4mrFphd",
        "name": "Spotify_GetCurrentlyPlaying",
    },
    {
        "role": "assistant",
        "content": 'The song "summer breeze" by The Dawning is currently playing. You can check it out on [Spotify](https://open.spotify.com/album/2dmrP48hhdCIoxeYJFMSVO).',
    },
    {"role": "user", "content": "please skip this song"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_htECRssaXZ4jtNvjdUY2r3ml",
                "type": "function",
                "function": {"name": "Spotify_SkipToNextTrack", "arguments": "{}"},
            }
        ],
    },
    {
        "role": "tool",
        "content": '{"album_artists":["Philó"],"album_id":"525aF5PKAQXzbmP7oAb0gC","album_name":"Skylar","album_spotify_url":"https://open.spotify.com/album/525aF5PKAQXzbmP7oAb0gC","currently_playing_type":"track","device_id":"84b6aa89387cfe3e132465001647027bfd1b44f3","device_name":"iPhone","is_playing":true,"progress_ms":233,"track_artists":["Philó"],"track_id":"5r9fTbn6YZVxHKaU4Rze3t","track_name":"Tempestade"}',
        "tool_call_id": "call_htECRssaXZ4jtNvjdUY2r3ml",
        "name": "Spotify_SkipToNextTrack",
    },
    {
        "role": "assistant",
        "content": 'I\'ve skipped to the next song. Now playing: "Tempestade" by Philó. You can listen to it on [Spotify](https://open.spotify.com/album/525aF5PKAQXzbmP7oAb0gC).',
    },
    {"role": "user", "content": "now what song is playing?"},
    {"role": "assistant", "content": 'The song now playing is "Tempestade" by Philó.'},
]

# This history is a conversation where the user asks for what is currently playing, and then asks for more information about the track, then asks for the audio features for the track.
history_3 = [
    {"role": "user", "content": "get info about 14CQdqVFygEls6szbfwuTL"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_bFqQIQY89z82BXJqSXhlkiro",
                "type": "function",
                "function": {
                    "name": "Spotify_GetTrackFromId",
                    "arguments": '{"track_id":"14CQdqVFygEls6szbfwuTL"}',
                },
            }
        ],
    },
    {
        "role": "tool",
        "content": '{"album":{"album_type":"single","artists":[{"external_urls":{"spotify":"https://open.spotify.com/artist/4ev14fn325vhWuykve3QtA"},"href":"https://api.spotify.com/v1/artists/4ev14fn325vhWuykve3QtA","id":"4ev14fn325vhWuykve3QtA","name":"The Dawning","type":"artist","uri":"spotify:artist:4ev14fn325vhWuykve3QtA"}],"available_markets":["AR","AU","AT","BE","BO","BR","BG","CA","CL","CO","CR","CY","CZ","DK","DO","DE","EC","EE","SV","FI","FR","GR","GT","HN","HK","HU","IS","IE","IT","LV","LT","LU","MY","MT","MX","NL","NZ","NI","NO","PA","PY","PE","PH","PL","PT","SG","SK","ES","SE","CH","TW","TR","UY","US","GB","AD","LI","MC","ID","JP","TH","VN","RO","IL","ZA","SA","AE","BH","QA","OM","KW","EG","MA","DZ","TN","LB","JO","PS","IN","BY","KZ","MD","UA","AL","BA","HR","ME","MK","RS","SI","KR","BD","PK","LK","GH","KE","NG","TZ","UG","AG","AM","BS","BB","BZ","BT","BW","BF","CV","CW","DM","FJ","GM","GE","GD","GW","GY","HT","JM","KI","LS","LR","MW","MV","ML","MH","FM","NA","NR","NE","PW","PG","PR","WS","SM","ST","SN","SC","SL","SB","KN","LC","VC","SR","TL","TO","TT","TV","VU","AZ","BN","BI","KH","CM","TD","KM","GQ","SZ","GA","GN","KG","LA","MO","MR","MN","NP","RW","TG","UZ","ZW","BJ","MG","MU","MZ","AO","CI","DJ","ZM","CD","CG","IQ","LY","TJ","VE","ET","XK"],"external_urls":{"spotify":"https://open.spotify.com/album/2dmrP48hhdCIoxeYJFMSVO"},"href":"https://api.spotify.com/v1/albums/2dmrP48hhdCIoxeYJFMSVO","id":"2dmrP48hhdCIoxeYJFMSVO","images":[{"height":640,"url":"https://i.scdn.co/image/ab67616d0000b2730046525154a4201332796065","width":640},{"height":300,"url":"https://i.scdn.co/image/ab67616d00001e020046525154a4201332796065","width":300},{"height":64,"url":"https://i.scdn.co/image/ab67616d000048510046525154a4201332796065","width":64}],"name":"summer breeze","release_date":"2024-08-02","release_date_precision":"day","total_tracks":1,"type":"album","uri":"spotify:album:2dmrP48hhdCIoxeYJFMSVO"},"artists":[{"external_urls":{"spotify":"https://open.spotify.com/artist/4ev14fn325vhWuykve3QtA"},"href":"https://api.spotify.com/v1/artists/4ev14fn325vhWuykve3QtA","id":"4ev14fn325vhWuykve3QtA","name":"The Dawning","type":"artist","uri":"spotify:artist:4ev14fn325vhWuykve3QtA"}],"available_markets":["AR","AU","AT","BE","BO","BR","BG","CA","CL","CO","CR","CY","CZ","DK","DO","DE","EC","EE","SV","FI","FR","GR","GT","HN","HK","HU","IS","IE","IT","LV","LT","LU","MY","MT","MX","NL","NZ","NI","NO","PA","PY","PE","PH","PL","PT","SG","SK","ES","SE","CH","TW","TR","UY","US","GB","AD","LI","MC","ID","JP","TH","VN","RO","IL","ZA","SA","AE","BH","QA","OM","KW","EG","MA","DZ","TN","LB","JO","PS","IN","BY","KZ","MD","UA","AL","BA","HR","ME","MK","RS","SI","KR","BD","PK","LK","GH","KE","NG","TZ","UG","AG","AM","BS","BB","BZ","BT","BW","BF","CV","CW","DM","FJ","GM","GE","GD","GW","GY","HT","JM","KI","LS","LR","MW","MV","ML","MH","FM","NA","NR","NE","PW","PG","PR","WS","SM","ST","SN","SC","SL","SB","KN","LC","VC","SR","TL","TO","TT","TV","VU","AZ","BN","BI","KH","CM","TD","KM","GQ","SZ","GA","GN","KG","LA","MO","MR","MN","NP","RW","TG","UZ","ZW","BJ","MG","MU","MZ","AO","CI","DJ","ZM","CD","CG","IQ","LY","TJ","VE","ET","XK"],"disc_number":1,"duration_ms":165811,"explicit":false,"external_ids":{"isrc":"SE69N2406255"},"external_urls":{"spotify":"https://open.spotify.com/track/14CQdqVFygEls6szbfwuTL"},"href":"https://api.spotify.com/v1/tracks/14CQdqVFygEls6szbfwuTL","id":"14CQdqVFygEls6szbfwuTL","is_local":false,"name":"summer breeze","popularity":60,"preview_url":"https://p.scdn.co/mp3-preview/9b2ac80563d092f9b1d442f09635ccf646ccb3e0?cid=26913f34d26f4c16a15d5a93e309a1dc","track_number":1,"type":"track","uri":"spotify:track:14CQdqVFygEls6szbfwuTL"}',
        "tool_call_id": "call_bFqQIQY89z82BXJqSXhlkiro",
        "name": "Spotify_GetTrackFromId",
    },
    {
        "role": "assistant",
        "content": 'The track "Summer Breeze" by The Dawning is available on Spotify. Here are some details about the track:\n\n- **Artist:** [The Dawning](https://open.spotify.com/artist/4ev14fn325vhWuykve3QtA)\n- **Album:** [Summer Breeze](https://open.spotify.com/album/2dmrP48hhdCIoxeYJFMSVO) (Single)\n- **Release Date:** August 2, 2024\n- **Duration:** 2 minutes and 45 seconds\n- **Popularity:** 60\n- **ISRC:** SE69N2406255\n- **Explicit Content:** No\n\nThe track is available in numerous markets, including the US, UK, Canada, Australia, and many more. You can listen to a preview of the track [here](https://p.scdn.co/mp3-preview/9b2ac80563d092f9b1d442f09635ccf646ccb3e0?cid=26913f34d26f4c16a15d5a93e309a1dc).',
    },
]


@tool_eval()
def spotify_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Spotify "track" tools."""
    suite = EvalSuite(
        name="Spotify Tools Evaluation",
        system_message="You are an AI assistant that can manage Spotify using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get information about a track",
        user_message="can you get more info about that song",
        expected_tool_calls=[
            (
                get_track_from_id,
                {
                    "track_id": "03gaqN3aWm9TQxuHay0G8R",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="track_id", weight=1.0),
        ],
        additional_messages=history,
    )

    suite.add_case(
        name="Get audio features for a track",
        user_message="what bpm is that song?",
        expected_tool_calls=[
            (
                get_tracks_audio_features,
                {
                    "track_ids": [
                        "14CQdqVFygEls6szbfwuTL",
                        "5r9fTbn6YZVxHKaU4Rze3t",
                    ]
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="track_id", weight=1.0),
        ],
        additional_messages=history_2,
    )

    suite.add_case(
        name="Get recommendations based on a specific track",
        user_message="Give me 6 recommendations based on this song.",
        expected_tool_calls=[
            (
                get_recommendations,
                {
                    "seed_artists": ["4ev14fn325vhWuykve3QtA"],
                    "seed_genres": [],  # None provided in the history
                    "seed_tracks": ["14CQdqVFygEls6szbfwuTL"],
                    "limit": 6,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="seed_artists", weight=0.3),
            BinaryCritic(critic_field="seed_genres", weight=0.3),
            BinaryCritic(critic_field="seed_tracks", weight=0.3),
        ],
        additional_messages=history_3,
    )

    return suite
