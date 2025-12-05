import sqlite3
from datetime import datetime, timedelta

DB_NAME = "schedule.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # [CẬP NHẬT] Thêm cột end_time vào bảng
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
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if data.get('start_time'):
        c.execute('''
            INSERT INTO events (event_name, start_time, end_time, location, reminder_minutes)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get('event', 'Sự kiện không tên'),
            data.get('start_time'),
            data.get('end_time'), # Có thể là None
            data.get('location', ''),
            data.get('reminder_minutes', 0)
        ))
        conn.commit()
    conn.close()

def get_all_events():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # [CẬP NHẬT] Lấy đủ 6 cột bao gồm end_time
    c.execute("SELECT id, event_name, start_time, end_time, location, reminder_minutes FROM events ORDER BY start_time ASC")
    rows = c.fetchall()
    conn.close()
    return rows

def delete_event(event_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM events WHERE id=?", (event_id,))
    conn.commit()
    conn.close()

def update_event(event_id, new_name, new_start_time, new_end_time, new_location, new_remind):
    # (Để đơn giản, tạm thời update chưa xử lý end_time, giữ nguyên logic cũ hoặc bạn có thể tự bổ sung)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        UPDATE events 
        SET event_name=?, start_time=?, end_time=?, location=?, reminder_minutes=?
        WHERE id=?
    ''', (new_name, new_start_time, new_end_time, new_location, new_remind, event_id))
    conn.commit()
    conn.close()

# --- [SỬA LẠI] HÀM KIỂM TRA XUNG ĐỘT (HIỂN THỊ TẤT CẢ SỰ KIỆN TRÙNG) ---
def check_overlap(new_start_iso, new_end_iso=None):
    """
    Kiểm tra xem thời gian mới có bị trùng với sự kiện đã có không.
    Trả về: (Có trùng không?, Danh sách tên các sự kiện bị trùng)
    """
    events = get_all_events()
    conflicting_events = [] # [MỚI] Danh sách chứa tên các sự kiện bị trùng
    
    # Parse thời gian mới
    try:
        new_start = datetime.fromisoformat(new_start_iso)
        # Nếu không có end_time, mặc định sự kiện kéo dài 60 phút để check
        new_end = datetime.fromisoformat(new_end_iso) if new_end_iso else new_start + timedelta(minutes=60)
    except ValueError:
        return False, [] # Không check được nếu format sai

    for ev in events:
        # Cấu trúc ev trả về từ get_all_events: 
        # (0: id, 1: event_name, 2: start_time, 3: end_time, 4: location, 5: reminder_minutes)
        
        existing_start_iso = ev[2]
        existing_end_iso = ev[3]  
        name = ev[1]

        try:
            existing_start = datetime.fromisoformat(existing_start_iso)
            # Nếu sự kiện cũ không có end_time, cũng mặc định là 60 phút
            existing_end = datetime.fromisoformat(existing_end_iso) if existing_end_iso else existing_start + timedelta(minutes=60)

            # Logic kiểm tra giao nhau: (StartA < EndB) và (EndA > StartB)
            if new_start < existing_end and new_end > existing_start:
                conflicting_events.append(name) # [MỚI] Thêm vào danh sách thay vì return ngay
        except (ValueError, TypeError):
            continue

    # [MỚI] Trả về True nếu danh sách không rỗng
    if conflicting_events:
        return True, conflicting_events
        
    return False, []