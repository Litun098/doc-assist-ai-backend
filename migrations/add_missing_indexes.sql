-- Add missing indexes for foreign keys to improve query performance

-- Add index for chat_messages.session_id
CREATE INDEX IF NOT EXISTS chat_messages_session_id_idx ON public.chat_messages(session_id);

-- Add index for chat_sessions.user_id
CREATE INDEX IF NOT EXISTS chat_sessions_user_id_idx ON public.chat_sessions(user_id);

-- Add index for documents.user_id
CREATE INDEX IF NOT EXISTS documents_user_id_idx ON public.documents(user_id);

-- Add index for session_documents.document_id
CREATE INDEX IF NOT EXISTS session_documents_document_id_idx ON public.session_documents(document_id);

-- Note: The unused indexes on refresh_tokens (refresh_tokens_user_id_idx and refresh_tokens_token_idx)
-- are kept for now as they will likely be used once the refresh token functionality is actively used.
-- These indexes support the RLS policies and token lookup operations that will be performed.
