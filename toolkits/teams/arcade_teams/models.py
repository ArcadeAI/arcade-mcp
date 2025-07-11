from enum import Enum


class TeamMembershipType(Enum):
    DIRECT_MEMBER = "direct_member_of_the_team"
    MEMBER_OF_SHARED_CHANNEL = "member_of_a_shared_channel_in_another_team"
