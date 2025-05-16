# How to Fix RLS Performance Issues in AnyDocAI

This guide will help you fix Row Level Security (RLS) performance issues in your Supabase database for AnyDocAI.

## Background

Row Level Security (RLS) is a feature in PostgreSQL that allows you to restrict which rows a user can access in a table. In AnyDocAI, we use RLS to ensure that users can only access their own data.

## Performance Issues Detected

The Supabase database linter has identified two main performance issues with your RLS policies:

1. **Multiple Permissive Policies**: You have multiple permissive policies for the same role and action on several tables, which is inefficient as each policy must be executed for every relevant query.

2. **Auth Function Re-evaluation**: The `auth.uid()` function is being re-evaluated for each row, which can cause performance problems at scale.

## Impact of These Issues

These performance issues can significantly impact your application as it grows:

1. **Slower Queries**: Each additional policy adds overhead to query execution
2. **Higher Database Load**: Re-evaluating `auth.uid()` for each row increases CPU usage
3. **Reduced Scalability**: As your tables grow, these inefficiencies become more pronounced

## Solution

We've created a comprehensive SQL script that addresses both issues:

1. **Consolidating Policies**: The script replaces multiple policies with a single policy using `FOR ALL` instead of separate policies for `SELECT`, `INSERT`, `UPDATE`, and `DELETE`.

2. **Optimizing Auth Function Calls**: The script uses `(SELECT auth.uid())` instead of `auth.uid()` to ensure the function is evaluated only once per query, not once per row.

## Steps to Fix

### 1. Run the Optimized RLS Policy Script

1. Log in to your Supabase dashboard at https://app.supabase.com/
2. Select your AnyDocAI project
3. Go to the SQL Editor (left sidebar)
4. Create a new query
5. Copy and paste the contents of `scripts/fix_rls_policies.sql` into the editor
6. Run the query
7. Verify that the query executed successfully

### 2. What the Script Does

The script performs the following steps:

1. **Disables RLS** temporarily on all tables to ensure a clean slate
2. **Drops all existing policies** using a comprehensive approach that finds and removes all policies
3. **Re-enables RLS** on all tables
4. **Creates new optimized policies** that:
   - Use `(SELECT auth.uid())` instead of `auth.uid()`
   - Consolidate multiple policies into single policies where possible
   - Maintain the same security model as the original policies
5. **Verifies** that the policies are in place

### 3. Key Optimizations

#### Before:
```sql
CREATE POLICY "Users can view their own documents" ON documents
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own documents" ON documents
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own documents" ON documents
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own documents" ON documents
  FOR DELETE USING (auth.uid() = user_id);
```

#### After:
```sql
CREATE POLICY "Users can access their own documents" ON documents
  FOR ALL USING ((SELECT auth.uid()) = user_id);
```

This single policy:
- Replaces four separate policies
- Uses `(SELECT auth.uid())` to evaluate the function only once
- Maintains the same security model

## Verification

After making these changes, you can verify that the RLS policies are working correctly by:

1. Running the test_rls.py script:
   ```
   python scripts/test_rls.py
   ```

2. Testing the application to ensure that users can access their own data

3. Checking the browser console for any authentication errors

## Optimized RLS Policies Overview

The script sets up the following optimized policies:

### Users Table
- **Consolidated**: Users can access (view, insert, update, delete) their own data
- Service role can access all users

### Documents Table
- **Consolidated**: Users can access (view, insert, update, delete) their own documents
- Service role can access all documents

### Chat Sessions Table
- **Consolidated**: Users can access (view, insert, update, delete) their own chat sessions
- Service role can access all chat sessions

### Chat Messages Table
- **Consolidated**: Users can access (view, insert) messages in their own sessions
- Service role can access all chat messages

### Session Documents Table
- Users can view and delete documents in their own sessions
- Users can insert documents in their own sessions (with additional checks)
- Service role can access all session documents

### User Usage Table
- Users can view their own usage
- Service role can access all user usage

All policies use `(SELECT auth.uid())` instead of `auth.uid()` for better performance.

## Troubleshooting

If you encounter any issues after running the script:

1. Check the Supabase SQL Editor output for any error messages
2. Verify that all tables have RLS enabled by running:
   ```sql
   SELECT tablename, rowsecurity
   FROM pg_tables
   WHERE schemaname = 'public';
   ```
3. Verify that policies are in place by running:
   ```sql
   SELECT tablename, policyname, cmd, qual, with_check
   FROM pg_policies
   WHERE schemaname = 'public'
   ORDER BY tablename, policyname;
   ```
4. Run the test script to verify RLS policies are working correctly:
   ```
   python scripts/test_rls.py
   ```

## Expected Benefits

After implementing these optimizations, you should see:

1. **Improved Query Performance**: Queries will execute faster, especially for large tables
2. **Reduced Database Load**: The database will have less work to do for each query
3. **Better Scalability**: Your application will be able to handle more users and data without performance degradation
4. **Simplified Policy Management**: Fewer policies means easier maintenance and less chance of conflicts

## References

- [Supabase RLS Documentation](https://supabase.com/docs/guides/auth/row-level-security)
- [PostgreSQL RLS Performance Tips](https://supabase.com/docs/guides/database/postgres/row-level-security#call-functions-with-select)
