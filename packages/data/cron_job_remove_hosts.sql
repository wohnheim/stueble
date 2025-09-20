SELECT cron.schedule(
  '0 7 * * 4', -- every Thursday at 7am
  $$UPDATE users SET user_role = 'user'
    WHERE user_role = 'host';$$);
 