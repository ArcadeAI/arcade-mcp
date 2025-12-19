"""Track management for comparative evaluations.

A track represents an isolated tool registry with a unique name.
This enables running the same evaluation cases against different
tool sources (e.g., different MCP servers) for comparison.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from arcade_evals._evalsuite._tool_registry import EvalSuiteToolRegistry


class TrackManager:
    """Manages named tracks, each with its own isolated tool registry.

    Tracks enable comparative evaluations where the same cases are run
    against different tool sources.

    Example:
        manager = TrackManager()
        manager.create_track("Google Weather", registry1)
        manager.create_track("OpenWeather", registry2)

        for track_name in manager.get_track_names():
            registry = manager.get_registry(track_name)
            # Run cases against this registry
    """

    def __init__(self) -> None:
        self._tracks: dict[str, EvalSuiteToolRegistry] = {}

    def create_track(self, name: str, registry: EvalSuiteToolRegistry) -> str:
        """Create a new track with an isolated registry.

        Args:
            name: Unique track name.
            registry: The tool registry for this track.

        Returns:
            The track name (for use as track ID).

        Raises:
            ValueError: If track name already exists.
        """
        if name in self._tracks:
            raise ValueError(f"Track '{name}' already exists. Use a unique track name.")
        self._tracks[name] = registry
        return name

    def get_registry(self, track_name: str) -> EvalSuiteToolRegistry | None:
        """Get the registry for a track.

        Args:
            track_name: The track name.

        Returns:
            The registry if found, None otherwise.
        """
        return self._tracks.get(track_name)

    def get_track_names(self) -> list[str]:
        """Get all registered track names.

        Returns:
            List of track names in registration order.
        """
        return list(self._tracks.keys())

    def has_track(self, name: str) -> bool:
        """Check if a track exists.

        Args:
            name: The track name.

        Returns:
            True if track exists, False otherwise.
        """
        return name in self._tracks

    def track_count(self) -> int:
        """Get number of registered tracks.

        Returns:
            Number of tracks.
        """
        return len(self._tracks)

    def get_all_registries(self) -> dict[str, EvalSuiteToolRegistry]:
        """Get all registries by track name.

        Returns:
            Dictionary mapping track names to registries.
        """
        return dict(self._tracks)
