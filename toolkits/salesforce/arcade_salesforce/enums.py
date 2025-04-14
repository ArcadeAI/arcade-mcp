from enum import Enum
from typing import cast


class SalesforceObject(Enum):
    ACCOUNT = "Account"
    CALL = "Call"
    CONTACT = "Contact"
    EMAIL = "Email"
    EVENT = "Event"
    LEAD = "Lead"
    NOTE = "Note"
    OPPORTUNITY = "Opportunity"
    TASK = "Task"
    USER = "User"

    @property
    def plural(self) -> str:
        if self == SalesforceObject.OPPORTUNITY:
            return "Opportunities"
        return cast(str, self.value) + "s"
