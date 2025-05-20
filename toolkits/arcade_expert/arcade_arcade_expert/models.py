import validators
from pydantic import BaseModel


class Links(BaseModel):
    links: list[str]

    def validate_links(self) -> None:
        """Validate links, removing any invalid ones"""
        valid_links = []

        for link in self.links:
            if validators.url(link):
                valid_links.append(link)

        self.links = valid_links
