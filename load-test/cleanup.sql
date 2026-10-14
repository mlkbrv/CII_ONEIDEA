BEGIN;

CREATE TEMP TABLE lt_users AS
SELECT user_id FROM users WHERE email LIKE '%@loadtest.invalid';

SELECT count(*) AS test_users FROM lt_users;

DELETE FROM votes WHERE voter_id IN (SELECT user_id FROM lt_users) OR voted_for_user_id IN (SELECT user_id FROM lt_users);
DELETE FROM competitions WHERE challenger_id IN (SELECT user_id FROM lt_users) OR opponent_id IN (SELECT user_id FROM lt_users);
DELETE FROM competition_requests WHERE challenger_id IN (SELECT user_id FROM lt_users) OR opponent_id IN (SELECT user_id FROM lt_users);
DELETE FROM coin_transactions WHERE user_id IN (SELECT user_id FROM lt_users);
UPDATE qr_codes SET status = 'ACTIVE', redeemed_by_user_id = NULL, redeemed_at = NULL
  WHERE redeemed_by_user_id IN (SELECT user_id FROM lt_users);
DELETE FROM users WHERE user_id IN (SELECT user_id FROM lt_users);

SELECT count(*) AS left_over FROM users WHERE email LIKE '%@loadtest.invalid';

COMMIT;
