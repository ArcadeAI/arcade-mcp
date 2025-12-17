# Billing Limits Endpoint Implementation Summary

## Overview

This implementation adds a new billing limits endpoint to the Arcade cloud service that allows the Engine to fetch usage limits based on subscription plans.

## What Was Created

### 1. Core Module: `/libs/arcade-serve/arcade_serve/fastapi/billing.py`

A new FastAPI module containing:

- **PlanType Enum**: Defines subscription tiers (FREE, GROWTH, ENTERPRISE)
- **BillingLimits Model**: Pydantic model for limit data
- **BillingLimitsResponse Model**: Response schema
- **get_limits_for_plan()**: Function to retrieve limits based on plan type
- **create_billing_router()**: Factory function to create the FastAPI router with authentication

#### Plan Limits

| Plan       | Deployments | Self-Hosted Workers |
|------------|-------------|---------------------|
| Free       | 1           | 5                   |
| Growth     | 5           | Unlimited (null)    |
| Enterprise | Unlimited   | Unlimited (null)    |

### 2. Tests: `/libs/tests/worker/test_billing.py`

Comprehensive test suite with 10 test cases covering:
- Plan limit validation for all three tiers
- Endpoint responses with/without authentication
- Default behavior (defaults to FREE plan)
- Error cases (missing tenant_id, invalid tokens)

**All tests pass ✓**

### 3. Example Application: `/examples/billing_limits_example.py`

A working example showing how to:
- Create a FastAPI app with the billing router
- Configure authentication
- Make requests with curl and Python

### 4. Documentation: `/libs/arcade-serve/README_BILLING.md`

Comprehensive documentation including:
- Usage instructions
- Request/response formats
- Authentication details
- Database integration guide (for future implementation)
- Caching recommendations
- Example code snippets

### 5. Version Updates

Updated `arcade-serve` version from `3.2.1` to `3.3.0` following semantic versioning rules.

## API Endpoint

### `GET /billing/limits`

**Headers:**
- `tenant-id`: Organization/tenant identifier (required)
- `x-plan-type`: Plan type - "free", "growth", or "enterprise" (optional, defaults to "free")
- `Authorization`: Bearer token (required when auth is enabled)

**Response:**
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

## Authentication

The endpoint uses JWT authentication compatible with Arcade Engine tokens:
- Algorithm: HS256
- Audience: "worker"
- Token version: "1"
- Can be disabled for testing with `disable_auth=True`

## Database Integration (Future)

The implementation is structured to easily integrate with a database:

1. Currently uses `x-plan-type` header to determine plan
2. Can be modified to query `organization_to_account` and `customer` tables
3. Documentation includes SQL schema examples and integration code

Suggested database schema:
```sql
CREATE TABLE organization_to_account (
    organization_id VARCHAR PRIMARY KEY,
    customer_id UUID NOT NULL,
    worker_allowance INT
);

CREATE TABLE customer (
    id UUID PRIMARY KEY,
    plan_id VARCHAR NOT NULL  -- 'free', 'growth', 'enterprise'
);
```

## Caching

For production use, the documentation recommends caching limits with a 5-minute TTL to reduce database load.

## Testing

Run tests:
```bash
pytest libs/tests/worker/test_billing.py -v
```

All 10 tests pass with 91% code coverage on the billing module.

## Code Quality

- ✓ All tests passing
- ✓ Type checking passes (mypy)
- ✓ Linting passes (ruff)
- ✓ Follows existing code patterns
- ✓ Comprehensive documentation

## Next Steps (Not Implemented Yet - Out of Scope)

1. **Metrics tracking**: Add OpenTelemetry metrics for worker uptime
2. **Database integration**: Connect to actual `arcade` database
3. **Orb webhook handling**: Update limits based on subscription changes
4. **Usage tracking**: Endpoints to track current usage against limits
5. **Enforcement**: Engine-side enforcement of limits with caching

## Files Changed

### New Files
- `/libs/arcade-serve/arcade_serve/fastapi/billing.py`
- `/libs/tests/worker/test_billing.py`
- `/examples/billing_limits_example.py`
- `/libs/arcade-serve/README_BILLING.md`

### Modified Files
- `/libs/arcade-serve/arcade_serve/fastapi/__init__.py` - Added billing exports
- `/libs/arcade-serve/pyproject.toml` - Version bump to 3.3.0

## Usage Example

```python
from fastapi import FastAPI
from arcade_serve.fastapi import create_billing_router

app = FastAPI()
billing_router = create_billing_router(
    secret="your-worker-secret",
    disable_auth=False
)
app.include_router(billing_router)
```

## Integration with Engine

The Engine can now:
1. Generate a JWT token using the worker secret
2. Call `GET /billing/limits` with tenant ID and plan type
3. Cache the limits locally to avoid repeated API calls
4. Enforce deployment and worker limits based on the response

---

**Implementation Status**: ✅ Complete and tested
**Linear Issue**: PLT-368
