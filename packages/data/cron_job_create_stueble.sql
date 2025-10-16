CREATE OR REPLACE FUNCTION create_stueble_motto_if_not_exists()
RETURNS void AS $$
DECLARE next_wednesday DATE;
BEGIN
next_wednesday := CURRENT_DATE + ((2 + EXTRACT(DOW FROM CURRENT_DATE)) % 7) * INTERVAL '1 day' AS next_wednesday;
IF NOT EXISTS (SELECT id FROM stueble_motto WHERE date_of_time = next_wednesday) THEN
    INSERT INTO stueble_motto (motto, date_of_time)
    VALUES ('', next_wednesday);
END IF;
END;
$$ LANGUAGE plpgsql;

SELECT cron.schedule(
  '0 8 * * *',
  $$SELECT create_stueble_motto_if_not_exists();$$
);
