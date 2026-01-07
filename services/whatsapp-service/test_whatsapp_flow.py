"""
Test complete WhatsApp flow by simulating webhook calls
This simulates Evolution API sending webhooks to our WhatsApp Service
"""
import asyncio
import httpx
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_SERVICE_URL = os.getenv("WHATSAPP_SERVICE_URL", "http://localhost:8002")
BACKEND_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")


def create_webhook_payload(from_phone: str, message: str, message_id: str = None):
    """Create a realistic Evolution API webhook payload"""
    if not message_id:
        message_id = f"TEST_{datetime.utcnow().timestamp()}"

    return {
        "event": "messages.upsert",
        "instance": "agente_portero",
        "data": {
            "key": {
                "remoteJid": f"{from_phone}@s.whatsapp.net",
                "fromMe": False,
                "id": message_id
            },
            "pushName": "Test User",
            "message": {
                "conversation": message
            },
            "messageType": "conversation",
            "messageTimestamp": int(datetime.utcnow().timestamp()),
            "status": "RECEIVED"
        }
    }


async def test_whatsapp_flow():
    """Test complete WhatsApp flow scenarios"""
    print("🧪 Testing WhatsApp Service Flow\n")
    print(f"   WhatsApp Service: {WHATSAPP_SERVICE_URL}")
    print(f"   Backend API: {BACKEND_URL}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:

        # Pre-check: Verify services are running
        print("0️⃣  Pre-flight checks...")
        try:
            # Check WhatsApp Service
            response = await client.get(f"{WHATSAPP_SERVICE_URL}/health")
            if response.status_code == 200:
                print("   ✅ WhatsApp Service is running")
            else:
                print("   ❌ WhatsApp Service not responding")
                return False

            # Check Backend
            response = await client.get(f"{BACKEND_URL}/health")
            if response.status_code == 200:
                print("   ✅ Backend API is running")
            else:
                print("   ❌ Backend API not responding")
                return False
        except Exception as e:
            print(f"   ❌ Error connecting to services: {e}")
            print("   💡 Make sure both services are running:")
            print("      - Backend: cd services/backend && python main.py")
            print("      - WhatsApp: cd services/whatsapp-service && python main.py")
            return False

        # Test resident phone from seed data
        test_phone = "5218112345678"  # Juan Pérez García - Unit A-101

        # Scenario 1: Authorize visitor
        print("\n1️⃣  Scenario: Resident authorizes visitor via WhatsApp")
        print("   📱 Message: 'Viene María González en 10 minutos'")
        webhook_data = create_webhook_payload(
            from_phone=test_phone,
            message="Viene María González en 10 minutos"
        )
        try:
            response = await client.post(
                f"{WHATSAPP_SERVICE_URL}/webhook",
                json=webhook_data
            )
            print(f"   📨 Webhook sent (status {response.status_code})")
            if response.status_code == 200:
                print("   ✅ WhatsApp Service processed the message")
                print("   💬 Check the logs for:")
                print("      - Intent: authorize_visitor")
                print("      - Visitor: María González")
                print("      - Backend API call to /visitors/authorize")
                await asyncio.sleep(2)  # Give time for processing
            else:
                print(f"   ❌ Failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Scenario 2: Request gate opening
        print("\n2️⃣  Scenario: Resident requests remote gate opening")
        print("   📱 Message: 'Ábreme la puerta por favor'")
        webhook_data = create_webhook_payload(
            from_phone=test_phone,
            message="Ábreme la puerta por favor"
        )
        try:
            response = await client.post(
                f"{WHATSAPP_SERVICE_URL}/webhook",
                json=webhook_data
            )
            print(f"   📨 Webhook sent (status {response.status_code})")
            if response.status_code == 200:
                print("   ✅ WhatsApp Service processed the message")
                print("   💬 Check the logs for:")
                print("      - Intent: open_gate")
                print("      - Backend API call to /gates/open")
                await asyncio.sleep(2)
            else:
                print(f"   ❌ Failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Scenario 3: Create maintenance report
        print("\n3️⃣  Scenario: Resident reports maintenance issue")
        print("   📱 Message: 'Reportar: La luz del pasillo no funciona'")
        webhook_data = create_webhook_payload(
            from_phone=test_phone,
            message="Reportar: La luz del pasillo no funciona"
        )
        try:
            response = await client.post(
                f"{WHATSAPP_SERVICE_URL}/webhook",
                json=webhook_data
            )
            print(f"   📨 Webhook sent (status {response.status_code})")
            if response.status_code == 200:
                print("   ✅ WhatsApp Service processed the message")
                print("   💬 Check the logs for:")
                print("      - Intent: create_report")
                print("      - Report type: maintenance")
                print("      - Backend API call to /reports/")
                await asyncio.sleep(2)
            else:
                print(f"   ❌ Failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Scenario 4: Query access logs
        print("\n4️⃣  Scenario: Resident queries today's visitors")
        print("   📱 Message: '¿Quién ha venido hoy?'")
        webhook_data = create_webhook_payload(
            from_phone=test_phone,
            message="¿Quién ha venido hoy?"
        )
        try:
            response = await client.post(
                f"{WHATSAPP_SERVICE_URL}/webhook",
                json=webhook_data
            )
            print(f"   📨 Webhook sent (status {response.status_code})")
            if response.status_code == 200:
                print("   ✅ WhatsApp Service processed the message")
                print("   💬 Check the logs for:")
                print("      - Intent: query_logs")
                print("      - Query type: today")
                print("      - Backend API call to /access/logs")
                await asyncio.sleep(2)
            else:
                print(f"   ❌ Failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Scenario 5: Unknown intent (conversation)
        print("\n5️⃣  Scenario: General conversation")
        print("   📱 Message: 'Hola, ¿cómo estás?'")
        webhook_data = create_webhook_payload(
            from_phone=test_phone,
            message="Hola, ¿cómo estás?"
        )
        try:
            response = await client.post(
                f"{WHATSAPP_SERVICE_URL}/webhook",
                json=webhook_data
            )
            print(f"   📨 Webhook sent (status {response.status_code})")
            if response.status_code == 200:
                print("   ✅ WhatsApp Service processed the message")
                print("   💬 Check the logs for:")
                print("      - Intent: unknown")
                print("      - Response with help menu")
                await asyncio.sleep(2)
            else:
                print(f"   ❌ Failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Verify backend data was created
        print("\n6️⃣  Verifying backend data...")
        try:
            # Check if visitor was authorized
            response = await client.get(f"{BACKEND_URL}/api/v1/residents/by-phone/{test_phone}")
            if response.status_code == 200:
                resident = response.json()
                condominium_id = resident['condominium_id']

                # Get visitors
                response = await client.get(
                    f"{BACKEND_URL}/api/v1/visitors/?status=approved&limit=5",
                    headers={"x-tenant-id": condominium_id}
                )
                if response.status_code == 200:
                    visitors = response.json()
                    maria_found = any(v['name'] == 'María González' for v in visitors)
                    if maria_found:
                        print("   ✅ Visitor 'María González' was authorized in database")
                    else:
                        print("   ⚠️  Visitor not found (might not have been created)")

                # Get reports
                response = await client.get(
                    f"{BACKEND_URL}/api/v1/reports/?limit=5",
                    headers={"x-tenant-id": condominium_id}
                )
                if response.status_code == 200:
                    reports = response.json()
                    light_report = any('luz' in r['description'].lower() for r in reports)
                    if light_report:
                        print("   ✅ Maintenance report was created in database")
                    else:
                        print("   ⚠️  Report not found (might not have been created)")
            else:
                print("   ⚠️  Could not verify backend data")
        except Exception as e:
            print(f"   ⚠️  Error verifying: {e}")

    print("\n" + "="*60)
    print("✅ WhatsApp flow test completed!")
    print("="*60)
    print("\n💡 Review the service logs to see the complete flow:")
    print("   - Intent parsing with GPT-4")
    print("   - Backend API calls")
    print("   - WhatsApp responses sent")
    print("\n📊 To test with real WhatsApp:")
    print("   1. Configure Evolution API webhook to point to WhatsApp Service")
    print("   2. Send messages from WhatsApp number: 5218112345678")
    print("   3. Monitor the logs in real-time")
    return True


if __name__ == "__main__":
    asyncio.run(test_whatsapp_flow())
