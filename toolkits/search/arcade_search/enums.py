from enum import Enum


class GoogleFinanceWindow(Enum):
    ONE_DAY = "1D"
    FIVE_DAYS = "5D"
    ONE_MONTH = "1M"
    SIX_MONTHS = "6M"
    YEAR_TO_DATE = "YTD"
    ONE_YEAR = "1Y"
    FIVE_YEARS = "5Y"
    MAX = "MAX"


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
