-- Auto-Campaign Automation fields on auto_discovery_settings.
-- Apply this migration before deploying the corresponding application code.

ALTER TABLE auto_discovery_settings
    ADD COLUMN IF NOT EXISTS auto_campaign_enabled            BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS auto_campaign_paused             BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS auto_campaign_opportunity_threshold FLOAT    NOT NULL DEFAULT 30.0,
    ADD COLUMN IF NOT EXISTS auto_campaign_daily_limit        INTEGER      NOT NULL DEFAULT 50,
    ADD COLUMN IF NOT EXISTS auto_campaign_email_account_ids  JSONB        NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS auto_campaign_start_time         VARCHAR(5)   NOT NULL DEFAULT '09:00',
    ADD COLUMN IF NOT EXISTS auto_campaign_end_time           VARCHAR(5)   NOT NULL DEFAULT '17:00',
    ADD COLUMN IF NOT EXISTS auto_campaign_last_created_at    TIMESTAMPTZ  NULL,
    ADD COLUMN IF NOT EXISTS auto_campaigns_created           INTEGER      NOT NULL DEFAULT 0;
