BEGIN;

WITH t AS (
    SELECT type_id FROM coin_transaction_types WHERE type_name = 'admin_adjustment'
),
upd AS (
    UPDATE users u
    SET coin_balance = u.coin_balance + 1000
    FROM t
    WHERE NOT EXISTS (
        SELECT 1 FROM coin_transactions c
        WHERE c.user_id = u.user_id AND c.type_id = t.type_id AND c.amount = 1000
    )
    RETURNING u.user_id, u.coin_balance
)
INSERT INTO coin_transactions (user_id, type_id, amount, balance_after)
SELECT upd.user_id, t.type_id, 1000, upd.coin_balance FROM upd, t;

SELECT count(*) AS users_with_bonus FROM coin_transactions
WHERE amount = 1000 AND type_id = (SELECT type_id FROM coin_transaction_types WHERE type_name = 'admin_adjustment');

COMMIT;
