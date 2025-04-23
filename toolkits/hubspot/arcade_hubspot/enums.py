from enum import Enum


class HubspotObject(Enum):
    ACCOUNT = "account"
    CALL = "call"
    COMMUNICATION = "communication"
    COMPANY = "company"
    CONTACT = "contact"
    DEAL = "deal"
    EMAIL = "email"
    MEETING = "meeting"
    NOTE = "note"
    TASK = "task"

    @property
    def plural(self) -> str:
        if self.value == "company":
            return "companies"
        return f"{self.value}s"
