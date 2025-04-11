from typing import cast

from arcade_salesforce.enums import SalesforceObject


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


def clean_account_data(data: dict) -> dict:
    data["AccountType"] = data["Type"]
    del data["Type"]
    data["ObjectType"] = SalesforceObject.ACCOUNT.value
    ignore_fields = [
        "attributes",
        "CleanStatus",
        "LastReferencedDate",
        "LastViewedDate",
        "SystemModstamp",
        "BillingCity",
        "BillingCountry",
        "BillingCountryCode",
        "BillingPostalCode",
        "BillingState",
        "BillingStateCode",
        "BillingStreet",
        "ShippingCity",
        "ShippingCountry",
        "ShippingCountryCode",
        "ShippingPostalCode",
        "ShippingState",
        "ShippingStateCode",
        "ShippingStreet",
        "PhotoUrl",
    ]
    return {k: v for k, v in data.items() if v is not None and k not in ignore_fields}


def clean_contact_data(data: dict) -> dict:
    data["ObjectType"] = SalesforceObject.CONTACT.value
    ignore_fields = [
        "attributes",
        "CleanStatus",
        "LastReferencedDate",
        "LastViewedDate",
        "SystemModstamp",
        "PhotoUrl",
    ]
    return {k: v for k, v in data.items() if v is not None and k not in ignore_fields}


def clean_lead_data(data: dict) -> dict:
    data["ObjectType"] = SalesforceObject.LEAD.value
    ignore_fields = [
        "attributes",
        "CleanStatus",
        "LastReferencedDate",
        "LastViewedDate",
        "SystemModstamp",
    ]
    return {k: v for k, v in data.items() if v is not None and k not in ignore_fields}


def clean_note_data(data: dict) -> dict:
    data["ObjectType"] = SalesforceObject.NOTE.value
    ignore_fields = [
        "attributes",
        "CleanStatus",
        "LastReferencedDate",
        "LastViewedDate",
        "SystemModstamp",
    ]
    return {k: v for k, v in data.items() if v is not None and k not in ignore_fields}


def clean_task_data(data: dict) -> dict:
    data["ObjectType"] = data["TaskSubtype"]
    del data["TaskSubtype"]
    ignore_fields = [
        "attributes",
        "CleanStatus",
        "SystemModstamp",
    ]
    return {k: v for k, v in data.items() if v is not None and k not in ignore_fields}


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
    fields = ["AccountId", "CreatedById", "LastModifiedById", "OwnerId", "WhoId"]
    referenced_ids = set()
    for data in data_objects:
        for field in fields:
            if field in data:
                referenced_ids.add(data[field])
    return referenced_ids


def expand_associations(data: dict, objects_by_id: dict) -> dict:
    fields = ["AccountId", "CreatedById", "LastModifiedById", "OwnerId", "WhoId"]

    for field in fields:
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
