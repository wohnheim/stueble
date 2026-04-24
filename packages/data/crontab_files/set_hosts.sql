-- Run at: 10 6 * * 4 (every Thursday at 6:10 AM)
WITH remove_old_hosts AS (
    UPDATE users
    SET user_role = 'user'
    WHERE user_role = 'host'
), 
applics (date_of_time, application_id, application_group) AS (
    SELECT a.date_of, a.application_id, a.application_group
    FROM stueble.dates d
    JOIN stueble.applications a ON d.application_id = a.id
    WHERE date_of_time >= CURRENT_DATE OR (CURRENT_TIME < '06:00:00' AND date_of_time = CURRENT_DATE - INTERVAL '1 day')
    ORDER BY date_of_time ASC
    LIMIT 1
)
UPDATE users
SET user_role = 'host'
WHERE id IN (
    SELECT user_id
    FROM stueble.applicants
    WHERE application_group = (
        SELECT application_group
        FROM applics
        ORDER BY date_of_time ASC
        LIMIT 1)
    );