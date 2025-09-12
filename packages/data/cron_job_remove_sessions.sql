DELETE * FROM sessions
WHERE expiration_date <= NOW();