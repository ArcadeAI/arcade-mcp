from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_search
from arcade_search.constants import (
    DEFAULT_GOOGLE_MAPS_COUNTRY,
    DEFAULT_GOOGLE_MAPS_DISTANCE_UNIT,
    DEFAULT_GOOGLE_MAPS_LANGUAGE,
    DEFAULT_GOOGLE_MAPS_TRAVEL_MODE,
)
from arcade_search.enums import GoogleMapsDistanceUnit, GoogleMapsTravelMode
from arcade_search.tools.google_maps import (
    get_directions_between_addresses,
    get_directions_between_coordinates,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)

catalog = ToolCatalog()
# Register the Google Search tool
catalog.add_module(arcade_search)


@tool_eval()
def google_maps_directions_by_addresses_eval_suite() -> EvalSuite:
    """Create an evaluation suite for the Google Maps Directions tools."""
    suite = EvalSuite(
        name="Google Maps Directions Tool Evaluation",
        system_message="You are an AI assistant that can get directions from Google Maps using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get directions between two addresses",
        user_message="Get directions from Google Maps between the following addresses: 1600 Amphitheatre Parkway, Mountain View, CA 94043 and 1 Infinite Loop, Cupertino, CA 95014.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_directions_between_addresses,
                args={
                    "origin_address": "1600 Amphitheatre Parkway, Mountain View, CA 94043",
                    "destination_address": "1 Infinite Loop, Cupertino, CA 95014",
                    "language": DEFAULT_GOOGLE_MAPS_LANGUAGE,
                    "country": DEFAULT_GOOGLE_MAPS_COUNTRY,
                    "distance_unit": DEFAULT_GOOGLE_MAPS_DISTANCE_UNIT,
                    "travel_mode": DEFAULT_GOOGLE_MAPS_TRAVEL_MODE,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="origin_address", weight=0.3),
            SimilarityCritic(critic_field="destination_address", weight=0.3),
            BinaryCritic(critic_field="language", weight=0.1),
            BinaryCritic(critic_field="country", weight=0.1),
            BinaryCritic(critic_field="distance_unit", weight=0.1),
            BinaryCritic(critic_field="travel_mode", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get directions between two addresses with custom distance unit and travel mode",
        user_message="Get walking directions from Google Maps between the following addresses in miles: 1600 Amphitheatre Parkway, Mountain View, CA 94043 and 1 Infinite Loop, Cupertino, CA 95014.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_directions_between_addresses,
                args={
                    "origin_address": "1600 Amphitheatre Parkway, Mountain View, CA 94043",
                    "destination_address": "1 Infinite Loop, Cupertino, CA 95014",
                    "language": DEFAULT_GOOGLE_MAPS_LANGUAGE,
                    "country": DEFAULT_GOOGLE_MAPS_COUNTRY,
                    "distance_unit": GoogleMapsDistanceUnit.MILES.value,
                    "travel_mode": GoogleMapsTravelMode.WALKING.value,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="origin_address", weight=0.3),
            SimilarityCritic(critic_field="destination_address", weight=0.3),
            BinaryCritic(critic_field="language", weight=0.1),
            BinaryCritic(critic_field="country", weight=0.1),
            BinaryCritic(critic_field="distance_unit", weight=0.1),
            BinaryCritic(critic_field="travel_mode", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get directions between two addresses in a given country and language",
        user_message="Get directions from Google Maps in Portuguese between the following addresses in Brazil: Rua do Amendoim, 1, Belo Horizonte, MG and Av. do Descobrimento, 515, Porto Seguro, BA.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_directions_between_addresses,
                args={
                    "origin_address": "Rua do Amendoim, 1, Belo Horizonte, MG",
                    "destination_address": "Av. do Descobrimento, 515, Porto Seguro, BA",
                    "language": "pt",
                    "country": "br",
                    "distance_unit": DEFAULT_GOOGLE_MAPS_DISTANCE_UNIT,
                    "travel_mode": DEFAULT_GOOGLE_MAPS_TRAVEL_MODE,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="origin_address", weight=0.3),
            SimilarityCritic(critic_field="destination_address", weight=0.3),
            BinaryCritic(critic_field="language", weight=0.1),
            BinaryCritic(critic_field="country", weight=0.1),
            BinaryCritic(critic_field="distance_unit", weight=0.1),
            BinaryCritic(critic_field="travel_mode", weight=0.1),
        ],
    )

    return suite


@tool_eval()
def google_maps_directions_by_coordinates_eval_suite() -> EvalSuite:
    """Create an evaluation suite for the Google Maps Directions tools."""
    suite = EvalSuite(
        name="Google Maps Directions Tool Evaluation",
        system_message="You are an AI assistant that can get directions from Google Maps using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get directions between two coordinates",
        user_message="Get directions from Google Maps between the following coordinates: 37.422740,-122.084961 and 37.331820,-122.031180.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_directions_between_coordinates,
                args={
                    "origin_latitude": "37.422740",
                    "origin_longitude": "-122.084961",
                    "destination_latitude": "37.331820",
                    "destination_longitude": "-122.031180",
                    "language": DEFAULT_GOOGLE_MAPS_LANGUAGE,
                    "country": DEFAULT_GOOGLE_MAPS_COUNTRY,
                    "distance_unit": DEFAULT_GOOGLE_MAPS_DISTANCE_UNIT,
                    "travel_mode": DEFAULT_GOOGLE_MAPS_TRAVEL_MODE,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="origin_latitude", weight=0.15),
            SimilarityCritic(critic_field="origin_longitude", weight=0.15),
            SimilarityCritic(critic_field="destination_latitude", weight=0.15),
            SimilarityCritic(critic_field="destination_longitude", weight=0.15),
            BinaryCritic(critic_field="language", weight=0.1),
            BinaryCritic(critic_field="country", weight=0.1),
            BinaryCritic(critic_field="distance_unit", weight=0.1),
            BinaryCritic(critic_field="travel_mode", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get directions between two coordinates with custom distance unit and travel mode",
        user_message="Get walking directions from Google Maps between the following coordinates in miles: 37.422740,-122.084961 and 37.331820,-122.031180.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_directions_between_coordinates,
                args={
                    "origin_latitude": "37.422740",
                    "origin_longitude": "-122.084961",
                    "destination_latitude": "37.331820",
                    "destination_longitude": "-122.031180",
                    "language": DEFAULT_GOOGLE_MAPS_LANGUAGE,
                    "country": DEFAULT_GOOGLE_MAPS_COUNTRY,
                    "distance_unit": GoogleMapsDistanceUnit.MILES.value,
                    "travel_mode": GoogleMapsTravelMode.WALKING.value,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="origin_latitude", weight=0.15),
            SimilarityCritic(critic_field="origin_longitude", weight=0.15),
            SimilarityCritic(critic_field="destination_latitude", weight=0.15),
            SimilarityCritic(critic_field="destination_longitude", weight=0.15),
            BinaryCritic(critic_field="language", weight=0.1),
            BinaryCritic(critic_field="country", weight=0.1),
            BinaryCritic(critic_field="distance_unit", weight=0.1),
            BinaryCritic(critic_field="travel_mode", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get directions between two coordinates in a given country and language",
        user_message="Get directions from Google Maps in Portuguese between the following coordinates in Brazil: 37.422740,-122.084961 and 37.331820,-122.031180.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_directions_between_coordinates,
                args={
                    "origin_latitude": "37.422740",
                    "origin_longitude": "-122.084961",
                    "destination_latitude": "37.331820",
                    "destination_longitude": "-122.031180",
                    "language": "pt",
                    "country": "br",
                    "distance_unit": DEFAULT_GOOGLE_MAPS_DISTANCE_UNIT,
                    "travel_mode": DEFAULT_GOOGLE_MAPS_TRAVEL_MODE,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="origin_latitude", weight=0.15),
            SimilarityCritic(critic_field="origin_longitude", weight=0.15),
            SimilarityCritic(critic_field="destination_latitude", weight=0.15),
            SimilarityCritic(critic_field="destination_longitude", weight=0.15),
            BinaryCritic(critic_field="language", weight=0.1),
            BinaryCritic(critic_field="country", weight=0.1),
            BinaryCritic(critic_field="distance_unit", weight=0.1),
            BinaryCritic(critic_field="travel_mode", weight=0.1),
        ],
    )

    return suite
