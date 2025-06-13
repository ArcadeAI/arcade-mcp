from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_stripe
from arcade_stripe.tools.stripe import (
    create_billing_portal_session,
    create_customer,
    create_invoice,
    create_invoice_item,
    create_payment_link,
    create_price,
    create_product,
    create_refund,
    finalize_invoice,
    list_customers,
    list_invoices,
    list_payment_intents,
    list_prices,
    list_products,
    retrieve_balance,
)

rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_stripe)


@tool_eval()
def stripe_eval_suite() -> EvalSuite:
    """Evaluation suite for Stripe Tools."""
    suite = EvalSuite(
        name="Stripe Tools Evaluation Suite",
        system_message=(
            "You are an AI assistant that helps users "
            "interact with Stripe using the provided tools."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Create a customer",
        user_message=(
            "add 'Alice Jenner' to my customers. she has a gmail that is just her first name"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_customer,
                args={"name": "Alice Jenner", "email": "alice@gmail.com"},
            )
        ],
        critics=[
            BinaryCritic(critic_field="name", weight=0.5),
            BinaryCritic(critic_field="email", weight=0.5),
        ],
    )

    suite.add_case(
        name="List customers with limit",
        user_message="get 5 customers",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_customers,
                args={
                    "limit": 5,
                    "email": None,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="limit", weight=1.0),
        ],
    )

    suite.add_case(
        name="Create a product",
        user_message=(
            "Create a product named 'Pro Subscription' that provides: "
            "- Higher rate limits"
            "- Priority support"
            "- Early access to new features"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_product,
                args={
                    "name": "Pro Subscription",
                    "description": (
                        "Provides higher rate limits, priority support, "
                        "and early access to new features."
                    ),
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="name", weight=0.6),
            SimilarityCritic(
                critic_field="description",
                weight=0.4,
                similarity_threshold=0.75,
            ),
        ],
    )

    suite.add_case(
        name="List products",
        user_message="List 10 of my products.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_products,
                args={
                    "limit": 10,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="limit", weight=1.0),
        ],
    )

    suite.add_case(
        name="Create a price",
        user_message="Create a price of $1298.99 for product 'prod_ABC123' in us currency.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_price,
                args={
                    "product": "prod_ABC123",
                    "unit_amount": 129899,
                    "currency": "usd",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="product", weight=0.4),
            BinaryCritic(critic_field="unit_amount", weight=0.3),
            SimilarityCritic(
                critic_field="currency",
                weight=0.3,
                similarity_threshold=0.95,
            ),
        ],
    )

    suite.add_case(
        name="Create a payment link",
        user_message=(
            "Joe needs a link to pay for my product. price is 'price_XYZ789'. create it please"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_payment_link,
                args={
                    "price": "price_XYZ789",
                    "quantity": 1,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="price", weight=0.5),
            BinaryCritic(critic_field="quantity", weight=0.5),
        ],
    )

    suite.add_case(
        name="Retrieve balance",
        user_message="How much money do i have",
        expected_tool_calls=[
            ExpectedToolCall(
                func=retrieve_balance,
                args={},
            )
        ],
        critics=[],
    )

    suite.add_case(
        name="Create a refund",
        user_message="Refund the payment intent 'pi_789XYZ' for 5 bucks.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_refund,
                args={
                    "payment_intent": "pi_789XYZ",
                    "amount": 500,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="payment_intent", weight=0.5),
            BinaryCritic(critic_field="amount", weight=0.5),
        ],
    )

    suite.add_case(
        name="Create billing portal session",
        user_message="Create a billing portal session for customer 'cus_test123' with return URL 'https://example.com/return'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_billing_portal_session,
                args={
                    "customer": "cus_test123",
                    "return_url": "https://example.com/return",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="customer", weight=0.6),
            BinaryCritic(critic_field="return_url", weight=0.4),
        ],
    )

    suite.add_case(
        name="List prices for a product",
        user_message="what are the prices for my product 'prod_ABC123'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_prices,
                args={
                    "product": "prod_ABC123",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="product", weight=1.0),
        ],
    )

    suite.add_case(
        name="List invoices for a customer",
        user_message="get invoices for my customer 'cus_456def'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_invoices,
                args={
                    "customer": "cus_456def",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="customer", weight=1.0),
        ],
    )

    suite.add_case(
        name="Create an invoice",
        user_message="Create an invoice for my customer 'cus_456def' with 15 days until due.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_invoice,
                args={
                    "customer": "cus_456def",
                    "days_until_due": 15,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="customer", weight=0.5),
            BinaryCritic(critic_field="days_until_due", weight=0.5),
        ],
    )

    suite.add_case(
        name="Create an invoice item",
        user_message=(
            "Create an invoice item for my customer 'cus_456def' "
            "for price 'price_789ghi' on invoice 'in_123test'."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_invoice_item,
                args={
                    "customer": "cus_456def",
                    "price": "price_789ghi",
                    "invoice": "in_123test",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="customer", weight=0.33),
            BinaryCritic(critic_field="price", weight=0.33),
            BinaryCritic(critic_field="invoice", weight=0.34),
        ],
    )

    suite.add_case(
        name="Finalize an invoice",
        user_message="Make 'in_123test' finalized.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=finalize_invoice,
                args={"invoice": "in_123test"},
            )
        ],
        critics=[
            BinaryCritic(critic_field="invoice", weight=1.0),
        ],
    )

    suite.add_case(
        name="List payment intents for a customer",
        user_message="get payment intents for my customer 'cus_456def'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_payment_intents,
                args={"customer": "cus_456def"},
            )
        ],
        critics=[
            BinaryCritic(critic_field="customer", weight=1.0),
        ],
    )

    return suite
