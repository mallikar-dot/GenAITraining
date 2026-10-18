
import os
import json
from pathlib import Path
from decimal import Decimal

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "").strip()

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "shopping_cart_db",
}

app = FastAPI(
    title="LuxeCart Shopping Cart API",
    description="Shopping cart management with an AI assistant",
    version="1.0.0",
)


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as exc:
        print("Database connection error:", exc)
        raise HTTPException(
            status_code=500,
            detail="Could not connect to the shopping cart database.",
        ) from exc


def serialize_order(order):
    if order is None:
        return None

    result = dict(order)

    if result.get("total_amount") is not None:
        result["total_amount"] = float(result["total_amount"])

    return result


# --------------------------------------------------
# CREATE TABLE IF IT DOES NOT EXIST
# --------------------------------------------------

@app.on_event("startup")
def initialize_database():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INT AUTO_INCREMENT PRIMARY KEY,
                customer_name VARCHAR(100) NOT NULL,
                product_name VARCHAR(150) NOT NULL,
                quantity INT NOT NULL DEFAULT 1,
                total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                status VARCHAR(30) NOT NULL DEFAULT 'Booked'
            )
        """)

        connection.commit()
        print("Shopping cart database is ready.")

    except Exception as exc:
        print("Database initialization error:", exc)
        raise

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=100)
    product_name: str = Field(min_length=1, max_length=150)
    quantity: int = Field(gt=0)
    total_amount: Decimal = Field(ge=0)


class QuantityUpdate(BaseModel):
    quantity: int = Field(gt=0)


class TotalUpdate(BaseModel):
    total_amount: Decimal = Field(ge=0)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.get("/", include_in_schema=False)
def home():
    html_file = BASE_DIR / "templates" / "index.html"

    if not html_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Frontend not found. Check templates/index.html.",
        )

    return FileResponse(html_file)


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "running",
        "ai_provider": "Ollama Cloud",
        "ai_configured": bool(OLLAMA_API_KEY),
    }


# --------------------------------------------------
# GET ALL ORDERS
# --------------------------------------------------

@app.get("/orders")
def get_orders():
    connection = get_db_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT order_id, customer_name, product_name,
                   quantity, total_amount, status
            FROM orders
            ORDER BY order_id DESC
        """)

        return [
            serialize_order(order)
            for order in cursor.fetchall()
        ]

    except Error as exc:
        print("Get orders error:", exc)
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve orders.",
        ) from exc

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# CREATE ORDER
# --------------------------------------------------

@app.post("/orders", status_code=201)
def create_order(order: OrderCreate):
    connection = get_db_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            INSERT INTO orders
                (customer_name, product_name, quantity,
                 total_amount, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            order.customer_name.strip(),
            order.product_name.strip(),
            order.quantity,
            order.total_amount,
            "Booked",
        ))

        new_order_id = cursor.lastrowid
        connection.commit()

        cursor.execute("""
            SELECT order_id, customer_name, product_name,
                   quantity, total_amount, status
            FROM orders
            WHERE order_id = %s
        """, (new_order_id,))

        return serialize_order(cursor.fetchone())

    except Error as exc:
        connection.rollback()
        print("Create order error:", exc)
        raise HTTPException(
            status_code=500,
            detail="Could not create the order.",
        ) from exc

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# GET ONE ORDER
# --------------------------------------------------

@app.get("/orders/{order_id}")
def get_order(order_id: int):
    connection = get_db_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT order_id, customer_name, product_name,
                   quantity, total_amount, status
            FROM orders
            WHERE order_id = %s
        """, (order_id,))

        order = cursor.fetchone()

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found.",
            )

        return serialize_order(order)

    except HTTPException:
        raise

    except Error as exc:
        print("Get order error:", exc)
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve the order.",
        ) from exc

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# UPDATE ORDER QUANTITY
# --------------------------------------------------

@app.put("/orders/{order_id}/quantity")
def update_quantity(order_id: int, data: QuantityUpdate):
    connection = get_db_connection()
    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE orders
            SET quantity = %s
            WHERE order_id = %s
        """, (data.quantity, order_id))

        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT order_id FROM orders WHERE order_id = %s",
                (order_id,),
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail="Order not found.",
                )

        connection.commit()

        return {
            "message": "Order quantity updated successfully.",
            "order_id": order_id,
            "quantity": data.quantity,
        }

    except HTTPException:
        raise

    except Error as exc:
        connection.rollback()
        print("Update quantity error:", exc)
        raise HTTPException(
            status_code=500,
            detail="Could not update order quantity.",
        ) from exc

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# UPDATE ORDER TOTAL
# --------------------------------------------------

