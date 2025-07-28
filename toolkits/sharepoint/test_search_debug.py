#!/usr/bin/env python3
"""
Test script for debugging SharePoint search functionality.
"""

import asyncio
import logging
import sys
from unittest.mock import MagicMock

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import the search functions
from arcade_sharepoint.tools.search import search_documents, comprehensive_document_search


async def test_search_functions():
    """Test various search approaches."""
    
    # Create a mock context (you'll need to replace this with real authentication)
    mock_context = MagicMock()
    mock_context.get_auth_token_or_empty.return_value = "YOUR_AUTH_TOKEN_HERE"
    
    search_term = "bios"
    
    logger.info("="*60)
    logger.info(f"Testing SharePoint search for term: '{search_term}'")
    logger.info("="*60)
    
    # Test 1: Original search_documents function
    logger.info("\n🔍 Test 1: Original search_documents function")
    logger.info("-" * 40)
    
    try:
        result1 = await search_documents(
            context=mock_context,
            search_term=search_term,
            limit=10
        )
        
        logger.info(f"Result 1 - Documents found: {result1.get('count', 0)}")
        logger.info(f"Result 1 - Debug info: {result1.get('debug_info', {})}")
        
        if result1.get('documents'):
            for i, doc in enumerate(result1['documents'][:3]):  # Show first 3
                resource = doc.get('resource', {})
                logger.info(f"Document {i+1}: {resource.get('name', 'No name')} - {resource.get('web_url', 'No URL')}")
        
    except Exception as e:
        logger.error(f"Test 1 failed: {str(e)}")
    
    # Test 2: Comprehensive search function
    logger.info("\n🔍 Test 2: Comprehensive search function")
    logger.info("-" * 40)
    
    try:
        result2 = await comprehensive_document_search(
            context=mock_context,
            search_term=search_term,
            limit=10
        )
        
        logger.info(f"Result 2 - Documents found: {result2.get('count', 0)}")
        logger.info(f"Result 2 - Strategies used: {result2.get('strategies_used', [])}")
        logger.info(f"Result 2 - Total found before limit: {result2.get('total_found_before_limit', 0)}")
        logger.info(f"Result 2 - Debug info: {result2.get('debug_info', {})}")
        
        if result2.get('documents'):
            for i, doc in enumerate(result2['documents'][:3]):  # Show first 3
                resource = doc.get('resource', {})
                strategy = doc.get('found_by_strategy', 'Unknown')
                logger.info(f"Document {i+1} (found by {strategy}): {resource.get('name', 'No name')} - {resource.get('web_url', 'No URL')}")
        
    except Exception as e:
        logger.error(f"Test 2 failed: {str(e)}")
    
    # Test 3: Search with different terms
    test_terms = ["BIOS", "boot", "recovery", "boot loop"]
    
    logger.info("\n🔍 Test 3: Testing different search terms")
    logger.info("-" * 40)
    
    for term in test_terms:
        logger.info(f"\nTesting search term: '{term}'")
        try:
            result = await search_documents(
                context=mock_context,
                search_term=term,
                limit=5
            )
            
            count = result.get('count', 0)
            logger.info(f"  Found {count} documents for '{term}'")
            
            if count > 0:
                for doc in result.get('documents', [])[:2]:  # Show first 2
                    resource = doc.get('resource', {})
                    logger.info(f"    - {resource.get('name', 'No name')}")
            
        except Exception as e:
            logger.error(f"  Search for '{term}' failed: {str(e)}")


def main():
    """Main function to run the tests."""
    logger.info("Starting SharePoint search debugging...")
    
    # Note: This script requires proper authentication setup
    logger.warning("⚠️  This script requires proper authentication setup!")
    logger.warning("⚠️  Replace 'YOUR_AUTH_TOKEN_HERE' with a real token or set up proper auth.")
    
    # Run the async tests
    asyncio.run(test_search_functions())
    
    logger.info("Debugging complete!")


if __name__ == "__main__":
    main() 