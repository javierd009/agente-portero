# Testing Guide - Agente Portero

Complete guide for testing the Agente Portero system from local development to production.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Test Suite Overview](#test-suite-overview)
- [Individual Tests](#individual-tests)
- [Manual Testing](#manual-testing)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### 1. Database Setup
```bash
# Start PostgreSQL (via Docker)
docker-compose up -d postgres redis

# Seed the database with test data
cd services/backend
python seed_data.py

# You should see:
# ✅ 1 Condominium: Residencial del Valle
# ✅ 3 Residents with WhatsApp numbers
# ✅ 2 Vehicles
# ✅ 1 AI Agent
```

### 2. Start Backend Service
```bash
cd services/backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python main.py

# Should start on http://localhost:8000
# Verify: curl http://localhost:8000/health
```

### 3. Start WhatsApp Service
```bash
cd services/whatsapp-service
source venv/bin/activate  # or venv\Scripts\activate on Windows
python main.py

# Should start on http://localhost:8002
# Verify: curl http://localhost:8002/health
```

### 4. Evolution API (Optional for full integration)
```bash
# Start Evolution API via Docker
docker-compose up -d evolution-api

# Access at: http://localhost:8080
# Create instance named: agente_portero
# Scan QR code with WhatsApp Business
```

---

## Quick Start

### Run Complete Test Suite
```bash
# From project root
./test_all.sh
```

This will run all tests in sequence:
1. ✅ Evolution API connectivity (if available)
2. ✅ Backend API endpoints
3. ✅ WhatsApp Service flow simulation

---

## Test Suite Overview

### Test Files

| File | Purpose | Service Required |
|------|---------|------------------|
| `services/whatsapp-service/test_evolution_api.py` | Verify Evolution API connectivity | Evolution API |
| `services/backend/test_backend_api.py` | Test all backend endpoints | Backend API |
| `services/whatsapp-service/test_whatsapp_flow.py` | Simulate complete WhatsApp flows | Backend + WhatsApp Service |
| `test_all.sh` | Orchestrate all tests | All services |

---

## Individual Tests

### Test 1: Evolution API Connectivity

Tests if Evolution API is reachable and properly configured.

```bash
cd services/whatsapp-service
python test_evolution_api.py
```

**What it tests:**
- ✅ Instance exists and is connected
- ✅ Can fetch instance info
- ✅ API authentication works

**Expected output:**
```
🧪 Testing Evolution API Connectivity

1️⃣  Checking if instance exists...
   ✅ Instance found: {...}
   📱 Connection state: open

2️⃣  Getting instance info...
   ✅ Found 1 instances
   📱 Our instance: {...}

✅ Evolution API is reachable and working!
```

---

### Test 2: Backend API Endpoints

Tests all backend endpoints required for WhatsApp integration.

```bash
cd services/backend
python test_backend_api.py
```

**What it tests:**
1. ✅ Health check
2. ✅ `GET /api/v1/residents/by-phone/{phone}` - Find resident by WhatsApp number
3. ✅ `POST /api/v1/visitors/authorize` - Pre-authorize visitor
4. ✅ `GET /api/v1/visitors/check-authorization/{name}` - Check if visitor authorized
5. ✅ `POST /api/v1/reports/` - Create incident report
6. ✅ `GET /api/v1/access/logs?query_type=today` - Query access logs
7. ✅ `GET /api/v1/reports/stats/summary` - Get report statistics
8. ✅ `GET /api/v1/visitors/` - List visitors

**Expected output:**
```
🧪 Testing Backend API Endpoints

1️⃣  Health check...
   ✅ Backend is healthy: {"status": "ok"}

3️⃣  Testing GET /api/v1/residents/by-phone/{phone}...
   ✅ Found resident: Juan Pérez García - Unit A-101
   🏢 Condominium ID: 123e4567-...

4️⃣  Testing POST /api/v1/visitors/authorize...
   ✅ Visitor authorized: María González
   ⏰ Valid until: 2024-01-06T14:30:00

... (all tests pass)

✅ All critical Backend API endpoints are working!
```

---

### Test 3: WhatsApp Service Flow

Simulates complete WhatsApp flows by sending webhook payloads to WhatsApp Service.

```bash
cd services/whatsapp-service
python test_whatsapp_flow.py
```

**What it tests:**

**Scenario 1: Authorize Visitor**
- 📱 Message: "Viene María González en 10 minutos"
- ✅ Parsed intent: `authorize_visitor`
- ✅ Backend call: `POST /visitors/authorize`
- ✅ WhatsApp response sent

**Scenario 2: Open Gate Remotely**
- 📱 Message: "Ábreme la puerta por favor"
- ✅ Parsed intent: `open_gate`
- ✅ Backend call: `POST /gates/open`
- ✅ WhatsApp response sent

**Scenario 3: Create Maintenance Report**
- 📱 Message: "Reportar: La luz del pasillo no funciona"
- ✅ Parsed intent: `create_report`
- ✅ Backend call: `POST /reports/`
- ✅ WhatsApp response sent

**Scenario 4: Query Access Logs**
- 📱 Message: "¿Quién ha venido hoy?"
- ✅ Parsed intent: `query_logs`
- ✅ Backend call: `GET /access/logs?query_type=today`
- ✅ WhatsApp response sent

**Scenario 5: General Conversation**
- 📱 Message: "Hola, ¿cómo estás?"
- ✅ Parsed intent: `unknown`
- ✅ Help menu sent

**Expected output:**
```
🧪 Testing WhatsApp Service Flow

0️⃣  Pre-flight checks...
   ✅ WhatsApp Service is running
   ✅ Backend API is running

1️⃣  Scenario: Resident authorizes visitor via WhatsApp
   📱 Message: 'Viene María González en 10 minutos'
   📨 Webhook sent (status 200)
   ✅ WhatsApp Service processed the message
   💬 Check the logs for:
      - Intent: authorize_visitor
      - Visitor: María González
      - Backend API call to /visitors/authorize

... (all scenarios pass)

6️⃣  Verifying backend data...
   ✅ Visitor 'María González' was authorized in database
   ✅ Maintenance report was created in database

✅ WhatsApp flow test completed!
```

---

## Manual Testing

### Test with Real WhatsApp Messages

1. **Configure ngrok for webhook URL**
```bash
ngrok http 8002

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
```

2. **Configure webhook in Evolution API**
```bash
# Using Evolution API UI or API:
curl -X POST http://localhost:8080/webhook/set/agente_portero \
  -H "apikey: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://abc123.ngrok.io/webhook",
    "webhook_by_events": false,
    "events": ["MESSAGES_UPSERT"]
  }'
```

3. **Send test messages from WhatsApp**

Use one of the seeded phone numbers:
- **Juan Pérez**: `+52 81 1234 5678` (WhatsApp: 5218112345678)
- **María Rodríguez**: `+52 81 9876 5432` (WhatsApp: 5218198765432)
- **Carlos Martínez**: `+52 81 5555 1234` (WhatsApp: 5218155551234)

**Test Messages:**

```
✅ "Viene Pedro Ramírez en 10 minutos"
   → Should authorize visitor

✅ "Ábreme la puerta"
   → Should trigger gate opening

✅ "Reportar: El elevador no funciona"
   → Should create maintenance report

✅ "¿Quién vino hoy?"
   → Should query today's visitors

✅ "Ayuda"
   → Should show help menu
```

4. **Monitor logs in real-time**

```bash
# Terminal 1: Backend logs
cd services/backend
python main.py

# Terminal 2: WhatsApp Service logs
cd services/whatsapp-service
python main.py

# Terminal 3: ngrok logs
ngrok http 8002
```

---

## Testing Checklist

Use this checklist when testing the complete system:

### Backend Setup
- [ ] PostgreSQL running (`docker-compose up -d postgres`)
- [ ] Redis running (`docker-compose up -d redis`)
- [ ] Database seeded (`python seed_data.py`)
- [ ] Backend service running on port 8000
- [ ] Backend health check passes (`curl localhost:8000/health`)

### WhatsApp Service Setup
- [ ] WhatsApp Service running on port 8002
- [ ] WhatsApp health check passes (`curl localhost:8002/health`)
- [ ] `.env` file configured with:
  - [ ] `EVOLUTION_API_URL`
  - [ ] `EVOLUTION_API_KEY`
  - [ ] `OPENAI_API_KEY`
  - [ ] `BACKEND_API_URL`
  - [ ] `REDIS_URL`

### Evolution API Setup (for real WhatsApp)
- [ ] Evolution API running on port 8080
- [ ] Instance created: `agente_portero`
- [ ] QR code scanned with WhatsApp Business
- [ ] Instance state: `open`
- [ ] Webhook configured with ngrok URL

### Test Execution
- [ ] Evolution API test passes
- [ ] Backend API test passes
- [ ] WhatsApp flow simulation passes
- [ ] Real WhatsApp message received and processed
- [ ] Visitor authorized in database
- [ ] Report created in database
- [ ] WhatsApp response received

---

## Troubleshooting

### Backend API errors

**Error**: `DATABASE_URL environment variable is not set`
```bash
# Solution: Create .env file
cd services/backend
cp .env.example .env
# Edit DATABASE_URL to point to your PostgreSQL
```

**Error**: `Resident not found by phone`
```bash
# Solution: Run seed_data.py
cd services/backend
python seed_data.py
```

### WhatsApp Service errors

**Error**: `OPENAI_API_KEY not set`
```bash
# Solution: Add to .env
cd services/whatsapp-service
echo "OPENAI_API_KEY=sk-..." >> .env
```

**Error**: `Evolution API not reachable`
```bash
# Solution: Start Evolution API
docker-compose up -d evolution-api
# Or configure EVOLUTION_API_URL in .env
```

**Error**: `Redis connection refused`
```bash
# Solution: Start Redis
docker-compose up -d redis
```

### Evolution API errors

**Error**: `Instance not found`
```bash
# Solution: Create instance via Evolution API
# 1. Open http://localhost:8080
# 2. Create instance: agente_portero
# 3. Scan QR code
```

**Error**: `Webhook not receiving messages`
```bash
# Solution: Verify webhook is configured
curl http://localhost:8080/webhook/find/agente_portero \
  -H "apikey: YOUR_API_KEY"

# Should show your ngrok URL
```

### General debugging

**Enable verbose logging**
```bash
# Backend
export LOG_LEVEL=DEBUG
python main.py

# WhatsApp Service
export LOG_LEVEL=DEBUG
python main.py
```

**Check service status**
```bash
# Backend
curl http://localhost:8000/health

# WhatsApp Service
curl http://localhost:8002/health

# Evolution API
curl http://localhost:8080
```

**View database contents**
```bash
# Connect to PostgreSQL
docker exec -it agente_portero_postgres psql -U postgres -d agente_portero

# Query visitors
SELECT * FROM visitor WHERE status = 'approved';

# Query reports
SELECT * FROM report ORDER BY created_at DESC LIMIT 10;
```

---

## Cost Monitoring

When testing with real OpenAI API calls, monitor your usage:

```python
# Add to WhatsApp Service logs
import tiktoken

def count_tokens(messages):
    encoding = tiktoken.encoding_for_model("gpt-4")
    tokens = sum(len(encoding.encode(m["content"])) for m in messages)
    return tokens

# Log in webhook_handler.py
tokens_used = count_tokens(messages)
logger.info(f"GPT-4 tokens used: {tokens_used}")
```

**Estimated costs per test:**
- Intent parsing (GPT-4): ~200 tokens = $0.006 per message
- 100 test messages = ~$0.60

---

## Next Steps

After successful testing:

1. ✅ **Deploy to staging environment**
   - Set up production PostgreSQL
   - Configure production Evolution API
   - Deploy with proper secrets management

2. ✅ **Implement monitoring**
   - Set up logging aggregation (e.g., Loki)
   - Add metrics (Prometheus)
   - Configure alerts

3. ✅ **Load testing**
   - Simulate multiple concurrent WhatsApp messages
   - Test with realistic condominium size (50-200 units)
   - Measure response times

4. ✅ **Security audit**
   - Review multi-tenant isolation
   - Test authentication/authorization
   - Verify webhook signature validation

---

**Happy Testing! 🚀**

Para soporte: Revisa los logs de cada servicio o abre un issue en el repositorio.
