#!/usr/bin/env python3
"""
Test FASE 1: Supabase Database Setup
Verifica que todas las tablas, índices y seed data estén correctamente creados
"""

import os
import sys
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, inspect

# Colors for terminal output
class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color

def print_header(msg: str):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
    print(f"{Colors.BLUE}{msg}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*60}{Colors.NC}\n")

def print_test(msg: str):
    print(f"{Colors.YELLOW}[TEST] {msg}{Colors.NC}")

def print_success(msg: str):
    print(f"{Colors.GREEN}✅ PASS: {msg}{Colors.NC}")

def print_fail(msg: str, error: str = ""):
    print(f"{Colors.RED}❌ FAIL: {msg}{Colors.NC}")
    if error:
        print(f"{Colors.RED}   Error: {error}{Colors.NC}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️  WARNING: {msg}{Colors.NC}")

class TestResults:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.errors: List[str] = []

    def add_pass(self):
        self.total += 1
        self.passed += 1

    def add_fail(self, error: str):
        self.total += 1
        self.failed += 1
        self.errors.append(error)

    def print_summary(self):
        print_header("TEST RESULTS SUMMARY")
        print(f"\n{Colors.BLUE}Total Tests:{Colors.NC} {self.total}")
        print(f"{Colors.GREEN}Passed:{Colors.NC} {self.passed}")
        print(f"{Colors.RED}Failed:{Colors.NC} {self.failed}")

        if self.total > 0:
            pass_rate = (self.passed * 100) // self.total
            print(f"{Colors.BLUE}Pass Rate:{Colors.NC} {pass_rate}%")

        if self.failed > 0:
            print(f"\n{Colors.RED}Errors encountered:{Colors.NC}")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")

        print()

        if self.failed == 0:
            print(f"{Colors.GREEN}🎉 ALL TESTS PASSED!{Colors.NC}")
            print(f"{Colors.GREEN}FASE 1 (Supabase) is configured correctly.{Colors.NC}\n")
            return 0
        else:
            print(f"{Colors.RED}❌ SOME TESTS FAILED{Colors.NC}")
            print(f"{Colors.RED}Fix the issues above before proceeding to FASE 2.{Colors.NC}\n")
            return 1

async def test_supabase_connection(results: TestResults):
    """Test 1: Database Connection"""
    print_header("1. DATABASE CONNECTION")

    print_test("Loading environment variables")

    # Try to load from .env.production first, then .env
    if os.path.exists('.env.production'):
        load_dotenv('.env.production')
        print("   Loaded .env.production")
    elif os.path.exists('.env'):
        load_dotenv('.env')
        print("   Loaded .env")
    else:
        print_warning("No .env file found, using environment variables")

    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print_fail("DATABASE_URL not set", "Set DATABASE_URL in .env.production")
        results.add_fail("DATABASE_URL not configured")
        return None

    # Convert postgresql:// to postgresql+asyncpg:// for async driver
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)

    print_success("DATABASE_URL is configured")

    # Mask password in display
    masked_url = database_url
    if '@' in masked_url:
        parts = masked_url.split('@')
        if ':' in parts[0]:
            user_pass = parts[0].rsplit(':', 1)
            masked_url = f"{user_pass[0]}:***@{parts[1]}"

    print(f"   URL: {masked_url}")
    results.add_pass()

    print_test("Connecting to Supabase database")

    try:
        engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
            print_success(f"Connected to database")
            print(f"   PostgreSQL version: {version}")
            results.add_pass()

        return engine

    except Exception as e:
        print_fail("Cannot connect to database", str(e))
        results.add_fail(f"Database connection error: {str(e)}")
        return None

async def test_tables_exist(engine, results: TestResults):
    """Test 2: Required Tables Exist"""
    print_header("2. DATABASE TABLES")

    expected_tables = [
        'condominiums',
        'agents',
        'residents',
        'visitors',
        'vehicles',
        'access_logs',
        'reports',
        'camera_events',
        'notifications'
    ]

    print_test(f"Checking for {len(expected_tables)} required tables")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # Get list of tables
            result = await session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]

            print(f"   Found {len(tables)} tables in public schema")

            all_present = True
            for table in expected_tables:
                if table in tables:
                    print(f"   ✅ {table}")
                else:
                    print(f"   ❌ {table} - MISSING")
                    all_present = False

            if all_present:
                print_success("All required tables exist")
                results.add_pass()
            else:
                print_fail("Some tables are missing", "Run SQL schema from DEPLOYMENT_GUIDE.md")
                results.add_fail("Missing database tables")

    except Exception as e:
        print_fail("Error checking tables", str(e))
        results.add_fail(f"Table check error: {str(e)}")

