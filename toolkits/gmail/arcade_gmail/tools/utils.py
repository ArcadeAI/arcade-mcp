from base64 import urlsafe_b64decode
import re
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup


def parse_email(email_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    Parse email data and extract relevant information.

    Args:
        email_data (Dict[str, Any]): Raw email data from Gmail API.

    Returns:
        Optional[Dict[str, str]]: Parsed email details or None if parsing fails.
    """
    try:
        payload = email_data["payload"]
        headers = {d["name"].lower(): d["value"] for d in payload["headers"]}

        body_data = _get_email_body(payload)

        return {
            "from": headers.get("from", ""),
            "date": headers.get("date", ""),
            "subject": headers.get("subject", "No subject"),
            "body": _clean_email_body(body_data) if body_data else "",
        }
    except Exception as e:
        print(f"Error parsing email {email_data.get('id', 'unknown')}: {e}")
        return None


def _get_email_body(payload: Dict[str, Any]) -> Optional[str]:
    """
    Extract email body from payload.

    Args:
        payload (Dict[str, Any]): Email payload data.

    Returns:
        Optional[str]: Decoded email body or None if not found.
    """
    if "body" in payload and payload["body"].get("data"):
        return urlsafe_b64decode(payload["body"]["data"]).decode()

    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and "data" in part["body"]:
            return urlsafe_b64decode(part["body"]["data"]).decode()

    return None


def _clean_email_body(body: str) -> str:
    """
    Remove HTML tags and clean up email body text while preserving most content.

    Args:
        body (str): The raw email body text.

    Returns:
        str: Cleaned email body text.
    """
    try:
        # Remove HTML tags using BeautifulSoup
        soup = BeautifulSoup(body, "html.parser")
        text = soup.get_text(separator=" ")

        # Clean up the text
        text = _clean_text(text)

        return text.strip()
    except Exception as e:
        print(f"Error cleaning email body: {e}")
        return body


def _clean_text(text: str) -> str:
    """
    Clean up the text while preserving most content.

    Args:
        text (str): The input text.

    Returns:
        str: Cleaned text.
    """
    # Replace multiple newlines with a single newline
    text = re.sub(r"\n+", "\n", text)

    # Replace multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)

    # Remove leading/trailing whitespace from each line
    text = "\n".join(line.strip() for line in text.split("\n"))

    return text
