#!/bin/bash
# Script to create a test analytics.db for development/testing
# Usage: ./scripts/create-test-analytics-db.sh /path/to/your/project

set -e

PROJECT_PATH="${1:-$(pwd)}"
DB_DIR="$PROJECT_PATH/.auto-claude"
DB_PATH="$DB_DIR/analytics.db"

echo "Creating test analytics database..."
echo "Project path: $PROJECT_PATH"
echo "Database path: $DB_PATH"

# Create directory if needed
mkdir -p "$DB_DIR"

# Remove existing test database
if [ -f "$DB_PATH" ]; then
    echo "Removing existing database..."
    rm "$DB_PATH"
fi

# Create database with schema and test data
sqlite3 "$DB_PATH" << 'EOF'
-- Create conversations table (matches backend schema)
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_id TEXT NOT NULL,
    session_number INTEGER NOT NULL,
    phase TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    total_cost_usd REAL DEFAULT 0,
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    model TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Insert realistic test data spanning 7 days
-- Spec 001: Feature implementation
INSERT INTO conversations (spec_id, session_number, phase, started_at, ended_at, total_cost_usd, total_input_tokens, total_output_tokens, model) VALUES
('001-auth-feature', 1, 'planner', datetime('now', '-6 days', '+9 hours'), datetime('now', '-6 days', '+9 hours', '+8 minutes'), 0.12, 4500, 1800, 'claude-sonnet-4'),
('001-auth-feature', 2, 'coder', datetime('now', '-6 days', '+10 hours'), datetime('now', '-6 days', '+10 hours', '+45 minutes'), 0.89, 28000, 12000, 'claude-sonnet-4'),
('001-auth-feature', 3, 'coder', datetime('now', '-6 days', '+11 hours'), datetime('now', '-6 days', '+11 hours', '+30 minutes'), 0.56, 18000, 7500, 'claude-sonnet-4'),
('001-auth-feature', 4, 'qa_reviewer', datetime('now', '-6 days', '+12 hours'), datetime('now', '-6 days', '+12 hours', '+15 minutes'), 0.23, 8000, 3200, 'claude-sonnet-4'),
('001-auth-feature', 5, 'qa_fixer', datetime('now', '-6 days', '+13 hours'), datetime('now', '-6 days', '+13 hours', '+20 minutes'), 0.34, 11000, 4800, 'claude-sonnet-4');

-- Spec 002: Bug fix
INSERT INTO conversations (spec_id, session_number, phase, started_at, ended_at, total_cost_usd, total_input_tokens, total_output_tokens, model) VALUES
('002-login-bugfix', 1, 'planner', datetime('now', '-5 days', '+14 hours'), datetime('now', '-5 days', '+14 hours', '+5 minutes'), 0.08, 3000, 1200, 'claude-sonnet-4'),
('002-login-bugfix', 2, 'coder', datetime('now', '-5 days', '+14 hours', '+10 minutes'), datetime('now', '-5 days', '+14 hours', '+25 minutes'), 0.28, 9000, 4000, 'claude-sonnet-4'),
('002-login-bugfix', 3, 'qa_reviewer', datetime('now', '-5 days', '+15 hours'), datetime('now', '-5 days', '+15 hours', '+10 minutes'), 0.15, 5500, 2200, 'claude-sonnet-4');

-- Spec 003: UI enhancement
INSERT INTO conversations (spec_id, session_number, phase, started_at, ended_at, total_cost_usd, total_input_tokens, total_output_tokens, model) VALUES
('003-dashboard-ui', 1, 'planner', datetime('now', '-4 days', '+10 hours'), datetime('now', '-4 days', '+10 hours', '+12 minutes'), 0.18, 6500, 2600, 'claude-sonnet-4'),
('003-dashboard-ui', 2, 'coder', datetime('now', '-4 days', '+11 hours'), datetime('now', '-4 days', '+12 hours', '+30 minutes'), 1.45, 48000, 19000, 'claude-sonnet-4'),
('003-dashboard-ui', 3, 'coder', datetime('now', '-4 days', '+13 hours'), datetime('now', '-4 days', '+13 hours', '+45 minutes'), 0.72, 24000, 9500, 'claude-sonnet-4'),
('003-dashboard-ui', 4, 'qa_reviewer', datetime('now', '-4 days', '+14 hours'), datetime('now', '-4 days', '+14 hours', '+20 minutes'), 0.31, 10500, 4200, 'claude-sonnet-4'),
('003-dashboard-ui', 5, 'qa_fixer', datetime('now', '-4 days', '+15 hours'), datetime('now', '-4 days', '+15 hours', '+15 minutes'), 0.22, 7200, 3000, 'claude-sonnet-4'),
('003-dashboard-ui', 6, 'qa_reviewer', datetime('now', '-4 days', '+16 hours'), datetime('now', '-4 days', '+16 hours', '+8 minutes'), 0.12, 4000, 1600, 'claude-sonnet-4');

