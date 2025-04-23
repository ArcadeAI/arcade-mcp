from typing import Any, Callable

from arcade_hubspot.constants import GLOBALLY_IGNORED_FIELDS
from arcade_hubspot.enums import HubspotObject


def remove_none_values(data: dict) -> dict:
    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        if value is None or key in GLOBALLY_IGNORED_FIELDS:
            continue
        if isinstance(value, dict):
            cleaned_dict = remove_none_values(value)
            if cleaned_dict:
                cleaned[key] = cleaned_dict
        elif isinstance(value, (list, tuple, set)):
            collection_type = type(value)
            cleaned_list = [remove_none_values(item) for item in value]
            if cleaned_list:
                cleaned[key] = collection_type(cleaned_list)
        else:
            cleaned[key] = value
    return cleaned


def prepare_api_search_response(data: dict, object_type: HubspotObject) -> dict:
    response: dict[str, Any] = {
        object_type.plural: [clean_data(company, object_type) for company in data["results"]],
    }

    after = data.get("paging", {}).get("next", {}).get("after")

    if after:
        response["pagination"] = {
            "are_there_more_results?": True,
            "next_page_token": after,
        }
    else:
        response["pagination"] = {
            "are_there_more_results?": False,
        }

    return response


def rename_dict_keys(data: dict, rename: dict) -> dict:
    for old_key, new_key in rename.items():
        if old_key in data:
            data[new_key] = data[old_key]
            data.pop(old_key, None)
    return data


def global_cleaner(clean_func: Callable[[dict], dict]) -> Callable[[dict], dict]:
    def global_cleaner(data: dict) -> dict:
        cleaned_data: dict[str, Any] = {}
        if "hs_object_id" in data:
            cleaned_data["id"] = data["hs_object_id"]
            del data["hs_object_id"]

        data = rename_dict_keys(
            data,
            {
                "hubspot_owner_id": "owner_id",
                "hs_timestamp": "datetime",
                "hs_body_preview": "body",
            },
        )

        for key, value in data.items():
            if key in GLOBALLY_IGNORED_FIELDS or value is None:
                continue

            if isinstance(value, dict):
                cleaned_data[key] = global_cleaner(value)

            elif isinstance(value, (list, tuple, set)):
                cleaned_items = []
                for item in value:
                    if isinstance(item, dict):
                        cleaned_items.append(global_cleaner(item))
                    else:
                        cleaned_items.append(item)
                cleaned_data[key] = cleaned_items
            else:
                cleaned_data[key] = value
        return cleaned_data

    def wrapper(data: dict) -> dict:
        return remove_none_values(global_cleaner(clean_func(data["properties"])))

    return wrapper


def clean_data(data: dict, object_type: HubspotObject) -> dict:
    _mapping = {
        HubspotObject.CALL: clean_call_data,
        HubspotObject.COMPANY: clean_company_data,
        HubspotObject.CONTACT: clean_contact_data,
        HubspotObject.DEAL: clean_deal_data,
        HubspotObject.EMAIL: clean_email_data,
        HubspotObject.MEETING: clean_meeting_data,
        HubspotObject.NOTE: clean_note_data,
        HubspotObject.TASK: clean_task_data,
    }
    try:
        return _mapping[object_type](data)
    except KeyError:
        raise ValueError(f"Unsupported object type: {object_type}")


@global_cleaner
def clean_company_data(data: dict) -> dict:
    data["object_type"] = HubspotObject.COMPANY.value
    data["website"] = data.get("website", data.get("domain"))
    data.pop("domain", None)

    data["address"] = {
        "street": data.get("address"),
        "city": data.get("city"),
        "state": data.get("state"),
        "zip": data.get("zip"),
        "country": data.get("country"),
    }
    data.pop("address", None)
    data.pop("city", None)
    data.pop("state", None)
    data.pop("zip", None)
    data.pop("country", None)

    data["annual_revenue"] = {
        "value": data.get("annualrevenue"),
        "currency": data.get("hs_annual_revenue_currency_code"),
    }
    data.pop("annualrevenue", None)
    data.pop("hs_annual_revenue_currency_code", None)

    rename = {
        "linkedin_company_page": "linkedin_url",
        "numberofemployees": "employee_count",
        "type": "company_type",
        "annualrevenue": "annual_revenue",
        "lifecyclestage": "lifecycle_stage",
        "hs_lead_status": "lead_status",
    }
    data = rename_dict_keys(data, rename)
    return data


@global_cleaner
def clean_contact_data(data: dict) -> dict:
    data["object_type"] = HubspotObject.CONTACT.value
    rename = {
        "lifecyclestage": "lifecycle_stage",
        "hs_lead_status": "lead_status",
        "email": "email_address",
    }
    data = rename_dict_keys(data, rename)
    return data


