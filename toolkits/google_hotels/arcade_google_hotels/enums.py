from enum import Enum


class GoogleHotelsSortBy(Enum):
    RELEVANCE = "RELEVANCE"
    LOWEST_PRICE = "LOWEST_PRICE"
    HIGHEST_RATING = "HIGHEST_RATING"
    MOST_REVIEWED = "MOST_REVIEWED"

    def to_api_value(self) -> int | None:
        _map = {
            "RELEVANCE": None,
            "LOWEST_PRICE": 3,
            "HIGHEST_RATING": 8,
            "MOST_REVIEWED": 13,
        }
        return _map[self.value]
