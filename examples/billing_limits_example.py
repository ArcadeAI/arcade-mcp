"""
Example: Billing Limits Endpoint

This example demonstrates how to create a FastAPI application with the billing limits endpoint.
The endpoint can be used by the Arcade Engine to fetch billing limits for tenants.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from arcade_serve.fastapi import create_billing_router

# Create the FastAPI app
app = FastAPI(
    title="Arcade Cloud API",
    description="API for managing billing limits and usage quotas",
    version="1.0.0",
)

# Add CORS middleware (configure as needed for your environment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the worker secret from environment variable
# This should be the same secret used by the Arcade Engine
worker_secret = os.environ.get("ARCADE_WORKER_SECRET")

# Create and include the billing router
# Set disable_auth=True for testing, but use authentication in production
billing_router = create_billing_router(
    secret=worker_secret,
    disable_auth=worker_secret is None,  # Disable auth if no secret is set
)
app.include_router(billing_router)


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {"message": "Arcade Cloud API", "status": "healthy"}


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    # Run the server
    # In production, you would use a production ASGI server like gunicorn with uvicorn workers
    uvicorn.run(
        "billing_limits_example:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


# Example usage with curl:
#
# Get billing limits for a free plan tenant (without authentication):
# curl -X GET http://localhost:8000/billing/limits \
#   -H "tenant-id: org-123" \
#   -H "x-plan-type: free"
#
# Get billing limits for a growth plan tenant:
# curl -X GET http://localhost:8000/billing/limits \
#   -H "tenant-id: org-456" \
#   -H "x-plan-type: growth"
#
# Get billing limits for an enterprise plan tenant:
# curl -X GET http://localhost:8000/billing/limits \
#   -H "tenant-id: org-789" \
#   -H "x-plan-type: enterprise"
#
# With authentication (if ARCADE_WORKER_SECRET is set):
# curl -X GET http://localhost:8000/billing/limits \
#   -H "tenant-id: org-123" \
#   -H "x-plan-type: free" \
#   -H "Authorization: Bearer <your-jwt-token>"
