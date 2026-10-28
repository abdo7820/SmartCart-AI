CREATE TABLE accounts (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'admin')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at BIGINT NOT NULL,
    last_login_at BIGINT
);

CREATE TABLE customer_profiles (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL UNIQUE REFERENCES accounts(id),
    origin TEXT NOT NULL CHECK (origin IN ('new', 'linked_historical')),
    historical_visitor_id BIGINT UNIQUE,
    country TEXT,
    created_at BIGINT NOT NULL
);

CREATE TABLE auth_sessions (
    token_hash TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    csrf_token TEXT NOT NULL,
    created_at BIGINT NOT NULL,
    expires_at BIGINT NOT NULL
);
CREATE INDEX idx_auth_sessions_account ON auth_sessions(account_id);

CREATE TABLE account_preferences (
    account_id TEXT PRIMARY KEY REFERENCES accounts(id),
    departments TEXT NOT NULL,
    updated_at BIGINT NOT NULL
);

CREATE TABLE interaction_events (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    ts BIGINT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('view', 'addtocart')),
    item_id BIGINT NOT NULL,
    session_key TEXT NOT NULL
);
CREATE INDEX idx_interaction_account_ts ON interaction_events(account_id, ts);

CREATE TABLE chat_conversations (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    title TEXT NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL
);
CREATE INDEX idx_chat_conv_account ON chat_conversations(account_id, updated_at);

CREATE TABLE chat_messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    product_ids TEXT NOT NULL DEFAULT '[]',
    meta TEXT NOT NULL DEFAULT '{}',
    created_at BIGINT NOT NULL
);
CREATE INDEX idx_chat_msg_conv ON chat_messages(conversation_id, created_at);

CREATE TABLE recommendation_requests (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    ts BIGINT NOT NULL,
    source TEXT NOT NULL,
    n_items INTEGER NOT NULL
);
CREATE INDEX idx_reco_req_ts ON recommendation_requests(ts);

CREATE TABLE audit_events (
    id TEXT PRIMARY KEY,
    ts BIGINT NOT NULL,
    actor_account_id TEXT,
    action TEXT NOT NULL,
    target TEXT,
    details TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_audit_ts ON audit_events(ts)
