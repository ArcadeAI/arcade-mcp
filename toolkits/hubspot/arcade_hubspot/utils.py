from typing import Callable

from arcade_hubspot.constants import GLOBALLY_IGNORED_FIELDS
from arcade_hubspot.enums import HubspotObject


def remove_none_values(data: dict) -> dict:
    return {k: v for k, v in data.items() if v is not None}


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


def global_cleaner(clean_func: Callable[[dict], dict]) -> Callable[[dict], dict]:
    def global_cleaner(data: dict) -> dict:
        cleaned_data = {}
        if "hs_object_id" in data:
            cleaned_data["id"] = data["hs_object_id"]
            del data["hs_object_id"]

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
        return clean_func(global_cleaner(data["properties"]))

    return wrapper


def clean_data(data: dict, object_type: HubspotObject) -> dict:
    if object_type == HubspotObject.COMPANY:
        return clean_company_data(data)
    else:
        raise ValueError(f"Unsupported object type: {object_type}")


@global_cleaner
def clean_company_data(data: dict) -> dict:
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "phone": data.get("phone"),
        "website": data.get("website", data.get("domain")),
    }
