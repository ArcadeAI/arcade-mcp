from enum import Enum


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
