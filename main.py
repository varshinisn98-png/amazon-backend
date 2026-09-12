from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import uuid
import sqlite3

from filesops import read_json
from database import (
    get_connection,
    initialize_database,
    insert_user,
    insert_product
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Amazon Backend System",
    description="Mini Amazon Backend using FastAPI, SQLite and ChromaDB",
    version="1.0.0"
)


# ============================================================
# FILE PATHS
# ============================================================

USER_FILE = "user_details.json"
PRODUCT_FILE = "product_details.json"


# ============================================================
# CHROMADB
# ============================================================

try:

    import chromadb

    chroma_client = chromadb.PersistentClient(
        path="./chroma_db"
    )

    product_collection = chroma_client.get_or_create_collection(
        name="products"
    )

    CHROMA_AVAILABLE = True

except Exception as error:

    print("ChromaDB initialization failed:")
    print(error)

    chroma_client = None
    product_collection = None
    CHROMA_AVAILABLE = False


# ============================================================
# PYDANTIC MODELS
# ============================================================


class LoginRequest(BaseModel):
    email: str
    password: str


class ProductCreate(BaseModel):
    product_id: str
    product_name: str
    description: str
    price: float
    quantity: int


class InventoryUpdate(BaseModel):
    quantity: int


class OrderCreate(BaseModel):
    user_id: str
    product_id: str
    quantity: int
    address_id: Optional[str] = None


class AddressCreate(BaseModel):
    name: str
    house: str
    street: str
    city: str
    state: str
    pincode: str


class AddressUpdate(BaseModel):
    name: Optional[str] = None
    house: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None


class PaymentCreate(BaseModel):
    user_id: str
    order_id: str
    amount: float
    payment_method: str


class CheckoutRequest(BaseModel):
    user_id: str
    product_id: str
    quantity: int
    address_id: str
    payment_method: str


# ============================================================
# STARTUP
# ============================================================


@app.on_event("startup")
def startup():

    print("Starting Amazon Backend...")

    # Create database tables
    initialize_database()

    # Load users
    users = read_json(USER_FILE)

    for user in users:
        insert_user(user)

    # Load products
    products = read_json(PRODUCT_FILE)

    for product in products:
        insert_product(product)

    # Add products to ChromaDB
    if CHROMA_AVAILABLE:

        for product in products:

            try:

                product_collection.upsert(
                    ids=[product["product_id"]],

                    documents=[
                        product["product_name"]
                        + " "
                        + product["description"]
                    ],

                    metadatas=[
                        {
                            "product_id": product["product_id"],
                            "product_name": product["product_name"],
                            "price": product["price"]
                        }
                    ]
                )

            except Exception as error:

                print(
                    "ChromaDB product insert error:",
                    error
                )

    print("Amazon Backend started successfully.")


# ============================================================
# HOME
# ============================================================


@app.get("/")
def home():

    return {
        "message": "Amazon Backend API is running",
        "status": "success"
    }


# ============================================================
# AUTHENTICATION
# ============================================================


@app.post("/auth/login")
def login(request: LoginRequest):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT user_id, name, email
        FROM users
        WHERE email = ?
        AND password = ?
    """, (
        request.email,
        request.password
    ))

    user = cursor.fetchone()

    connection.close()

    if user is None:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    return {
        "message": "Login successful",
        "user_id": user["user_id"],
        "name": user["name"],
        "email": user["email"]
    }


# ============================================================
# GET ALL PRODUCTS
# ============================================================


@app.get("/products")
def get_products():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM products
    """)

    products = cursor.fetchall()

    connection.close()

    return {
        "count": len(products),
        "products": [dict(product) for product in products]
    }


# ============================================================
# SEARCH PRODUCTS
# ============================================================


