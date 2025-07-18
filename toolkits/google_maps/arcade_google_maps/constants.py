import os

from arcade_google_maps.enums import GoogleMapsDistanceUnit, GoogleMapsTravelMode

DEFAULT_GOOGLE_LANGUAGE = os.getenv("ARCADE_GOOGLE_LANGUAGE", "en")

DEFAULT_GOOGLE_MAPS_LANGUAGE = os.getenv("ARCADE_GOOGLE_MAPS_LANGUAGE", DEFAULT_GOOGLE_LANGUAGE)
DEFAULT_GOOGLE_MAPS_COUNTRY = os.getenv("ARCADE_GOOGLE_MAPS_COUNTRY")
DEFAULT_GOOGLE_MAPS_DISTANCE_UNIT = GoogleMapsDistanceUnit(
    os.getenv("ARCADE_GOOGLE_MAPS_DISTANCE_UNIT", GoogleMapsDistanceUnit.KM.value)
)
DEFAULT_GOOGLE_MAPS_TRAVEL_MODE = GoogleMapsTravelMode(
    os.getenv("ARCADE_GOOGLE_MAPS_TRAVEL_MODE", GoogleMapsTravelMode.BEST.value)
)
