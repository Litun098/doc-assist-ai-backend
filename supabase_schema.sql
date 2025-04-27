-- AnyDocAI Supabase Schema for Phase 2

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users Table
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  email TEXT UNIQUE NOT NULL,
  full_name TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_login TIMESTAMP WITH TIME ZONE,
  subscription_tier TEXT DEFAULT 'free'
);

-- Documents Table
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  file_name TEXT NOT NULL,
  file_type TEXT NOT NULL,
  file_size INTEGER NOT NULL,
  s3_key TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  processed_at TIMESTAMP WITH TIME ZONE,
  error_message TEXT,
  metadata JSONB DEFAULT '{}'::JSONB
);

-- Chat Sessions Table
CREATE TABLE IF NOT EXISTS chat_sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_message_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chat Messages Table
CREATE TABLE IF NOT EXISTS chat_messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::JSONB
);

-- Document Sessions Junction Table
CREATE TABLE IF NOT EXISTS session_documents (
  session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  PRIMARY KEY (session_id, document_id)
);

-- User Usage Tracking Table
CREATE TABLE IF NOT EXISTS user_usage (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  month DATE NOT NULL,
  tokens_used INTEGER DEFAULT 0,
  model TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (user_id, month, model)
);

-- Row Level Security Policies

-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_usage ENABLE ROW LEVEL SECURITY;

-- Users Policy
CREATE POLICY "Users can view their own data" ON users
  FOR SELECT USING (auth.uid() = id);

-- Documents Policies
CREATE POLICY "Users can view their own documents" ON documents
  FOR SELECT USING (auth.uid() = user_id);
  
CREATE POLICY "Users can insert their own documents" ON documents
  FOR INSERT WITH CHECK (auth.uid() = user_id);
  
CREATE POLICY "Users can update their own documents" ON documents
  FOR UPDATE USING (auth.uid() = user_id);
  
CREATE POLICY "Users can delete their own documents" ON documents
  FOR DELETE USING (auth.uid() = user_id);

-- Chat Sessions Policies
CREATE POLICY "Users can view their own chat sessions" ON chat_sessions
  FOR SELECT USING (auth.uid() = user_id);
  
CREATE POLICY "Users can insert their own chat sessions" ON chat_sessions
  FOR INSERT WITH CHECK (auth.uid() = user_id);
  
CREATE POLICY "Users can update their own chat sessions" ON chat_sessions
  FOR UPDATE USING (auth.uid() = user_id);
  
CREATE POLICY "Users can delete their own chat sessions" ON chat_sessions
  FOR DELETE USING (auth.uid() = user_id);

-- Chat Messages Policies
CREATE POLICY "Users can view messages in their sessions" ON chat_messages
  FOR SELECT USING (
    auth.uid() IN (
      SELECT user_id FROM chat_sessions WHERE id = chat_messages.session_id
    )
  );
  
CREATE POLICY "Users can insert messages in their sessions" ON chat_messages
  FOR INSERT WITH CHECK (
    auth.uid() IN (
      SELECT user_id FROM chat_sessions WHERE id = chat_messages.session_id
    )
  );

-- Session Documents Policies
CREATE POLICY "Users can view their session documents" ON session_documents
  FOR SELECT USING (
    auth.uid() IN (
      SELECT user_id FROM chat_sessions WHERE id = session_documents.session_id
    )
  );
  
CREATE POLICY "Users can insert their session documents" ON session_documents
  FOR INSERT WITH CHECK (
    auth.uid() IN (
      SELECT user_id FROM chat_sessions WHERE id = session_documents.session_id
    ) AND
    auth.uid() IN (
      SELECT user_id FROM documents WHERE id = session_documents.document_id
    )
  );
  
CREATE POLICY "Users can delete their session documents" ON session_documents
  FOR DELETE USING (
    auth.uid() IN (
      SELECT user_id FROM chat_sessions WHERE id = session_documents.session_id
    )
  );

-- User Usage Policies
CREATE POLICY "Users can view their own usage" ON user_usage
  FOR SELECT USING (auth.uid() = user_id);