@app.get("/products/search")
def search_products(keyword: str):

    # Try ChromaDB first
    if CHROMA_AVAILABLE:

        try:

            result = product_collection.get(
                where_document={
                    "$contains": keyword
                }
            )

            products = []

            ids = result.get("ids", [])
            documents = result.get("documents", [])
            metadatas = result.get("metadatas", [])

            for i in range(len(ids)):

                product = {
                    "product_id": ids[i]
                }

                if i < len(documents):
                    product["description"] = documents[i]

                if i < len(metadatas) and metadatas[i]:
                    product.update(metadatas[i])

                products.append(product)

            if products:

                return {
                    "source": "ChromaDB",
                    "keyword": keyword,
                    "count": len(products),
                    "products": products
                }

        except Exception as error:

            print(
                "ChromaDB search error:",
                error
            )

    # Fallback to SQLite search
    connection = get_connection()
    cursor = connection.cursor()

    search_value = f"%{keyword}%"

    cursor.execute("""
        SELECT *
        FROM products
        WHERE product_name LIKE ?
        OR description LIKE ?
    """, (
        search_value,
        search_value
    ))

    products = cursor.fetchall()

    connection.close()

    return {
        "source": "SQLite",
        "keyword": keyword,
        "count": len(products),
        "products": [
            dict(product)
            for product in products
        ]
    }


# ============================================================
# GET SINGLE PRODUCT
# ============================================================


@app.get("/products/{product_id}")
def get_product(product_id: str):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM products
        WHERE product_id = ?
    """, (product_id,))

    product = cursor.fetchone()

    connection.close()

    if product is None:

        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return dict(product)


# ============================================================
# ADD PRODUCT
# ============================================================


@app.post("/products")
def create_product(product: ProductCreate):

    if product.quantity < 0:

        raise HTTPException(
            status_code=400,
            detail="Quantity cannot be negative"
        )

    if product.price < 0:

        raise HTTPException(
            status_code=400,
            detail="Price cannot be negative"
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO products
            (
                product_id,
                product_name,
                description,
                price,
                quantity
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            product.product_id,
            product.product_name,
            product.description,
            product.price,
            product.quantity
        ))

        connection.commit()

    except sqlite3.IntegrityError:

        connection.close()

        raise HTTPException(
            status_code=400,
            detail="Product ID already exists"
        )

    connection.close()

    # Add to ChromaDB
    if CHROMA_AVAILABLE:

        try:

            product_collection.upsert(
                ids=[product.product_id],

                documents=[
                    product.product_name
                    + " "
                    + product.description
                ],

                metadatas=[
                    {
                        "product_id": product.product_id,
                        "product_name": product.product_name,
                        "price": product.price
                    }
                ]
            )

        except Exception as error:

            print(
                "ChromaDB insert error:",
                error
            )

    return {
        "message": "Product created successfully",
        "product": product.model_dump()
    }


# ============================================================
# CHECK PRODUCT AVAILABILITY
# ============================================================


@app.get("/products/{product_id}/availability")
def check_availability(product_id: str):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            product_id,
            product_name,
            quantity
        FROM products
        WHERE product_id = ?
    """, (product_id,))

    product = cursor.fetchone()

    connection.close()

    if product is None:

        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    if product["quantity"] > 0:

        return {
            "product_id": product["product_id"],
            "product_name": product["product_name"],
            "quantity": product["quantity"],
            "status": "Available"
        }

    return {
        "product_id": product["product_id"],
        "product_name": product["product_name"],
        "quantity": 0,
        "status": "Out of Stock"
    }


# ============================================================
# UPDATE INVENTORY
# ============================================================


