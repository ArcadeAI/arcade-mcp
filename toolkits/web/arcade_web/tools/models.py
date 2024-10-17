from enum import Enum


# Models and enums for firecrawl web tools
class Formats(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    RAW_HTML = "rawHtml"
    LINKS = "links"
    SCREENSHOT = "screenshot"
    EXTRACT = "extract"
    SCREENSHOT_AT_FULL_PAGE = "screenshot@fullPage"
