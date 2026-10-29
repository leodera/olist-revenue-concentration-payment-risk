WITH core_categories AS (
    SELECT 
        COALESCE(t.product_category_name_english, p.product_category_name, 'Uncategorized') AS product_name
    FROM order_items oi
    JOIN orders o 
        ON oi.order_id = o.order_id
    LEFT JOIN products p 
        ON oi.product_id = p.product_id
    LEFT JOIN product_category_name_translation t 
        ON p.product_category_name = t.product_category_name
    WHERE o.order_status = 'delivered'
    GROUP BY 1
    ORDER BY SUM(oi.price) DESC
    LIMIT 18
),
category_orders_payments AS (
    SELECT 
        COALESCE(t.product_category_name_english, p.product_category_name, 'Uncategorized') AS product_name,
        o.order_id,
        MAX(CASE WHEN op.payment_type = 'credit_card' THEN 1 ELSE 0 END) AS used_credit_card,
        MAX(CASE WHEN op.payment_type = 'boleto' THEN 1 ELSE 0 END) AS used_boleto,
        MAX(CASE WHEN op.payment_type = 'voucher' THEN 1 ELSE 0 END) AS used_voucher,
        MAX(CASE WHEN op.payment_type = 'credit_card' THEN op.payment_installments ELSE NULL END) AS cc_installments
    FROM order_items oi
    JOIN orders o 
        ON oi.order_id = o.order_id
    LEFT JOIN products p 
        ON oi.product_id = p.product_id
    LEFT JOIN product_category_name_translation t 
        ON p.product_category_name = t.product_category_name
    JOIN order_payments op 
        ON o.order_id = op.order_id
    WHERE o.order_status = 'delivered'
      AND COALESCE(t.product_category_name_english, p.product_category_name, 'Uncategorized') IN (SELECT product_name FROM core_categories)
    GROUP BY 1, 2
)
SELECT 
    product_name,
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(100.0 * SUM(used_credit_card) / COUNT(DISTINCT order_id), 1) AS pct_credit_card,
    ROUND(100.0 * SUM(used_boleto) / COUNT(DISTINCT order_id), 1) AS pct_boleto,
    ROUND(100.0 * SUM(used_voucher) / COUNT(DISTINCT order_id), 1) AS pct_voucher,
    ROUND(AVG(cc_installments), 1) AS avg_cc_installments,
    ROUND(100.0 * COUNT(CASE WHEN cc_installments >= 6 THEN 1 END) / COUNT(CASE WHEN cc_installments IS NOT NULL THEN 1 END), 1) AS pct_orders_with_6plus_installments
FROM category_orders_payments
GROUP BY product_name
ORDER BY total_orders DESC;