@app.put("/products/{product_id}/inventory")
def update_inventory(
    product_id: str,
    request: InventoryUpdate
):

    if request.quantity < 0:

        raise HTTPException(
            status_code=400,
            detail="Quantity cannot be negative"
        )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE products
        SET quantity = ?
        WHERE product_id = ?
    """, (
        request.quantity,
        product_id
    ))

    if cursor.rowcount == 0:

        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    connection.commit()

    cursor.execute("""
        SELECT *
        FROM products
        WHERE product_id = ?
    """, (product_id,))

    product = cursor.fetchone()

    connection.close()

    return {
        "message": "Inventory updated successfully",
        "product": dict(product)
    }


# ============================================================
# CREATE ORDER
# ============================================================


@app.post("/orders")
def create_order(request: OrderCreate):

    if request.quantity <= 0:

        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than zero"
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # ----------------------------------------------------
        # Check user
        # ----------------------------------------------------

        cursor.execute("""
            SELECT *
            FROM users
            WHERE user_id = ?
        """, (request.user_id,))

        user = cursor.fetchone()

        if user is None:

            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # ----------------------------------------------------
        # Check product
        # ----------------------------------------------------

        cursor.execute("""
            SELECT *
            FROM products
            WHERE product_id = ?
        """, (request.product_id,))

        product = cursor.fetchone()

        if product is None:

            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        # ----------------------------------------------------
        # Check stock
        # ----------------------------------------------------

        if product["quantity"] < request.quantity:

            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Insufficient stock",
                    "available_quantity": product["quantity"]
                }
            )

        # ----------------------------------------------------
        # Check address if provided
        # ----------------------------------------------------

        if request.address_id:

            cursor.execute("""
                SELECT *
                FROM addresses
                WHERE address_id = ?
                AND user_id = ?
            """, (
                request.address_id,
                request.user_id
            ))

            address = cursor.fetchone()

            if address is None:

                raise HTTPException(
                    status_code=404,
                    detail="Address not found for this user"
                )

        # ----------------------------------------------------
        # Calculate amount
        # ----------------------------------------------------

        total_amount = (
            product["price"]
            * request.quantity
        )

        # ----------------------------------------------------
        # Generate Order ID
        # ----------------------------------------------------

        order_id = "O" + uuid.uuid4().hex[:8].upper()

        # ----------------------------------------------------
        # Reduce stock
        # ----------------------------------------------------

        cursor.execute("""
            UPDATE products
            SET quantity = quantity - ?
            WHERE product_id = ?
            AND quantity >= ?
        """, (
            request.quantity,
            request.product_id,
            request.quantity
        ))

        if cursor.rowcount == 0:

            raise HTTPException(
                status_code=400,
                detail="Unable to reserve stock"
            )

        # ----------------------------------------------------
        # Create order
        # ----------------------------------------------------

        cursor.execute("""
            INSERT INTO orders
            (
                order_id,
                user_id,
                product_id,
                quantity,
                total_amount,
                address_id,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id,
            request.user_id,
            request.product_id,
            request.quantity,
            total_amount,
            request.address_id,
            "CREATED"
        ))

        connection.commit()

    except HTTPException:
        connection.rollback()
        connection.close()
        raise

    except Exception as error:

        connection.rollback()
        connection.close()

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    connection.close()

    return {
        "message": "Order created successfully",
        "order_id": order_id,
        "user_id": request.user_id,
        "product_id": request.product_id,
        "quantity": request.quantity,
        "total_amount": total_amount,
        "status": "CREATED"
    }


# ============================================================
# GET ORDER
# ============================================================


@app.get("/orders/{order_id}")
def get_order(order_id: str):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            o.*,
            p.product_name,
            u.name AS user_name
        FROM orders o
        JOIN products p
            ON o.product_id = p.product_id
        JOIN users u
            ON o.user_id = u.user_id
        WHERE o.order_id = ?
    """, (order_id,))

    order = cursor.fetchone()

    connection.close()

    if order is None:

        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    return dict(order)


# ============================================================
# GET USER ORDERS
# ============================================================


@app.get("/users/{user_id}/orders")
def get_user_orders(user_id: str):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            o.*,
            p.product_name
        FROM orders o
        JOIN products p
            ON o.product_id = p.product_id
        WHERE o.user_id = ?
        ORDER BY o.created_at DESC
    """, (user_id,))

    orders = cursor.fetchall()

    connection.close()

    return {
        "user_id": user_id,
        "count": len(orders),
        "orders": [
            dict(order)
            for order in orders
        ]
    }


# ============================================================
# ADD ADDRESS
# ============================================================


@app.post("/users/{user_id}/address")
def add_address(
    user_id: str,
    address: AddressCreate
):

    connection = get_connection()
    cursor = connection.cursor()

    # Check user
    cursor.execute("""
        SELECT user_id
        FROM users
        WHERE user_id = ?
    """, (user_id,))

    user = cursor.fetchone()

    if user is None:

        connection.close()

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    address_id = "A" + uuid.uuid4().hex[:8].upper()

    cursor.execute("""
        INSERT INTO addresses
        (
            address_id,
            user_id,
            name,
            house,
            street,
            city,
            state,
            pincode
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        address_id,
        user_id,
        address.name,
        address.house,
        address.street,
        address.city,
        address.state,
        address.pincode
    ))

    connection.commit()
    connection.close()

    return {
        "message": "Address added successfully",
        "address_id": address_id,
        "user_id": user_id
    }


# ============================================================
# GET USER ADDRESS
# ============================================================


@app.get("/users/{user_id}/address")
def get_address(user_id: str):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM addresses
        WHERE user_id = ?
    """, (user_id,))

    addresses = cursor.fetchall()

    connection.close()

    return {
        "user_id": user_id,
        "count": len(addresses),
        "addresses": [
            dict(address)
            for address in addresses
        ]
    }


