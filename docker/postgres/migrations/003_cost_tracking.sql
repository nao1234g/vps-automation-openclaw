-- ============================================================================
-- Cost Tracking Schema Migration
-- ============================================================================
--
-- このマイグレーションは、コスト追跡機能に必要なテーブルを作成します
--
-- 実行方法:
-- docker compose -f docker-compose.production.yml exec postgres \
--   psql -U openclaw -d openclaw -f /docker-entrypoint-initdb.d/003_cost_tracking.sql
--
-- ============================================================================

\c openclaw;

-- ----------------------------------------------------------------------------
-- API Usage Tracking Table
-- ----------------------------------------------------------------------------
-- API使用量を記録（リアルタイム）

CREATE TABLE IF NOT EXISTS api_usage (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- API呼び出し情報
    service VARCHAR(50) NOT NULL,  -- 'anthropic', 'openai', etc.
    model VARCHAR(100) NOT NULL,   -- 'claude-sonnet-4-5-20250929', etc.
    endpoint VARCHAR(255),          -- API endpoint

    -- トークン使用量
    tokens_input BIGINT NOT NULL DEFAULT 0,
    tokens_output BIGINT NOT NULL DEFAULT 0,
    tokens_total BIGINT GENERATED ALWAYS AS (tokens_input + tokens_output) STORED,

    -- コスト計算
    cost_input_usd DECIMAL(10, 4),
    cost_output_usd DECIMAL(10, 4),
    cost_total_usd DECIMAL(10, 4) GENERATED ALWAYS AS (cost_input_usd + cost_output_usd) STORED,

    -- メタデータ
    user_id VARCHAR(100),
    workflow_id VARCHAR(100),
    request_id VARCHAR(255),

    -- パフォーマンス情報
    latency_ms INTEGER,
    status_code INTEGER,
    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- インデックス用制約
    CONSTRAINT api_usage_date_check CHECK (date IS NOT NULL),
    CONSTRAINT api_usage_tokens_check CHECK (tokens_input >= 0 AND tokens_output >= 0)
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_api_usage_date ON api_usage(date DESC);
CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_usage(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_api_usage_service ON api_usage(service);
CREATE INDEX IF NOT EXISTS idx_api_usage_model ON api_usage(model);
CREATE INDEX IF NOT EXISTS idx_api_usage_user ON api_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_workflow ON api_usage(workflow_id);

-- パーティショニング用（オプション：大量データの場合）
-- CREATE INDEX IF NOT EXISTS idx_api_usage_date_timestamp ON api_usage(date, timestamp DESC);

-- ----------------------------------------------------------------------------
-- Daily Costs Summary Table
-- ----------------------------------------------------------------------------
-- 日次コスト集計テーブル

CREATE TABLE IF NOT EXISTS daily_costs (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,

    -- API コスト
    api_calls INTEGER DEFAULT 0,
    input_tokens BIGINT DEFAULT 0,
    output_tokens BIGINT DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    api_cost_usd DECIMAL(10, 4) DEFAULT 0,

    -- インフラコスト
    vps_cost_jpy INTEGER DEFAULT 0,
    storage_cost_jpy INTEGER DEFAULT 0,
    network_cost_jpy INTEGER DEFAULT 0,

    -- 合計コスト
    total_cost_usd DECIMAL(10, 4) DEFAULT 0,
    total_cost_jpy INTEGER DEFAULT 0,

    -- メタデータ
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT daily_costs_date_check CHECK (date IS NOT NULL)
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_daily_costs_date ON daily_costs(date DESC);

-- ----------------------------------------------------------------------------
-- Monthly Budget Table
-- ----------------------------------------------------------------------------
-- 月次予算管理

CREATE TABLE IF NOT EXISTS monthly_budgets (
    id SERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,

    -- 予算設定
    budget_usd DECIMAL(10, 4) NOT NULL,
    budget_jpy INTEGER NOT NULL,

    -- 実績
    actual_cost_usd DECIMAL(10, 4) DEFAULT 0,
    actual_cost_jpy INTEGER DEFAULT 0,

    -- 予測
    forecast_cost_usd DECIMAL(10, 4),
    forecast_cost_jpy INTEGER,

    -- ステータス
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'exceeded', 'closed'
    alert_sent BOOLEAN DEFAULT FALSE,

    -- タイムスタンプ
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT monthly_budgets_unique_month UNIQUE (year, month),
    CONSTRAINT monthly_budgets_month_check CHECK (month >= 1 AND month <= 12)
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_monthly_budgets_year_month ON monthly_budgets(year DESC, month DESC);

-- ----------------------------------------------------------------------------
-- Resource Usage Table
-- ----------------------------------------------------------------------------
-- リソース使用量の追跡

CREATE TABLE IF NOT EXISTS resource_usage (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- CPU
    cpu_percent DECIMAL(5, 2),
    cpu_cores INTEGER,

    -- メモリ
    memory_used_bytes BIGINT,
    memory_total_bytes BIGINT,
    memory_percent DECIMAL(5, 2),

    -- ディスク
    disk_used_bytes BIGINT,
    disk_total_bytes BIGINT,
    disk_percent DECIMAL(5, 2),

    -- ネットワーク
    network_rx_bytes BIGINT,
    network_tx_bytes BIGINT,

    -- コンテナ別
    container_name VARCHAR(100),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_resource_usage_timestamp ON resource_usage(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_resource_usage_container ON resource_usage(container_name);

-- パーティショニング用（大量データ対応）
CREATE INDEX IF NOT EXISTS idx_resource_usage_timestamp_container ON resource_usage(timestamp DESC, container_name);

-- ----------------------------------------------------------------------------
-- Cost Alerts Table
-- ----------------------------------------------------------------------------
-- コストアラート履歴

CREATE TABLE IF NOT EXISTS cost_alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL,  -- 'budget_warning', 'budget_exceeded', 'forecast_exceeded'
    severity VARCHAR(20) NOT NULL,     -- 'info', 'warning', 'critical'

    -- アラート内容
    message TEXT NOT NULL,
    current_cost_usd DECIMAL(10, 4),
    current_cost_jpy INTEGER,
    budget_usd DECIMAL(10, 4),
    budget_jpy INTEGER,

    -- 通知状況
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_channels TEXT[],  -- ['slack', 'email', 'telegram']

    -- タイムスタンプ
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,

    -- メタデータ
    metadata JSONB
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_cost_alerts_triggered ON cost_alerts(triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_cost_alerts_type ON cost_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_cost_alerts_severity ON cost_alerts(severity);

-- ----------------------------------------------------------------------------
-- Views for Easy Querying
-- ----------------------------------------------------------------------------

-- 日次コスト集計ビュー
CREATE OR REPLACE VIEW v_daily_cost_summary AS
SELECT
    date,
    SUM(tokens_input) as total_input_tokens,
    SUM(tokens_output) as total_output_tokens,
    SUM(tokens_total) as total_tokens,
    COUNT(*) as api_calls,
    SUM(cost_total_usd) as total_api_cost_usd,
    ROUND(SUM(cost_total_usd) * 150, 0) as total_api_cost_jpy
FROM api_usage
GROUP BY date
ORDER BY date DESC;

-- 月次コスト集計ビュー
CREATE OR REPLACE VIEW v_monthly_cost_summary AS
SELECT
    DATE_TRUNC('month', date) as month,
    SUM(tokens_input) as total_input_tokens,
    SUM(tokens_output) as total_output_tokens,
    SUM(tokens_total) as total_tokens,
    COUNT(*) as api_calls,
    SUM(cost_total_usd) as total_api_cost_usd,
    ROUND(SUM(cost_total_usd) * 150, 0) as total_api_cost_jpy
FROM api_usage
GROUP BY DATE_TRUNC('month', date)
ORDER BY month DESC;

-- サービス別コスト集計ビュー
CREATE OR REPLACE VIEW v_cost_by_service AS
SELECT
    service,
    model,
    DATE_TRUNC('month', date) as month,
    SUM(tokens_input) as total_input_tokens,
    SUM(tokens_output) as total_output_tokens,
    COUNT(*) as api_calls,
    SUM(cost_total_usd) as total_cost_usd,
    ROUND(AVG(latency_ms), 2) as avg_latency_ms
FROM api_usage
GROUP BY service, model, DATE_TRUNC('month', date)
ORDER BY month DESC, total_cost_usd DESC;

-- ユーザー別コスト集計ビュー
CREATE OR REPLACE VIEW v_cost_by_user AS
SELECT
    user_id,
    DATE_TRUNC('month', date) as month,
    SUM(tokens_total) as total_tokens,
    COUNT(*) as api_calls,
    SUM(cost_total_usd) as total_cost_usd
FROM api_usage
WHERE user_id IS NOT NULL
GROUP BY user_id, DATE_TRUNC('month', date)
ORDER BY month DESC, total_cost_usd DESC;

-- ----------------------------------------------------------------------------
-- Functions
-- ----------------------------------------------------------------------------

-- 日次コスト集計を更新する関数
CREATE OR REPLACE FUNCTION update_daily_costs()
RETURNS void AS $$
BEGIN
    INSERT INTO daily_costs (
        date,
        api_calls,
        input_tokens,
        output_tokens,
        total_tokens,
        api_cost_usd,
        vps_cost_jpy,
        storage_cost_jpy,
        total_cost_usd,
        total_cost_jpy,
        updated_at
    )
    SELECT
        date,
        COUNT(*) as api_calls,
        SUM(tokens_input) as input_tokens,
        SUM(tokens_output) as output_tokens,
        SUM(tokens_total) as total_tokens,
        SUM(cost_total_usd) as api_cost_usd,
        ROUND(1200.0 / 30, 0)::INTEGER as vps_cost_jpy,  -- VPS日割り
        10 as storage_cost_jpy,                           -- ストレージ日割り
        SUM(cost_total_usd) as total_cost_usd,
        ROUND(SUM(cost_total_usd) * 150 + 1200.0 / 30 + 10, 0)::INTEGER as total_cost_jpy,
        NOW()
    FROM api_usage
    WHERE date = CURRENT_DATE
    GROUP BY date
    ON CONFLICT (date) DO UPDATE SET
        api_calls = EXCLUDED.api_calls,
        input_tokens = EXCLUDED.input_tokens,
        output_tokens = EXCLUDED.output_tokens,
        total_tokens = EXCLUDED.total_tokens,
        api_cost_usd = EXCLUDED.api_cost_usd,
        vps_cost_jpy = EXCLUDED.vps_cost_jpy,
        storage_cost_jpy = EXCLUDED.storage_cost_jpy,
        total_cost_usd = EXCLUDED.total_cost_usd,
        total_cost_jpy = EXCLUDED.total_cost_jpy,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- 古いデータを削除する関数（90日以上前）
CREATE OR REPLACE FUNCTION cleanup_old_api_usage()
RETURNS INTEGER AS $$
DECLARE
    deleted_rows INTEGER;
BEGIN
    DELETE FROM api_usage
    WHERE date < CURRENT_DATE - INTERVAL '90 days';

    GET DIAGNOSTICS deleted_rows = ROW_COUNT;

    RAISE NOTICE 'Deleted % old API usage records', deleted_rows;
    RETURN deleted_rows;
END;
$$ LANGUAGE plpgsql;

-- 古いリソース使用量データを削除（30日以上前）
CREATE OR REPLACE FUNCTION cleanup_old_resource_usage()
RETURNS INTEGER AS $$
DECLARE
    deleted_rows INTEGER;
BEGIN
    DELETE FROM resource_usage
    WHERE timestamp < NOW() - INTERVAL '30 days';

    GET DIAGNOSTICS deleted_rows = ROW_COUNT;

    RAISE NOTICE 'Deleted % old resource usage records', deleted_rows;
    RETURN deleted_rows;
END;
$$ LANGUAGE plpgsql;

-- 予算アラートをチェックする関数
CREATE OR REPLACE FUNCTION check_budget_alert()
RETURNS void AS $$
DECLARE
    current_month_cost DECIMAL(10, 4);
    budget DECIMAL(10, 4);
    budget_percent DECIMAL(5, 2);
BEGIN
    -- 今月の予算を取得
    SELECT budget_usd INTO budget
    FROM monthly_budgets
    WHERE year = EXTRACT(YEAR FROM CURRENT_DATE)
      AND month = EXTRACT(MONTH FROM CURRENT_DATE);

    -- 予算が設定されていない場合は終了
    IF budget IS NULL THEN
        RETURN;
    END IF;

    -- 今月のコストを計算
    SELECT COALESCE(SUM(cost_total_usd), 0) INTO current_month_cost
    FROM api_usage
    WHERE DATE_TRUNC('month', date) = DATE_TRUNC('month', CURRENT_DATE);

    -- 予算使用率を計算
    budget_percent := (current_month_cost / budget) * 100;

    -- 80%超過でwarning
    IF budget_percent > 80 AND budget_percent <= 100 THEN
        INSERT INTO cost_alerts (
            alert_type,
            severity,
            message,
            current_cost_usd,
            budget_usd
        ) VALUES (
            'budget_warning',
            'warning',
            FORMAT('Budget usage is at %.1f%%. Current: $%.2f / Budget: $%.2f',
                   budget_percent, current_month_cost, budget),
            current_month_cost,
            budget
        );
    END IF;

    -- 100%超過でcritical
    IF budget_percent > 100 THEN
        INSERT INTO cost_alerts (
            alert_type,
            severity,
            message,
            current_cost_usd,
            budget_usd
        ) VALUES (
            'budget_exceeded',
            'critical',
            FORMAT('Budget exceeded! Usage: %.1f%%. Current: $%.2f / Budget: $%.2f',
                   budget_percent, current_month_cost, budget),
            current_month_cost,
            budget
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------------------------------
-- Triggers
-- ----------------------------------------------------------------------------

-- API使用量が追加されたら日次コストを自動更新
CREATE OR REPLACE FUNCTION trigger_update_daily_costs()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM update_daily_costs();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER api_usage_after_insert
    AFTER INSERT ON api_usage
    FOR EACH STATEMENT
    EXECUTE FUNCTION trigger_update_daily_costs();

-- ----------------------------------------------------------------------------
-- Initial Data
-- ----------------------------------------------------------------------------

-- 今月の予算を作成（存在しない場合）
INSERT INTO monthly_budgets (year, month, budget_usd, budget_jpy)
VALUES (
    EXTRACT(YEAR FROM CURRENT_DATE),
    EXTRACT(MONTH FROM CURRENT_DATE),
    35.00,  -- $35
    5000    -- ¥5000
)
ON CONFLICT (year, month) DO NOTHING;

-- サンプルデータ（開発・テスト用）
-- 本番環境では不要な場合はコメントアウト

-- INSERT INTO api_usage (date, service, model, tokens_input, tokens_output, cost_input_usd, cost_output_usd, user_id)
-- VALUES
--     (CURRENT_DATE, 'anthropic', 'claude-sonnet-4-5', 10000, 5000, 0.03, 0.075, 'test-user'),
--     (CURRENT_DATE - 1, 'anthropic', 'claude-sonnet-4-5', 15000, 7500, 0.045, 0.1125, 'test-user'),
--     (CURRENT_DATE - 2, 'anthropic', 'claude-haiku-4-5', 50000, 25000, 0.04, 0.10, 'test-user');

-- ----------------------------------------------------------------------------
-- Permissions
-- ----------------------------------------------------------------------------

-- N8Nユーザーにテーブルへのアクセス権を付与
GRANT SELECT, INSERT, UPDATE ON api_usage TO openclaw;
GRANT SELECT, INSERT, UPDATE ON daily_costs TO openclaw;
GRANT SELECT ON monthly_budgets TO openclaw;
GRANT SELECT, INSERT ON cost_alerts TO openclaw;
GRANT SELECT ON resource_usage TO openclaw;

-- ビューへのアクセス権
GRANT SELECT ON v_daily_cost_summary TO openclaw;
GRANT SELECT ON v_monthly_cost_summary TO openclaw;
GRANT SELECT ON v_cost_by_service TO openclaw;
GRANT SELECT ON v_cost_by_user TO openclaw;

-- シーケンスへのアクセス権
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO openclaw;

-- ----------------------------------------------------------------------------
-- Complete Message
-- ----------------------------------------------------------------------------

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Cost Tracking Schema Created!';
    RAISE NOTICE '========================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Tables Created:';
    RAISE NOTICE '  - api_usage';
    RAISE NOTICE '  - daily_costs';
    RAISE NOTICE '  - monthly_budgets';
    RAISE NOTICE '  - resource_usage';
    RAISE NOTICE '  - cost_alerts';
    RAISE NOTICE '';
    RAISE NOTICE 'Views Created:';
    RAISE NOTICE '  - v_daily_cost_summary';
    RAISE NOTICE '  - v_monthly_cost_summary';
    RAISE NOTICE '  - v_cost_by_service';
    RAISE NOTICE '  - v_cost_by_user';
    RAISE NOTICE '';
    RAISE NOTICE 'Functions Created:';
    RAISE NOTICE '  - update_daily_costs()';
    RAISE NOTICE '  - cleanup_old_api_usage()';
    RAISE NOTICE '  - cleanup_old_resource_usage()';
    RAISE NOTICE '  - check_budget_alert()';
    RAISE NOTICE '';
    RAISE NOTICE 'Usage:';
    RAISE NOTICE '  - scripts/cost_tracker.sh --daily';
    RAISE NOTICE '  - scripts/cost_tracker.sh --monthly';
    RAISE NOTICE '  - scripts/cost_tracker.sh --forecast';
    RAISE NOTICE '';
END $$;
