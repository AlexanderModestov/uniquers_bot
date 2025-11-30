"""
Test script to verify LLM logging setup
Run this to check if logging is working correctly
"""

import asyncio
import sys
import os

# Add bot directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

from bot.supabase_client import SupabaseClient
from bot.services.llm_logger import LLMLogger
from bot.config import Config


async def test_database_connection():
    """Test 1: Verify database connection"""
    print("=" * 60)
    print("TEST 1: Database Connection")
    print("=" * 60)

    try:
        # Validate config
        Config.validate()
        print("✅ Config validated successfully")
        print(f"   Supabase URL: {Config.SUPABASE_URL}")

        # Create client
        client = SupabaseClient(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        print("✅ SupabaseClient created successfully")

        return client
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_table_exists(client):
    """Test 2: Check if llm_request_logs table exists"""
    print("\n" + "=" * 60)
    print("TEST 2: Table Existence")
    print("=" * 60)

    try:
        # Try to query the table (will fail if table doesn't exist)
        response = client.client.table('llm_request_logs').select('id').limit(1).execute()
        print("✅ Table 'llm_request_logs' exists")
        print(f"   Current record count: {len(response.data)}")
        return True
    except Exception as e:
        print(f"❌ Table 'llm_request_logs' does NOT exist or is inaccessible")
        print(f"   Error: {e}")
        print("\n⚠️  You need to apply the migration first!")
        print("   See database/README.md for instructions")
        return False


async def test_manual_insert(client):
    """Test 3: Try manual insert to verify permissions"""
    print("\n" + "=" * 60)
    print("TEST 3: Manual Insert Test")
    print("=" * 60)

    try:
        result = await client.log_llm_request(
            request_type='chat',
            model='test-model',
            user_id=None,
            input_text='Test input',
            output_text='Test output',
            tokens_total=100,
            latency_ms=500,
            success=True
        )

        if result:
            print("✅ Successfully inserted test record")
            print(f"   Record ID: {result.get('id')}")

            # Clean up test record
            try:
                client.client.table('llm_request_logs').delete().eq('id', result['id']).execute()
                print("✅ Test record cleaned up")
            except:
                print("⚠️  Could not delete test record (not critical)")

            return True
        else:
            print("❌ Insert returned None - check logs for errors")
            return False

    except Exception as e:
        print(f"❌ Failed to insert test record: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_logger(client):
    """Test 4: Test LLMLogger service"""
    print("\n" + "=" * 60)
    print("TEST 4: LLMLogger Service Test")
    print("=" * 60)

    try:
        logger = LLMLogger(client)
        print("✅ LLMLogger created successfully")

        # Test chat logging
        success = await logger.log_chat_request(
            model='test-gpt-4',
            input_text='Test question',
            output_text='Test answer',
            user_id=1,
            tokens_prompt=10,
            tokens_completion=20,
            tokens_total=30,
            latency_ms=250,
            success=True
        )

        if success:
            print("✅ LLMLogger.log_chat_request() succeeded")

            # Verify the record was created
            response = client.client.table('llm_request_logs').select('*').eq('model', 'test-gpt-4').execute()
            if response.data:
                print(f"✅ Found {len(response.data)} test record(s) in database")
                # Clean up
                for record in response.data:
                    client.client.table('llm_request_logs').delete().eq('id', record['id']).execute()
                print("✅ Test records cleaned up")

            return True
        else:
            print("❌ LLMLogger.log_chat_request() returned False")
            return False

    except Exception as e:
        print(f"❌ LLMLogger test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n" + "=" * 60)
    print("LLM LOGGING DIAGNOSTIC TEST")
    print("=" * 60)

    # Test 1: Database connection
    client = await test_database_connection()
    if not client:
        print("\n❌ Cannot proceed - database connection failed")
        return

    # Test 2: Table exists
    table_exists = await test_table_exists(client)
    if not table_exists:
        print("\n❌ Cannot proceed - table does not exist")
        print("\n📝 NEXT STEPS:")
        print("   1. Go to Supabase Dashboard → SQL Editor")
        print("   2. Run the migration: database/migrations/create_llm_logs_table.sql")
        print("   3. Run this test again")
        return

    # Test 3: Manual insert
    insert_works = await test_manual_insert(client)
    if not insert_works:
        print("\n❌ Manual insert failed - check permissions")
        return

    # Test 4: Logger service
    logger_works = await test_logger(client)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    if table_exists and insert_works and logger_works:
        print("✅ ALL TESTS PASSED - Logging should work correctly!")
        print("\nYour logging system is properly configured.")
        print("Logs will now appear in Supabase → Table Editor → llm_request_logs")
    else:
        print("❌ SOME TESTS FAILED - See errors above")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
