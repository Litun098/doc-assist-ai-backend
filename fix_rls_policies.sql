-- AnyDocAI RLS Policy Fix Script
-- This script fixes Row Level Security (RLS) policies for AnyDocAI Supabase database
-- It removes all existing policies and creates new optimized ones
-- Addresses both auth.uid() re-evaluation and multiple permissive policies issues

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

-- STEP 4: Create new optimized policies
-- Note: We use (SELECT auth.uid()) instead of auth.uid() to avoid re-evaluation
--       We explicitly specify the role for each policy to avoid multiple permissive policies

-- ==================== USERS TABLE POLICIES ====================
-- Authenticated users can only access their own data
CREATE POLICY "users_authenticated_policy" ON users
  FOR ALL TO authenticated
  USING ((SELECT auth.uid()) = id);

-- Service role can access all users data (for admin/backend operations)
CREATE POLICY "users_service_policy" ON users
  FOR ALL TO service_role
  USING ((SELECT auth.role()) = 'service_role');

-- ==================== DOCUMENTS TABLE POLICIES ====================
-- Authenticated users can only access their own documents
CREATE POLICY "documents_authenticated_policy" ON documents
  FOR ALL TO authenticated
  USING ((SELECT auth.uid()) = user_id);

-- Service role can access all documents (for admin/backend operations)
CREATE POLICY "documents_service_policy" ON documents
  FOR ALL TO service_role
  USING ((SELECT auth.role()) = 'service_role');

-- ==================== CHAT SESSIONS TABLE POLICIES ====================
-- Authenticated users can only access their own chat sessions
CREATE POLICY "chat_sessions_authenticated_policy" ON chat_sessions
  FOR ALL TO authenticated
  USING ((SELECT auth.uid()) = user_id);

-- Service role can access all chat sessions (for admin/backend operations)
CREATE POLICY "chat_sessions_service_policy" ON chat_sessions
  FOR ALL TO service_role
  USING ((SELECT auth.role()) = 'service_role');

-- ==================== CHAT MESSAGES TABLE POLICIES ====================
-- Authenticated users can only access messages in their own sessions
CREATE POLICY "chat_messages_authenticated_policy" ON chat_messages
  FOR ALL TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM chat_sessions
      WHERE id = chat_messages.session_id
      AND user_id = (SELECT auth.uid())
    )
  );

-- Service role can access all chat messages (for admin/backend operations)
CREATE POLICY "chat_messages_service_policy" ON chat_messages
  FOR ALL TO service_role
  USING ((SELECT auth.role()) = 'service_role');

-- ==================== SESSION DOCUMENTS TABLE POLICIES ====================
-- Authenticated users can view session documents for sessions they own
CREATE POLICY "session_documents_authenticated_select_policy" ON session_documents
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM chat_sessions
      WHERE id = session_documents.session_id
      AND user_id = (SELECT auth.uid())
    )
  );

-- Authenticated users can only link documents they own to sessions they own
CREATE POLICY "session_documents_authenticated_insert_policy" ON session_documents
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM chat_sessions
      WHERE id = session_documents.session_id
      AND user_id = (SELECT auth.uid())
    ) AND
    EXISTS (
      SELECT 1 FROM documents
      WHERE id = session_documents.document_id
      AND user_id = (SELECT auth.uid())
    )
  );

-- Authenticated users can only unlink documents from sessions they own
CREATE POLICY "session_documents_authenticated_delete_policy" ON session_documents
  FOR DELETE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM chat_sessions
      WHERE id = session_documents.session_id
      AND user_id = (SELECT auth.uid())
    )
  );

-- Service role can access all session documents (for admin/backend operations)
CREATE POLICY "session_documents_service_policy" ON session_documents
  FOR ALL TO service_role
  USING ((SELECT auth.role()) = 'service_role');

-- ==================== USER USAGE TABLE POLICIES ====================
-- Authenticated users can only view their own usage data
CREATE POLICY "user_usage_authenticated_select_policy" ON user_usage
  FOR SELECT TO authenticated
  USING ((SELECT auth.uid()) = user_id);

-- Only the service role can modify usage data
CREATE POLICY "user_usage_service_policy" ON user_usage
  FOR ALL TO service_role
  USING ((SELECT auth.role()) = 'service_role');

-- STEP 5: Verify policies are in place
SELECT tablename, policyname, cmd, qual, with_check, roles
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