@app.put("/orders/{order_id}/total")
def update_total(order_id: int, data: TotalUpdate):
    connection = get_db_connection()
    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE orders
            SET total_amount = %s
            WHERE order_id = %s
        """, (data.total_amount, order_id))

        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT order_id FROM orders WHERE order_id = %s",
                (order_id,),
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail="Order not found.",
                )

        connection.commit()

        return {
            "message": "Order total updated successfully.",
            "order_id": order_id,
            "total_amount": float(data.total_amount),
        }

    except HTTPException:
        raise

    except Error as exc:
        connection.rollback()
        print("Update total error:", exc)
        raise HTTPException(
            status_code=500,
            detail="Could not update order total.",
        ) from exc

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# CANCEL ORDER
# --------------------------------------------------

@app.patch("/orders/{order_id}/cancel")
def cancel_order(order_id: int):
    connection = get_db_connection()
    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE orders
            SET status = 'Cancelled'
            WHERE order_id = %s
        """, (order_id,))

        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT order_id FROM orders WHERE order_id = %s",
                (order_id,),
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail="Order not found.",
                )

        connection.commit()

        return {
            "message": "Order cancelled successfully.",
            "order_id": order_id,
            "status": "Cancelled",
        }

    except HTTPException:
        raise

    except Error as exc:
        connection.rollback()
        print("Cancel order error:", exc)
        raise HTTPException(
            status_code=500,
            detail="Could not cancel the order.",
        ) from exc

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# DELETE ONE ORDER
# --------------------------------------------------

@app.delete("/orders/{order_id}")
def delete_order(order_id: int):
    connection = get_db_connection()
    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM orders WHERE order_id = %s",
            (order_id,),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Order not found.",
            )

        connection.commit()

        return {
            "message": "Order deleted successfully.",
            "order_id": order_id,
        }

    except HTTPException:
        raise

    except Error as exc:
        connection.rollback()
        print("Delete order error:", exc)
        raise HTTPException(
            status_code=500,
            detail="Could not delete the order.",
        ) from exc

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# DELETE ALL ORDERS
# --------------------------------------------------

@app.delete("/orders")
def delete_all_orders():
    connection = get_db_connection()
    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute("DELETE FROM orders")
        deleted_count = cursor.rowcount

        connection.commit()

        return {
            "message": "All orders deleted successfully.",
            "deleted_count": deleted_count,
        }

    except Error as exc:
        connection.rollback()
        print("Delete all orders error:", exc)
        raise HTTPException(
            status_code=500,
            detail="Could not delete orders.",
        ) from exc

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# OLLAMA CLOUD CHATBOT
# --------------------------------------------------

@app.post("/chat")
def chat_with_ai(data: ChatRequest):
    if not OLLAMA_API_KEY:
        raise HTTPException(
            status_code=503,
            detail=(
                "OLLAMA_API_KEY is missing. Add it to your .env file "
                "and restart FastAPI."
            ),
        )

    messages = [
        {
            "role": "system",
            "content": (
                "You are the LuxeCart shopping assistant. "
                "Help users with shopping cart features, products, "
                "quantities, prices, and general shopping questions. "
                "Be friendly and concise. "
                "Never claim an order was changed, cancelled, or deleted "
                "unless the application actually completed that action. "
                "Do not invent order details."
            ),
        }
    ]

    for message in data.messages[-20:]:
        if message.role not in ("user", "assistant"):
            raise HTTPException(
                status_code=400,
                detail="Chat messages must use user or assistant roles.",
            )

        if message.content.strip():
            messages.append({
                "role": message.role,
                "content": message.content.strip(),
            })

    if len(messages) == 1 or messages[-1]["role"] != "user":
        raise HTTPException(
            status_code=400,
            detail="Please send a user message.",
        )

    payload = {
        "model": "gemma4:31b",
        "messages": messages,
        "stream": False,
    }

    request = Request(
        url="https://ollama.com/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OLLAMA_API_KEY}",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=180) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

        reply = result.get("message", {}).get("content")

        if not reply:
            raise HTTPException(
                status_code=502,
                detail="Ollama returned an empty response.",
            )

        return {"reply": reply}

    except HTTPError as exc:
        error_body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        print("Ollama HTTP status:", exc.code)
        print("Ollama error:", error_body[:1000])

        if exc.code == 401:
            detail = "Ollama authentication failed. Check your API key."
        elif exc.code == 403:
            detail = (
                "Ollama denied access. Check your account, model access, "
                "and cloud eligibility."
            )
        elif exc.code == 429:
            detail = (
                "Ollama usage limit reached. Check your account and plan."
            )
        else:
            detail = f"Ollama API request failed with HTTP {exc.code}."

        raise HTTPException(
            status_code=502,
            detail=detail,
        ) from exc

    except URLError as exc:
        print("Ollama connection error:", exc)
        raise HTTPException(
            status_code=503,
            detail="Could not connect to Ollama Cloud. Check your internet connection.",
        ) from exc

    except (KeyError, ValueError) as exc:
        print("Ollama response parsing error:", exc)
        raise HTTPException(
            status_code=502,
            detail="Received an invalid response from Ollama.",
        ) from exc

    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail="The AI assistant timed out. Please try again.",
        ) from exc
