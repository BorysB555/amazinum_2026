import pandas as pd
import logging

def clean_customers(df):
    initial_count = len(df)
    
    #Відсутні ID та Дублікати
    df = df.dropna(subset=['customer_id'])
    df = df.drop_duplicates(subset=['customer_id'])
    
    # Валідація Email та видалення порожніх
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    df = df[df['email'].fillna('').str.match(email_regex)]
    
    # Мітки часу
    df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
    df = df.dropna(subset=['created_at'])
    
    logging.info(f"Customers: видалено {initial_count - len(df)} некоректних рядків.")
    return df

def clean_products(df):
    initial_count = len(df)
    
    # Дублікати PK
    df = df.drop_duplicates(subset=['product_id'])
    
    # Ціни > 0
    df = df[df['price'] > 0]
    
    logging.info(f"Products: видалено {initial_count - len(df)} некоректних рядків.")
    return df

def clean_orders(df, valid_customer_ids):
    initial_count = len(df)
    
    # ID та Дублікати
    df = df.dropna(subset=['order_id'])
    df = df.drop_duplicates(subset=['order_id'])
    
    # Регістр статусів та невідомі статуси -> 'other'
    df['order_status'] = df['order_status'].str.lower()
    allowed_statuses = ['completed', 'pending', 'cancelled', 'returned']
    df.loc[~df['order_status'].isin(allowed_statuses), 'order_status'] = 'other'
    
    # Дати
    df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
    df = df.dropna(subset=['created_at'])
    
    # Посилання на клієнтів
    df = df[df['customer_id'].isin(valid_customer_ids)]
    
    logging.info(f"Orders: видалено {initial_count - len(df)} рядків через помилки ID, статусів або зв'язків.")
    return df

def clean_order_items(df, valid_order_ids, valid_product_ids):
    initial_count = len(df)
    
    # Дублікати та кількість > 0
    df = df.drop_duplicates(subset=['order_item_id'])
    df = df[df['quantity'] > 0]
    
    # Посилання на замовлення та товари (Referential Integrity)
    df = df[df['order_id'].isin(valid_order_ids)]
    df = df[df['product_id'].isin(valid_product_ids)]
    
    logging.info(f"Order Items: видалено {initial_count - len(df)} рядків через некоректну кількість або відсутні посилання.")
    return df