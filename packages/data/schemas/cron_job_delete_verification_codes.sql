SELECT cron.schedule(
    '* * * * *',
WITH config AS ($$SELECT verification_code_expiration_minutes AS expiration_time;
                FROM configurations)

                DELETE FROM verification_codes
                USING config
                WHERE created_at + (config.verification_code_expiration_minutes || ' minute')::interval > NOW();
                $$);
