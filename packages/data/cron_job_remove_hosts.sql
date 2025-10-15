SELECT cron.schedule(
  '51 5 * * 4', -- every Thursday at 5:51am
  $$UPDATE users SET user_role = 'user'
    WHERE user_role = 'host';
    $$);

  -- TODO: UPDATE users SET user_role = 'host' WHERE user_role = 'user' AND 