import os

from arcade_search.enums import GoogleMapsDistanceUnit, GoogleMapsTravelMode

# ------------------------------------------------------------------------------------------------
# Google default constants
# ------------------------------------------------------------------------------------------------
DEFAULT_GOOGLE_LANGUAGE = os.getenv("ARCADE_GOOGLE_LANGUAGE", "en")
DEFAULT_GOOGLE_COUNTRY = os.getenv("ARCADE_GOOGLE_COUNTRY")

# ------------------------------------------------------------------------------------------------
# Google News default constants
# ------------------------------------------------------------------------------------------------
DEFAULT_GOOGLE_NEWS_LANGUAGE = os.getenv("ARCADE_GOOGLE_NEWS_LANGUAGE", DEFAULT_GOOGLE_LANGUAGE)
DEFAULT_GOOGLE_NEWS_COUNTRY = os.getenv("ARCADE_GOOGLE_NEWS_COUNTRY")

# ------------------------------------------------------------------------------------------------
# Google Jobs default constants
# ------------------------------------------------------------------------------------------------
DEFAULT_GOOGLE_JOBS_LANGUAGE = os.getenv("ARCADE_GOOGLE_JOBS_LANGUAGE", DEFAULT_GOOGLE_LANGUAGE)

# ------------------------------------------------------------------------------------------------
# Google Maps default constants
# ------------------------------------------------------------------------------------------------
DEFAULT_GOOGLE_MAPS_LANGUAGE = os.getenv("ARCADE_GOOGLE_MAPS_LANGUAGE", DEFAULT_GOOGLE_LANGUAGE)
DEFAULT_GOOGLE_MAPS_COUNTRY = os.getenv("ARCADE_GOOGLE_MAPS_COUNTRY")
DEFAULT_GOOGLE_MAPS_DISTANCE_UNIT = GoogleMapsDistanceUnit(
    os.getenv("ARCADE_GOOGLE_MAPS_DISTANCE_UNIT", GoogleMapsDistanceUnit.KM.value)
)
DEFAULT_GOOGLE_MAPS_TRAVEL_MODE = GoogleMapsTravelMode(
    os.getenv("ARCADE_GOOGLE_MAPS_TRAVEL_MODE", GoogleMapsTravelMode.BEST.value)
)

# ------------------------------------------------------------------------------------------------
# YouTube default constants
# ------------------------------------------------------------------------------------------------
YOUTUBE_MAX_DESCRIPTION_LENGTH = 500
DEFAULT_YOUTUBE_SEARCH_LANGUAGE = os.getenv("ARCADE_YOUTUBE_SEARCH_LANGUAGE")
DEFAULT_YOUTUBE_SEARCH_COUNTRY = os.getenv("ARCADE_YOUTUBE_SEARCH_COUNTRY")

# ------------------------------------------------------------------------------------------------
# Google Shopping default constants
# ------------------------------------------------------------------------------------------------
DEFAULT_GOOGLE_SHOPPING_LANGUAGE = os.getenv(
    "ARCADE_GOOGLE_SHOPPING_LANGUAGE", DEFAULT_GOOGLE_LANGUAGE
)
DEFAULT_GOOGLE_SHOPPING_COUNTRY = os.getenv(
    "ARCADE_GOOGLE_SHOPPING_COUNTRY", DEFAULT_GOOGLE_COUNTRY
)
