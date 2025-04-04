from enum import Enum


# ------------------------------------------------------------------------------------------------
# Google Finance enumerations
# ------------------------------------------------------------------------------------------------
class GoogleFinanceWindow(Enum):
    ONE_DAY = "1D"
    FIVE_DAYS = "5D"
    ONE_MONTH = "1M"
    SIX_MONTHS = "6M"
    YEAR_TO_DATE = "YTD"
    ONE_YEAR = "1Y"
    FIVE_YEARS = "5Y"
    MAX = "MAX"


# ------------------------------------------------------------------------------------------------
# Google Flights enumerations
# ------------------------------------------------------------------------------------------------
class GoogleFlightsTravelClass(Enum):
    ECONOMY = "ECONOMY"
    PREMIUM_ECONOMY = "PREMIUM_ECONOMY"
    BUSINESS = "BUSINESS"
    FIRST = "FIRST"

    def to_api_value(self) -> int:
        _map = {
            "ECONOMY": 1,
            "PREMIUM_ECONOMY": 2,
            "BUSINESS": 3,
            "FIRST": 4,
        }
        return _map[self.value]


class GoogleFlightsMaxStops(Enum):
    ANY = "ANY"
    NONSTOP = "NONSTOP"
    ONE = "ONE"
    TWO = "TWO"

    def to_api_value(self) -> int:
        _map = {
            "ANY": 0,
            "NONSTOP": 1,
            "ONE": 2,
            "TWO": 3,
        }
        return _map[self.value]


class GoogleFlightsSortBy(Enum):
    TOP_FLIGHTS = "TOP_FLIGHTS"
    PRICE = "PRICE"
    DEPARTURE_TIME = "DEPARTURE_TIME"
    ARRIVAL_TIME = "ARRIVAL_TIME"
    DURATION = "DURATION"
    EMISSIONS = "EMISSIONS"

    def to_api_value(self) -> int:
        _map = {
            "TOP_FLIGHTS": 1,
            "PRICE": 2,
            "DEPARTURE_TIME": 3,
            "ARRIVAL_TIME": 4,
            "DURATION": 5,
            "EMISSIONS": 6,
        }
        return _map[self.value]


# ------------------------------------------------------------------------------------------------
# Google Hotels enumerations
# ------------------------------------------------------------------------------------------------
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


# ------------------------------------------------------------------------------------------------
# Google Maps enumerations
# ------------------------------------------------------------------------------------------------
class GoogleMapsTravelMode(Enum):
    BEST = "best"
    DRIVING = "driving"
    MOTORCYCLE = "motorcycle"
    PUBLIC_TRANSPORTATION = "public_transportation"
    WALKING = "walking"
    BICYCLE = "bicycle"
    FLIGHT = "flight"

    def to_api_value(self) -> int:
        _map = {
            str(self.BEST): 6,
            str(self.DRIVING): 0,
            str(self.MOTORCYCLE): 9,
            str(self.PUBLIC_TRANSPORTATION): 3,
            str(self.WALKING): 2,
            str(self.BICYCLE): 1,
            str(self.FLIGHT): 4,
        }
        return _map[str(self)]


class GoogleMapsDistanceUnit(Enum):
    KM = "km"
    MILES = "mi"

    def to_api_value(self) -> int:
        _map = {
            str(self.KM): 0,
            str(self.MILES): 1,
        }
        return _map[str(self)]


# ------------------------------------------------------------------------------------------------
# Walmart enumerations
# ------------------------------------------------------------------------------------------------
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
