from enum import Enum


class ResponseFormat(str, Enum):
    """Response format options for search results."""

    JSON = "json"
    HTML = "html"


class TimeRange(str, Enum):
    """Time range options for filtering search results."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class SafeSearchLevel(str, Enum):
    """Safe search level options."""

    OFF = "off"
    MODERATE = "moderate"
    STRICT = "strict"

    def to_api_value(self) -> int:
        _map = {
            "off": 0,
            "moderate": 1,
            "strict": 2,
        }
        return _map[self.value]


class ImageSize(str, Enum):
    """Image size filter options."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class ImageType(str, Enum):
    """Image type filter options."""

    PHOTO = "photo"
    CLIPART = "clipart"
    LINE = "line"
    ANIMATED = "animated"


class ImageLayout(str, Enum):
    """Image layout filter options."""

    SQUARE = "square"
    TALL = "tall"
    WIDE = "wide"


class ImageColor(str, Enum):
    """Image color filter options."""

    COLOR = "color"
    GRAYSCALE = "grayscale"
    TRANSPARENT = "transparent"


class VideoDuration(str, Enum):
    """Video duration filter options."""

    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
