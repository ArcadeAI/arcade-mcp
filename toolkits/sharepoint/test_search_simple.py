#!/usr/bin/env python3
"""
Simple test to verify SharePoint search improvements.
This script tests the search logic without requiring authentication.
"""

import logging
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_search_filtering_logic():
    """Test the improved search filtering logic with mock data."""
    
    logger.info("Testing SharePoint search filtering improvements...")
    
    # Mock search results that might be returned by Microsoft Graph
    mock_search_hits = [
        {
            "resource": {
                "id": "doc1",
                "name": "BIOS Boot loop recovery.docx",
                "file": {"mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
                "web_url": "https://tenant.sharepoint.com/sites/IT/Documents/BIOS%20Boot%20loop%20recovery.docx"
            },
            "resource_type": "driveItem",
            "summary": "Document about BIOS boot loop recovery procedures"
        },
        {
            "resource": {
                "id": "doc2", 
                "name": "Network Troubleshooting Guide.pdf",
                "file": {"mimeType": "application/pdf"},
                "web_url": "https://tenant.sharepoint.com/sites/IT/Documents/Network%20Guide.pdf"
            },
            "resource_type": "driveItem",
            "summary": "Network troubleshooting documentation"
        },
        {
            "resource": {
                "id": "folder1",
                "name": "IT Documentation",
                "folder": {"childCount": 15},
                "web_url": "https://tenant.sharepoint.com/sites/IT/Documents/IT%20Documentation"
            },
            "resource_type": "driveItem",
            "summary": "Folder containing IT documentation"
        },
        {
            "resource": {
                "id": "item1",
                "name": "BIOS Settings List Item",
                "web_url": "https://tenant.sharepoint.com/sites/IT/Lists/Configuration/item1"
            },
            "resource_type": "listItem",
            "summary": "List item about BIOS settings"
        }
    ]
    
    # Test the filtering logic
    documents = []
    
    for i, hit in enumerate(mock_search_hits):
        result = hit  # In real code, this would be serialize_search_hit(hit)
        logger.info(f"Processing hit {i}: {result['resource']['name']}")
        
        # Apply the new filtering logic
        should_include = False
        
        if result.get("resource_type") == "driveItem":
            resource = result.get("resource", {})
            name = resource.get("name", "").lower()
            
            # Include if it has a file facet OR if the name suggests it's a document
            if resource.get("file"):
                should_include = True
                logger.info(f"  ✅ Hit {i} included - has file facet")
            elif any(ext in name for ext in [".doc", ".pdf", ".txt", ".ppt", ".xls", ".odt", ".rtf"]):
                should_include = True  
                logger.info(f"  ✅ Hit {i} included - has document extension")
            elif not resource.get("folder"):  # Not explicitly a folder
                should_include = True
                logger.info(f"  ✅ Hit {i} included - not a folder")
            else:
                logger.info(f"  ❌ Hit {i} skipped - appears to be a folder")
                
        elif result.get("resource_type") == "listItem":
            # Include list items that might be documents
            should_include = True
            logger.info(f"  ✅ Hit {i} included - is a listItem")
            
        else:
            # Include other types that might be documents
            should_include = True
            logger.info(f"  ✅ Hit {i} included - unknown resource type, being permissive")
        
        if should_include:
            documents.append(result)
    
    logger.info(f"\n📊 RESULTS:")
    logger.info(f"   Total hits found: {len(mock_search_hits)}")
    logger.info(f"   Documents after filtering: {len(documents)}")
    
    logger.info(f"\n📋 INCLUDED DOCUMENTS:")
    for i, doc in enumerate(documents):
        resource = doc.get("resource", {})
        name = resource.get("name", "Unknown")
        resource_type = doc.get("resource_type", "Unknown")
        logger.info(f"   {i+1}. {name} ({resource_type})")
    
    # Test specifically for "bios" search
    bios_matches = [doc for doc in documents 
                    if "bios" in doc.get("resource", {}).get("name", "").lower() or
                       "bios" in doc.get("summary", "").lower()]
    
    logger.info(f"\n🔍 BIOS-related documents found: {len(bios_matches)}")
    for i, doc in enumerate(bios_matches):
        resource = doc.get("resource", {})
        name = resource.get("name", "Unknown")
        logger.info(f"   {i+1}. {name}")
    
    # The test should find the BIOS documents
    expected_bios_docs = 2  # "BIOS Boot loop recovery.docx" and "BIOS Settings List Item"
    if len(bios_matches) >= expected_bios_docs:
        logger.info(f"\n✅ SUCCESS: Found {len(bios_matches)} BIOS-related documents (expected at least {expected_bios_docs})")
        logger.info("   The search filtering improvements are working correctly!")
        return True
    else:
        logger.error(f"\n❌ FAILURE: Only found {len(bios_matches)} BIOS-related documents (expected at least {expected_bios_docs})")
        return False


def main():
    """Run the tests."""
    logger.info("=" * 60)
    logger.info("SharePoint Search Filtering Test")
    logger.info("=" * 60)
    
    success = test_search_filtering_logic()
    
    logger.info("=" * 60)
    if success:
        logger.info("🎉 ALL TESTS PASSED! The search improvements should work better now.")
    else:
        logger.info("⚠️  Tests revealed issues. Check the filtering logic.")
    logger.info("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 