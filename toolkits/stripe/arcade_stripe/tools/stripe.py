from typing import Annotated

from arcade_tdk import ToolContext, tool
from stripe_agent_toolkit.api import StripeAPI


def run_stripe_tool(context: ToolContext, method_name: str, params: dict) -> str:
    """
    Helper function that retrieves the Stripe secret key, initializes the API,
    and executes the specified method with the provided parameters.
    """
    api_key = context.get_secret("STRIPE_SECRET_KEY")
    stripe_api = StripeAPI(secret_key=api_key, context=None)
    params = {k: v for k, v in params.items() if v is not None}
    return stripe_api.run(method_name, **params)  # type: ignore[no-any-return]


@tool(requires_secrets=["STRIPE_SECRET_KEY"])
def create_customer(
    context: ToolContext,
    name: Annotated[str, "The name of the customer."],
    email: Annotated[str | None, "The email of the customer."] = None,
) -> Annotated[str, "This tool will create a customer in Stripe."]:
    """This tool will create a customer in Stripe."""
    return run_stripe_tool(context, "create_customer", {"name": name, "email": email})


@tool(requires_secrets=["STRIPE_SECRET_KEY"])
def list_customers(
    context: ToolContext,
    limit: Annotated[
        int | None,
        "A limit on the number of objects to be returned. Limit can range between 1 and 100.",
    ] = None,
    email: Annotated[
        str | None,
        "A case-sensitive filter on the list based on the customer's email field. "
        "The value must be a string.",
    ] = None,
) -> Annotated[str, "This tool will fetch a list of Customers from Stripe."]:
    """This tool will fetch a list of Customers from Stripe."""
    return run_stripe_tool(context, "list_customers", {"limit": limit, "email": email})


@tool(requires_secrets=["STRIPE_SECRET_KEY"])
def create_product(
    context: ToolContext,
    name: Annotated[str, "The name of the product."],
    description: Annotated[str | None, "The description of the product."] = None,
) -> Annotated[str, "This tool will create a product in Stripe."]:
    """This tool will create a product in Stripe."""
    return run_stripe_tool(context, "create_product", {"name": name, "description": description})


@tool(requires_secrets=["STRIPE_SECRET_KEY"])
def list_products(
    context: ToolContext,
    limit: Annotated[
        int | None,
        "A limit on the number of objects to be returned. Limit can range between 1 and 100, "
        "and the default is 10.",
    ] = None,
) -> Annotated[str, "This tool will fetch a list of Products from Stripe."]:
    """This tool will fetch a list of Products from Stripe."""
    return run_stripe_tool(context, "list_products", {"limit": limit})


@tool(requires_secrets=["STRIPE_SECRET_KEY"])
def create_price(
    context: ToolContext,
    product: Annotated[str, "The ID of the product to create the price for."],
    unit_amount: Annotated[int, "The unit amount of the price in cents."],
    currency: Annotated[str, "The currency of the price."],
) -> Annotated[str, "This tool will create a price in Stripe. If a product has not already been"]:
    """This tool will create a price in Stripe. If a product has not already been"""
    return run_stripe_tool(
        context,
        "create_price",
        {"product": product, "unit_amount": unit_amount, "currency": currency},
    )


@tool(requires_secrets=["STRIPE_SECRET_KEY"])
def list_prices(
    context: ToolContext,
    product: Annotated[str | None, "The ID of the product to list prices for."] = None,
    limit: Annotated[
        int | None,
        "A limit on the number of objects to be returned. Limit can range between 1 and 100, "
        "and the default is 10.",
    ] = None,
) -> Annotated[str, "This tool will fetch a list of Prices from Stripe."]:
    """This tool will fetch a list of Prices from Stripe."""
    return run_stripe_tool(context, "list_prices", {"product": product, "limit": limit})


@tool(requires_secrets=["STRIPE_SECRET_KEY"])
def create_payment_link(
    context: ToolContext,
    price: Annotated[str, "The ID of the price to create the payment link for."],
    quantity: Annotated[int, "The quantity of the product to include."],
) -> Annotated[str, "This tool will create a payment link in Stripe."]:
    """This tool will create a payment link in Stripe."""
    return run_stripe_tool(context, "create_payment_link", {"price": price, "quantity": quantity})


