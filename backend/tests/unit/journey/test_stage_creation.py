#!/usr/bin/env python3
"""
Test script to verify stage creation works correctly
"""

import sys
import json
import requests
from pathlib import Path

# Add the server modules to path
# Update path to import from journey-scripts
project_root = Path(__file__).parent.parent.parent.parent
scripts_path = project_root / "scripts" / "journey-scripts"
sys.path.insert(0, str(scripts_path))

def test_stage_creation():
    """Test stage creation functionality"""
    
    server_url = "http://localhost:8000"
    
    print("🧪 Testing Stage Creation Functionality")
    print("=" * 50)
    
    # Step 1: Create a new journey
    print("\n1️⃣ Creating a new journey...")
    create_journey_data = {
        "action": "create",
        "journey_id": "",
        "journey_data": {
            "name": "Test Journey for Stage Creation",
            "description": "Test journey to verify stage creation works",
            "oda_component_type": "customer-management",
            "source_type": "database",
            "priority": "high"
        }
    }
    
    response = requests.post(f"{server_url}/tools/journeys", json=create_journey_data)
    if response.status_code != 200:
        print(f"❌ Failed to create journey: {response.status_code}")
        print(response.text)
        return False
    
    result = response.json()
    if result.get("result", {}).get("status") != "success":
        print(f"❌ Journey creation failed: {result}")
        return False
    
    journey_id = result["result"]["journey_id"]
    print(f"✅ Created journey: {journey_id}")
    
    # Step 2: Check if default stages were created
    print(f"\n2️⃣ Checking default stages for journey {journey_id}...")
    list_stages_data = {
        "action": "list_stages",
        "journey_id": journey_id
    }
    
    response = requests.post(f"{server_url}/tools/journeys", json=list_stages_data)
    if response.status_code != 200:
        print(f"❌ Failed to list stages: {response.status_code}")
        print(response.text)
        return False
    
    result = response.json()
    total_stages = result.get("result", {}).get("total_stages", 0)
    stages = result.get("result", {}).get("stages", [])
    
    print(f"📊 Found {total_stages} stages")
    for stage in stages:
        print(f"   - {stage.get('stage_id')}: {stage.get('name')}")
    
    # Step 3: Add default stages if none exist
    if total_stages == 0:
        print(f"\n3️⃣ Adding default stages to journey {journey_id}...")
        add_default_stages_data = {
            "action": "add_default_stages",
            "journey_id": journey_id
        }
        
        response = requests.post(f"{server_url}/tools/journeys", json=add_default_stages_data)
        if response.status_code != 200:
            print(f"❌ Failed to add default stages: {response.status_code}")
            print(response.text)
            return False
        
        result = response.json()
        print(f"📝 Add default stages result: {result.get('result', {}).get('message')}")
        
        # Check verification details
        verification = result.get("result", {}).get("verification_details", {})
        print(f"🔍 Verification details:")
        print(f"   - Requested: {verification.get('stages_requested', 0)}")
        print(f"   - Successfully added: {verification.get('stages_successfully_added', 0)}")
        print(f"   - Failed: {verification.get('stages_failed', 0)}")
        print(f"   - Verified present: {verification.get('stages_verified_present', 0)}")
        
        # Check stages again
        print(f"\n4️⃣ Checking stages again after adding defaults...")
        response = requests.post(f"{server_url}/tools/journeys", json=list_stages_data)
        if response.status_code == 200:
            result = response.json()
            total_stages = result.get("result", {}).get("total_stages", 0)
            stages = result.get("result", {}).get("stages", [])
            
            print(f"📊 Now found {total_stages} stages")
            for stage in stages:
                print(f"   - {stage.get('stage_id')}: {stage.get('name')}")
    
    # Step 4: Add a custom stage
    print(f"\n5️⃣ Adding a custom stage to journey {journey_id}...")
    add_stage_data = {
        "action": "add_stage",
        "journey_id": journey_id,
        "stage_data": {
            "stage_id": "test_stage",
            "name": "Test Stage",
            "description": "A test stage to verify stage addition works",
            "order": 10
        }
    }
    
    response = requests.post(f"{server_url}/tools/journeys", json=add_stage_data)
    if response.status_code != 200:
        print(f"❌ Failed to add custom stage: {response.status_code}")
        print(response.text)
        return False
    
    result = response.json()
    if result.get("result", {}).get("status") != "success":
        print(f"❌ Custom stage addition failed: {result}")
        return False
    
    print(f"✅ Added custom stage: {result.get('result', {}).get('message')}")
    
    # Step 5: Final verification
    print(f"\n6️⃣ Final verification...")
    response = requests.post(f"{server_url}/tools/journeys", json=list_stages_data)
    if response.status_code == 200:
        result = response.json()
        total_stages = result.get("result", {}).get("total_stages", 0)
        stages = result.get("result", {}).get("stages", [])
        
        print(f"📊 Final count: {total_stages} stages")
        for stage in stages:
            print(f"   - {stage.get('stage_id')}: {stage.get('name')}")
        
        # Check if our test stage is there
        test_stage_found = any(stage.get('stage_id') == 'test_stage' for stage in stages)
        if test_stage_found:
            print("✅ Custom stage successfully added and verified!")
            return True
        else:
            print("❌ Custom stage was not found in the final verification")
            return False
    
    return False

if __name__ == "__main__":
    try:
        success = test_stage_creation()
        if success:
            print("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 