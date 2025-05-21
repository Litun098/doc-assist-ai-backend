-- Drop existing triggers, functions, and table
DROP TRIGGER IF EXISTS refresh_tokens_updated_at ON refresh_tokens;
DROP TRIGGER IF EXISTS cleanup_expired_refresh_tokens ON refresh_tokens;
DROP FUNCTION IF EXISTS update_refresh_tokens_updated_at();
DROP FUNCTION IF EXISTS cleanup_expired_refresh_tokens();

-- Drop existing table (this will also drop all policies)
DROP TABLE IF EXISTS refresh_tokens;

-- Create refresh tokens table
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP WITH TIME ZONE
);

-- Create index on user_id for faster lookups
CREATE INDEX refresh_tokens_user_id_idx ON refresh_tokens(user_id);

-- Create index on token for faster lookups
CREATE INDEX refresh_tokens_token_idx ON refresh_tokens(token);

-- Create RLS policies for refresh_tokens table
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own refresh tokens
CREATE POLICY refresh_tokens_select_policy ON refresh_tokens
    FOR SELECT
    USING (user_id = (SELECT auth.uid()));

-- Policy: Users can only insert their own refresh tokens
CREATE POLICY refresh_tokens_insert_policy ON refresh_tokens
    FOR INSERT
    WITH CHECK (user_id = (SELECT auth.uid()));

-- Policy: Users can only update their own refresh tokens
CREATE POLICY refresh_tokens_update_policy ON refresh_tokens
    FOR UPDATE
    USING (user_id = (SELECT auth.uid()));

-- Policy: Users can only delete their own refresh tokens
CREATE POLICY refresh_tokens_delete_policy ON refresh_tokens
    FOR DELETE
    USING (user_id = (SELECT auth.uid()));

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_refresh_tokens_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- Create trigger to automatically update updated_at timestamp
CREATE TRIGGER refresh_tokens_updated_at
BEFORE UPDATE ON refresh_tokens
FOR EACH ROW
EXECUTE FUNCTION update_refresh_tokens_updated_at();

-- Create function to clean up expired tokens
CREATE OR REPLACE FUNCTION cleanup_expired_refresh_tokens()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM refresh_tokens
    WHERE expires_at < NOW() OR is_revoked = TRUE;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- Create trigger to clean up expired tokens
CREATE TRIGGER cleanup_expired_refresh_tokens
AFTER INSERT ON refresh_tokens
EXECUTE FUNCTION cleanup_expired_refresh_tokens();
