from pydantic import BaseModel


class RequestData(BaseModel):
    """
    The raw data for a request to an actor.
    This is not intended to represent everything about an HTTP request,
    but just the essential info a framework integration will need to extract from the request.
    """

    path: str
    """The path of the request."""
    method: str
    """The method of the request."""
    body_json: dict | None = None
    """The deserialized body of the request (e.g. JSON)"""
