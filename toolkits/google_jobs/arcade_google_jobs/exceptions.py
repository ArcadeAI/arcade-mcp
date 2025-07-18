import json

from arcade_tdk.errors import RetryableToolError

from arcade_google_jobs.google_data import LANGUAGE_CODES


class GoogleRetryableError(RetryableToolError):
    pass


class LanguageNotFoundError(GoogleRetryableError):
    def __init__(self, language: str | None) -> None:
        valid_languages = json.dumps(LANGUAGE_CODES, default=str)
        message = f"Language not found: '{language}'."
        additional_message = f"Valid languages are: {valid_languages}"
        super().__init__(message, additional_prompt_content=additional_message)
