import asyncio
from os import environ

from arcade_ai.eval import EvalSuite, ScoredResponse
from arcade_mongodb.tools.mongodb import (
    discover_collections,
    discover_databases,
    find_documents,
    get_collection_schema,
)
from arcade_tdk import ToolContext, ToolSecretItem

MONGODB_CONNECTION_STRING = (
    environ.get("TEST_MONGODB_CONNECTION_STRING") or "mongodb://localhost:27017"
)


def mock_context() -> ToolContext:
    context = ToolContext()
    context.secrets = []
    context.secrets.append(
        ToolSecretItem(key="MONGODB_CONNECTION_STRING", value=MONGODB_CONNECTION_STRING)
    )
    return context


async def test_discover_databases() -> ScoredResponse:
    try:
        databases = await discover_databases(mock_context())
        return ScoredResponse(
            response=f"Found {len(databases)} databases: {databases}",
            score=1.0 if databases else 0.5,
        )
    except Exception as e:
        return ScoredResponse(response=f"Error: {e}", score=0.0)


async def test_discover_collections() -> ScoredResponse:
    try:
        # Try to discover collections in the first available database
        databases = await discover_databases(mock_context())
        if not databases:
            return ScoredResponse(response="No databases found", score=0.0)
        
        collections = await discover_collections(mock_context(), databases[0])
        return ScoredResponse(
            response=f"Found {len(collections)} collections in {databases[0]}: {collections}",
            score=1.0 if collections else 0.5,
        )
    except Exception as e:
        return ScoredResponse(response=f"Error: {e}", score=0.0)


async def test_get_collection_schema() -> ScoredResponse:
    try:
        databases = await discover_databases(mock_context())
        if not databases:
            return ScoredResponse(response="No databases found", score=0.0)
        
        collections = await discover_collections(mock_context(), databases[0])
        if not collections:
            return ScoredResponse(response="No collections found", score=0.0)
        
        schema = await get_collection_schema(mock_context(), databases[0], collections[0])
        return ScoredResponse(
            response=f"Schema for {databases[0]}.{collections[0]}: {schema}",
            score=1.0 if schema else 0.0,
        )
    except Exception as e:
        return ScoredResponse(response=f"Error: {e}", score=0.0)


async def test_find_documents() -> ScoredResponse:
    try:
        databases = await discover_databases(mock_context())
        if not databases:
            return ScoredResponse(response="No databases found", score=0.0)
        
        collections = await discover_collections(mock_context(), databases[0])
        if not collections:
            return ScoredResponse(response="No collections found", score=0.0)
        
        documents = await find_documents(
            mock_context(), databases[0], collections[0], limit=5
        )
        return ScoredResponse(
            response=f"Found {len(documents)} documents in {databases[0]}.{collections[0]}",
            score=1.0 if isinstance(documents, list) else 0.0,
        )
    except Exception as e:
        return ScoredResponse(response=f"Error: {e}", score=0.0)


def main() -> None:
    eval_suite = EvalSuite("MongoDB Toolkit Evaluation")
    eval_suite.add_eval("Discover Databases", test_discover_databases)
    eval_suite.add_eval("Discover Collections", test_discover_collections)
    eval_suite.add_eval("Get Collection Schema", test_get_collection_schema)
    eval_suite.add_eval("Find Documents", test_find_documents)
    
    asyncio.run(eval_suite.run())


if __name__ == "__main__":
    main()