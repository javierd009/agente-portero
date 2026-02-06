"""
Seed data for testing Agente Portero
Creates sample condominium, residents, agents, and reports
"""
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from dotenv import load_dotenv
load_dotenv()

from infrastructure.database import get_engine, init_db
from sqlmodel.ext.asyncio.session import AsyncSession
from domain.models import (
    Condominium,
    Agent,
    Resident,
    Visitor,
    Vehicle,
    Report,
)


async def seed_database():
    """Seed the database with test data"""
    print("🌱 Starting database seeding...")

    # Initialize database
    await init_db()
    print("✅ Database initialized")

    # Create async session
    engine = get_engine()
    async with AsyncSession(engine) as session:

        # 1. Create Condominium
        print("\n📍 Creating condominium...")
        condominium = Condominium(
            name="Residencial del Valle",
            slug="residencial-del-valle",
            address="Av. Principal 1234, Monterrey, NL",
            timezone="America/Mexico_City",
            settings={
                "gate_api_url": "http://192.168.1.100",
                "cameras": ["cam_01", "cam_02"],
                "notify_whatsapp": True,
                "auto_open_residents": True,
            },
            is_active=True
        )
        session.add(condominium)
        await session.commit()
        await session.refresh(condominium)
        print(f"   ✅ {condominium.name} (ID: {condominium.id})")

        # 2. Create Residents
        print("\n👥 Creating residents...")
        residents_data = [
            {
                "name": "Juan Pérez García",
                "unit": "A-101",
                "phone": "+52 81 1234 5678",
                "email": "juan.perez@gmail.com",
                "whatsapp": "5218112345678",  # Format for Evolution API
                "authorized_visitors": ["María González", "Pedro Ramírez"],
            },
            {
                "name": "María Rodríguez López",
                "unit": "A-205",
                "phone": "+52 81 9876 5432",
                "email": "maria.rodriguez@gmail.com",
                "whatsapp": "5218198765432",
                "authorized_visitors": ["Carlos Sánchez"],
            },
            {
                "name": "Carlos Martínez Hernández",
                "unit": "B-103",
                "phone": "+52 81 5555 1234",
                "email": "carlos.martinez@gmail.com",
                "whatsapp": "5218155551234",
                "authorized_visitors": [],
            },
        ]

        residents = []
        for res_data in residents_data:
            resident = Resident(
                condominium_id=condominium.id,
                **res_data,
                is_active=True
            )
            session.add(resident)
            residents.append(resident)

        await session.commit()
        for r in residents:
            await session.refresh(r)
            print(f"   ✅ {r.name} - {r.unit} (WhatsApp: {r.whatsapp})")

        # 3. Create Vehicles
        print("\n🚗 Creating vehicles...")
        vehicles_data = [
            {
                "resident_id": residents[0].id,
                "plate": "ABC-1234",
                "brand": "Toyota",
                "model": "Camry",
                "color": "Blanco",
            },
            {
                "resident_id": residents[1].id,
                "plate": "XYZ-5678",
                "brand": "Honda",
                "model": "Civic",
                "color": "Gris",
            },
        ]

        for veh_data in vehicles_data:
            vehicle = Vehicle(
                condominium_id=condominium.id,
                **veh_data,
                is_active=True
            )
            session.add(vehicle)

        await session.commit()
        print(f"   ✅ Created {len(vehicles_data)} vehicles")

        # 4. Create AI Agent
        print("\n🤖 Creating AI agent...")
        agent = Agent(
            condominium_id=condominium.id,
            name="Agente Virtual - Residencial del Valle",
            extension="100",
            prompt="""Eres el agente virtual de seguridad de Residencial del Valle.
Tu trabajo es:
1. Saludar cordialmente a los visitantes
2. Preguntar su nombre y a quién buscan
3. Verificar si están autorizados
4. Notificar al residente si es necesario
5. Abrir la puerta cuando sea apropiado

Siempre sé cortés, profesional y eficiente.""",
            voice_id="alloy",  # OpenAI voice
            language="es-MX",
            is_active=True,
            settings={
                "max_call_duration": 300,  # 5 minutes
                "enable_transfer": True,
                "fallback_number": "+52 81 1111 1111",
            }
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)
        print(f"   ✅ {agent.name}")

        # 5. Create Sample Visitors (historical)
        print("\n🚶 Creating sample visitors...")
        visitors_data = [
            {
                "resident_id": residents[0].id,
                "name": "María González",
                "phone": "+52 81 2222 3333",
                "status": "exited",
                "authorized_by": "resident",
                "entry_time": datetime.utcnow() - timedelta(hours=2),
                "exit_time": datetime.utcnow() - timedelta(hours=1),
            },
            {
                "resident_id": residents[1].id,
                "name": "Delivery Uber Eats",
                "status": "exited",
                "authorized_by": "whatsapp",
                "entry_time": datetime.utcnow() - timedelta(hours=4),
                "exit_time": datetime.utcnow() - timedelta(hours=4, minutes=-5),
            },
        ]

        for vis_data in visitors_data:
            visitor = Visitor(
                condominium_id=condominium.id,
                **vis_data
            )
            session.add(visitor)

        await session.commit()
        print(f"   ✅ Created {len(visitors_data)} historical visitors")

        # 6. Create Sample Reports
        print("\n📝 Creating sample reports...")
        reports_data = [
            {
                "resident_id": residents[0].id,
                "report_type": "maintenance",
                "title": "Luz fundida en pasillo",
                "description": "La luz del pasillo principal (Edificio A) está fundida",
                "location": "Pasillo principal - Edificio A",
                "urgency": "normal",
                "status": "pending",
                "source": "whatsapp",
            },
            {
                "resident_id": residents[1].id,
                "report_type": "security",
                "title": "Puerta de estacionamiento no cierra bien",
                "description": "La puerta automática del estacionamiento no cierra completamente",
                "location": "Estacionamiento subterráneo",
                "urgency": "high",
                "status": "in_progress",
                "source": "web",
            },
            {
                "resident_id": residents[2].id,
                "report_type": "noise",
                "title": "Ruido excesivo en unidad vecina",
                "description": "La unidad B-104 tiene música alta después de las 11 PM",
                "location": "Edificio B, piso 1",
                "urgency": "low",
                "status": "resolved",
                "source": "whatsapp",
                "resolved_at": datetime.utcnow() - timedelta(days=1),
                "resolution_notes": "Se habló con el residente. Prometió bajar el volumen.",
            },
        ]

        for rep_data in reports_data:
            report = Report(
                condominium_id=condominium.id,
                **rep_data
            )
            session.add(report)

        await session.commit()
        print(f"   ✅ Created {len(reports_data)} sample reports")

    print("\n" + "="*60)
    print("✅ Database seeding completed successfully!")
    print("="*60)
    print("\n📊 Summary:")
    print(f"   • 1 Condominium: {condominium.name}")
    print(f"   • {len(residents)} Residents")
    print(f"   • {len(vehicles_data)} Vehicles")
    print(f"   • 1 AI Agent")
    print(f"   • {len(visitors_data)} Sample Visitors")
    print(f"   • {len(reports_data)} Sample Reports")
    print("\n🔑 Condominium ID (save this for API calls):")
    print(f"   {condominium.id}")
    print("\n📱 Test WhatsApp numbers:")
    for r in residents:
        print(f"   • {r.name}: {r.whatsapp}")
    print("\n💡 Next steps:")
    print("   1. Send WhatsApp message to one of the numbers above")
    print("   2. Test: 'Viene Pedro Ramírez en 10 minutos'")
    print("   3. Check the backend API: http://localhost:8000/docs")
    print()


async def clear_database():
    """Clear all data from database (DANGER!)"""
    print("⚠️  CLEARING DATABASE...")

    from sqlmodel import SQLModel

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

    print("✅ Database cleared and recreated")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        print("⚠️  WARNING: This will delete ALL data!")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.lower() == "yes":
            asyncio.run(clear_database())
            asyncio.run(seed_database())
        else:
            print("Aborted.")
    else:
        asyncio.run(seed_database())