# ============================================================
# UPDATE ADDRESS
# ============================================================


@app.put("/users/{user_id}/address/{address_id}")
def update_address(
    user_id: str,
    address_id: str,
    address: AddressUpdate
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM addresses
        WHERE address_id = ?
        AND user_id = ?
    """, (
        address_id,
        user_id
    ))

    existing = cursor.fetchone()

    if existing is None:

        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Address not found"
        )

    # Keep old value if new value isn't supplied

    name = (
        address.name
        if address.name is not None
        else existing["name"]
    )

    house = (
        address.house
        if address.house is not None
        else existing["house"]
    )

    street = (
        address.street
        if address.street is not None
        else existing["street"]
    )

    city = (
        address.city
        if address.city is not None
        else existing["city"]
    )

    state = (
        address.state
        if address.state is not None
        else existing["state"]
    )

    pincode = (
        address.pincode
        if address.pincode is not None
        else existing["pincode"]
    )

    cursor.execute("""
        UPDATE addresses
        SET
            name = ?,
            house = ?,
            street = ?,
            city = ?,
            state = ?,
            pincode = ?
        WHERE address_id = ?
        AND user_id = ?
    """, (
        name,
        house,
        street,
        city,
        state,
        pincode,
        address_id,
        user_id
    ))

    connection.commit()

    cursor.execute("""
        SELECT *
        FROM addresses
        WHERE address_id = ?
    """, (address_id,))

    updated_address = cursor.fetchone()

    connection.close()

    return {
        "message": "Address updated successfully",
        "address": dict(updated_address)
    }


# ============================================================
# PAYMENT
# ============================================================


@app.post("/payments")
def make_payment(request: PaymentCreate):

    if request.amount <= 0:

        raise HTTPException(
            status_code=400,
            detail="Payment amount must be greater than zero"
        )

    connection = get_connection()
    cursor = connection.cursor()

    # --------------------------------------------------------
    # Check user
    # --------------------------------------------------------

    cursor.execute("""
        SELECT *
        FROM users
        WHERE user_id = ?
    """, (request.user_id,))

    user = cursor.fetchone()

    if user is None:

        connection.close()

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # --------------------------------------------------------
    # Check order
    # --------------------------------------------------------

    cursor.execute("""
        SELECT *
        FROM orders
        WHERE order_id = ?
        AND user_id = ?
    """, (
        request.order_id,
        request.user_id
    ))

    order = cursor.fetchone()

    if order is None:

        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    # --------------------------------------------------------
    # Check amount
    # --------------------------------------------------------

    if abs(request.amount - order["total_amount"]) > 0.01:

        connection.close()

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Payment amount does not match order amount",
                "order_amount": order["total_amount"]
            }
        )

    # --------------------------------------------------------
    # Generate transaction ID
    # --------------------------------------------------------

    transaction_id = (
        "T"
        + uuid.uuid4().hex[:8].upper()
    )

    # --------------------------------------------------------
    # Simulated payment
    # --------------------------------------------------------

    payment_status = "SUCCESS"

    cursor.execute("""
        INSERT INTO payments
        (
            transaction_id,
            user_id,
            order_id,
            amount,
            payment_method,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        transaction_id,
        request.user_id,
        request.order_id,
        request.amount,
        request.payment_method,
        payment_status
    ))

    # Update order
    cursor.execute("""
        UPDATE orders
        SET status = ?
        WHERE order_id = ?
    """, (
        "CONFIRMED",
        request.order_id
    ))

    connection.commit()
    connection.close()

    return {
        "message": "Payment successful",
        "transaction_id": transaction_id,
        "order_id": request.order_id,
        "amount": request.amount,
        "payment_method": request.payment_method,
        "status": "SUCCESS"
    }


# ============================================================
# GET PAYMENT
# ============================================================


