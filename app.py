from flask import Flask, render_template, request, redirect, session
import psycopg2
import os
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = "secret123"

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

# ✅ NEW: Initialize DB
def init_db():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id SERIAL PRIMARY KEY,
        name VARCHAR(100),
        phone VARCHAR(15) UNIQUE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        room_id SERIAL PRIMARY KEY,
        room_name VARCHAR(100),
        capacity INT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        booking_id SERIAL PRIMARY KEY,
        student_id INT REFERENCES students(student_id),
        room_id INT REFERENCES rooms(room_id),
        date DATE,
        status VARCHAR(20)
    );
    """)

    # Insert default rooms
    cur.execute("""
    INSERT INTO rooms (room_name, capacity)
    VALUES ('Room A',5),('Room B',3),('Room C',4)
    ON CONFLICT DO NOTHING;
    """)

    conn.commit()
    cur.close()
    conn.close()

# ✅ AUTO RUN DB INIT (works on Render)
@app.before_request
def setup():
    init_db()

# ---------------- HOME ----------------
@app.route('/')
def index():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM rooms")
    rooms = cur.fetchall()

    today = date.today()

    conn.close()
    return render_template('index.html', rooms=rooms, today=today)

# ---------------- BOOK ----------------
@app.route('/book', methods=['POST'])
def book():
    name = request.form['name']
    phone = request.form['phone']
    room_id = int(request.form['room'])
    date_val = request.form['date']

    if not name or not phone or not date_val:
        return "All fields required ❌"

    if len(name) < 3:
        return "Name too short ❌"

    if not phone.isdigit() or len(phone) != 10:
        return "Invalid phone number ❌"

    try:
        booking_date = datetime.strptime(date_val, "%Y-%m-%d").date()
        today = datetime.today().date()

        if booking_date < today:
            return "Cannot book past dates ❌"
    except:
        return "Invalid date format ❌"

    conn = connect_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO students (name, phone) VALUES (%s, %s) ON CONFLICT (phone) DO NOTHING",
        (name, phone)
    )

    cur.execute("SELECT student_id FROM students WHERE phone=%s", (phone,))
    student_id = cur.fetchone()[0]

    original_room_id = room_id

    cur.execute("SELECT capacity FROM rooms WHERE room_id=%s", (room_id,))
    capacity = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM bookings WHERE room_id=%s AND date=%s AND status='Confirmed'",
        (room_id, date_val)
    )
    count = cur.fetchone()[0]

    if count >= capacity:
        cur.execute("SELECT room_id, capacity FROM rooms")
        rooms = cur.fetchall()

        found = False
        for r in rooms:
            r_id, r_capacity = r

            cur.execute(
                "SELECT COUNT(*) FROM bookings WHERE room_id=%s AND date=%s AND status='Confirmed'",
                (r_id, date_val)
            )
            r_count = cur.fetchone()[0]

            if r_count < r_capacity:
                room_id = r_id
                found = True
                break

        if not found:
            conn.close()
            return "❌ All rooms are full. Try another date."

    cur.execute(
        "INSERT INTO bookings (student_id, room_id, date, status) VALUES (%s, %s, %s, %s)",
        (student_id, room_id, date_val, 'Pending')
    )
    conn.commit()

    cur.execute("SELECT room_name FROM rooms WHERE room_id=%s", (room_id,))
    room_name = cur.fetchone()[0]

    conn.close()

    note = ""
    if room_id != original_room_id:
        note = "⚠ Selected room was full. Assigned another room."

    return render_template(
        'success.html',
        name=name,
        room=room_name,
        date=date_val,
        status="Pending",
        phone=phone,
        note=note
    )

# (rest of your code unchanged...)
