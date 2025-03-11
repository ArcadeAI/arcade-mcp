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
