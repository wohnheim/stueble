SELECT cron.schedule(
               '52 4 * * *',
               $$DELETE * FROM sessions WHERE expiration_date <= NOW();
                WITH config AS (reset_code_expiration_minutes AS expiration_time;
                FROM configurations)

                DELETE FROM verification_codes
                USING config
                WHERE created_at + (config.reset_code_expiration_minutes || ' minute')::interval > NOW();$$
);