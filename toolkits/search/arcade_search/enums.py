from enum import Enum

# ------------------------------------------------------------------------------
# Google Finance
# ------------------------------------------------------------------------------


class GoogleFinanceWindow(Enum):
    ONE_DAY = "1D"
    FIVE_DAYS = "5D"
    ONE_MONTH = "1M"
    SIX_MONTHS = "6M"
    YEAR_TO_DATE = "YTD"
    ONE_YEAR = "1Y"
    FIVE_YEARS = "5Y"
    MAX = "MAX"


# ------------------------------------------------------------------------------
# Google Flights
# ------------------------------------------------------------------------------


class GoogleFlightsTravelClass(Enum):
    ECONOMY = "ECONOMY"
    PREMIUM_ECONOMY = "PREMIUM_ECONOMY"
    BUSINESS = "BUSINESS"
    FIRST = "FIRST"

    def to_api_value(self) -> int:
        map_ = {
            "ECONOMY": 1,
            "PREMIUM_ECONOMY": 2,
            "BUSINESS": 3,
            "FIRST": 4,
        }
        return map_[self.value]


class GoogleFlightsMaxStops(Enum):
    ANY = "ANY"
    NONSTOP = "NONSTOP"
    ONE = "ONE"
    TWO = "TWO"

    def to_api_value(self) -> int:
        map_ = {
            "ANY": 0,
            "NONSTOP": 1,
            "ONE": 2,
            "TWO": 3,
        }
        return map_[self.value]


class GoogleFlightsSortBy(Enum):
    TOP_FLIGHTS = "TOP_FLIGHTS"
    PRICE = "PRICE"
    DEPARTURE_TIME = "DEPARTURE_TIME"
    ARRIVAL_TIME = "ARRIVAL_TIME"
    DURATION = "DURATION"
    EMISSIONS = "EMISSIONS"

    def to_api_value(self) -> int:
        map_ = {
            "TOP_FLIGHTS": 1,
            "PRICE": 2,
            "DEPARTURE_TIME": 3,
            "ARRIVAL_TIME": 4,
            "DURATION": 5,
            "EMISSIONS": 6,
        }
        return map_[self.value]


# ------------------------------------------------------------------------------
# Google Hotels
# ------------------------------------------------------------------------------


class GoogleHotelsSortBy(Enum):
    RELEVANCE = "RELEVANCE"
    LOWEST_PRICE = "LOWEST_PRICE"
    HIGHEST_RATING = "HIGHEST_RATING"
    MOST_REVIEWED = "MOST_REVIEWED"

    def to_api_value(self) -> int | None:
        map_ = {
            "RELEVANCE": None,
            "LOWEST_PRICE": 3,
            "HIGHEST_RATING": 8,
            "MOST_REVIEWED": 13,
        }
        return map_[self.value]