-- Spec 004: API integration
INSERT INTO conversations (spec_id, session_number, phase, started_at, ended_at, total_cost_usd, total_input_tokens, total_output_tokens, model) VALUES
('004-api-integration', 1, 'planner', datetime('now', '-3 days', '+9 hours'), datetime('now', '-3 days', '+9 hours', '+15 minutes'), 0.25, 8500, 3400, 'claude-sonnet-4'),
('004-api-integration', 2, 'coder', datetime('now', '-3 days', '+10 hours'), datetime('now', '-3 days', '+11 hours'), 1.12, 36000, 14500, 'claude-sonnet-4'),
('004-api-integration', 3, 'qa_reviewer', datetime('now', '-3 days', '+12 hours'), datetime('now', '-3 days', '+12 hours', '+18 minutes'), 0.28, 9500, 3800, 'claude-sonnet-4');

-- Spec 005: Performance optimization
INSERT INTO conversations (spec_id, session_number, phase, started_at, ended_at, total_cost_usd, total_input_tokens, total_output_tokens, model) VALUES
('005-perf-optimize', 1, 'planner', datetime('now', '-2 days', '+11 hours'), datetime('now', '-2 days', '+11 hours', '+10 minutes'), 0.15, 5200, 2100, 'claude-sonnet-4'),
('005-perf-optimize', 2, 'coder', datetime('now', '-2 days', '+12 hours'), datetime('now', '-2 days', '+13 hours', '+20 minutes'), 1.85, 62000, 24000, 'claude-opus-4'),
('005-perf-optimize', 3, 'coder', datetime('now', '-2 days', '+14 hours'), datetime('now', '-2 days', '+14 hours', '+50 minutes'), 0.95, 32000, 12800, 'claude-opus-4'),
('005-perf-optimize', 4, 'qa_reviewer', datetime('now', '-2 days', '+15 hours'), datetime('now', '-2 days', '+15 hours', '+25 minutes'), 0.42, 14000, 5600, 'claude-sonnet-4');

-- Spec 006: Documentation
INSERT INTO conversations (spec_id, session_number, phase, started_at, ended_at, total_cost_usd, total_input_tokens, total_output_tokens, model) VALUES
('006-docs-update', 1, 'planner', datetime('now', '-1 day', '+10 hours'), datetime('now', '-1 day', '+10 hours', '+6 minutes'), 0.09, 3200, 1300, 'claude-haiku-3'),
('006-docs-update', 2, 'coder', datetime('now', '-1 day', '+10 hours', '+10 minutes'), datetime('now', '-1 day', '+10 hours', '+35 minutes'), 0.18, 12000, 8000, 'claude-haiku-3'),
('006-docs-update', 3, 'qa_reviewer', datetime('now', '-1 day', '+11 hours'), datetime('now', '-1 day', '+11 hours', '+8 minutes'), 0.06, 2500, 1000, 'claude-haiku-3');

-- Spec 007: Current active session (no end time)
INSERT INTO conversations (spec_id, session_number, phase, started_at, ended_at, total_cost_usd, total_input_tokens, total_output_tokens, model) VALUES
('007-analytics-test', 1, 'planner', datetime('now', '-30 minutes'), datetime('now', '-20 minutes'), 0.14, 4800, 1900, 'claude-sonnet-4'),
('007-analytics-test', 2, 'coder', datetime('now', '-15 minutes'), NULL, 0.38, 12500, 5000, 'claude-sonnet-4');

-- Show summary
SELECT '=== Test Analytics Database Created ===' as status;
SELECT 'Total conversations: ' || COUNT(*) as summary FROM conversations;
SELECT 'Total cost: $' || printf('%.2f', SUM(total_cost_usd)) as cost FROM conversations;
SELECT 'Total input tokens: ' || printf('%,d', SUM(total_input_tokens)) as input_tokens FROM conversations;
SELECT 'Total output tokens: ' || printf('%,d', SUM(total_output_tokens)) as output_tokens FROM conversations;
SELECT 'Active sessions: ' || COUNT(*) as active FROM conversations WHERE ended_at IS NULL;
SELECT 'Unique specs: ' || COUNT(DISTINCT spec_id) as specs FROM conversations;
EOF

echo ""
echo "Test database created successfully!"
echo ""
echo "To use:"
echo "1. Start the Electron app: npm run dev"
echo "2. Add/select a project pointing to: $PROJECT_PATH"
echo "3. Click the Analytics icon (chart) in the sidebar or press 'Y'"
echo ""
