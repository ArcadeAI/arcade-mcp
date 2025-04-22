get_post_in_subreddit_messages = [
    {
        "role": "user",
        "content": "get 1 post from AskReddit that are contentious at this moment",
    },
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_ZjRic1hS43o10EjutTFgotBh",
                "type": "function",
                "function": {
                    "name": "Reddit_GetPostsInSubreddit",
                    "arguments": '{"subreddit":"AskReddit","listing":"controversial","time_range":"NOW","limit":1}',  # noqa: E501
                },
            }
        ],
    },
    {
        "role": "tool",
        "content": '{"cursor":"t3_1abcdef","posts":[{"author":"StewieGriffin","created_utc":1743457013,"id":"1abcdef","is_video":false,"name":"t3_1abcdef","num_comments":55,"permalink":"/r/AskReddit/comments/1abcdef/why_does_my_dog_have_four_legs/","score":2,"subreddit":"AskReddit","title":"Why does my dog have four legs?","upvote_ratio":0.55,"upvotes":2,"url":"https://www.reddit.com/r/AskReddit/comments/1abcdef/why_does_my_dog_have_four_legs/"}]}',  # noqa: E501
        "tool_call_id": "call_ZjRic1hS43o10EjutTFgotBh",
        "name": "Reddit_GetPostsInSubreddit",
    },
    {
        "role": "assistant",
        "content": "Here's a contentious post from AskReddit that is generating some discussion:\n\n**Title:** Why does my dog have four legs?\n\n- **Author:**StewieGriffin\n- **Score:** 2\n- **Upvote Ratio:** 55%\n- **Number of Comments:** 55\n- **Posted:**[Link](https://www.reddit.com/r/AskReddit/comments/1abcdef/why_does_my_dog_have_four_legs/)",  # noqa: E501
    },
]
