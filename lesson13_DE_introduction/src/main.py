import pandas as pd
from sqlalchemy import create_engine, text
import cleaner
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(message)s')

DB_URL = os.getenv('DB_URL', 'postgresql://user:password@db:5432/homework')

def run_etl():
    logging.info("--- Завантаження даних ---")
    cust_raw = pd.read_csv('data/customers.csv')
    prod_raw = pd.read_csv('data/products.csv')
    ord_raw = pd.read_csv('data/orders.csv')
    items_raw = pd.read_csv('data/order_items.csv')

    logging.info("--- Очищення даних ---")
    df_customers = cleaner.clean_customers(cust_raw)
    df_products = cleaner.clean_products(prod_raw)
    df_orders = cleaner.clean_orders(ord_raw, df_customers['customer_id'])
    df_items = cleaner.clean_order_items(items_raw, df_orders['order_id'], df_products['product_id'])

    engine = create_engine(DB_URL)

    logging.info("--- Очищення старих об'єктів у БД ---")
    with engine.begin() as conn:
        # Видаляємо всі в'юхи (views), щоб вони не блокували заміну таблиць
        conn.execute(text("DROP VIEW IF EXISTS analytics_sales_by_category CASCADE;"))
        conn.execute(text("DROP VIEW IF EXISTS report_revenue_by_category CASCADE;"))
        conn.execute(text("DROP VIEW IF EXISTS report_monthly_stats CASCADE;"))
        conn.execute(text("DROP VIEW IF EXISTS report_top_customers CASCADE;"))

    logging.info("--- Завантаження в базу PostgreSQL ---")
    with engine.begin() as conn:
        df_customers.to_sql('customers', conn, if_exists='replace', index=False)
        df_products.to_sql('products', conn, if_exists='replace', index=False)
        df_orders.to_sql('orders', conn, if_exists='replace', index=False)
        df_items.to_sql('order_items', conn, if_exists='replace', index=False)

    logging.info("--- Створення аналітичних звітів ---")
    with engine.begin() as conn:
        # 1. Виручка по категоріях
        conn.execute(text("""
            CREATE VIEW report_revenue_by_category AS
            SELECT p.category, ROUND(SUM(i.quantity * p.price)::numeric, 2) as total_revenue
            FROM order_items i
            JOIN products p ON i.product_id = p.product_id
            GROUP BY 1 ORDER BY 2 DESC;
        """))

        # 2. Щомісячна динаміка
        conn.execute(text("""
            CREATE VIEW report_monthly_stats AS
            SELECT 
                TO_CHAR(o.created_at, 'YYYY-MM') as month,
                COUNT(DISTINCT o.order_id) as total_orders,
                ROUND(SUM(i.quantity * p.price)::numeric, 2) as monthly_revenue
            FROM orders o
            JOIN order_items i ON o.order_id = i.order_id
            JOIN products p ON i.product_id = p.product_id
            WHERE o.order_status = 'completed'
            GROUP BY 1 ORDER BY 1;
        """))

        # 3. ТОП-10 клієнтів
        conn.execute(text("""
            CREATE VIEW report_top_customers AS
            SELECT 
                c.customer_id, c.email, 
                COUNT(DISTINCT o.order_id) as orders_count,
                ROUND(SUM(i.quantity * p.price)::numeric, 2) as total_spent
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            JOIN order_items i ON o.order_id = i.order_id
            JOIN products p ON i.product_id = p.product_id
            GROUP BY 1, 2 ORDER BY 4 DESC LIMIT 10;
        """))

    # Експорт у CSV
    os.makedirs('output', exist_ok=True)
    pd.read_sql("SELECT * FROM report_revenue_by_category", engine).to_csv('output/revenue_by_category.csv', index=False)
    pd.read_sql("SELECT * FROM report_monthly_stats", engine).to_csv('output/monthly_stats.csv', index=False)
    pd.read_sql("SELECT * FROM report_top_customers", engine).to_csv('output/top_customers.csv', index=False)
    
    logging.info("Аналітичні звіти збережено в папку 'output/'")
    logging.info("ETL ПРОЦЕС ЗАВЕРШЕНО УСПІШНО!")

if __name__ == "__main__":
    run_etl()