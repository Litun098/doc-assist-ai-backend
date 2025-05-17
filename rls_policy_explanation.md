# AnyDocAI Row Level Security (RLS) Policy Explanation

This document explains the Row Level Security (RLS) policies implemented for AnyDocAI's Supabase database, focusing on how they support the session-first document management approach and ensure proper data isolation between users.

## Overview of RLS in Supabase

Row Level Security (RLS) in Supabase allows you to control which rows in a table a user can access. This is essential for multi-tenant applications like AnyDocAI where each user should only see their own data.

## Key Principles of Our RLS Implementation

1. **Data Isolation**: Users can only access their own data or data related to resources they own
2. **Performance Optimization**: Using `(SELECT auth.uid())` instead of `auth.uid()` to avoid re-evaluation
3. **Role-Specific Policies**: Explicitly specifying the role for each policy using the `TO` clause
4. **Query Efficiency**: Using `EXISTS` subqueries instead of `IN` for better performance
5. **Session-First Approach**: Supporting the session-first document management workflow

## Table-by-Table RLS Policies

### Users Table

```sql
-- Authenticated users can only access their own data
CREATE POLICY "users_authenticated_policy" ON users
  FOR ALL TO authenticated
  USING ((SELECT auth.uid()) = id);

-- Service role can access all users data
CREATE POLICY "users_service_policy" ON users
  FOR ALL TO service_role
  USING ((SELECT auth.role()) = 'service_role');
```

**Explanation**:
- Users can only view and modify their own user record
- The service role can access all user records for backend operations
- Using `(SELECT auth.uid())` instead of `auth.uid()` prevents re-evaluation for each row
- The `TO authenticated` and `TO service_role` clauses ensure policies only apply to specific roles
- This supports the authentication flow in the API implementation plan

### Documents Table

```sql
-- Authenticated users can only access their own documents
CREATE POLICY "documents_authenticated_policy" ON documents
  FOR ALL TO authenticated
  USING ((SELECT auth.uid()) = user_id);

-- Service role can access all documents
CREATE POLICY "documents_service_policy" ON documents
  FOR ALL TO service_role
  USING ((SELECT auth.role()) = 'service_role');
```

**Explanation**:
- Users can only access documents they own
- Using `(SELECT auth.uid())` improves performance
- The `TO authenticated` and `TO service_role` clauses prevent multiple permissive policies
- This supports the document APIs in the implementation plan, particularly:
  - `listAllDocuments`
  - `getDocumentById`
  - `deleteDocument`

### Chat Sessions Table

```sql
-- Authenticated users can only access their own chat sessions
CREATE POLICY "chat_sessions_authenticated_policy" ON chat_sessions
  FOR ALL TO authenticated
  USING ((SELECT auth.uid()) = user_id);

-- Service role can access all chat sessions
CREATE POLICY "chat_sessions_service_policy" ON chat_sessions
  FOR ALL TO service_role
  USING ((SELECT auth.role()) = 'service_role');
```

**Explanation**:
- Users can only access chat sessions they created
- Using `(SELECT auth.uid())` improves performance
- The `TO authenticated` and `TO service_role` clauses ensure policies only apply to specific roles
- This supports the session APIs in the implementation plan:
  - `createSession`
  - `listSessions`
  - `getSession`
  - `updateSession`
  - `deleteSession`

### Chat Messages Table

```sql
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

-- Service role can access all chat messages
CREATE POLICY "chat_messages_service_policy" ON chat_messages
  FOR ALL TO service_role
  USING ((SELECT auth.role()) = 'service_role');
```

**Explanation**:
- Users can only access messages in sessions they own
- This uses a subquery to check if the user owns the session that contains the message
- Using `(SELECT auth.uid())` improves performance
- The `TO authenticated` and `TO service_role` clauses prevent multiple permissive policies
- This supports the chat APIs in the implementation plan:
  - `getMessages`
  - `sendMessage`

### Session Documents Table

