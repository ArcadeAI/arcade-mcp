# Billing Limits Endpoint

This module provides a FastAPI endpoint for retrieving billing limits based on subscription plans. It's designed to be used by the Arcade Engine to enforce usage limits for different tenant plans.

## Features

- **Plan-based limits**: Different subscription tiers (Free, Growth, Enterprise) have different limits
- **JWT Authentication**: Secure endpoint using the same JWT authentication as worker endpoints
- **Easy integration**: Simple router that can be added to any FastAPI application
- **Database-ready**: Structured to easily integrate with database queries in the future

## Usage

### Basic Setup

```python
from fastapi import FastAPI
from arcade_serve.fastapi import create_billing_router

app = FastAPI()

# Create and include the billing router
billing_router = create_billing_router(
    secret="your-worker-secret",
    disable_auth=False,  # Set to True for testing
)
app.include_router(billing_router)
```

### Making Requests

The endpoint expects two headers:
- `tenant-id`: The organization/tenant identifier
- `x-plan-type`: The subscription plan type (free, growth, or enterprise)

#### Example with curl

```bash
# Free plan (1 deployment, 5 self-hosted workers)
curl -X GET http://localhost:8000/billing/limits \
  -H "tenant-id: org-123" \
  -H "x-plan-type: free" \
  -H "Authorization: Bearer <jwt-token>"

# Growth plan (5 deployments, unlimited self-hosted workers)
curl -X GET http://localhost:8000/billing/limits \
  -H "tenant-id: org-456" \
  -H "x-plan-type: growth" \
  -H "Authorization: Bearer <jwt-token>"

# Enterprise plan (unlimited deployments and workers)
curl -X GET http://localhost:8000/billing/limits \
  -H "tenant-id: org-789" \
  -H "x-plan-type: enterprise" \
  -H "Authorization: Bearer <jwt-token>"
```

#### Example with Python

```python
import httpx
import jwt
import time

# Generate a JWT token (same format as engine tokens)
secret = "your-worker-secret"
token = jwt.encode(
    {
        "ver": "1",
        "aud": "worker",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,  # 1 hour expiration
    },
    secret,
    algorithm="HS256",
)

# Make the request
response = httpx.get(
    "http://localhost:8000/billing/limits",
    headers={
        "tenant-id": "org-123",
        "x-plan-type": "growth",
        "Authorization": f"Bearer {token}",
    },
)

print(response.json())
# Output:
# {
#   "tenant_id": "org-123",
#   "limits": {
#     "deployments": 5,
#     "self_hosted_workers": null,  # null means unlimited
#     "plan_type": "growth"
#   }
# }
```

## Plan Limits

| Plan       | Deployments | Self-Hosted Workers |
|------------|-------------|---------------------|
| Free       | 1           | 5                   |
| Growth     | 5           | Unlimited           |
| Enterprise | Unlimited   | Unlimited           |

Note: Growth plan is currently limited to 5 deployments, but this will change based on business requirements.

## Response Format

### Success Response (200 OK)

```json
{
  "tenant_id": "org-123",
  "limits": {
    "deployments": 5,
    "self_hosted_workers": null,
    "plan_type": "growth"
  }
}
```

- `deployments`: Maximum number of deployments allowed. `null` means unlimited.
- `self_hosted_workers`: Maximum number of self-hosted workers allowed. `null` means unlimited.
- `plan_type`: The subscription plan type.

### Error Responses

#### 401 Unauthorized

```json
{
  "detail": "Invalid token. Error: Signature has expired"
}
```

#### 422 Validation Error

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["header", "tenant-id"],
      "msg": "Field required"
    }
  ]
}
```

## Authentication

The endpoint uses the same JWT authentication as Arcade worker endpoints:

- **Algorithm**: HS256
- **Audience**: "worker"
- **Token Version**: "1"
- **Header Format**: `Authorization: Bearer <token>`

### Token Payload

```json
{
  "ver": "1",
  "aud": "worker",
  "iat": 1234567890,
  "exp": 1234571490
}
```

## Integration with Database

Currently, the endpoint determines limits based on the `x-plan-type` header. To integrate with a database:

1. **Modify the endpoint handler** to query the database instead of using the header:

```python
@router.get("/limits")
async def get_billing_limits(
    tenant_id: str = Header(...),
    db: Session = Depends(get_db),  # Your database dependency
) -> BillingLimitsResponse:
    # Query the database for the tenant's plan
    tenant = db.query(OrganizationToAccount).filter_by(
        organization_id=tenant_id
    ).first()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get the plan type from the customer table
    customer = db.query(Customer).filter_by(
        id=tenant.customer_id
    ).first()
    
    plan_type = PlanType(customer.plan_id)
    limits = get_limits_for_plan(plan_type)
    
    return BillingLimitsResponse(
        tenant_id=tenant_id,
        limits=limits,
    )
```

2. **Database Schema** (example):

```sql
-- Organization to account mapping
CREATE TABLE organization_to_account (
    id UUID PRIMARY KEY,
    organization_id VARCHAR NOT NULL,
    customer_id UUID NOT NULL,
    worker_allowance INT,  -- Could be used to override default limits
    created_at TIMESTAMP DEFAULT NOW()
);

-- Customer/billing information
CREATE TABLE customer (
    id UUID PRIMARY KEY,
    plan_id VARCHAR NOT NULL,  -- 'free', 'growth', 'enterprise'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

3. **Caching**: For production use, consider caching the limits to reduce database load:

```python
from functools import lru_cache
from datetime import datetime, timedelta

# Simple in-memory cache with TTL
_cache = {}
_cache_ttl = timedelta(minutes=5)

async def get_billing_limits_cached(tenant_id: str) -> BillingLimitsResponse:
    cache_key = f"limits:{tenant_id}"
    
    if cache_key in _cache:
        cached_data, cached_time = _cache[cache_key]
        if datetime.now() - cached_time < _cache_ttl:
            return cached_data
    
    # Fetch from database
    limits = await get_billing_limits_from_db(tenant_id)
    
    # Cache the result
    _cache[cache_key] = (limits, datetime.now())
    
    return limits
```

## Testing

Run the tests with:

```bash
pytest libs/tests/worker/test_billing.py -v
```

## Future Enhancements

1. **Usage Tracking**: Add endpoints for tracking current usage against limits
2. **Overage Handling**: Support for soft limits with overage charges
3. **Custom Limits**: Allow per-tenant custom limits that override plan defaults
4. **Webhooks**: Integration with Orb webhooks to update limits based on subscription changes
5. **Metrics**: Add OpenTelemetry metrics for limit checks and violations

## See Also

- [arcade-serve FastAPI Worker](../README.md)
- [Example Usage](../../examples/billing_limits_example.py)
- [Linear Issue PLT-368](https://linear.app/arcadedev/issue/PLT-368)