@app.get("/payments/{transaction_id}")
def get_payment(transaction_id: str):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM payments
        WHERE transaction_id = ?
    """, (transaction_id,))

    payment = cursor.fetchone()

    connection.close()

    if payment is None:

        raise HTTPException(
            status_code=404,
            detail="Transaction not found"
        )

    return dict(payment)


# ============================================================
# CHECKOUT
# ============================================================


@app.post("/checkout")
def checkout(request: CheckoutRequest):

    if request.quantity <= 0:

        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than zero"
        )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # ====================================================
        # 1. CHECK USER
        # ====================================================

        cursor.execute("""
            SELECT *
            FROM users
            WHERE user_id = ?
        """, (request.user_id,))

        user = cursor.fetchone()

        if user is None:

            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # ====================================================
        # 2. CHECK PRODUCT
        # ====================================================

        cursor.execute("""
            SELECT *
            FROM products
            WHERE product_id = ?
        """, (request.product_id,))

        product = cursor.fetchone()

        if product is None:

            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        # ====================================================
        # 3. CHECK STOCK
        # ====================================================

        if product["quantity"] < request.quantity:

            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Product is not available",
                    "available_quantity": product["quantity"]
                }
            )

        # ====================================================
        # 4. CHECK ADDRESS
        # ====================================================

        cursor.execute("""
            SELECT *
            FROM addresses
            WHERE address_id = ?
            AND user_id = ?
        """, (
            request.address_id,
            request.user_id
        ))

        address = cursor.fetchone()

        if address is None:

            raise HTTPException(
                status_code=404,
                detail="Address not found for this user"
            )

        # ====================================================
        # 5. CALCULATE TOTAL
        # ====================================================

        total_amount = (
            product["price"]
            * request.quantity
        )

        # ====================================================
        # 6. GENERATE ORDER ID
        # ====================================================

        order_id = (
            "O"
            + uuid.uuid4().hex[:8].upper()
        )

        # ====================================================
        # 7. RESERVE / REDUCE STOCK
        # ====================================================

        cursor.execute("""
            UPDATE products
            SET quantity = quantity - ?
            WHERE product_id = ?
            AND quantity >= ?
        """, (
            request.quantity,
            request.product_id,
            request.quantity
        ))

        if cursor.rowcount == 0:

            raise HTTPException(
                status_code=400,
                detail="Unable to reserve product"
            )

        # ====================================================
        # 8. CREATE ORDER
        # ====================================================

        cursor.execute("""
            INSERT INTO orders
            (
                order_id,
                user_id,
                product_id,
                quantity,
                total_amount,
                address_id,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id,
            request.user_id,
            request.product_id,
            request.quantity,
            total_amount,
            request.address_id,
            "PAYMENT_PENDING"
        ))

        # ====================================================
        # 9. GENERATE TRANSACTION ID
        # ====================================================

        transaction_id = (
            "T"
            + uuid.uuid4().hex[:8].upper()
        )

        # ====================================================
        # 10. SIMULATE PAYMENT
        # ====================================================

        payment_status = "SUCCESS"

        cursor.execute("""
            INSERT INTO payments
            (
                transaction_id,
                user_id,
                order_id,
                amount,
                payment_method,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            transaction_id,
            request.user_id,
            order_id,
            total_amount,
            request.payment_method,
            payment_status
        ))

        # ====================================================
        # 11. CONFIRM ORDER
        # ====================================================

        cursor.execute("""
            UPDATE orders
            SET status = ?
            WHERE order_id = ?
        """, (
            "CONFIRMED",
            order_id
        ))

        # ====================================================
        # 12. COMMIT EVERYTHING
        # ====================================================

        connection.commit()

    except HTTPException:

        connection.rollback()
        connection.close()

        raise

    except Exception as error:

        connection.rollback()
        connection.close()

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    connection.close()

    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    return {
        "message": "Order placed successfully",

        "order": {
            "order_id": order_id,
            "user_id": request.user_id,
            "product_id": request.product_id,
            "quantity": request.quantity,
            "amount": total_amount,
            "address_id": request.address_id,
            "status": "CONFIRMED"
        },

        "payment": {
            "transaction_id": transaction_id,
            "payment_method": request.payment_method,
            "amount": total_amount,
            "status": "SUCCESS"
        }
    }