from enum import Enum


class ConversationType(str, Enum):
    PUBLIC_CHANNEL = "public_channel"  # Public channels are visible to all users in the workspace
    PRIVATE_CHANNEL = "private_channel"  # Private channels are visible to only specific users
    MPIM = "mpim"  # Multi-person direct message conversation
    IM = "im"  # Two person direct message conversation
