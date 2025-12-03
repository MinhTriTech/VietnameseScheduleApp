import sqlite3
from datetime import datetime

DB_NAME = "schedule.db"

def init_db():
    """Khởi tạo database và bảng nếu chưa có"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tạo bảng events với các cột theo yêu cầu đồ án
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            location TEXT,
            reminder_minutes INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_event(data):
    """Thêm một sự kiện mới vào DB"""
    # data là dictionary đầu ra từ nlp_engine
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Chỉ lưu nếu có thời gian cụ thể
    if data.get('start_time'):
        c.execute('''
            INSERT INTO events (event_name, start_time, location, reminder_minutes)
            VALUES (?, ?, ?, ?)
        ''', (
            data.get('event', 'Sự kiện không tên'),
            data.get('start_time'),
            data.get('location', ''),
            data.get('reminder_minutes', 0)
        ))
        conn.commit()
        print(f"-> Đã lưu sự kiện: {data.get('event')}")
    else:
        print("-> Lỗi: Không có thời gian, không lưu được.")
    
    conn.close()

def get_all_events():
    """Lấy danh sách tất cả sự kiện (để hiển thị lên lịch)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Sắp xếp theo thời gian để sự kiện sắp tới hiện lên đầu
    c.execute("SELECT * FROM events ORDER BY start_time ASC")
    rows = c.fetchall()
    conn.close()
    return rows

def delete_event(event_id):
    """Xóa sự kiện theo ID"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM events WHERE id=?", (event_id,))
    conn.commit()
    conn.close()

# --- CHẠY THỬ (TEST) ---
if __name__ == "__main__":
    # 1. Tạo file database
    init_db()
    print("Đã khởi tạo database thành công!")
    
    # 2. Thử thêm dữ liệu giả
    dummy_data = {
        'event': 'Test Database',
        'start_time': '2025-12-05T08:00:00',
        'location': 'Phòng Lab',
        'reminder_minutes': 10
    }
    add_event(dummy_data)
    
    # 3. In ra xem thử có gì trong đó chưa
    events = get_all_events()
    print("Danh sách sự kiện hiện có:", events)