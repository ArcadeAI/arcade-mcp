"""
Billing and Usage Limits API

This module provides endpoints for retrieving billing limits and usage quotas
for different subscription plans.
"""

from enum import Enum
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from arcade_serve.core.auth import validate_engine_token


class PlanType(str, Enum):
    """Subscription plan types."""

    FREE = "free"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class BillingLimits(BaseModel):
    """Billing limits for a tenant."""

    deployments: int | None = Field(
        None,
        description="Maximum number of deployments allowed. None means unlimited.",
    )
    self_hosted_workers: int | None = Field(
        None,
        description="Maximum number of self-hosted workers allowed. None means unlimited.",
    )
    plan_type: PlanType = Field(
        ...,
        description="The subscription plan type",
    )


class BillingLimitsRequest(BaseModel):
    """Request model for fetching billing limits."""

    tenant_id: str = Field(
        ...,
        description="The tenant/organization ID to fetch limits for",
    )


class BillingLimitsResponse(BaseModel):
    """Response model containing billing limits."""

    tenant_id: str = Field(..., description="The tenant/organization ID")
    limits: BillingLimits = Field(..., description="The billing limits for this tenant")


def get_limits_for_plan(plan_type: PlanType) -> BillingLimits:
    """
    Get the billing limits for a given plan type.

    Plan limits:
    - Free: 1 deployment, 5 self-hosted workers
    - Growth: 5 deployments (for now), unlimited self-hosted workers
    - Enterprise: unlimited deployments and workers

    Args:
        plan_type: The subscription plan type

    Returns:
        BillingLimits object with the appropriate limits
    """
    if plan_type == PlanType.FREE:
        return BillingLimits(
            deployments=1,
            self_hosted_workers=5,
            plan_type=plan_type,
        )
    elif plan_type == PlanType.GROWTH:
        return BillingLimits(
            deployments=5,  # Limited to 5 for now as specified
            self_hosted_workers=None,  # Unlimited
            plan_type=plan_type,
        )
    elif plan_type == PlanType.ENTERPRISE:
        return BillingLimits(
            deployments=None,  # Unlimited
            self_hosted_workers=None,  # Unlimited
            plan_type=plan_type,
        )
    else:
        # Default to free plan for unknown types
        return BillingLimits(
            deployments=1,
            self_hosted_workers=5,
            plan_type=PlanType.FREE,
        )


def create_billing_router(
    secret: str | None = None,
    disable_auth: bool = False,
) -> APIRouter:
    """
    Create a FastAPI router with billing limits endpoints.

    Args:
        secret: Optional secret for JWT authentication
        disable_auth: Whether to disable authentication

    Returns:
        APIRouter configured with billing endpoints
    """
    router = APIRouter(
        prefix="/billing",
        tags=["Billing"],
        responses={
            401: {"description": "Unauthorized - Invalid or missing authentication token"},
            500: {"description": "Internal Server Error"},
        },
    )

    async def validate_auth(
        authorization: Annotated[Optional[str], Header()] = None,
    ) -> None:
        """Dependency to validate authentication token."""
        if disable_auth:
            return

        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract the token from "Bearer <token>"
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format. Expected 'Bearer <token>'",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = parts[1]
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error: no secret configured",
            )

        validation_result = validate_engine_token(secret, token)
        if not validation_result.valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token. Error: {validation_result.error}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @router.get(
        "/limits",
        response_model=BillingLimitsResponse,
        summary="Get billing limits",
        description="""
        Get the billing limits for a tenant based on their subscription plan.

        This endpoint returns usage limits including:
        - Maximum number of deployments
        - Maximum number of self-hosted workers

        The limits are determined by the tenant's subscription plan:
        - Free: 1 deployment, 5 self-hosted workers
        - Growth: 5 deployments, unlimited self-hosted workers
        - Enterprise: unlimited deployments and workers
        """,
        dependencies=[Depends(validate_auth)] if not disable_auth else [],
    )
    async def get_billing_limits(
        tenant_id: str = Header(..., description="The tenant/organization ID"),
        plan_type: PlanType = Header(
            PlanType.FREE,
            alias="x-plan-type",
            description="The subscription plan type (defaults to free if not provided)",
        ),
    ) -> BillingLimitsResponse:
        """
        Get billing limits for a tenant.

        Currently, this endpoint determines limits based on the plan_type header.
        In the future, this will query the database to fetch the actual plan
        associated with the tenant.

        Args:
            tenant_id: The tenant/organization ID (from header)
            plan_type: The subscription plan type (from header, defaults to FREE)

        Returns:
            BillingLimitsResponse containing the limits for the tenant
        """
        limits = get_limits_for_plan(plan_type)

        return BillingLimitsResponse(
            tenant_id=tenant_id,
            limits=limits,
        )

    return router
