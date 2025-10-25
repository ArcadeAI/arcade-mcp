import json
import time
from enum import Enum
from typing import Annotated, Any, cast

import requests
from arcade_core.errors import RetryableToolError
from arcade_tdk import ToolContext, tool

from arcade_brightdata.bright_data_client import BrightDataClient


class DeviceType(str, Enum):
    MOBILE = "mobile"
    IOS = "ios"
    IPHONE = "iphone"
    IPAD = "ipad"
    ANDROID = "android"
    ANDROID_TABLET = "android_tablet"


class SearchEngine(str, Enum):
    GOOGLE = "google"
    BING = "bing"
    YANDEX = "yandex"


class SearchType(str, Enum):
    IMAGES = "images"
    SHOPPING = "shopping"
    NEWS = "news"
    JOBS = "jobs"


class SourceType(str, Enum):
    AMAZON_PRODUCT = "amazon_product"
    AMAZON_PRODUCT_REVIEWS = "amazon_product_reviews"
    LINKEDIN_PERSON_PROFILE = "linkedin_person_profile"
    LINKEDIN_COMPANY_PROFILE = "linkedin_company_profile"
    ZOOMINFO_COMPANY_PROFILE = "zoominfo_company_profile"
    INSTAGRAM_PROFILES = "instagram_profiles"
    INSTAGRAM_POSTS = "instagram_posts"
    INSTAGRAM_REELS = "instagram_reels"
    INSTAGRAM_COMMENTS = "instagram_comments"
    FACEBOOK_POSTS = "facebook_posts"
    FACEBOOK_MARKETPLACE_LISTINGS = "facebook_marketplace_listings"
    FACEBOOK_COMPANY_REVIEWS = "facebook_company_reviews"
    X_POSTS = "x_posts"
    ZILLOW_PROPERTIES_LISTING = "zillow_properties_listing"
    BOOKING_HOTEL_LISTINGS = "booking_hotel_listings"
    YOUTUBE_VIDEOS = "youtube_videos"


@tool(requires_secrets=["BRIGHTDATA_API_KEY", "BRIGHTDATA_ZONE"])
def scrape_as_markdown(
    context: ToolContext,
    url: Annotated[str, "URL to scrape"],
) -> Annotated[str, "Scraped webpage content as Markdown"]:
    """
    Scrape a webpage and return content in Markdown format using Bright Data.

    Examples:
        scrape_as_markdown("https://example.com") -> "# Example Page\n\nContent..."
        scrape_as_markdown("https://news.ycombinator.com") -> "# Hacker News\n..."
    """
    api_key = context.get_secret("BRIGHTDATA_API_KEY")
    zone = context.get_secret("BRIGHTDATA_ZONE")
    client = BrightDataClient.create_client(api_key=api_key, zone=zone)

    payload = {"url": url, "zone": zone, "format": "raw", "data_format": "markdown"}
    return client.make_request(payload)


