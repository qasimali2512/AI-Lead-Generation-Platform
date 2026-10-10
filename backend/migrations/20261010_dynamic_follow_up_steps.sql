-- Dynamic follow-up drafts are generated only when a step becomes due.
-- Apply this migration to the existing PostgreSQL/Supabase database before
-- deploying the corresponding application code.
ALTER TABLE follow_up_steps
    ALTER COLUMN draft_id DROP NOT NULL;
