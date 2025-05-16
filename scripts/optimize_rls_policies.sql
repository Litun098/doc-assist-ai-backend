-- AnyDocAI RLS Policy Optimization Script
-- Run this script in the Supabase SQL Editor to optimize RLS policies for performance

-- STEP 1: Drop ALL existing policies using a more comprehensive approach
-- This will remove all policies from all tables, regardless of their names

-- Get all policies for users table and drop them
DO $$
DECLARE
    policy_record RECORD;
BEGIN
    FOR policy_record IN
        SELECT policyname
        FROM pg_policies
        WHERE tablename = 'users' AND schemaname = 'public'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON users', policy_record.policyname);
        RAISE NOTICE 'Dropped policy % on users', policy_record.policyname;
    END LOOP;
END $$;

-- Get all policies for documents table and drop them
DO $$
DECLARE
    policy_record RECORD;
BEGIN
    FOR policy_record IN
        SELECT policyname
        FROM pg_policies
        WHERE tablename = 'documents' AND schemaname = 'public'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON documents', policy_record.policyname);
        RAISE NOTICE 'Dropped policy % on documents', policy_record.policyname;
    END LOOP;
END $$;

-- Get all policies for chat_sessions table and drop them
DO $$
DECLARE
    policy_record RECORD;
BEGIN
    FOR policy_record IN
        SELECT policyname
        FROM pg_policies
        WHERE tablename = 'chat_sessions' AND schemaname = 'public'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON chat_sessions', policy_record.policyname);
        RAISE NOTICE 'Dropped policy % on chat_sessions', policy_record.policyname;
    END LOOP;
END $$;

-- Get all policies for chat_messages table and drop them
DO $$
DECLARE
    policy_record RECORD;
BEGIN
    FOR policy_record IN
        SELECT policyname
        FROM pg_policies
        WHERE tablename = 'chat_messages' AND schemaname = 'public'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON chat_messages', policy_record.policyname);
        RAISE NOTICE 'Dropped policy % on chat_messages', policy_record.policyname;
    END LOOP;
END $$;

-- Get all policies for session_documents table and drop them
DO $$
DECLARE
    policy_record RECORD;
BEGIN
    FOR policy_record IN
        SELECT policyname
        FROM pg_policies
        WHERE tablename = 'session_documents' AND schemaname = 'public'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON session_documents', policy_record.policyname);
        RAISE NOTICE 'Dropped policy % on session_documents', policy_record.policyname;
    END LOOP;
END $$;

-- Get all policies for user_usage table and drop them
DO $$
DECLARE
    policy_record RECORD;
BEGIN
    FOR policy_record IN
        SELECT policyname
        FROM pg_policies
        WHERE tablename = 'user_usage' AND schemaname = 'public'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON user_usage', policy_record.policyname);
        RAISE NOTICE 'Dropped policy % on user_usage', policy_record.policyname;
    END LOOP;
END $$;

-- Now create optimized policies using (SELECT auth.uid()) to avoid re-evaluation
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

-- Verify policies are in place
SELECT tablename, policyname, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
