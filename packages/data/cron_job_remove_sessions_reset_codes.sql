SELECT cron.schedule(
               '52 4 * * *',
               $$DELETE * FROM sessions WHERE expiration_date <= NOW();
                $$
);