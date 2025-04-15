from typing import Callable

from arcade_hubspot.constants import GLOBALLY_IGNORED_FIELDS
from arcade_hubspot.enums import HubspotObject


def remove_none_values(data: dict) -> dict:
    cleaned = {}
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
    response = {
        object_type.plural: [clean_data(company, object_type) for company in data["results"]],
    }

    after = data.get("paging", {}).get("next", {}).get("after")

    if after:
        response["more_results"] = True
        response["next_page_token"] = after
    else:
        response["more_results"] = False

    return response


def rename_dict_keys(data: dict, rename: dict) -> dict:
    for old_key, new_key in rename.items():
        if old_key in data:
            data[new_key] = data[old_key]
            data.pop(old_key, None)
    return data


def global_cleaner(clean_func: Callable[[dict], dict]) -> Callable[[dict], dict]:
    def global_cleaner(data: dict) -> dict:
        cleaned_data = {}
        if "hs_object_id" in data:
            cleaned_data["id"] = data["hs_object_id"]
            del data["hs_object_id"]

        data = rename_dict_keys(data, {"hubspot_owner_id": "owner_id"})

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
                cleaned_data[key] = cleaned_items  # type: ignore[assignment]
            else:
                cleaned_data[key] = value
        return cleaned_data

    def wrapper(data: dict) -> dict:
        return remove_none_values(clean_func(global_cleaner(data["properties"])))

    return wrapper


def clean_data(data: dict, object_type: HubspotObject) -> dict:
    _mapping = {
        HubspotObject.COMPANY: clean_company_data,
        HubspotObject.CONTACT: clean_contact_data,
        HubspotObject.DEAL: clean_deal_data,
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
    return data


@global_cleaner
def clean_contact_data(data: dict) -> dict:
    data["object_type"] = HubspotObject.CONTACT.value
    rename = {
        "lifecyclestage": "lifecycle_stage",
        "hs_lead_status": "lead_status",
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
