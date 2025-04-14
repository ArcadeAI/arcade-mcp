from enum import Enum


class HubspotObject(Enum):
    COMPANY = "company"
    CONTACT = "contact"
    LEAD = "lead"

    @property
    def plural(self) -> str:
        if self.value == "company":
            return "companies"
        return f"{self.value}s"
