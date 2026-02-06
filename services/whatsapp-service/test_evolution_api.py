"""
Test Evolution API connectivity and basic functionality
Run this to verify Evolution API is working before testing the full flow
"""
import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "B6D711FCDE4D4FD5936544120E713976")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE_NAME", "agente_portero")


async def test_evolution_api():
    """Test Evolution API endpoints"""
    print("🧪 Testing Evolution API Connectivity\n")
    print(f"   URL: {EVOLUTION_API_URL}")
    print(f"   Instance: {EVOLUTION_INSTANCE}\n")

    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Check instance exists
        print("1️⃣  Checking if instance exists...")
        try:
            url = f"{EVOLUTION_API_URL}/instance/connectionState/{EVOLUTION_INSTANCE}"
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Instance found: {data}")
                state = data.get("instance", {}).get("state")
                print(f"   📱 Connection state: {state}")
            else:
                print(f"   ❌ Instance not found (status {response.status_code})")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

        # Test 2: Get instance info
        print("\n2️⃣  Getting instance info...")
        try:
            url = f"{EVOLUTION_API_URL}/instance/fetchInstances"
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                instances = response.json()
                print(f"   ✅ Found {len(instances)} instances")
                for inst in instances:
                    if inst.get("instance", {}).get("instanceName") == EVOLUTION_INSTANCE:
                        print(f"   📱 Our instance: {inst}")
            else:
                print(f"   ⚠️  Could not fetch instances (status {response.status_code})")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 3: Send test message (optional - commented out to avoid spam)
        print("\n3️⃣  Test message sending (SKIPPED)")
        print("   💡 To test sending, uncomment the code and provide a test phone number")

        # Uncomment to test sending:
        # TEST_PHONE = "5218112345678"  # Replace with your test number
        # try:
        #     url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
        #     payload = {
        #         "number": TEST_PHONE,
        #         "text": "🧪 Test message from Agente Portero"
        #     }
        #     response = await client.post(url, headers=headers, json=payload)
        #     if response.status_code == 201:
        #         print(f"   ✅ Test message sent successfully")
        #     else:
        #         print(f"   ❌ Failed to send (status {response.status_code}): {response.text}")
        # except Exception as e:
        #     print(f"   ❌ Error: {e}")

    print("\n" + "="*60)
    print("✅ Evolution API is reachable and working!")
    print("="*60)
    return True


if __name__ == "__main__":
    asyncio.run(test_evolution_api())
