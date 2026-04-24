-- Run at: 52 4 * * * (every day at 4:52 AM)
DELETE FROM sessions WHERE expiration_date <= NOW();