@tool(requires_secrets=["BRIGHTDATA_API_KEY", "BRIGHTDATA_ZONE"])
def search_engine(  # noqa: C901
    context: ToolContext,
    query: Annotated[str, "Search query"],
    engine: Annotated[SearchEngine, "Search engine to use"] = SearchEngine.GOOGLE,
    language: Annotated[str | None, "Two-letter language code"] = None,
    country_code: Annotated[str | None, "Two-letter country code"] = None,
    search_type: Annotated[SearchType | None, "Type of search"] = None,
    start: Annotated[int | None, "Results pagination offset"] = None,
    num_results: Annotated[int, "Number of results to return. The default is 10"] = 10,
    location: Annotated[str | None, "Location for search results"] = None,
    device: Annotated[DeviceType | None, "Device type"] = None,
    return_json: Annotated[bool, "Return JSON instead of Markdown"] = False,
) -> Annotated[str, "Search results as Markdown or JSON"]:
    """
    Search using Google, Bing, or Yandex with advanced parameters using Bright Data.

    Examples:
        search_engine("climate change") -> "# Search Results\n\n## Climate Change - Wikipedia\n..."
        search_engine("Python tutorials", engine="bing", num_results=5) -> "# Bing Results\n..."
        search_engine("cats", search_type="images", country_code="us") -> "# Image Results\n..."
    """
    api_key = context.get_secret("BRIGHTDATA_API_KEY")
    zone = context.get_secret("BRIGHTDATA_ZONE")
    client = BrightDataClient.create_client(api_key=api_key, zone=zone)

    encoded_query = BrightDataClient.encode_query(query)

    base_urls = {
        SearchEngine.GOOGLE: f"https://www.google.com/search?q={encoded_query}",
        SearchEngine.BING: f"https://www.bing.com/search?q={encoded_query}",
        SearchEngine.YANDEX: f"https://yandex.com/search/?text={encoded_query}",
    }

    search_url = base_urls[engine]

    if engine == SearchEngine.GOOGLE:
        params = []

        if language:
            params.append(f"hl={language}")

        if country_code:
            params.append(f"gl={country_code}")

        if search_type:
            if search_type == SearchType.JOBS:
                params.append("ibp=htl;jobs")
            else:
                search_types = {
                    SearchType.IMAGES: "isch",
                    SearchType.SHOPPING: "shop",
                    SearchType.NEWS: "nws",
                }
                tbm_value = search_types.get(search_type, search_type)
                params.append(f"tbm={tbm_value}")

        if start is not None:
            params.append(f"start={start}")

        if num_results:
            params.append(f"num={num_results}")

        if location:
            params.append(f"uule={BrightDataClient.encode_query(location)}")

        if device:
            device_value = "1"

            if device.value in ["ios", "iphone"]:
                device_value = "ios"
            elif device.value == "ipad":
                device_value = "ios_tablet"
            elif device.value == "android":
                device_value = "android"
            elif device.value == "android_tablet":
                device_value = "android_tablet"

            params.append(f"brd_mobile={device_value}")

        if return_json:
            params.append("brd_json=1")

        if params:
            search_url += "&" + "&".join(params)

    payload = {
        "url": search_url,
        "zone": zone,
        "format": "raw",
        "data_format": "markdown" if not return_json else "raw",
    }

    return client.make_request(payload)


@tool(requires_secrets=["BRIGHTDATA_API_KEY"])
def web_data_feed(
    context: ToolContext,
    source_type: Annotated[SourceType, "Type of data source"],
    url: Annotated[str, "URL of the web resource to extract data from"],
    num_of_reviews: Annotated[
        int | None,
        (
            "Number of reviews to retrieve. Only applicable for "
            "facebook_company_reviews. Default is None"
        ),
    ] = None,
    timeout: Annotated[int, "Maximum time in seconds to wait for data retrieval"] = 600,
    polling_interval: Annotated[int, "Time in seconds between polling attempts"] = 1,
) -> Annotated[str, "Structured data from the requested source as JSON"]:
    """
    Extract structured data from various websites like LinkedIn, Amazon, Instagram, etc.
    NEVER MADE UP LINKS - IF LINKS ARE NEEDED, EXECUTE search_engine FIRST.
    Supported source types:
    - amazon_product, amazon_product_reviews
    - linkedin_person_profile, linkedin_company_profile
    - zoominfo_company_profile
    - instagram_profiles, instagram_posts, instagram_reels, instagram_comments
    - facebook_posts, facebook_marketplace_listings, facebook_company_reviews
    - x_posts
    - zillow_properties_listing
    - booking_hotel_listings
    - youtube_videos

    Examples:
        web_data_feed("amazon_product", "https://amazon.com/dp/B08N5WRWNW")
            -> "{\"title\": \"Product Name\", ...}"
        web_data_feed("linkedin_person_profile", "https://linkedin.com/in/johndoe")
            -> "{\"name\": \"John Doe\", ...}"
        web_data_feed(
            "facebook_company_reviews", "https://facebook.com/company", num_of_reviews=50
        ) -> "[{\"review\": \"...\", ...}]"
    """
    api_key = context.get_secret("BRIGHTDATA_API_KEY")
    client = BrightDataClient.create_client(api_key=api_key)
    if num_of_reviews is not None and source_type != SourceType.FACEBOOK_COMPANY_REVIEWS:
        msg = (
            f"num_of_reviews parameter is only applicable for facebook_company_reviews, "
            f"not for {source_type.value}"
        )
        prompt = (
            "The num_of_reviews parameter should only be used with "
            "facebook_company_reviews source type."
        )
        raise RetryableToolError(msg, additional_prompt_content=prompt)
    data = _extract_structured_data(
        client=client,
        source_type=source_type,
        url=url,
        num_of_reviews=num_of_reviews,
        timeout=timeout,
        polling_interval=polling_interval,
    )
    return json.dumps(data, indent=2)