async def test_indexes_exist(engine, results: TestResults):
    """Test 3: Required Indexes Exist"""
    print_header("3. DATABASE INDEXES")

    expected_indexes = [
        'idx_residents_whatsapp',
        'idx_access_logs_created_at',
        'idx_reports_status'
    ]

    print_test(f"Checking for {len(expected_indexes)} critical indexes")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            result = await session.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                ORDER BY indexname
            """))
            indexes = [row[0] for row in result.fetchall()]

            print(f"   Found {len(indexes)} indexes total")

            all_present = True
            for index in expected_indexes:
                if index in indexes:
                    print(f"   ✅ {index}")
                else:
                    print(f"   ❌ {index} - MISSING")
                    all_present = False

            if all_present:
                print_success("All critical indexes exist")
                results.add_pass()
            else:
                print_fail("Some indexes are missing", "Performance may be affected")
                results.add_fail("Missing database indexes")

    except Exception as e:
        print_fail("Error checking indexes", str(e))
        results.add_fail(f"Index check error: {str(e)}")

async def test_seed_data(engine, results: TestResults):
    """Test 4: Seed Data Exists"""
    print_header("4. SEED DATA")

    print_test("Checking for seed data in tables")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # Check condominiums
            result = await session.execute(text("SELECT COUNT(*) FROM condominiums"))
            condo_count = result.scalar()
            print(f"   Condominiums: {condo_count}")

            if condo_count > 0:
                result = await session.execute(text("SELECT name, slug FROM condominiums LIMIT 1"))
                condo = result.fetchone()
                print(f"      Example: {condo[0]} ({condo[1]})")
                print_success(f"Found {condo_count} condominium(s)")
                results.add_pass()
            else:
                print_fail("No condominiums found", "Run seed data SQL")
                results.add_fail("Missing seed data: condominiums")

            # Check residents
            result = await session.execute(text("SELECT COUNT(*) FROM residents"))
            resident_count = result.scalar()
            print(f"   Residents: {resident_count}")

            if resident_count > 0:
                result = await session.execute(text(
                    "SELECT name, unit, whatsapp FROM residents WHERE whatsapp IS NOT NULL LIMIT 1"
                ))
                resident = result.fetchone()
                if resident:
                    print(f"      Example: {resident[0]} (Unit {resident[1]}, WhatsApp: {resident[2]})")
                print_success(f"Found {resident_count} resident(s)")
                results.add_pass()
            else:
                print_fail("No residents found", "Run seed data SQL")
                results.add_fail("Missing seed data: residents")

            # Check agents
            result = await session.execute(text("SELECT COUNT(*) FROM agents"))
            agent_count = result.scalar()
            print(f"   AI Agents: {agent_count}")

            if agent_count > 0:
                print_success(f"Found {agent_count} agent(s)")
                results.add_pass()
            else:
                print_warning("No agents found - This is optional for testing")

    except Exception as e:
        print_fail("Error checking seed data", str(e))
        results.add_fail(f"Seed data check error: {str(e)}")

async def test_rls_enabled(engine, results: TestResults):
    """Test 5: Row Level Security (RLS) Enabled"""
    print_header("5. ROW LEVEL SECURITY (RLS)")

    print_test("Checking RLS status on tables")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            result = await session.execute(text("""
                SELECT tablename, rowsecurity
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
            """))
            tables = result.fetchall()

            rls_enabled_count = 0
            rls_disabled_count = 0

            for table, rls in tables:
                if rls:
                    print(f"   ✅ {table} - RLS enabled")
                    rls_enabled_count += 1
                else:
                    print(f"   ⚠️  {table} - RLS disabled")
                    rls_disabled_count += 1

            if rls_enabled_count > 0:
                print_success(f"RLS enabled on {rls_enabled_count} table(s)")
                results.add_pass()
            else:
                print_warning("No tables have RLS enabled")
                print_warning("This is a security concern for multi-tenant setup")
                results.add_fail("RLS not enabled on any tables")

    except Exception as e:
        print_fail("Error checking RLS", str(e))
        results.add_fail(f"RLS check error: {str(e)}")

async def test_critical_queries(engine, results: TestResults):
    """Test 6: Critical Queries Work"""
    print_header("6. CRITICAL QUERIES")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # Test 6.1: Get resident by WhatsApp
            print_test("Query: Get resident by WhatsApp number")
            result = await session.execute(text(
                "SELECT id, name, unit, whatsapp FROM residents WHERE whatsapp IS NOT NULL LIMIT 1"
            ))
            resident = result.fetchone()

            if resident:
                print(f"   Found: {resident[1]} - Unit {resident[2]} - {resident[3]}")
                print_success("Resident by WhatsApp query works")
                results.add_pass()
            else:
                print_fail("No residents with WhatsApp found", "Add seed data")
                results.add_fail("Cannot query residents by WhatsApp")

            # Test 6.2: Get recent access logs
            print_test("Query: Get recent access logs")
            result = await session.execute(text(
                "SELECT COUNT(*) FROM access_logs WHERE created_at > NOW() - INTERVAL '7 days'"
            ))
            log_count = result.scalar()
            print(f"   Access logs (last 7 days): {log_count}")
            print_success("Access logs query works")
            results.add_pass()

            # Test 6.3: Get reports by status
            print_test("Query: Get reports by status")
            result = await session.execute(text(
                "SELECT COUNT(*), status FROM reports GROUP BY status"
            ))
            report_stats = result.fetchall()

            if report_stats:
                for count, status in report_stats:
                    print(f"   {status}: {count}")
                print_success("Reports query works")
                results.add_pass()
            else:
                print_warning("No reports found - This is OK for initial setup")
                results.add_pass()

    except Exception as e:
        print_fail("Error executing critical queries", str(e))
        results.add_fail(f"Critical query error: {str(e)}")

async def main():
    """Main test runner"""
    print_header("FASE 1: SUPABASE DATABASE TESTS")
    print(f"Started at: {Colors.BLUE}{asyncio.get_event_loop().time()}{Colors.NC}\n")

    results = TestResults()

    # Test 1: Connection
    engine = await test_supabase_connection(results)

    if not engine:
        print_fail("Cannot proceed without database connection")
        results.print_summary()
        return 1

    # Test 2-6: Database structure and data
    await test_tables_exist(engine, results)
    await test_indexes_exist(engine, results)
    await test_seed_data(engine, results)
    await test_rls_enabled(engine, results)
    await test_critical_queries(engine, results)

    # Close engine
    await engine.dispose()

    # Print summary and return exit code
    return results.print_summary()

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Tests interrupted by user{Colors.NC}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {e}{Colors.NC}\n")
        sys.exit(2)
