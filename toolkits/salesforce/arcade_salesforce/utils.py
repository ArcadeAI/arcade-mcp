import string
from typing import Any, Callable, cast

from arcade_salesforce.constants import ASSOCIATION_REFERENCE_FIELDS, GLOBALLY_IGNORED_FIELDS
from arcade_salesforce.enums import SalesforceObject


def remove_fields_globally_ignored(clean_func: Callable[[dict], dict]) -> Callable[[dict], dict]:
    def global_cleaner(data: dict) -> dict:
        cleaned_data = {}
        for key, value in data.items():
            if key in GLOBALLY_IGNORED_FIELDS or value is None:
                continue

            if isinstance(value, dict):
                cleaned_data[key] = global_cleaner(value)
            elif isinstance(value, (list, tuple, set)):
                cleaned_data[key] = [global_cleaner(item) for item in value]
            else:
                cleaned_data[key] = value
        return cleaned_data

    def wrapper(data: dict) -> dict:
        return global_cleaner(clean_func(data))

    return wrapper


def clean_object_data(data: dict) -> dict:
    obj_type = data["attributes"]["type"]
    if obj_type == SalesforceObject.ACCOUNT.value:
        return clean_account_data(data)
    elif obj_type == SalesforceObject.CONTACT.value:
        return clean_contact_data(data)
    elif obj_type == SalesforceObject.LEAD.value:
        return clean_lead_data(data)
    elif obj_type == SalesforceObject.NOTE.value:
        return clean_note_data(data)
    elif obj_type == SalesforceObject.TASK.value:
        return clean_task_data(data)
    elif obj_type == SalesforceObject.USER.value:
        return clean_user_data(data)
    raise ValueError(f"Unknown object type: '{obj_type}' in object: {data}")


@remove_fields_globally_ignored
def clean_account_data(data: dict) -> dict:
    data["AccountType"] = data["Type"]
    del data["Type"]
    data["ObjectType"] = SalesforceObject.ACCOUNT.value
    ignore_fields = [
        "BillingCity",
        "BillingCountry",
        "BillingCountryCode",
        "BillingPostalCode",
        "BillingState",
        "BillingStateCode",
        "BillingStreet",
        "LastActivityDate",
        "ShippingCity",
        "ShippingCountry",
        "ShippingCountryCode",
        "ShippingPostalCode",
        "ShippingState",
        "ShippingStateCode",
        "ShippingStreet",
    ]
    return {k: v for k, v in data.items() if v is not None and k not in ignore_fields}


@remove_fields_globally_ignored
def clean_contact_data(data: dict) -> dict:
    data["ObjectType"] = SalesforceObject.CONTACT.value
    ignore_fields = ["IsEmailBounced", "IsPriorityRecord"]
    return {k: v for k, v in data.items() if v is not None and k not in ignore_fields}


@remove_fields_globally_ignored
def clean_lead_data(data: dict) -> dict:
    data["ObjectType"] = SalesforceObject.LEAD.value
    return data


@remove_fields_globally_ignored
def clean_opportunity_data(data: dict) -> dict:
    data["ObjectType"] = SalesforceObject.OPPORTUNITY.value
    data["Amount"] = {
        "Value": data["Amount"],
        "ClosingProbability": data["Probability"]
        if not isinstance(data["Probability"], (int, float))
        else data["Probability"] / 100,
        "ExpectedRevenue": data["ExpectedRevenue"],
    }
    del data["Probability"]
    del data["ExpectedRevenue"]
    return data


@remove_fields_globally_ignored
def clean_note_data(data: dict) -> dict:
    data["ObjectType"] = SalesforceObject.NOTE.value
    return data


@remove_fields_globally_ignored
def clean_task_data(data: dict) -> dict:
    data["ObjectType"] = data["TaskSubtype"]
    data["AssociatedToWhom"] = data["WhoId"]
    ignore_fields = [
        "IsArchived",
        "IsClosed",
        "IsDeleted",
        "IsHighPriority",
        "IsRecurrence",
        "IsReminderSet",
        "TaskSubtype",
        "WhoId",
    ]

    if data["ObjectType"] == SalesforceObject.EMAIL.value:
        data["Email"] = format_email(data["Description"])
        del data["ActivityDate"]
        del data["CompletedDateTime"]
        del data["Description"]
        del data["Subject"]
        del data["OwnerId"]
        del data["Priority"]
        del data["Status"]

    return {k: v for k, v in data.items() if v is not None and k not in ignore_fields}


@remove_fields_globally_ignored
def clean_user_data(data: dict) -> dict:
    data["ObjectType"] = SalesforceObject.USER.value
    ignore_fields = [
        "attributes",
        "CleanStatus",
        "LastReferencedDate",
        "LastViewedDate",
        "SystemModstamp",
    ]
    return {k: v for k, v in data.items() if v is not None and k not in ignore_fields}


def get_ids_referenced(*data_objects: dict) -> set[str]:
    referenced_ids = set()
    for data in data_objects:
        for field in ASSOCIATION_REFERENCE_FIELDS:
            if field in data:
                referenced_ids.add(data[field])
    return referenced_ids


def expand_associations(data: dict, objects_by_id: dict) -> dict:
    for field in ASSOCIATION_REFERENCE_FIELDS:
        if field not in data:
            continue

        associated_object = objects_by_id.get(data[field])

        if isinstance(associated_object, dict):
            del data[field]
            data[field.rstrip("Id")] = simplified_object_data(associated_object)

    return data


def simplified_object_data(data: dict) -> dict:
    return {
        "Id": data["Id"],
        "Name": data["Name"],
        "ObjectType": get_object_type(data),
    }


def get_object_type(data: dict) -> str:
    return cast(str, data.get("ObjectType")) or cast(str, data["attributes"]["type"])


def build_soql_query(query: str, **kwargs: Any) -> str:
    return query.format(**{key: sanitize_soql_argument(value) for key, value in kwargs.items()})


def sanitize_soql_argument(value: Any) -> str:
    allowed_chars = string.ascii_letters + string.digits
    if not isinstance(value, str):
        value = str(value)
    return "".join([char for char in value if char in allowed_chars])


def format_email(description: str) -> dict:
    email = {
        "To": description.split("To:")[1].split("\n")[0].strip(),
        "CC": description.split("CC:")[1].split("\n")[0].strip(),
        "BCC": description.split("BCC:")[1].split("\n")[0].strip(),
        "Attachment": description.split("Attachment:")[1].split("\n")[0].strip(),
        "Subject": description.split("Subject:")[1].split("\n")[0].strip(),
        "Body": description.split("Body:\n")[1].strip(),
    }

    if email["Attachment"] == "--none--":
        email["Attachment"] = None

    return email


def remove_none_values(data: dict) -> dict:
    return {k: v for k, v in data.items() if v is not None}