@tool(requires_secrets=["STRIPE_SECRET_KEY"])
def list_invoices(
    context: ToolContext,
    customer: Annotated[str | None, "The ID of the customer to list invoices for."] = None,
    limit: Annotated[
        int | None,
        "A limit on the number of objects to be returned. Limit can range between 1 and 100, "
        "and the default is 10.",
    ] = None,
) -> Annotated[str, "This tool will list invoices in Stripe."]:
    """This tool will list invoices in Stripe."""
    return run_stripe_tool(context, "list_invoices", {"customer": customer, "limit": limit})


@tool(requires_secrets=["STRIPE_SECRET_KEY"])
def create_invoice(
    context: ToolContext,
    customer: Annotated[str, "The ID of the customer to create the invoice for."],
    days_until_due: Annotated[int | None, "The number of days until the invoice is due."] = None,
) -> Annotated[str, "This tool will create an invoice in Stripe."]:
    """This tool will create an invoice in Stripe."""
    return run_stripe_tool(
        context, "create_invoice", {"customer": customer, "days_until_due": days_until_due}
    )


@tool(requires_secrets=["STRIPE_SECRET_KEY"])
def create_invoice_item(
    context: ToolContext,
    customer: Annotated[str, "The ID of the customer to create the invoice item for."],
    price: Annotated[str, "The ID of the price for the item."],
    invoice: Annotated[str, "The ID of the invoice to create the item for."],
) -> Annotated[str, "This tool will create an invoice item in Stripe."]:
    """This tool will create an invoice item in Stripe."""
    return run_stripe_tool(
        context, "create_invoice_item", {"customer": customer, "price": price, "invoice": invoice}
    )


@tool(requires_secrets=["STRIPE_SECRET_KEY"])
def finalize_invoice(
    context: ToolContext, invoice: Annotated[str, "The ID of the invoice to finalize."]
) -> Annotated[str, "This tool will finalize an invoice in Stripe."]:
    """This tool will finalize an invoice in Stripe."""
    return run_stripe_tool(context, "finalize_invoice", {"invoice": invoice})


@tool(requires_secrets=["STRIPE_SECRET_KEY"])
def retrieve_balance(
    context: ToolContext,
) -> Annotated[str, "This tool will retrieve the balance from Stripe. It takes no input."]:
    """This tool will retrieve the balance from Stripe. It takes no input."""
    return run_stripe_tool(context, "retrieve_balance", {})


@tool(requires_secrets=["STRIPE_SECRET_KEY"])
def create_refund(
    context: ToolContext,
    payment_intent: Annotated[str, "The ID of the PaymentIntent to refund."],
    amount: Annotated[int | None, "The amount to refund in cents."] = None,
) -> Annotated[str, "This tool will refund a payment intent in Stripe."]:
    """This tool will refund a payment intent in Stripe."""
    return run_stripe_tool(
        context, "create_refund", {"payment_intent": payment_intent, "amount": amount}
    )


@tool(requires_secrets=["STRIPE_SECRET_KEY"])
def list_payment_intents(
    context: ToolContext,
    customer: Annotated[str | None, "The ID of the customer to list payment intents for."] = None,
    limit: Annotated[
        int | None,
        "A limit on the number of objects to be returned. Limit can range between 1 and 100.",
    ] = None,
) -> Annotated[str, "This tool will list payment intents in Stripe."]:
    """This tool will list payment intents in Stripe."""
    return run_stripe_tool(context, "list_payment_intents", {"customer": customer, "limit": limit})


@tool(requires_secrets=["STRIPE_SECRET_KEY"])
def create_billing_portal_session(
    context: ToolContext,
    customer: Annotated[str, "The ID of the customer to create the billing portal session for."],
    return_url: Annotated[str | None, "The default URL to return to afterwards."] = None,
) -> Annotated[str, "This tool will create a billing portal session."]:
    """This tool will create a billing portal session."""
    return run_stripe_tool(
        context, "create_billing_portal_session", {"customer": customer, "return_url": return_url}
    )
