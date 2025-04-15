from enum import Enum


class HubspotObject(Enum):
    COMPANY = "company"
    CONTACT = "contact"
    DEAL = "deal"

    @property
    def plural(self) -> str:
        if self.value == "company":
            return "companies"
        return f"{self.value}s"
