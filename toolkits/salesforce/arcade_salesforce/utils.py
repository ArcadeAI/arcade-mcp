from arcade_salesforce.enums import SalesforceObject


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
