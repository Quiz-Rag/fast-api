#!/usr/bin/env python3
"""
Test script to validate the search API endpoints.
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_collections_endpoint():
    """Test the collections listing endpoint."""
    print("Testing /api/collections endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/collections")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.json()
    except Exception as e:
        print(f"Error testing collections endpoint: {e}")
        return None

def test_search_endpoint(query="security", collection_name="lecture_23_slides", top_k=3):
    """Test the search endpoint."""
    print(f"\nTesting /api/search endpoint with query: '{query}'...")
    try:
        params = {
            "query": query,
            "collection_name": collection_name,
            "top_k": top_k
        }
        response = requests.get(f"{BASE_URL}/search", params=params)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.json()
    except Exception as e:
        print(f"Error testing search endpoint: {e}")
        return None

def test_search_with_different_queries():
    """Test search with various queries."""
    queries = [
        "authentication",
        "ticket hijacking", 
        "malicious user",
        "network security",
        "protocol"
    ]
    
    for query in queries:
        print(f"\n{'='*50}")
        print(f"Testing query: '{query}'")
        print('='*50)
        result = test_search_endpoint(query, "lecture_23_slides", 2)
        if result and "documents" in result:
            print(f"Found {len(result['documents'])} results")
            for i, doc in enumerate(result['documents'][:2], 1):
                print(f"\nResult {i}:")
                print(f"  Content preview: {doc.get('content', '')[:150]}...")
                print(f"  Similarity score: {doc.get('similarity_score', 'N/A')}")

if __name__ == "__main__":
    print("Testing Search API Endpoints")
    print("="*50)
    
    # Test collections endpoint
    collections = test_collections_endpoint()
    
    # Test search endpoint
    if collections and collections.get("collections"):
        collection_name = collections["collections"][0]["name"]
        test_search_endpoint("security", collection_name)
        
        # Test with different queries
        test_search_with_different_queries()
    else:
        print("No collections found or error accessing collections endpoint")