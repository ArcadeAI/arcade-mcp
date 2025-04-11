from enum import Enum


class SalesforceObject(Enum):
    ACCOUNT = "Account"
    CONTACT = "Contact"
    LEAD = "Lead"
    NOTE = "Note"
    CALL = "Call"
    TASK = "Task"
    USER = "User"

    @property
    def plural(self) -> str:
        return self.value + "s"
