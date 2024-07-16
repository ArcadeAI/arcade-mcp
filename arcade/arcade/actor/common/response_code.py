import dataclasses
from enum import Enum
from typing import Any


class CustomCodeBase(Enum):
    """Custom status code base class"""

    @property
    def code(self) -> Any:
        """
        Get status code
        """
        return self.value[0]

    @property
    def msg(self) -> Any:
        """
        Get status code information
        """
        return self.value[1]


class CustomResponseCode(CustomCodeBase):
    """Custom response status codes"""

    HTTP_200 = (200, "Request Successful")
    HTTP_201 = (201, "Created Successfully")
    HTTP_202 = (202, "Request Accepted, but Processing Not Yet Complete")
    HTTP_204 = (204, "Request Successful, but No Content Returned")
    HTTP_400 = (400, "Bad Request")
    HTTP_401 = (401, "Unauthorized")
    HTTP_403 = (403, "Forbidden Access")
    HTTP_404 = (404, "Requested Resource Not Found")
    HTTP_410 = (410, "Requested Resource Permanently Deleted")
    HTTP_422 = (422, "Invalid Request Parameters")
    HTTP_425 = (425, "Request Unexecutable, as Server Cannot Meet Requirements")
    HTTP_429 = (429, "Too Many Requests, Server Limiting")
    HTTP_500 = (500, "Internal Server Error")
    HTTP_502 = (502, "Gateway Error")
    HTTP_503 = (503, "Server Temporarily Unable to Process Request")
    HTTP_504 = (504, "Gateway Timeout")


@dataclasses.dataclass
class CustomResponse:
    """
    Provides open response status codes, rather than enums, which can be useful if you want to customize response information
    """

    code: int
    msg: str


class StandardResponseCode:
    """Standard response status codes"""

    """
    HTTP codes
    See HTTP Status Code Registry:
    https://www.iana.org/assignments/http-status-codes/http-status-codes.xhtml

    And RFC 2324 - https://tools.ietf.org/html/rfc2324
    """
    HTTP_100 = 100  # CONTINUE
    HTTP_101 = 101  # SWITCHING_PROTOCOLS
    HTTP_102 = 102  # PROCESSING
    HTTP_103 = 103  # EARLY_HINTS
    HTTP_200 = 200  # OK
    HTTP_201 = 201  # CREATED
    HTTP_202 = 202  # ACCEPTED
    HTTP_203 = 203  # NON_AUTHORITATIVE_INFORMATION
    HTTP_204 = 204  # NO_CONTENT
    HTTP_205 = 205  # RESET_CONTENT
    HTTP_206 = 206  # PARTIAL_CONTENT
    HTTP_207 = 207  # MULTI_STATUS
    HTTP_208 = 208  # ALREADY_REPORTED
    HTTP_226 = 226  # IM_USED
    HTTP_300 = 300  # MULTIPLE_CHOICES
    HTTP_301 = 301  # MOVED_PERMANENTLY
    HTTP_302 = 302  # FOUND
    HTTP_303 = 303  # SEE_OTHER
    HTTP_304 = 304  # NOT_MODIFIED
    HTTP_305 = 305  # USE_PROXY
    HTTP_307 = 307  # TEMPORARY_REDIRECT
    HTTP_308 = 308  # PERMANENT_REDIRECT
    HTTP_400 = 400  # BAD_REQUEST
    HTTP_401 = 401  # UNAUTHORIZED
    HTTP_402 = 402  # PAYMENT_REQUIRED
    HTTP_403 = 403  # FORBIDDEN
    HTTP_404 = 404  # NOT_FOUND
    HTTP_405 = 405  # METHOD_NOT_ALLOWED
    HTTP_406 = 406  # NOT_ACCEPTABLE
    HTTP_407 = 407  # PROXY_AUTHENTICATION_REQUIRED
    HTTP_408 = 408  # REQUEST_TIMEOUT
    HTTP_409 = 409  # CONFLICT
    HTTP_410 = 410  # GONE
    HTTP_411 = 411  # LENGTH_REQUIRED
    HTTP_412 = 412  # PRECONDITION_FAILED
    HTTP_413 = 413  # REQUEST_ENTITY_TOO_LARGE
    HTTP_414 = 414  # REQUEST_URI_TOO_LONG
    HTTP_415 = 415  # UNSUPPORTED_MEDIA_TYPE
    HTTP_416 = 416  # REQUESTED_RANGE_NOT_SATISFIABLE
    HTTP_417 = 417  # EXPECTATION_FAILED
    HTTP_418 = 418  # UNUSED
    HTTP_421 = 421  # MISDIRECTED_REQUEST
    HTTP_422 = 422  # UNPROCESSABLE_CONTENT
    HTTP_423 = 423  # LOCKED
    HTTP_424 = 424  # FAILED_DEPENDENCY
    HTTP_425 = 425  # TOO_EARLY
    HTTP_426 = 426  # UPGRADE_REQUIRED
    HTTP_427 = 427  # UNASSIGNED
    HTTP_428 = 428  # PRECONDITION_REQUIRED
    HTTP_429 = 429  # TOO_MANY_REQUESTS
    HTTP_430 = 430  # Unassigned
    HTTP_431 = 431  # REQUEST_HEADER_FIELDS_TOO_LARGE
    HTTP_451 = 451  # UNAVAILABLE_FOR_LEGAL_REASONS
    HTTP_500 = 500  # INTERNAL_SERVER_ERROR
    HTTP_501 = 501  # NOT_IMPLEMENTED
    HTTP_502 = 502  # BAD_GATEWAY
    HTTP_503 = 503  # SERVICE_UNAVAILABLE
    HTTP_504 = 504  # GATEWAY_TIMEOUT
    HTTP_505 = 505  # HTTP_VERSION_NOT_SUPPORTED
    HTTP_506 = 506  # VARIANT_ALSO_NEGOTIATES
    HTTP_507 = 507  # INSUFFICIENT_STORAGE
    HTTP_508 = 508  # LOOP_DETECTED
    HTTP_509 = 509  # UNASSIGNED
    HTTP_510 = 510  # NOT_EXTENDED
    HTTP_511 = 511  # NETWORK_AUTHENTICATION_REQUIRED

    """
    WebSocket codes
    https://www.iana.org/assignments/websocket/websocket.xml#close-code-number
    https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent
    """
    WS_1000 = 1000  # NORMAL_CLOSURE
    WS_1001 = 1001  # GOING_AWAY
    WS_1002 = 1002  # PROTOCOL_ERROR
    WS_1003 = 1003  # UNSUPPORTED_DATA
    WS_1005 = 1005  # NO_STATUS_RCVD
    WS_1006 = 1006  # ABNORMAL_CLOSURE
    WS_1007 = 1007  # INVALID_FRAME_PAYLOAD_DATA
    WS_1008 = 1008  # POLICY_VIOLATION
    WS_1009 = 1009  # MESSAGE_TOO_BIG
    WS_1010 = 1010  # MANDATORY_EXT
    WS_1011 = 1011  # INTERNAL_ERROR
    WS_1012 = 1012  # SERVICE_RESTART
    WS_1013 = 1013  # TRY_AGAIN_LATER
    WS_1014 = 1014  # BAD_GATEWAY
    WS_1015 = 1015  # TLS_HANDSHAKE
    WS_3000 = 3000  # UNAUTHORIZED
    WS_3003 = 3003  # FORBIDDEN
