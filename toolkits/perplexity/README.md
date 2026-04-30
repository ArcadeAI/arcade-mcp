# Arcade Perplexity Toolkit

Arcade.dev LLM tools for searching the web with the
[Perplexity Search API](https://docs.perplexity.ai/api-reference/search-post).

## Tools

- `search` — issue a query against `POST https://api.perplexity.ai/search`
  and return a list of results, each containing `title`, `url`, and
  `snippet`.

## Configuration

The toolkit requires a single secret:

| Secret | Description |
| --- | --- |
| `PERPLEXITY_API_KEY` | Your Perplexity API key (sent as `Authorization: Bearer ...`). |

Every outgoing request includes an `X-Pplx-Integration: arcade/<version>`
header so Perplexity can attribute traffic to this integration.

## Inputs

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `query` | string | — | The search query. |
| `max_results` | int | `5` | Clamped to `[1, 20]`. |
| `search_recency_filter` | enum | — | One of `hour`, `day`, `week`, `month`, `year`. |

## Output

```python
[
    {"title": "...", "url": "https://...", "snippet": "..."},
    ...
]
```

## Development

```bash
make install-local
make test
```