def _extract_structured_data(
    client: BrightDataClient,
    source_type: SourceType,
    url: str,
    num_of_reviews: int | None = None,
    timeout: int = 600,
    polling_interval: int = 1,
) -> dict[str, Any]:
    """
    Extract structured data from various sources.
    """
    datasets = {
        SourceType.AMAZON_PRODUCT: "gd_l7q7dkf244hwjntr0",
        SourceType.AMAZON_PRODUCT_REVIEWS: "gd_le8e811kzy4ggddlq",
        SourceType.LINKEDIN_PERSON_PROFILE: "gd_l1viktl72bvl7bjuj0",
        SourceType.LINKEDIN_COMPANY_PROFILE: "gd_l1vikfnt1wgvvqz95w",
        SourceType.ZOOMINFO_COMPANY_PROFILE: "gd_m0ci4a4ivx3j5l6nx",
        SourceType.INSTAGRAM_PROFILES: "gd_l1vikfch901nx3by4",
        SourceType.INSTAGRAM_POSTS: "gd_lk5ns7kz21pck8jpis",
        SourceType.INSTAGRAM_REELS: "gd_lyclm20il4r5helnj",
        SourceType.INSTAGRAM_COMMENTS: "gd_ltppn085pokosxh13",
        SourceType.FACEBOOK_POSTS: "gd_lyclm1571iy3mv57zw",
        SourceType.FACEBOOK_MARKETPLACE_LISTINGS: "gd_lvt9iwuh6fbcwmx1a",
        SourceType.FACEBOOK_COMPANY_REVIEWS: "gd_m0dtqpiu1mbcyc2g86",
        SourceType.X_POSTS: "gd_lwxkxvnf1cynvib9co",
        SourceType.ZILLOW_PROPERTIES_LISTING: "gd_lfqkr8wm13ixtbd8f5",
        SourceType.BOOKING_HOTEL_LISTINGS: "gd_m5mbdl081229ln6t4a",
        SourceType.YOUTUBE_VIDEOS: "gd_m5mbdl081229ln6t4a",
    }

    dataset_id = datasets[source_type]

    request_data = {"url": url}
    if source_type == SourceType.FACEBOOK_COMPANY_REVIEWS and num_of_reviews is not None:
        request_data["num_of_reviews"] = str(num_of_reviews)

    trigger_response = requests.post(
        "https://api.brightdata.com/datasets/v3/trigger",
        params={"dataset_id": dataset_id, "include_errors": "true"},
        headers=client.headers,
        json=[request_data],
        timeout=30,
    )

    trigger_data = trigger_response.json()
    if not trigger_data.get("snapshot_id"):
        msg = "No snapshot ID returned from trigger request"
        prompt = "Invalid input provided, use search_engine to get the relevant data first"
        raise RetryableToolError(msg, additional_prompt_content=prompt)

    snapshot_id = trigger_data["snapshot_id"]

    attempts = 0
    max_attempts = timeout

    while attempts < max_attempts:
        try:
            snapshot_response = requests.get(
                f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
                params={"format": "json"},
                headers=client.headers,
                timeout=30,
            )

            snapshot_data = cast(dict[str, Any], snapshot_response.json())

            if isinstance(snapshot_data, dict) and snapshot_data.get("status") in (
                "running",
                "building",
            ):
                attempts += 1
                time.sleep(polling_interval)
                continue
            else:
                return snapshot_data

        except Exception:
            attempts += 1
            time.sleep(polling_interval)

    msg = f"Timeout after {max_attempts} seconds waiting for {source_type.value} data"
    raise TimeoutError(msg)
