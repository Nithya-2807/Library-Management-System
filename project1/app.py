from flask import Flask, render_template, request, redirect
from flask import session
import mysql.connector

app = Flask(__name__)
app.secret_key = "secret123"

def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="nithya",
        database="studyroom"
    )

from datetime import date

@app.route('/')
def index():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM rooms")
    rooms = cur.fetchall()

    today = date.today()

    conn.close()
    return render_template('index.html', rooms=rooms, today=today)
from datetime import datetime

@app.route('/book', methods=['POST'])
def book():
    name = request.form['name']
    phone = request.form['phone']
    room_id = int(request.form['room'])
    date = request.form['date']

    # 🔥 BASIC VALIDATION
    if not name or not phone or not date:
        return "All fields required ❌"

    if len(name) < 3:
        return "Name too short ❌"

    if not phone.isdigit() or len(phone) != 10:
        return "Invalid phone number ❌"

    # 🔥 DATE VALIDATION
    try:
        booking_date = datetime.strptime(date, "%Y-%m-%d").date()
        today = datetime.today().date()

        if booking_date < today:
            return "Cannot book past dates ❌"
    except:
        return "Invalid date format ❌"

    conn = connect_db()
    cur = conn.cursor()

    # 🔥 INSERT STUDENT (avoid duplicates)
    cur.execute(
        "INSERT IGNORE INTO students (name, phone) VALUES (%s, %s)",
        (name, phone)
    )

    # 🔥 GET student_id
    cur.execute("SELECT student_id FROM students WHERE phone=%s", (phone,))
    result = cur.fetchone()
    if not result:
        conn.close()
        return "Student fetch failed ❌"

    student_id = result[0]

    original_room_id = room_id  # save original choice

    # 🔥 CHECK SELECTED ROOM
    cur.execute("SELECT capacity FROM rooms WHERE room_id=%s", (room_id,))
    capacity = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM bookings WHERE room_id=%s AND date=%s AND status='Confirmed'",
        (room_id, date)
    )
    count = cur.fetchone()[0]

    # 🔥 IF FULL → FIND ANOTHER ROOM
    if count >= capacity:

        cur.execute("SELECT room_id, capacity FROM rooms")
        rooms = cur.fetchall()

        found = False

        for r in rooms:
            r_id, r_capacity = r

            cur.execute(
                "SELECT COUNT(*) FROM bookings WHERE room_id=%s AND date=%s AND status='Confirmed'",
                (r_id, date)
            )
            r_count = cur.fetchone()[0]

            if r_count < r_capacity:
                room_id = r_id   # assign new room
                found = True
                break

        if not found:
            conn.close()
            return "❌ All rooms are full. Try another date."

    # 🔥 INSERT BOOKING
    try:
        cur.execute(
            "INSERT INTO bookings (student_id, room_id, date, status) VALUES (%s, %s, %s, %s)",
            (student_id, room_id, date, 'Pending')
        )
        conn.commit()
    except Exception as e:
        conn.close()
        return f"Booking failed ❌ {e}"

    # 🔥 GET ROOM NAME
    cur.execute("SELECT room_name FROM rooms WHERE room_id=%s", (room_id,))
    room_name = cur.fetchone()[0]

    conn.close()

    # 🔥 OPTIONAL MESSAGE
    note = ""
    if room_id != original_room_id:
        note = "⚠ Selected room was full. Assigned another room."

    return render_template(
        'success.html',
        name=name,
        room=room_name,
        date=date,
        status="Pending",
        phone=phone,
        note=note
    )
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    message = ""
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']

        if user == "admin" and pwd == "admin123":
            session['admin'] = True   # ✅ VERY IMPORTANT
            return redirect('/admin_dashboard')
        else:
            message = "Invalid Credentials"

    return render_template('admin.html', message=message)
@app.route('/cancel/<int:id>')
def cancel(id):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("UPDATE bookings SET status='Cancelled' WHERE booking_id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect('/view')
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
@app.route('/admin_dashboard')
def admin_dashboard():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM rooms")
    total_rooms = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM bookings")
    total_bookings = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM bookings WHERE status='Confirmed'")
    pending = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM bookings WHERE status='Confirmed'")
    confirmed = cur.fetchone()[0]

    conn.close()

    return render_template('admin_dashboard.html',
                           total_rooms=total_rooms,
                           total_bookings=total_bookings,
                           pending=pending,
                           confirmed=confirmed)
@app.route('/add_room', methods=['POST'])
def add_room():
    name = request.form['room_name']
    capacity = request.form['capacity']

    conn = connect_db()
    cur = conn.cursor()

    cur.execute("INSERT INTO rooms (room_name, capacity) VALUES (%s, %s)",
                (name, capacity))
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
@app.route('/delete_room/<int:id>')
def delete_room(id):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM rooms WHERE room_id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect('/manage_rooms')
@app.route('/approve/<int:id>')
def approve(id):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE bookings SET status='Confirmed' WHERE booking_id=%s",
        (id,)
    )
    conn.commit()
    conn.close()

    return redirect('/view')   # IMPORTANT
@app.route('/reject/<int:id>')
def reject(id):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE bookings SET status='Cancelled' WHERE booking_id=%s",
        (id,)
    )
    conn.commit()
    conn.close()

    return redirect('/view')   # IMPORTANT
@app.route('/students')
def students():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM students")
    students = cur.fetchall()

    conn.close()

    return render_template('students.html', students=students)
@app.route('/delete_student/<int:id>')
def delete_student(id):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM students WHERE student_id=%s", (id,))
    conn.commit()
    conn.close()

    return redirect('/students')
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
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


if __name__ == "__main__":
    app.run(debug=True)