from flask import Flask, render_template, request, redirect, session
import psycopg2
import os
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = "secret123"

def connect_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

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

    # ✅ PostgreSQL version of INSERT IGNORE
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

    # 🔁 Find alternate room
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

    # ✅ Insert booking
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

# ---------------- ADMIN LOGIN ----------------
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    message = ""
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']

        if user == "admin" and pwd == "admin123":
            session['admin'] = True
            return redirect('/admin_dashboard')
        else:
            message = "Invalid Credentials"

    return render_template('admin.html', message=message)

# ---------------- VIEW BOOKINGS ----------------
@app.route('/view')
def view():
    if 'admin' not in session:
        return redirect('/admin')

    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT 
        b.booking_id,
        s.name,
        r.room_name,
        b.date,
        b.status,
        r.capacity,
        (r.capacity - (
            SELECT COUNT(*)
            FROM bookings
            WHERE room_id = b.room_id
            AND date = b.date
            AND status = 'Confirmed'
        )) AS remaining_seats
    FROM bookings b
    JOIN students s ON b.student_id = s.student_id
    JOIN rooms r ON b.room_id = r.room_id
    """)

    bookings = cur.fetchall()
    conn.close()

    return render_template('view.html', bookings=bookings)

# ---------------- DASHBOARD ----------------
@app.route('/admin_dashboard')
def admin_dashboard():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM rooms")
    total_rooms = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM bookings")
    total_bookings = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM bookings WHERE status='Pending'")
    pending = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM bookings WHERE status='Confirmed'")
    confirmed = cur.fetchone()[0]

    conn.close()

    return render_template('admin_dashboard.html',
                           total_rooms=total_rooms,
                           total_bookings=total_bookings,
                           pending=pending,
                           confirmed=confirmed)

# ---------------- ROOMS ----------------
@app.route('/add_room', methods=['POST'])
def add_room():
    name = request.form['room_name']
    capacity = request.form['capacity']

    conn = connect_db()
    cur = conn.cursor()

    cur.execute("INSERT INTO rooms (room_name, capacity) VALUES (%s, %s)", (name, capacity))
    conn.commit()
    conn.close()

    return redirect('/manage_rooms')

@app.route('/manage_rooms')
def manage_rooms():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM rooms")
    rooms = cur.fetchall()

    conn.close()
    return render_template('manage_rooms.html', rooms=rooms)

# ---------------- APPROVE / REJECT ----------------
@app.route('/approve/<int:id>')
def approve(id):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("UPDATE bookings SET status='Confirmed' WHERE booking_id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect('/view')

@app.route('/reject/<int:id>')
def reject(id):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("UPDATE bookings SET status='Cancelled' WHERE booking_id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect('/view')

# ---------------- MY BOOKINGS ----------------
@app.route('/my_bookings', methods=['GET', 'POST'])
def my_bookings():
    bookings = []

    if request.method == 'POST':
        phone = request.form['phone']

        conn = connect_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT b.booking_id, s.name, r.room_name, b.date, b.status
            FROM bookings b
            JOIN students s ON b.student_id = s.student_id
            JOIN rooms r ON b.room_id = r.room_id
            WHERE s.phone = %s
        """, (phone,))

        bookings = cur.fetchall()
        conn.close()

    return render_template('my_bookings.html', bookings=bookings)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
