import sqlite3
from pathlib import Path


DATABASE_FILE = Path("amazon.db")


def get_connection():
    """
    Create and return a SQLite database connection.
    """

    connection = sqlite3.connect(
        DATABASE_FILE,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    """
    Create all required database tables.
    """

    connection = get_connection()
    cursor = connection.cursor()

    # USERS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # PRODUCTS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0
        )
    """)

    # ADDRESSES TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS addresses (
            address_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            house TEXT NOT NULL,
            street TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            pincode TEXT NOT NULL,

            FOREIGN KEY(user_id)
            REFERENCES users(user_id)
        )
    """)

    # ORDERS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            address_id TEXT,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(user_id)
            REFERENCES users(user_id),

            FOREIGN KEY(product_id)
            REFERENCES products(product_id),

            FOREIGN KEY(address_id)
            REFERENCES addresses(address_id)
        )
    """)

    # PAYMENTS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            transaction_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            order_id TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(user_id)
            REFERENCES users(user_id),

            FOREIGN KEY(order_id)
            REFERENCES orders(order_id)
        )
    """)

    connection.commit()
    connection.close()


def insert_user(user):
    """
    Insert a user into database.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (user_id, name, email, password)
        VALUES (?, ?, ?, ?)
    """, (
        user["user_id"],
        user["name"],
        user["email"],
        user["password"]
    ))

    connection.commit()
    connection.close()


def insert_product(product):
    """
    Insert a product into database.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO products
        (product_id, product_name, description, price, quantity)
        VALUES (?, ?, ?, ?, ?)
    """, (
        product["product_id"],
        product["product_name"],
        product["description"],
        product["price"],
        product["quantity"]
    ))

    connection.commit()
    connection.close()