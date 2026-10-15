
from fastapi import FastAPI, HTTPException, Path as ApiPath
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
from decimal import Decimal
from typing import Literal, Annotated

import mysql.connector
from mysql.connector import Error

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    model_validator
)


# 1. MYSQL CONNECTION

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "hotel_booking_db"
}


def get_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)

    except Error as exc:
        print("Database connection error:", exc)

        raise HTTPException(
            status_code=500,
            detail="Unable to connect to MySQL. Check your settings."
        )


# 2. CREATE TABLE

def create_table():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                booking_id INT AUTO_INCREMENT PRIMARY KEY,
                customer_name VARCHAR(100) NOT NULL,
                room_number INT NOT NULL,
                room_type VARCHAR(30) NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'Booked'
            )
        """)

        connection.commit()

    except Error as exc:
        connection.rollback()
        print("Table creation error:", exc)
        raise

    finally:
        cursor.close()
        connection.close()


# 3. APPLICATION LIFESPAN

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_table()
    yield


# CREATE THE FASTAPI APP ONLY ONCE

app = FastAPI(
    title="Hotel Room Booking System",
    description="API for managing hotel room bookings",
    version="1.0.0",
    lifespan=lifespan
)


# 4. PYDANTIC VALIDATION

RoomType = Literal["Standard", "Deluxe", "Suite"]


class BookingCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    customer_name: Annotated[
        str,
        Field(min_length=2, max_length=100)
    ]

    room_number: Annotated[
        int,
        Field(gt=0)
    ]

    room_type: RoomType

    amount: Annotated[
        Decimal,
        Field(gt=0, max_digits=10, decimal_places=2)
    ]


class RoomUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_number: Annotated[
        int,
        Field(gt=0)
    ] | None = None

    room_type: RoomType | None = None

    @model_validator(mode="after")
    def validate_update(self):
        if self.room_number is None and self.room_type is None:
            raise ValueError(
                "Provide a room number or room type."
            )

        return self


class ChatMessage(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: Annotated[
        str,
        Field(min_length=1, max_length=500)
    ]


# 5. HELPER FUNCTIONS

def find_booking(cursor, booking_id):
    cursor.execute(
        "SELECT * FROM bookings WHERE booking_id = %s",
        (booking_id,)
    )

    row = cursor.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Booking not found."
        )

    return row


def to_dict(row):
    return {
        "booking_id": row[0],
        "customer_name": row[1],
        "room_number": row[2],
        "room_type": row[3],
        "amount": float(row[4]),
        "status": row[5]
    }


def generate_chatbot_reply(message: str, bookings):
    text = message.strip().lower()

    if not text:
        return "Please type a question about booking, rooms, or hotel services."

    if any(word in text for word in ["hi", "hello", "hey"]):
        return "Hello! I can help with bookings, room types, check-in, and hotel support."

    if any(word in text for word in ["book", "reserve", "reservation"]):
        return (
            "You can create a reservation from the booking form on this page. "
            "Choose a guest name, room number, room type, and amount, then confirm."
        )

    if any(word in text for word in ["room", "suite", "deluxe", "standard"]):
        return (
            "We offer three room types: Standard, Deluxe, and Suite. "
            "Standard is the most basic option, Deluxe adds more space, and Suite offers a premium experience."
        )

    if any(word in text for word in ["price", "rate", "amount", "cost"]):
        return (
            "Room pricing is based on the selected room type and the amount you enter while booking. "
            "If needed, update the amount in the reservation form before confirming."
        )

    if any(word in text for word in ["check in", "checkin", "check-in"]):
        return (
            "To check in a guest, use the 'Guest Check-in & Check-out' section and enter the booking ID, then click Check In."
        )

    if any(word in text for word in ["check out", "checkout", "check-out"]):
        return (
            "To check out a guest, enter the booking ID in the same section and click Check Out."
        )

    if any(word in text for word in ["cancel", "cancellation"]):
        return (
            "You can cancel a booking from the guest status section by entering the booking ID and selecting Cancel Booking."
        )

    if any(word in text for word in ["search", "find", "lookup", "booking id"]):
        return (
            "Use the 'Find a Reservation' section to search a booking by ID and view the full reservation details."
        )

    if "status" in text:
        return (
            f"There are currently {len(bookings)} active booking records in the system. "
            "You can monitor their current status in the reservation overview table."
        )

    if any(word in text for word in ["help", "support", "thank you", "thanks"]):
        return "I can help with reservations, room types, booking status updates, check-in/out, and cancellation questions."

    return (
        "I can help with booking requests, room categories, reservation lookup, check-in/out, and cancellation support. "
        "Try asking about Standard, Deluxe, or Suite rooms, or how to create a booking."
    )


def check_room(cursor, room_number, exclude_id=None):
    query = """
        SELECT booking_id
        FROM bookings
        WHERE room_number = %s
        AND status IN ('Booked', 'Checked In')
    """

    params = [room_number]

    if exclude_id is not None:
        query += " AND booking_id != %s"
        params.append(exclude_id)

    cursor.execute(query, tuple(params))

    if cursor.fetchone():
        raise HTTPException(
            status_code=409,
            detail="This room already has an active booking."
        )


# 6. HTML HOME PAGE

@app.get("/", include_in_schema=False)
def home():
    file_path = Path(__file__).parent / "index.html"

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="index.html not found. Check that it is in the same folder as main.py."
        )

    return FileResponse(file_path)


# 7. CHATBOT HELPER

@app.post("/chat")
def chat_with_hotel_bot(chat: ChatMessage):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT room_type, status FROM bookings"
        )

        bookings = [
            {"room_type": row[0], "status": row[1]}
            for row in cursor.fetchall()
        ]

        return {
            "reply": generate_chatbot_reply(chat.message, bookings)
        }

    except Error as exc:
        print("Chatbot error:", exc)

        raise HTTPException(
            status_code=500,
            detail="Unable to process your chat request right now."
        )

    finally:
        cursor.close()
        connection.close()


# 8. CREATE BOOKING

@app.post("/bookings", status_code=201)
def create_booking(booking: BookingCreate):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        check_room(cursor, booking.room_number)

        cursor.execute("""
            INSERT INTO bookings
            (customer_name, room_number, room_type, amount, status)
            VALUES (%s, %s, %s, %s, 'Booked')
        """, (
            booking.customer_name,
            booking.room_number,
            booking.room_type,
            booking.amount
        ))

        connection.commit()

        return {
            "message": "Booking created successfully",
            "booking_id": cursor.lastrowid
        }

    except HTTPException:
        raise

    except Error as exc:
        connection.rollback()
        print("Create booking error:", exc)

        raise HTTPException(
            status_code=500,
            detail="Database error while creating booking."
        )

    finally:
        cursor.close()
        connection.close()


# 8. DISPLAY ALL BOOKINGS

@app.get("/bookings")
def display_bookings():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT * FROM bookings ORDER BY booking_id"
        )

        rows = cursor.fetchall()

        return [to_dict(row) for row in rows]

    except Error as exc:
        print("Display bookings error:", exc)

        raise HTTPException(
            status_code=500,
            detail="Database error while retrieving bookings."
        )

    finally:
        cursor.close()
        connection.close()


# 9. GET BOOKING BY ID

@app.get("/bookings/{booking_id}")
def get_booking(
    booking_id: Annotated[int, ApiPath(gt=0)]
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        row = find_booking(cursor, booking_id)

        return to_dict(row)

    except HTTPException:
        raise

    except Error as exc:
        print("Get booking error:", exc)

        raise HTTPException(
            status_code=500,
            detail="Database error while retrieving booking."
        )

    finally:
        cursor.close()
        connection.close()


# 10. UPDATE ROOM

@app.patch("/bookings/{booking_id}/room")
def update_room(
    booking_id: Annotated[int, ApiPath(gt=0)],
    room: RoomUpdate
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        row = find_booking(cursor, booking_id)

        if row[5] != "Booked":
            raise HTTPException(
                status_code=400,
                detail="Only Booked reservations can change rooms."
            )

        new_number = (
            room.room_number
            if room.room_number is not None
            else row[2]
        )

        new_type = (
            room.room_type
            if room.room_type is not None
            else row[3]
        )

        check_room(cursor, new_number, booking_id)

        cursor.execute("""
            UPDATE bookings
            SET room_number = %s, room_type = %s
            WHERE booking_id = %s
        """, (
            new_number,
            new_type,
            booking_id
        ))

        connection.commit()

        return {
            "message": "Room updated successfully",
            "booking_id": booking_id,
            "room_number": new_number,
            "room_type": new_type
        }

    except HTTPException:
        raise

    except Error as exc:
        connection.rollback()
        print("Update room error:", exc)

        raise HTTPException(
            status_code=500,
            detail="Database error while updating room."
        )

    finally:
        cursor.close()
        connection.close()


# 11. COMMON BOOKING STATUS FUNCTION

def change_status(
    booking_id,
    required_status,
    new_status
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        row = find_booking(cursor, booking_id)

        if row[5] != required_status:
            raise HTTPException(
                status_code=400,
                detail=f"Booking must have status {required_status}."
            )

        cursor.execute(
            """
            UPDATE bookings
            SET status = %s
            WHERE booking_id = %s
            """,
            (new_status, booking_id)
        )

        connection.commit()

        return {
            "message": "Booking status updated successfully",
            "booking_id": booking_id,
            "status": new_status
        }

    except HTTPException:
        raise

    except Error as exc:
        connection.rollback()
        print("Change status error:", exc)

        raise HTTPException(
            status_code=500,
            detail="Database error while updating booking status."
        )

    finally:
        cursor.close()
        connection.close()


# 12. CHECK IN

@app.patch("/bookings/{booking_id}/checkin")
def check_in(
    booking_id: Annotated[int, ApiPath(gt=0)]
):
    return change_status(
        booking_id,
        "Booked",
        "Checked In"
    )


# 13. CHECK OUT

@app.patch("/bookings/{booking_id}/checkout")
def check_out(
    booking_id: Annotated[int, ApiPath(gt=0)]
):
    return change_status(
        booking_id,
        "Checked In",
        "Checked Out"
    )


# 14. CANCEL BOOKING

@app.patch("/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: Annotated[int, ApiPath(gt=0)]
):
    return change_status(
        booking_id,
        "Booked",
        "Cancelled"
    )


# 15. DELETE ALL BOOKINGS

@app.delete("/bookings")
def delete_all_bookings():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM bookings")

        deleted_count = cursor.rowcount

        connection.commit()

        return {
            "message": "All bookings deleted",
            "deleted_count": deleted_count
        }

    except Error as exc:
        connection.rollback()
        print("Delete bookings error:", exc)

        raise HTTPException(
            status_code=500,
            detail="Database error while deleting bookings."
        )

    finally:
        cursor.close()
        connection.close()
