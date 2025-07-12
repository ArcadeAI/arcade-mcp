from enum import Enum


class WalmartSortBy(Enum):
    RELEVANCE = "relevance_according_to_keywords_searched"
    PRICE_LOW_TO_HIGH = "lowest_price_first"
    PRICE_HIGH_TO_LOW = "highest_price_first"
    BEST_SELLING = "best_selling_products_first"
    RATING_HIGH = "highest_rating_first"
    NEW_ARRIVALS = "new_arrivals_first"

    def to_api_value(self: "WalmartSortBy") -> str | None:
        _map = {
            str(self.RELEVANCE): None,
            str(self.PRICE_LOW_TO_HIGH): "price_low",
            str(self.PRICE_HIGH_TO_LOW): "price_high",
            str(self.BEST_SELLING): "best_seller",
            str(self.RATING_HIGH): "rating_high",
            str(self.NEW_ARRIVALS): "new",
        }
        return _map[str(self)]
