# Amazon Backend System

A containerized Amazon-like e-commerce backend built with **Python**, **FastAPI**, **SQLite** (SQL), **ChromaDB** (NoSQL), and **Docker**.

---

## 🌟 Key Features

- **User Authentication**: User login validation and profile handling.
- **Dual-Database Architecture**:
  - **SQL (SQLite)** for transactional user data (Users, Addresses, Orders, Payments).
  - **NoSQL (ChromaDB)** for high-performance product catalog metadata & keyword search.
- **Product Catalog Management**: Create products, check real-time stock availability, and update inventory in NoSQL.
- **Orders & Payments**: Cross-database transaction processing (stock reservation in NoSQL + order creation in SQL).
- **Docker Containerization**: Full Docker & Docker Compose setup with volume persistence for easy deployment.
- **Interactive API Documentation**: Built-in Swagger UI at `/docs`.

---

## 🏗️ Architecture & Database Separation

| Category | Storage Engine | Technology | Reason |
| :--- | :--- | :--- | :--- |
| **User Data** (Users, Addresses, Orders, Payments) | Relational DB | **SQLite (SQL)** | Strict ACID compliance, relational integrity, and structured tables. |
| **Product Metadata** (Catalog, Price, Stock, Descriptions) | Vector / Document DB | **ChromaDB (NoSQL)** | Dynamic document schema, fast product metadata retrieval, and keyword search. |

---

## 🚀 Quick Start with Docker (Recommended)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

### Running with Docker Compose
1. Clone the repository:
   ```bash
   git clone https://github.com/varshinisn98-png/amazon-backend.git
   cd amazon-backend
   ```
2. Build and start the container:
   ```bash
   docker compose up --build
   ```
3. Open your browser and navigate to:
   👉 **`http://localhost:8000/docs`**

To stop the container:
```bash
docker compose down
```

---

## 💻 Running Locally (Without Docker)

### Prerequisites
- Python 3.10+

### Steps
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the Uvicorn server:
   ```bash
   python -m uvicorn main:app --reload
   ```
3. Access API docs at `http://127.0.0.1:8000/docs`.

---

## 📁 Project Structure

```text
amazon-backend/
├── Dockerfile              # Docker container build script
├── docker-compose.yml      # Multi-container orchestration & volume mounts
├── .dockerignore           # Excluded files for Docker build context
├── .gitignore              # Ignored files for Git repository
├── main.py                 # FastAPI application, routing & NoSQL interactions
├── database.py             # SQLite database connections and table initialization
├── filesops.py             # JSON file reader/writer helpers
├── product_details.json    # Initial seed data for products
├── user_details.json       # Initial seed data for users
├── requirements.txt        # Python package dependencies
└── README.md               # Project documentation
```

---

## 🛠️ API Endpoints Summary

- `POST /auth/login` — Authenticate user
- `GET /products` — Retrieve all products (from ChromaDB NoSQL)
- `GET /products/search?keyword={kw}` — Search product catalog (via ChromaDB)
- `GET /products/{product_id}` — Get details of a single product
- `POST /products` — Add a new product to NoSQL
- `GET /products/{product_id}/availability` — Check stock status
- `PUT /products/{product_id}/inventory` — Update product stock level
- `POST /users/{user_id}/address` — Add user delivery address
- `POST /orders` — Create new order (Cross-DB operation)
- `GET /orders/{order_id}` — Get order details (Application-level join)
- `POST /payments` — Process payment for order
- `POST /checkout` — End-to-end checkout & stock deduction

---

## 📝 License
This project is developed for educational and demonstration purposes.
