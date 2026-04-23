-- 🔥 1. RESET DATABASE
DROP DATABASE IF EXISTS studyroom;
CREATE DATABASE studyroom;
USE studyroom;


-- 🔥 2. STUDENTS TABLE
CREATE TABLE students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15) UNIQUE NOT NULL
);


-- 🔥 3. ROOMS TABLE
CREATE TABLE rooms (
    room_id INT AUTO_INCREMENT PRIMARY KEY,
    room_name VARCHAR(50) NOT NULL,
    capacity INT NOT NULL
);


-- 🔥 4. ADMIN TABLE
CREATE TABLE admin (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(50) NOT NULL
);


-- 🔥 5. BOOKINGS TABLE (IMPORTANT)
CREATE TABLE bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    room_id INT,
    date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'Pending',

    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
);

-- ❗ NO UNIQUE(room_id, date)
-- ❗ NO PRIMARY KEY on room_id


-- 🔥 6. INSERT ROOMS
INSERT INTO rooms (room_name, capacity) VALUES
('Room 1', 4),
('Room 2', 6),
('Room 3', 8);


-- 🔥 7. INSERT ADMIN
INSERT INTO admin (username, password) VALUES
('admin', 'admin123');


-- 🔍 8. CHECK TABLES
SELECT * FROM rooms;
SELECT * FROM admin;