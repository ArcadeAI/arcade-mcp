from arcadepy import Arcade
from arcadepy.types import ToolDefinition
from arcadepy.types.shared import AuthorizationResponse


class ArcadeAuthMixin:
    """Mixin class providing authentication-related functionality for Arcade tools."""

    client: Arcade
    _tools: dict[str, ToolDefinition]

    def authorize(self, tool_name: str, user_id: str) -> AuthorizationResponse:
        """Authorize a user for a tool.

        Args:
            tool_name: The name of the tool to authorize.
            user_id: The user ID to authorize.

        Returns:
            AuthorizationResponse
        """
        return self.client.tools.authorize(tool_name=tool_name, user_id=user_id)

    def wait_for_completion(self, auth_response: AuthorizationResponse) -> AuthorizationResponse:
        """Wait for an authorization process to complete.

        Args:
            auth_response: The authorization response from the initial authorize call.

        Returns:
            AuthorizationResponse with completed status
        """
        return self.client.auth.wait_for_completion(auth_response)

    def is_authorized(self, authorization_id: str) -> bool:
        """Check if a tool authorization is complete."""
        return self.client.auth.status(id=authorization_id).status == "completed"

    def requires_auth(self, tool_name: str) -> bool:
        """Check if a tool requires authorization."""
        tool_def = self._tools.get(tool_name)
        if tool_def is None or tool_def.requirements is None:
            return False
        return tool_def.requirements.authorization is not None
