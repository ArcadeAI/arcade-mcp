from enum import Enum


class ConversationTypeSlackName(str, Enum):
    PUBLIC_CHANNEL = "public_channel"  # Public channels are visible to all users in the workspace
    PRIVATE_CHANNEL = "private_channel"  # Private channels are visible to only specific users
    MPIM = "mpim"  # Multi-person direct message conversation
    IM = "im"  # Two person direct message conversation


class ConversationType(str, Enum):
    PUBLIC_CHANNEL = "public_channel"
    PRIVATE_CHANNEL = "private_channel"
    MULTI_PERSON_DIRECT_MESSAGE = "multi_person_direct_message"
    DIRECT_MESSAGE = "direct_message"
