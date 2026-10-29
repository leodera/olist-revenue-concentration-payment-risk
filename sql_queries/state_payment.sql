WITH state_base AS (
    SELECT 
        c.customer_state,
        ROUND(SUM(oi.price), 2) AS sta_revenue,
        COUNT(DISTINCT o.order_id) AS total_orders,
        MAX(CASE WHEN op.payment_type = 'credit_card' THEN 1 ELSE 0 END) AS used_credit_card,
        MAX(CASE WHEN op.payment_type = 'boleto' THEN 1 ELSE 0 END) AS used_boleto,
        MAX(CASE WHEN op.payment_type = 'voucher' THEN 1 ELSE 0 END) AS used_voucher,
        MAX(CASE WHEN op.payment_type = 'credit_card' THEN op.payment_installments ELSE NULL END) AS cc_installments
    FROM orders o
    JOIN customers c 
        ON o.customer_id = c.customer_id
    JOIN order_items oi 
        ON o.order_id = oi.order_id
    JOIN order_payments op 
        ON o.order_id = op.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_state, o.order_id
),
state_aggregated AS (
    SELECT 
        customer_state,
        SUM(sta_revenue) AS sta_revenue,
        COUNT(DISTINCT total_orders) AS total_orders,
        ROUND(100.0 * SUM(used_credit_card) / COUNT(DISTINCT total_orders), 1) AS pct_credit_card,
        ROUND(100.0 * SUM(used_boleto) / COUNT(DISTINCT total_orders), 1) AS pct_boleto,
        ROUND(100.0 * SUM(used_voucher) / COUNT(DISTINCT total_orders), 1) AS pct_voucher,
        ROUND(AVG(cc_installments), 1) AS avg_cc_installments,
        ROUND(100.0 * COUNT(CASE WHEN cc_installments >= 6 THEN 1 END) / COUNT(CASE WHEN cc_installments IS NOT NULL THEN 1 END), 1) AS pct_cc_6plus_installments
    FROM state_base
    GROUP BY customer_state
),
state_shares AS (
    SELECT 
        customer_state,
        sta_revenue,
        ROUND(100.0 * sta_revenue / SUM(sta_revenue) OVER (), 2) AS pct_of_total_revenue,
        ROUND(100.0 * SUM(sta_revenue) OVER (
            ORDER BY sta_revenue DESC 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) / SUM(sta_revenue) OVER (), 2) AS cum_pct_revenue,
        total_orders,
        pct_credit_card,
        pct_boleto,
        pct_voucher,
        avg_cc_installments,
        pct_cc_6plus_installments
    FROM state_aggregated
)
SELECT *
FROM state_shares
ORDER BY sta_revenue DESC
LIMIT 7;