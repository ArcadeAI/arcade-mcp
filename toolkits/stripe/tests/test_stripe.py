import pytest

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


class DummyContext:
    def get_secret(self, key: str):
        return "test_secret_key"


class DummyStripeAPI:
    def __init__(self, secret_key, context):
        self.secret_key = secret_key

    def run(self, method_name, **params):
        return {"method": method_name, "params": params}


@pytest.mark.parametrize(
    ("current_tool", "params"),
    [
        (create_customer, {"name": "John Doe"}),
        (create_customer, {"name": "John Doe", "email": "john.doe@example.com"}),
        (list_customers, {}),
        (list_customers, {"limit": 10}),
        (list_customers, {"email": "john.doe@example.com"}),
        (list_customers, {"limit": 10, "email": "john.doe@example.com"}),
        (create_product, {"name": "Product 1"}),
        (create_product, {"name": "Product 1", "description": "Description 1"}),
        (list_products, {}),
        (list_products, {"limit": 10}),
        (create_price, {"product": "product_123", "unit_amount": 1000, "currency": "usd"}),
        (list_prices, {}),
        (list_prices, {"product": "product_123"}),
        (list_prices, {"limit": 10}),
        (list_prices, {"product": "product_123", "limit": 10}),
        (create_payment_link, {"price": "price_123", "quantity": 100}),
        (list_invoices, {}),
        (list_invoices, {"customer": "customer_123"}),
        (list_invoices, {"limit": 10}),
        (list_invoices, {"customer": "customer_123", "limit": 10}),
        (create_invoice, {"customer": "customer_123"}),
        (create_invoice, {"customer": "customer_123", "days_until_due": 30}),
        (
            create_invoice_item,
            {"customer": "customer_123", "price": "price_123", "invoice": "invoice_123"},
        ),
        (finalize_invoice, {"invoice": "invoice_123"}),
        (retrieve_balance, {}),
        (create_refund, {"payment_intent": "payment_intent_123"}),
        (create_refund, {"payment_intent": "payment_intent_123", "amount": 100}),
        (list_payment_intents, {}),
        (list_payment_intents, {"customer": "customer_123"}),
        (list_payment_intents, {"limit": 10}),
        (list_payment_intents, {"customer": "customer_123", "limit": 10}),
        (create_billing_portal_session, {"customer": "customer_123"}),
        (
            create_billing_portal_session,
            {"customer": "customer_123", "return_url": "https://example.com"},
        ),
    ],
)
def test_stripe_tools(monkeypatch, current_tool, params):
    monkeypatch.setattr("arcade_stripe.tools.stripe.StripeAPI", DummyStripeAPI)

    context = DummyContext()

    result = current_tool(context, **params)
    expected = {"method": current_tool.__name__, "params": params}

    assert result == expected
