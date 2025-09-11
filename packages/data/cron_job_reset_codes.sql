WITH config AS (reset_code_expiration_minutes AS expiration_time
FROM configurations)

DELETE FROM password_resets
USING config
WHERE created_at + (config.expiration_time || ' minute')::interval > NOW();