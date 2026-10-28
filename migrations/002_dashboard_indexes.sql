CREATE INDEX IF NOT EXISTS idx_interaction_events_ts ON interaction_events(ts);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_created_at ON chat_conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