```sql
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

-- Service role can access all session documents
CREATE POLICY "session_documents_service_policy" ON session_documents
  FOR ALL TO service_role
  USING ((SELECT auth.role()) = 'service_role');
```

**Explanation**:
- For the session_documents junction table, we need separate policies for different operations
- SELECT: Users can view document associations for sessions they own
- INSERT: Users can only link documents they own to sessions they own
- DELETE: Users can only unlink documents from sessions they own
- Using `(SELECT auth.uid())` improves performance
- The `TO authenticated` and `TO service_role` clauses prevent multiple permissive policies
- This supports the session-first document management approach and these APIs:
  - `uploadDocumentToSession`
  - `listSessionDocuments`
  - `addDocumentsToSession`
  - `removeDocumentFromSession`

### User Usage Table

```sql
-- Authenticated users can only view their own usage data
CREATE POLICY "user_usage_authenticated_select_policy" ON user_usage
  FOR SELECT TO authenticated
  USING ((SELECT auth.uid()) = user_id);

-- Only the service role can modify usage data
CREATE POLICY "user_usage_service_policy" ON user_usage
  FOR ALL TO service_role
  USING ((SELECT auth.role()) = 'service_role');
```

**Explanation**:
- Users can only view their own usage data
- Only the service role can insert, update, or delete usage data
- Using `(SELECT auth.uid())` improves performance
- The `TO authenticated` and `TO service_role` clauses prevent multiple permissive policies
- This ensures that usage tracking is controlled by the backend

## How These Policies Address the Warnings

### 1. Auth RLS Initialization Plan Warnings

The warnings about `auth.uid()` and `auth.role()` being re-evaluated for each row are fixed by:

- Using `(SELECT auth.uid())` instead of `auth.uid()`
- Using `(SELECT auth.role())` instead of `auth.role()`

This ensures these functions are evaluated only once per query, not once per row, which significantly improves performance for tables with many rows.

### 2. Multiple Permissive Policies Warnings

The warnings about multiple permissive policies for the same role and action are fixed by:

- Explicitly specifying the role for each policy using the `TO` clause (e.g., `TO authenticated`, `TO service_role`)
- Using role-specific policy names (e.g., `users_authenticated_policy` instead of `users_isolation_policy`)
- Ensuring each role has only one policy per table or per operation

By using the `TO` clause, we ensure that policies only apply to the specified roles, preventing the issue where multiple policies apply to the same role and action.

## How These Policies Support the Session-First Approach

The session-first document management approach in AnyDocAI means:

1. Users create a chat session first
2. Documents are uploaded directly to the session
3. Documents are processed and indexed with session context
4. Users interact with documents in the context of a session

The RLS policies support this workflow by:

1. Ensuring users can only access their own sessions and documents
2. Allowing users to link their documents to their sessions
3. Restricting access to messages within sessions they own
4. Enabling the backend service role to perform necessary operations

## Performance Considerations

1. **Optimized Function Calls**: Using `(SELECT auth.uid())` instead of `auth.uid()` prevents re-evaluation for each row
2. **Consolidated Policies**: Using `FOR ALL` instead of separate policies for each operation reduces the number of policies
3. **Efficient Subqueries**: Using `EXISTS` instead of `IN` for subqueries improves performance
4. **Role-Specific Policies**: Using the `TO` clause ensures policies only apply to specific roles

## Security Considerations

1. **Complete Coverage**: All tables have RLS enabled and appropriate policies
2. **No Data Leakage**: Users cannot access other users' data
3. **Service Role Access**: Backend operations can bypass RLS when needed
4. **Junction Table Protection**: The session_documents junction table has appropriate policies to prevent unauthorized associations

## How to Apply These Policies

Run the `fix_rls_policies.sql` script in the Supabase SQL Editor to apply these policies. The script will:

1. Temporarily disable RLS
2. Drop all existing policies
3. Re-enable RLS
4. Create the new optimized policies
5. Verify that the policies are in place
