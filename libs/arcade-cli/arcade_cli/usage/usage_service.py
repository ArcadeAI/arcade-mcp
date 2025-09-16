from posthog import Posthog


class UsageService:
    def __init__(self) -> None:
        self.posthog = Posthog(
            project_api_key="",  # Staging project key (write-only)
            host="https://us.i.posthog.com",
        )
        self.posthog.debug = True
        self.posthog.disabled = True

    def capture(self, event_name: str, properties: dict) -> None:
        print(f"Capturing event: {event_name} with properties: {properties}")
        self.posthog.capture(event_name, distinct_id="1234567890", properties=properties)
