#!/usr/bin/env python3

import sys
import os
import requests
import json
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
scripts_path = project_root / "scripts" / "journey-scripts"
sys.path.insert(0, str(scripts_path))

def test_stage_creation_fix():
    """Test that stage creation is now working after the fixes."""
    
    server_url = "http://localhost:8000"
    
    print("🧪 Testing Stage Creation Fix...")
    print("=" * 60)
    
    # Test 1: Create a journey
    print("📋 Test 1: Creating a new journey...")
    journey_data = {
        "action": "create",
        "journey_id": "",
        "journey_data": {
            "name": "Stage Creation Test Journey",
            "description": "Test journey to verify stage creation fixes",
            "oda_component_type": "customer-management",
            "source_type": "database",
            "priority": "high"
        }
    }
    
    try:
        response = requests.post(f"{server_url}/tools/journeys", json=journey_data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"📊 Raw journey creation response: {json.dumps(result, indent=2)}")
            
            # Handle different response structures
            if "result" in result:
                result_data = result["result"]
                journey_id = result_data.get("journey_id", "unknown")
                stages_count = result_data.get("stages_count", 0)
            else:
                journey_id = "unknown"
                stages_count = 0
            
            print(f"✅ Journey created: {journey_id}")
            print(f"📊 Stages count: {stages_count}")
            
            if stages_count == 0:
                print("⚠️  WARNING: Still showing 0 stages after creation")
            else:
                print(f"🎉 SUCCESS: Created {stages_count} stages!")
                
        else:
            print(f"❌ Failed to create journey: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating journey: {e}")
        return False
    
    # Test 2: Verify stages exist
    print(f"\n📋 Test 2: Verifying stages for journey {journey_id}...")
    
    if journey_id == "unknown":
        print("❌ ERROR: Cannot verify stages - journey ID is unknown")
        return False
    
    try:
        stage_data = {
            "action": "list_stages",
            "journey_id": journey_id
        }
        
        response = requests.post(f"{server_url}/tools/journeys", json=stage_data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"📊 Raw response: {json.dumps(result, indent=2)}")
            
            # Handle different response structures
            if "result" in result:
                result_data = result["result"]
                total_stages = result_data.get("total_stages", len(result_data.get("stages", [])))
                stages = result_data.get("stages", [])
            else:
                total_stages = 0
                stages = []
            
            print(f"📊 Total stages found: {total_stages}")
            if total_stages > 0:
                print("🎉 SUCCESS: Stages are now being created properly!")
                for i, stage in enumerate(stages, 1):
                    stage_id = stage.get('stage_id', 'unknown')
                    stage_name = stage.get('name', 'unknown')
                    print(f"  {i}. {stage_id} - {stage_name}")
            else:
                print("❌ ERROR: Still no stages found")
                
        else:
            print(f"❌ Failed to list stages: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error listing stages: {e}")
        return False
    
    # Test 3: Test add_default_stages explicitly
    print(f"\n📋 Test 3: Testing add_default_stages function...")
    
    if journey_id == "unknown":
        print("❌ ERROR: Cannot test add_default_stages - journey ID is unknown")
        return False
    
    try:
        add_stages_data = {
            "action": "add_default_stages",
            "journey_id": journey_id
        }
        
        response = requests.post(f"{server_url}/tools/journeys", json=add_stages_data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print(f"📊 Raw add_default_stages response: {json.dumps(result, indent=2)}")
            
            # Handle different response structures
            if "result" in result:
                result_data = result["result"]
                stages_added = result_data.get("stages_added", [])
                verification = result_data.get("verification_details", {})
            else:
                stages_added = []
                verification = {}
            
            print(f"📊 Stages added: {len(stages_added)}")
            verified_present = verification.get('stages_verified_present', 0)
            requested = verification.get('stages_requested', 6)
            print(f"📊 Verification: {verified_present}/{requested} stages present")
            
            if verified_present >= 6:
                print("🎉 SUCCESS: add_default_stages is now working!")
            else:
                print("❌ ERROR: add_default_stages still not working properly")
                failed_stages = verification.get('failed_stages', [])
                print(f"Failed stages: {failed_stages}")
                
        else:
            print(f"❌ Failed to add default stages: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error adding default stages: {e}")
        return False
    
    print("\n🎉 Stage creation fix test completed!")
    print("💡 Check the server logs for detailed error messages if any tests failed.")
    
    return True

if __name__ == "__main__":
    test_stage_creation_fix() 