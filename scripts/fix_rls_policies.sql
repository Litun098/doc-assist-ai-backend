-- AnyDocAI RLS Policy Fix Script
-- Run this script in the Supabase SQL Editor to fix RLS policies

-- STEP 1: Disable RLS temporarily for all tables to ensure clean slate
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE documents DISABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions DISABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE session_documents DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_usage DISABLE ROW LEVEL SECURITY;

-- STEP 2: Drop ALL existing policies using a comprehensive approach
DO $$
DECLARE
    policy_record RECORD;
    tables_to_check TEXT[] := ARRAY['users', 'documents', 'chat_sessions', 'chat_messages', 'session_documents', 'user_usage'];
    table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY tables_to_check
    LOOP
        FOR policy_record IN
            SELECT policyname
            FROM pg_policies
            WHERE tablename = table_name AND schemaname = 'public'
        LOOP
            EXECUTE format('DROP POLICY IF EXISTS %I ON %I', policy_record.policyname, table_name);
            RAISE NOTICE 'Dropped policy % on %', policy_record.policyname, table_name;
        END LOOP;
    END LOOP;
END $$;

-- STEP 3: Re-enable RLS for all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_usage ENABLE ROW LEVEL SECURITY;

-- STEP 4: Create new optimized policies using (SELECT auth.uid()) to avoid re-evaluation
-- and consolidate multiple policies where possible

-- Users Table Policies
CREATE POLICY "Users can access their own data" ON users
  FOR ALL USING ((SELECT auth.uid()) = id);

CREATE POLICY "Service role can access all users" ON users
  FOR ALL USING ((SELECT auth.role()) = 'service_role');

-- Documents Table Policies
CREATE POLICY "Users can access their own documents" ON documents
  FOR ALL USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "Service role can access all documents" ON documents
  FOR ALL USING ((SELECT auth.role()) = 'service_role');

-- Chat Sessions Table Policies
CREATE POLICY "Users can access their own chat sessions" ON chat_sessions
  FOR ALL USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "Service role can access all chat sessions" ON chat_sessions
  FOR ALL USING ((SELECT auth.role()) = 'service_role');

-- Chat Messages Table Policies
CREATE POLICY "Users can access messages in their sessions" ON chat_messages
  FOR ALL USING (
    (SELECT auth.uid()) IN (
      SELECT user_id FROM chat_sessions WHERE id = chat_messages.session_id
    )
  );

CREATE POLICY "Service role can access all chat messages" ON chat_messages
  FOR ALL USING ((SELECT auth.role()) = 'service_role');

-- Session Documents Table Policies
CREATE POLICY "Users can view and delete their session documents" ON session_documents
  FOR SELECT USING (
    (SELECT auth.uid()) IN (
      SELECT user_id FROM chat_sessions WHERE id = session_documents.session_id
    )
  );

CREATE POLICY "Users can insert their session documents" ON session_documents
  FOR INSERT WITH CHECK (
    (SELECT auth.uid()) IN (
      SELECT user_id FROM chat_sessions WHERE id = session_documents.session_id
    ) AND
    (SELECT auth.uid()) IN (
      SELECT user_id FROM documents WHERE id = session_documents.document_id
    )
  );

CREATE POLICY "Users can delete their session documents" ON session_documents
  FOR DELETE USING (
    (SELECT auth.uid()) IN (
      SELECT user_id FROM chat_sessions WHERE id = session_documents.session_id
    )
  );

CREATE POLICY "Service role can access all session documents" ON session_documents
  FOR ALL USING ((SELECT auth.role()) = 'service_role');

-- User Usage Table Policies
CREATE POLICY "Users can view their own usage" ON user_usage
  FOR SELECT USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "Service role can access all user usage" ON user_usage
  FOR ALL USING ((SELECT auth.role()) = 'service_role');

-- STEP 5: Verify policies are in place
SELECT tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- STEP 6: Run the test script to verify RLS policies are working correctly
-- python scripts/test_rls.py