@global_cleaner
def clean_deal_data(data: dict) -> dict:
    data["object_type"] = HubspotObject.DEAL.value

    if data.get("closedate") or data.get("hs_closed_amount"):
        data["close"] = {
            "is_closed": data.get("hs_is_closed"),
            "date": data.get("closedate"),
            "amount": data.get("hs_closed_amount"),
        }

        if data.get("hs_is_closed_won") in ["true", True]:
            data["close"]["status"] = "won"
            data["close"]["status_reason"] = data.get("closed_won_reason")
        elif data.get("hs_is_closed_lost") in ["true", True]:
            data["close"]["status"] = "lost"
            data["close"]["status_reason"] = data.get("closed_lost_reason")

    if data.get("amount"):
        data["amount"] = {
            "value": data["amount"],
            "currency": data.get("deal_currency_code"),
        }

        if data.get("hs_forecast_probability"):
            data["amount"]["forecast"] = {
                "probability": data["hs_forecast_probability"],
                "expected_value": data.get("hs_forecast_amount"),
            }

    rename = {
        "dealname": "name",
        "dealstage": "stage",
        "dealscore": "score",
        "dealtype": "type",
    }
    data = rename_dict_keys(data, rename)

    data.pop("hs_is_closed", None)
    data.pop("closedate", None)
    data.pop("hs_closed_amount", None)
    data.pop("deal_currency_code", None)
    data.pop("close_won_reason", None)
    data.pop("close_lost_reason", None)
    data.pop("hs_is_closed_won", None)
    data.pop("hs_is_closed_lost", None)
    data.pop("hs_forecast_probability", None)
    data.pop("hs_forecast_amount", None)

    return data


@global_cleaner
def clean_email_data(data: dict) -> dict:
    data["object_type"] = HubspotObject.EMAIL.value
    rename = {
        "hs_body_preview": "body",
        "hs_email_from_raw": "from",
        "hs_email_to_raw": "to",
        "hs_email_bcc_raw": "bcc",
        "hs_email_cc_raw": "cc",
        "hs_email_subject": "subject",
        "hs_email_status": "status",
        "hs_email_associated_contact_id": "contact_id",
    }
    data = rename_dict_keys(data, rename)
    return data


@global_cleaner
def clean_call_data(data: dict) -> dict:
    data["object_type"] = HubspotObject.CALL.value
    rename = {
        "hs_call_direction": "direction",
        "hs_call_status": "status",
        "hs_call_summary": "summary",
        "hs_call_title": "title",
        "hs_call_disposition": "outcome",
    }
    data = rename_dict_keys(data, rename)
    return data


@global_cleaner
def clean_note_data(data: dict) -> dict:
    data["object_type"] = HubspotObject.NOTE.value
    return data


@global_cleaner
def clean_meeting_data(data: dict) -> dict:
    data["object_type"] = HubspotObject.MEETING.value
    rename = {
        "hs_meeting_outcome": "outcome",
        "hs_meeting_location": "location",
        "hs_meeting_start_time": "start_time",
        "hs_meeting_end_time": "end_time",
    }
    data = rename_dict_keys(data, rename)

    data["content"] = {
        "title": data.get("hs_meeting_title"),
        "body": data.get("hs_body_preview"),
    }

    data.pop("hs_meeting_title", None)
    data.pop("hs_body_preview", None)

    data["schedule"] = {
        "start_time": data.get("start_time"),
        "end_time": data.get("end_time"),
    }

    data.pop("start_time", None)
    data.pop("end_time", None)

    return data


@global_cleaner
def clean_task_data(data: dict) -> dict:
    data["object_type"] = HubspotObject.TASK.value

    if data.get("hs_task_priority") == "NONE":
        data["hs_task_priority"] = None

    rename = {
        "hs_task_status": "status",
        "hs_task_priority": "priority",
        "hs_task_missed_due_date": "missed_due_date",
        "hs_task_type": "task_type",
        "hs_associated_contact_labels": "associated_contact",
    }
    data = rename_dict_keys(data, rename)

    data["content"] = {
        "body": data.get("hs_body_preview"),
        "subject": data.get("hs_task_subject"),
    }

    data.pop("hs_body_preview", None)
    data.pop("hs_task_subject", None)

    data["schedule"] = {
        "datetime": data.get("hs_timestamp"),
        "is_overdue": data.get("hs_task_is_overdue"),
    }

    data.pop("hs_timestamp", None)
    data.pop("hs_task_is_overdue", None)

    return data
