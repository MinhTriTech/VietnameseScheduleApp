import sqlite3
from datetime import datetime, timedelta

# Cấu hình tên cơ sở dữ liệu
DB_NAME = "schedule.db"

def init_db():
    """
    Khởi tạo cơ sở dữ liệu và bảng 'events' nếu chưa tồn tại.
    Cấu trúc bảng gồm: id, tên sự kiện, thời gian bắt đầu/kết thúc, địa điểm, nhắc nhở.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT, 
            location TEXT,
            reminder_minutes INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_event(data):
    """
    Thêm một sự kiện mới vào database.
    data (dict): Dictionary chứa thông tin sự kiện (event, start_time, end_time, location, reminder_minutes).
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Chỉ lưu nếu có thời gian bắt đầu hợp lệ
    if data.get('start_time'):
        c.execute('''
            INSERT INTO events (event_name, start_time, end_time, location, reminder_minutes)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get('event', 'Sự kiện không tên'),
            data.get('start_time'),
            data.get('end_time'), # Chấp nhận giá trị None 
            data.get('location', ''),
            data.get('reminder_minutes', 0)
        ))
        conn.commit()
    conn.close()

def get_all_events():
    """
    Lấy danh sách toàn bộ sự kiện, sắp xếp theo thời gian bắt đầu tăng dần.
    Returns: list - Danh sách các row dữ liệu từ database.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, event_name, start_time, end_time, location, reminder_minutes FROM events ORDER BY start_time ASC")
    rows = c.fetchall()
    conn.close()
    return rows

def delete_event(event_id):
    """
    Xóa sự kiện dựa trên ID.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM events WHERE id=?", (event_id,))
    conn.commit()
    conn.close()

def update_event(event_id, new_name, new_start_time, new_end_time, new_location, new_remind):
    """
    Cập nhật thông tin của một sự kiện đã tồn tại.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        UPDATE events 
        SET event_name=?, start_time=?, end_time=?, location=?, reminder_minutes=?
        WHERE id=?
    ''', (new_name, new_start_time, new_end_time, new_location, new_remind, event_id))
    conn.commit()
    conn.close()

def check_overlap(new_start_iso, new_end_iso=None):
    """
    Kiểm tra xung đột lịch trình (Conflict Detection).
    Sự kiện A và B trùng nhau khi: (StartA < EndB) và (EndA > StartB).

    new_start_iso (str): Thời gian bắt đầu dự kiến (ISO Format).
    new_end_iso (str, optional): Thời gian kết thúc dự kiến.

    Returns: tuple: (bool, list) - (Có trùng không, Danh sách tên các sự kiện bị trùng).
    """
    events = get_all_events()
    conflicting_events = [] 
    
    try:
        new_start = datetime.fromisoformat(new_start_iso)
        # Nếu không có thời gian kết thúc, mặc định sự kiện kéo dài 60 phút để kiểm tra va chạm
        new_end = datetime.fromisoformat(new_end_iso) if new_end_iso else new_start + timedelta(minutes=60)
    except ValueError:
        return False, [] 

    for ev in events:
        # Giải nén tuple dữ liệu từ DB
        # ev: (0: id, 1: name, 2: start, 3: end, 4: loc, 5: remind)
        existing_start_iso = ev[2]
        existing_end_iso = ev[3]  
        name = ev[1]

        try:
            existing_start = datetime.fromisoformat(existing_start_iso)
            # Tương tự, nếu sự kiện cũ không có end_time, giả định dài 60 phút
            existing_end = datetime.fromisoformat(existing_end_iso) if existing_end_iso else existing_start + timedelta(minutes=60)

            # Kiểm tra giao nhau
            if new_start < existing_end and new_end > existing_start:
                conflicting_events.append(name)
        except (ValueError, TypeError):
            continue

    if conflicting_events:
        return True, conflicting_events
        
    return False, []