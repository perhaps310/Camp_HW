import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import logging
import os

def extract_and_clean_data(data_dir):
    try:
        customers = pd.read_csv(f'{data_dir}/customers.csv')
        products = pd.read_csv(f'{data_dir}/products.csv')
        orders = pd.read_csv(f'{data_dir}/orders.csv')
        order_items = pd.read_csv(f'{data_dir}/order_items.csv')

        customers.columns = customers.columns.str.strip()
        products.columns = products.columns.str.strip()
        orders.columns = orders.columns.str.strip()
        order_items.columns = order_items.columns.str.strip()
        
    except FileNotFoundError as e:
        logging.error(f"Файл не знайдено: {e}. Перевір папку {data_dir}.")
        raise

    customers.dropna(subset=['customer_id'], inplace=True)
    customers.drop_duplicates(subset=['customer_id'], keep='last', inplace=True)
    email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    invalid_emails = ~customers['email'].astype(str).str.match(email_pattern)
    customers.loc[invalid_emails, 'email'] = 'unknown_' + customers['customer_id'].astype(str) + '@placeholder.com'

    products.dropna(subset=['product_id'], inplace=True)
    products.drop_duplicates(subset=['product_id'], keep='last', inplace=True)
    
    products['price'] = pd.to_numeric(products['price'], errors='coerce')
    median_price = products[products['price'] > 0]['price'].median()
    products['price'] = products['price'].apply(lambda x: median_price if pd.isna(x) or x <= 0 else x)

    orders.rename(columns={'created_at': 'order_date', 'order_status': 'status'}, inplace=True)

    orders.dropna(subset=['order_id'], inplace=True)
    orders.drop_duplicates(subset=['order_id'], keep='last', inplace=True)

    orders['order_date'] = pd.to_datetime(orders['order_date'], errors='coerce').fillna(pd.Timestamp('1970-01-01'))

    orders['status'] = orders['status'].astype(str).str.lower().str.strip()
    valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    orders['status'] = orders['status'].apply(lambda x: x if x in valid_statuses else 'unknown')

    orders = orders[orders['customer_id'].isin(customers['customer_id'])]

    order_items.dropna(subset=['order_id', 'product_id'], inplace=True)

    order_items['quantity'] = pd.to_numeric(order_items['quantity'], errors='coerce').fillna(1)
    order_items['quantity'] = order_items['quantity'].abs().replace(0, 1)
    
    order_items = order_items[order_items['order_id'].isin(orders['order_id'])]
    order_items = order_items[order_items['product_id'].isin(products['product_id'])]

    return customers, products, orders, order_items

def load_and_transform(customers, products, orders, order_items):
    db_user = os.environ.get('POSTGRES_USER', 'user')
    db_pass = os.environ.get('POSTGRES_PASSWORD', 'password')
    db_host = os.environ.get('POSTGRES_HOST', 'localhost')
    db_port = os.environ.get('POSTGRES_PORT', '5432')
    db_name = os.environ.get('POSTGRES_DB', 'ecommerce_db')

    db_url = f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'
    engine = create_engine(db_url)

    customers.to_sql('stg_customers', engine, if_exists='replace', index=False)
    products.to_sql('stg_products', engine, if_exists='replace', index=False)
    orders.to_sql('stg_orders', engine, if_exists='replace', index=False)
    order_items.to_sql('stg_order_items', engine, if_exists='replace', index=False)

    with engine.begin() as conn:
        conn.execute(text("""
            DROP TABLE IF EXISTS analytics_customer_ltv;
            CREATE TABLE analytics_customer_ltv AS
            SELECT 
                c.customer_id,
                COUNT(DISTINCT o.order_id) AS total_orders,
                SUM(oi.quantity * p.price) AS total_spent,
                MIN(o.order_date) AS first_order_date,
                MAX(o.order_date) AS last_order_date
            FROM stg_customers c
            LEFT JOIN stg_orders o ON c.customer_id = o.customer_id
            LEFT JOIN stg_order_items oi ON o.order_id = oi.order_id
            LEFT JOIN stg_products p ON oi.product_id = p.product_id
            GROUP BY c.customer_id;
        """))

        conn.execute(text("""
            DROP TABLE IF EXISTS analytics_monthly_sales;
            CREATE TABLE analytics_monthly_sales AS
            SELECT 
                DATE_TRUNC('month', o.order_date) AS order_month,
                p.product_id,
                SUM(oi.quantity) AS total_quantity_sold,
                SUM(oi.quantity * p.price) AS total_revenue
            FROM stg_orders o
            JOIN stg_order_items oi ON o.order_id = oi.order_id
            JOIN stg_products p ON oi.product_id = p.product_id
            GROUP BY DATE_TRUNC('month', o.order_date), p.product_id;
        """))

if __name__ == "__main__":
    DATA_DIRECTORY = r'C:/Users/orban/Downloads/hometask_lecture_13/hometask_lecture_13/data/raw'
    
    df_customers, df_products, df_orders, df_items = extract_and_clean_data(DATA_DIRECTORY)
    load_and_transform(df_customers, df_products, df_orders, df_items)