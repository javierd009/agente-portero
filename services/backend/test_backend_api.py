"""
Test Backend API endpoints required for WhatsApp Service
Run this after seeding the database to verify all endpoints work
"""
import asyncio
import httpx
import os
from uuid import UUID
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")


async def test_backend_api():
    """Test all critical backend endpoints for WhatsApp integration"""
    print("🧪 Testing Backend API Endpoints\n")
    print(f"   URL: {BACKEND_URL}\n")

    async with httpx.AsyncClient(timeout=30.0) as client:

        # Test 1: Health check
        print("1️⃣  Health check...")
        try:
            response = await client.get(f"{BACKEND_URL}/health")
            if response.status_code == 200:
                print(f"   ✅ Backend is healthy: {response.json()}")
            else:
                print(f"   ❌ Backend unhealthy (status {response.status_code})")
                return False
        except Exception as e:
            print(f"   ❌ Cannot reach backend: {e}")
            return False

        # Get condominium ID from seeded data (we know it from seed_data.py)
        # We'll need to query it first
        print("\n2️⃣  Getting condominium info...")
        try:
            # This endpoint doesn't exist yet, so we'll use a known UUID from seed
            # In production, you'd query /api/v1/condominiums
            # For now, we'll hardcode the expected slug
            condominium_id = None
            tenant_id_header = None

            # We'll set this after first resident query
            print("   💡 Will get tenant_id from resident query")
        except Exception as e:
            print(f"   ⚠️  Note: {e}")

        # Test 3: Get resident by phone (CRITICAL for WhatsApp)
        print("\n3️⃣  Testing GET /api/v1/residents/by-phone/{phone}...")
        test_phone = "5218112345678"  # Juan Pérez from seed data
        try:
            response = await client.get(f"{BACKEND_URL}/api/v1/residents/by-phone/{test_phone}")
            if response.status_code == 200:
                resident = response.json()
                print(f"   ✅ Found resident: {resident['name']} - Unit {resident['unit']}")
                condominium_id = resident['condominium_id']
                tenant_id_header = {"x-tenant-id": condominium_id}
                print(f"   🏢 Condominium ID: {condominium_id}")
            else:
                print(f"   ❌ Resident not found (status {response.status_code})")
                print(f"   💡 Did you run seed_data.py first?")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

        # Test 4: Authorize visitor (CRITICAL for WhatsApp pre-authorization)
        print("\n4️⃣  Testing POST /api/v1/visitors/authorize...")
        try:
            payload = {
                "condominium_id": condominium_id,
                "resident_id": resident['id'],
                "visitor_name": "Test Visitor - María González",
                "vehicle_plate": "TEST-123",
                "notes": "Authorized via WhatsApp (test)"
            }
            response = await client.post(
                f"{BACKEND_URL}/api/v1/visitors/authorize",
                json=payload
            )
            if response.status_code == 201:
                visitor = response.json()
                print(f"   ✅ Visitor authorized: {visitor['name']}")
                print(f"   ⏰ Valid until: {visitor['valid_until']}")
                visitor_id = visitor['id']
            else:
                print(f"   ❌ Failed to authorize (status {response.status_code}): {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

        # Test 5: Check visitor authorization (used by Voice Service)
        print("\n5️⃣  Testing GET /api/v1/visitors/check-authorization/{name}...")
        try:
            response = await client.get(
                f"{BACKEND_URL}/api/v1/visitors/check-authorization/María González",
                headers=tenant_id_header
            )
            if response.status_code == 200:
                visitor_check = response.json()
                if visitor_check:
                    print(f"   ✅ Visitor is authorized: {visitor_check['name']}")
                else:
                    print(f"   ⚠️  Visitor not found (might be expired)")
            else:
                print(f"   ❌ Check failed (status {response.status_code})")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 6: Create report (from WhatsApp)
        print("\n6️⃣  Testing POST /api/v1/reports/ (create report)...")
        try:
            payload = {
                "condominium_id": condominium_id,
                "resident_id": resident['id'],
                "report_type": "maintenance",
                "title": "Test Report - Luz fundida",
                "description": "Testing report creation from WhatsApp",
                "location": "Pasillo principal",
                "urgency": "normal",
                "source": "whatsapp"
            }
            response = await client.post(
                f"{BACKEND_URL}/api/v1/reports/",
                json=payload
            )
            if response.status_code == 201:
                report = response.json()
                print(f"   ✅ Report created: {report['title']}")
                print(f"   🆔 Report ID: {report['id']}")
                report_id = report['id']
            else:
                print(f"   ❌ Failed to create report (status {response.status_code}): {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

        # Test 7: Query access logs (WhatsApp query)
        print("\n7️⃣  Testing GET /api/v1/access/logs?query_type=today...")
        try:
            response = await client.get(
                f"{BACKEND_URL}/api/v1/access/logs?query_type=today&limit=10",
                headers=tenant_id_header
            )
            if response.status_code == 200:
                logs = response.json()
                print(f"   ✅ Found {len(logs)} access logs for today")
            else:
                print(f"   ⚠️  Query failed (status {response.status_code})")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 8: Get report stats
        print("\n8️⃣  Testing GET /api/v1/reports/stats/summary...")
        try:
            response = await client.get(
                f"{BACKEND_URL}/api/v1/reports/stats/summary",
                headers=tenant_id_header
            )
            if response.status_code == 200:
                stats = response.json()
                print(f"   ✅ Report stats: {stats['total']} total reports")
                print(f"   📊 By status: {stats['by_status']}")
            else:
                print(f"   ⚠️  Stats failed (status {response.status_code})")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 9: List visitors
        print("\n9️⃣  Testing GET /api/v1/visitors/...")
        try:
            response = await client.get(
                f"{BACKEND_URL}/api/v1/visitors/?status=approved&limit=10",
                headers=tenant_id_header
            )
            if response.status_code == 200:
                visitors = response.json()
                print(f"   ✅ Found {len(visitors)} approved visitors")
            else:
                print(f"   ⚠️  Query failed (status {response.status_code})")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n" + "="*60)
    print("✅ All critical Backend API endpoints are working!")
    print("="*60)
    print("\n💡 Next steps:")
    print("   1. Start WhatsApp Service: cd services/whatsapp-service && python main.py")
    print("   2. Configure webhook in Evolution API")
    print("   3. Test end-to-end flow by sending WhatsApp message")
    return True


if __name__ == "__main__":
    asyncio.run(test_backend_api())
