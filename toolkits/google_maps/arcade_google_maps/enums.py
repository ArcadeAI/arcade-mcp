from enum import Enum


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
