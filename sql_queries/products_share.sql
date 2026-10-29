WITH category_base AS (
    SELECT 
        COALESCE(t.product_category_name_english, p.product_category_name, 'Uncategorized') AS product_name,
        ROUND(SUM(oi.price), 2) AS product_revenue,
        COUNT(DISTINCT oi.order_id) AS total_orders
    FROM order_items oi
    JOIN orders o 
        ON oi.order_id = o.order_id
    LEFT JOIN products p 
        ON oi.product_id = p.product_id
    LEFT JOIN product_category_name_translation t 
        ON p.product_category_name = t.product_category_name
    WHERE o.order_status = 'delivered'
    GROUP BY 1
),
category_shares AS (
    SELECT 
        product_name,
        product_revenue,
        total_orders,
        ROUND(100.0 * product_revenue / SUM(product_revenue) OVER (), 2) AS pct_of_total_revenue,
        ROUND(100.0 * SUM(product_revenue) OVER (
            ORDER BY product_revenue DESC 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) / SUM(product_revenue) OVER (), 2) AS cum_pct_of_total_revenue
    FROM category_base
)
SELECT 
    product_name,
    product_revenue,
    total_orders,
    pct_of_total_revenue,
    cum_pct_of_total_revenue,
    CASE 
        WHEN cum_pct_of_total_revenue <= 80.0 OR product_name = 'pet_shop' THEN 'A. Top Product (Core)'
        WHEN cum_pct_of_total_revenue <= 95.0 THEN 'B. Next 15% (Mid)'
        ELSE 'C. Bottom % (Tail)'
    END AS revenue_tier
FROM category_shares
ORDER BY product_revenue DESC;