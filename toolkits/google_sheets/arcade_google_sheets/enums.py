from enum import Enum


class CellErrorType(str, Enum):
    """The type of error in a cell

    Implementation of https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/other#ErrorType
    """

    ERROR_TYPE_UNSPECIFIED = "ERROR_TYPE_UNSPECIFIED"  # The default error type, do not use this.
    ERROR = "ERROR"  # Corresponds to the #ERROR! error.
    NULL_VALUE = "NULL_VALUE"  # Corresponds to the #NULL! error.
    DIVIDE_BY_ZERO = "DIVIDE_BY_ZERO"  # Corresponds to the #DIV/0 error.
    VALUE = "VALUE"  # Corresponds to the #VALUE! error.
    REF = "REF"  # Corresponds to the #REF! error.
    NAME = "NAME"  # Corresponds to the #NAME? error.
    NUM = "NUM"  # Corresponds to the #NUM! error.
    N_A = "N_A"  # Corresponds to the #N/A error.
    LOADING = "LOADING"  # Corresponds to the Loading... state.


class NumberFormatType(str, Enum):
    NUMBER = "NUMBER"
    PERCENT = "PERCENT"
    CURRENCY = "CURRENCY"
