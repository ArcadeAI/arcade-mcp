import json
import time
from typing import Annotated, Dict, Optional

import requests
from arcade_tdk import ToolContext, tool

from ..bright_data_client import BrightDataClient


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
def get_screenshot(
    context: ToolContext,
    url: Annotated[str, "URL to screenshot"],
    output_path: Annotated[str, "Path to save the screenshot"],
) -> Annotated[str, "Path to the saved screenshot"]:
    """
    Take a screenshot of a webpage using Bright Data.
    
    Examples:
        get_screenshot("https://example.com", "/tmp/screenshot.png") -> "/tmp/screenshot.png"
        get_screenshot("https://google.com", "./google.png") -> "./google.png"
    """
    api_key = context.get_secret("BRIGHTDATA_API_KEY")
    zone = context.get_secret("BRIGHTDATA_ZONE")
    client = BrightDataClient.create_client(api_key=api_key, zone=zone)
    
    payload = {"url": url, "zone": zone, "format": "raw", "data_format": "screenshot"}
    
    response = requests.post(client.endpoint, headers=client.headers, data=json.dumps(payload))

    if response.status_code != 200:
        raise Exception(f"Error {response.status_code}: {response.text}")

    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path


@tool(requires_secrets=["BRIGHTDATA_API_KEY", "BRIGHTDATA_ZONE"])
def search_engine(
    context: ToolContext,
    query: Annotated[str, "Search query"],
    engine: Annotated[str, "Search engine to use (google, bing, yandex)"] = "google",
    language: Annotated[Optional[str], "Two-letter language code"] = None,
    country_code: Annotated[Optional[str], "Two-letter country code"] = None,
    search_type: Annotated[Optional[str], "Type of search (images, shopping, news)"] = None,
    start: Annotated[Optional[int], "Results pagination offset"] = None,
    num_results: Annotated[int, "Number of results to return"] = 10,
    location: Annotated[Optional[str], "Location for search results"] = None,
    device: Annotated[Optional[str], "Device type (mobile, ios, android, ipad, android_tablet)"] = None,
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
        "google": f"https://www.google.com/search?q={encoded_query}",
        "bing": f"https://www.bing.com/search?q={encoded_query}",
        "yandex": f"https://yandex.com/search/?text={encoded_query}",
    }

    if engine not in base_urls:
        raise ValueError(f"Unsupported search engine: {engine}. Use 'google', 'bing', or 'yandex'")

    search_url = base_urls[engine]

    if engine == "google":
        params = []

        if language:
            params.append(f"hl={language}")

        if country_code:
            params.append(f"gl={country_code}")

        if search_type:
            if search_type == "jobs":
                params.append("ibp=htl;jobs")
            else:
                search_types = {"images": "isch", "shopping": "shop", "news": "nws"}
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

            if device in ["ios", "iphone"]:
                device_value = "ios"
            elif device == "ipad":
                device_value = "ios_tablet"
            elif device == "android":
                device_value = "android"
            elif device == "android_tablet":
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
    source_type: Annotated[str, "Type of data source (e.g., 'linkedin_person_profile', 'amazon_product')"],
    url: Annotated[str, "URL of the web resource to extract data from"],
    num_of_reviews: Annotated[Optional[int], "Number of reviews to retrieve (facebook_company_reviews only)"] = None,
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
        web_data_feed("amazon_product", "https://amazon.com/dp/B08N5WRWNW") -> "{\"title\": \"Product Name\", ...}"
        web_data_feed("linkedin_person_profile", "https://linkedin.com/in/johndoe") -> "{\"name\": \"John Doe\", ...}"
        web_data_feed("facebook_company_reviews", "https://facebook.com/company", num_of_reviews=50) -> "[{\"review\": \"...\", ...}]"
    """
    api_key = context.get_secret("BRIGHTDATA_API_KEY")
    client = BrightDataClient.create_client(api_key=api_key)
    
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
    source_type: str,
    url: str,
    num_of_reviews: Optional[int] = None,
    timeout: int = 600,
    polling_interval: int = 1,
) -> Dict:
    """
    Extract structured data from various sources.
    """
    datasets = {
        "amazon_product": "gd_l7q7dkf244hwjntr0",
        "amazon_product_reviews": "gd_le8e811kzy4ggddlq",
        "linkedin_person_profile": "gd_l1viktl72bvl7bjuj0",
        "linkedin_company_profile": "gd_l1vikfnt1wgvvqz95w",
        "zoominfo_company_profile": "gd_m0ci4a4ivx3j5l6nx",
        "instagram_profiles": "gd_l1vikfch901nx3by4",
        "instagram_posts": "gd_lk5ns7kz21pck8jpis",
        "instagram_reels": "gd_lyclm20il4r5helnj",
        "instagram_comments": "gd_ltppn085pokosxh13",
        "facebook_posts": "gd_lyclm1571iy3mv57zw",
        "facebook_marketplace_listings": "gd_lvt9iwuh6fbcwmx1a",
        "facebook_company_reviews": "gd_m0dtqpiu1mbcyc2g86",
        "x_posts": "gd_lwxkxvnf1cynvib9co",
        "zillow_properties_listing": "gd_lfqkr8wm13ixtbd8f5",
        "booking_hotel_listings": "gd_m5mbdl081229ln6t4a",
        "youtube_videos": "gd_m5mbdl081229ln6t4a",
    }

    if source_type not in datasets:
        valid_sources = ", ".join(datasets.keys())
        raise ValueError(f"Invalid source_type: {source_type}. Valid options are: {valid_sources}")

    dataset_id = datasets[source_type]

    request_data = {"url": url}
    if source_type == "facebook_company_reviews" and num_of_reviews is not None:
        request_data["num_of_reviews"] = str(num_of_reviews)

    trigger_response = requests.post(
        "https://api.brightdata.com/datasets/v3/trigger",
        params={"dataset_id": dataset_id, "include_errors": True},
        headers=client.headers,
        json=[request_data],
    )

    trigger_data = trigger_response.json()
    if not trigger_data.get("snapshot_id"):
        raise Exception("No snapshot ID returned from trigger request")

    snapshot_id = trigger_data["snapshot_id"]

    attempts = 0
    max_attempts = timeout

    while attempts < max_attempts:
        try:
            snapshot_response = requests.get(
                f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
                params={"format": "json"},
                headers=client.headers,
            )

            snapshot_data = snapshot_response.json()

            if isinstance(snapshot_data, dict) and snapshot_data.get("status") in ("running", "building"):
                attempts += 1
                time.sleep(polling_interval)
                continue

            return snapshot_data

        except Exception:
            attempts += 1
            time.sleep(polling_interval)

    raise TimeoutError(f"Timeout after {max_attempts} seconds waiting for {source_type} data")