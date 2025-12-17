"""Tests for billing limits endpoint."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from arcade_serve.fastapi.billing import (
    BillingLimits,
    PlanType,
    create_billing_router,
    get_limits_for_plan,
)


class TestGetLimitsForPlan:
    """Test the get_limits_for_plan function."""

    def test_free_plan_limits(self) -> None:
        """Test that free plan has correct limits."""
        limits = get_limits_for_plan(PlanType.FREE)
        assert limits.deployments == 1
        assert limits.self_hosted_workers == 5
        assert limits.plan_type == PlanType.FREE

    def test_growth_plan_limits(self) -> None:
        """Test that growth plan has correct limits."""
        limits = get_limits_for_plan(PlanType.GROWTH)
        assert limits.deployments == 5
        assert limits.self_hosted_workers is None  # Unlimited
        assert limits.plan_type == PlanType.GROWTH

    def test_enterprise_plan_limits(self) -> None:
        """Test that enterprise plan has unlimited limits."""
        limits = get_limits_for_plan(PlanType.ENTERPRISE)
        assert limits.deployments is None  # Unlimited
        assert limits.self_hosted_workers is None  # Unlimited
        assert limits.plan_type == PlanType.ENTERPRISE


class TestBillingEndpoint:
    """Test the billing limits endpoint."""

    @pytest.fixture
    def app_with_auth(self) -> FastAPI:
        """Create a FastAPI app with billing routes and auth enabled."""
        app = FastAPI()
        router = create_billing_router(
            secret="test-secret-for-testing-purposes",
            disable_auth=False,
        )
        app.include_router(router)
        return app

    @pytest.fixture
    def app_without_auth(self) -> FastAPI:
        """Create a FastAPI app with billing routes and auth disabled."""
        app = FastAPI()
        router = create_billing_router(disable_auth=True)
        app.include_router(router)
        return app

    def test_get_limits_free_plan_no_auth(self, app_without_auth: FastAPI) -> None:
        """Test getting limits for free plan without authentication."""
        client = TestClient(app_without_auth)
        response = client.get(
            "/billing/limits",
            headers={
                "tenant-id": "test-tenant-123",
                "x-plan-type": "free",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "test-tenant-123"
        assert data["limits"]["deployments"] == 1
        assert data["limits"]["self_hosted_workers"] == 5
        assert data["limits"]["plan_type"] == "free"

    def test_get_limits_growth_plan_no_auth(self, app_without_auth: FastAPI) -> None:
        """Test getting limits for growth plan without authentication."""
        client = TestClient(app_without_auth)
        response = client.get(
            "/billing/limits",
            headers={
                "tenant-id": "test-tenant-456",
                "x-plan-type": "growth",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "test-tenant-456"
        assert data["limits"]["deployments"] == 5
        assert data["limits"]["self_hosted_workers"] is None
        assert data["limits"]["plan_type"] == "growth"

    def test_get_limits_enterprise_plan_no_auth(self, app_without_auth: FastAPI) -> None:
        """Test getting limits for enterprise plan without authentication."""
        client = TestClient(app_without_auth)
        response = client.get(
            "/billing/limits",
            headers={
                "tenant-id": "test-tenant-789",
                "x-plan-type": "enterprise",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "test-tenant-789"
        assert data["limits"]["deployments"] is None
        assert data["limits"]["self_hosted_workers"] is None
        assert data["limits"]["plan_type"] == "enterprise"

    def test_get_limits_defaults_to_free(self, app_without_auth: FastAPI) -> None:
        """Test that plan defaults to free when not specified."""
        client = TestClient(app_without_auth)
        response = client.get(
            "/billing/limits",
            headers={
                "tenant-id": "test-tenant-default",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "test-tenant-default"
        assert data["limits"]["deployments"] == 1
        assert data["limits"]["self_hosted_workers"] == 5
        assert data["limits"]["plan_type"] == "free"

    def test_get_limits_missing_tenant_id(self, app_without_auth: FastAPI) -> None:
        """Test that missing tenant_id returns 422."""
        client = TestClient(app_without_auth)
        response = client.get(
            "/billing/limits",
            headers={
                "x-plan-type": "free",
            },
        )
        assert response.status_code == 422

    def test_get_limits_requires_auth(self, app_with_auth: FastAPI) -> None:
        """Test that endpoint requires authentication when auth is enabled."""
        client = TestClient(app_with_auth)
        response = client.get(
            "/billing/limits",
            headers={
                "tenant-id": "test-tenant-123",
                "x-plan-type": "free",
            },
        )
        assert response.status_code == 401
        assert "authorization" in response.json()["detail"].lower()

    def test_get_limits_with_invalid_token(self, app_with_auth: FastAPI) -> None:
        """Test that invalid token returns 401."""
        client = TestClient(app_with_auth)
        response = client.get(
            "/billing/limits",
            headers={
                "tenant-id": "test-tenant-123",
                "x-plan-type": "free",
                "Authorization": "Bearer invalid-token",
            },
        )
        assert response.status_code == 401
