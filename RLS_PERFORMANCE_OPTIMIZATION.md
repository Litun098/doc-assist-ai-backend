# AnyDocAI RLS Performance Optimization

## Overview

The Supabase database linter has identified two main performance issues with your Row Level Security (RLS) policies:

1. **Auth RLS Initialization Plan Issues**: The `auth.uid()` function is being re-evaluated for each row, which can cause performance problems at scale.

2. **Multiple Permissive Policies**: You have multiple permissive policies for the same role and action on several tables, which is inefficient as each policy must be executed for every relevant query.

## Performance Impact

These issues can significantly impact the performance of your application, especially as your database grows:

- **Re-evaluating `auth.uid()`**: This function is called for every row being evaluated, which can be very expensive for large tables.
- **Multiple Permissive Policies**: Having multiple policies for the same role and action means that PostgreSQL has to evaluate all of them for each query, which multiplies the work needed.

## Solution

I've created a SQL script (`scripts/optimize_rls_policies.sql`) that addresses both issues:

1. **Using `(SELECT auth.uid())` instead of `auth.uid()`**: This ensures the function is evaluated only once per query, not once per row.

2. **Consolidating Policies**: Where possible, I've combined multiple policies into a single policy using the `FOR ALL` action instead of separate policies for `SELECT`, `INSERT`, `UPDATE`, and `DELETE`.

## Implementation Steps

1. Log in to your Supabase dashboard at https://app.supabase.com/
2. Select your AnyDocAI project
3. Go to the SQL Editor (left sidebar)
4. Create a new query
5. Copy and paste the contents of `scripts/optimize_rls_policies.sql` into the editor
6. Run the query
7. Verify that the query executed successfully

## Benefits

These optimizations will provide several benefits:

- **Improved Query Performance**: Queries will execute faster, especially for large tables.
- **Reduced Database Load**: The database will have less work to do for each query.
- **Better Scalability**: Your application will be able to handle more users and data without performance degradation.
- **Simplified Policy Management**: Fewer policies means easier maintenance and less chance of conflicts.

## Verification

After running the script, you can verify that the RLS policies are correctly set up by:

1. Running the test_rls.py script:
   ```
   python scripts/test_rls.py
   ```

2. Testing the application to ensure that users can still access their own data

3. Running the Supabase database linter again to confirm that the warnings are resolved

## Additional Notes

- The optimized policies maintain the same security model as the original policies, just with better performance.
- The script first drops all existing policies to avoid conflicts, then creates the optimized policies.
- For the `session_documents` table, I kept separate policies for different actions due to the complex conditions needed for the `INSERT` action.

## References

- [Supabase RLS Documentation](https://supabase.com/docs/guides/auth/row-level-security)
- [PostgreSQL RLS Performance Tips](https://supabase.com/docs/guides/database/postgres/row-level-security#call-functions-with-select)
