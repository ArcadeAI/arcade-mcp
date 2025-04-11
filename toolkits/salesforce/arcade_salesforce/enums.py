from enum import Enum


class SalesforceObject(Enum):
    ACCOUNT = "Account"
    CALL = "Call"
    CONTACT = "Contact"
    LEAD = "Lead"
    NOTE = "Note"
    OPPORTUNITY = "Opportunity"
    TASK = "Task"
    USER = "User"

    @property
    def plural(self) -> str:
        if self == SalesforceObject.OPPORTUNITY:
            return "Opportunities"
        return self.value + "s"
