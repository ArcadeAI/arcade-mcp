from typing import Annotated

from arcade_mcp_server import tool


@tool
def create_email_subject(
    email_content: Annotated[str, "The main topic or content of the email"],
    tone: Annotated[str, "Desired tone: 'professional', 'casual', or 'friendly'"] = "professional",
) -> dict[str, str]:
    """
    Generate an email subject line based on the email content.

    Useful when you need to create engaging subject lines that capture
    the essence of the email content. The subject should be concise and
    compelling while reflecting the main topic.
    """
    # In practice, this would use an AI model to generate the subject
    return {
        "subject": email_content[:60] + ("..." if len(email_content) > 60 else ""),
        "original_content": email_content,
        "tone_used": tone,
    }


@tool
def write_product_description(
    main_features: Annotated[str, "Key features or highlights of the product"],
    target_audience: Annotated[str, "Who this product is for"],
) -> dict[str, str]:
    """
    Create a marketing description for a product.

    The description should emphasize the key features while appealing
    to the target audience.
    """
    # In practice, this would use an AI model to craft the description
    description = f"Experience {main_features} designed for {target_audience}."

    return {
        "description": description,
        "features_highlighted": main_features,
        "target_audience": target_audience,
    }
