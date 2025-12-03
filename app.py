import streamlit as st
import pandas as pd
import time
from datetime import datetime
from nlp_engine import NLPProcessor
from database import add_event, get_all_events, delete_event, init_db
import threading
import ctypes  # Để gọi hộp thoại Windows
import winsound # Để phát tiếng bíp
# ... (giữ nguyên các import cũ: streamlit, pandas, nlp_engine...)

# 1. Cấu hình trang web
st.set_page_config(
    page_title="Trợ lý Lịch trình AI",
    page_icon="📅",
    layout="centered"
)

# 2. Khởi tạo các module (Load bộ não và bộ nhớ)
if 'processor' not in st.session_state:
    st.session_state.processor = NLPProcessor()
    init_db() # Đảm bảo DB luôn sẵn sàng

# --- HÀM CHẠY NGẦM (BACKGROUND THREAD) ---
def check_reminders_loop():
    """Hàm này sẽ chạy vĩnh viễn trong một luồng riêng"""
    while True:
        # 1. Lấy giờ hiện tại
        now = datetime.now()
        current_time_str = now.strftime("%Y-%m-%dT%H:%M:00") # Chặt bỏ giây lẻ
        
        # 2. Kết nối DB (Lưu ý: Thread riêng phải tự kết nối DB riêng)
        # Chúng ta import hàm get_all_events nhưng cần lọc lại logic
        # Để đơn giản, ta viết query trực tiếp ở đây
        try:
            conn = sqlite3.connect("schedule.db")
            c = conn.cursor()
            # Tìm sự kiện có giờ bắt đầu == giờ hiện tại
            c.execute("SELECT event_name, location FROM events WHERE start_time LIKE ?", (current_time_str + '%',))
            events = c.fetchall()
            conn.close()

            # 3. Nếu có sự kiện -> Bắn thông báo
            for event in events:
                message = f"Đến giờ: {event[0]}\nTại: {event[1]}"
                
                # Phát tiếng bíp
                try: winsound.Beep(1000, 500) 
                except: pass
                
                # Hiện Pop-up của Windows (MessageBox)
                # 0x40000 = TopMost (luôn hiện trên cùng)
                ctypes.windll.user32.MessageBoxW(0, message, "⏰ NHẮC NHỞ LỊCH TRÌNH", 0x40000 | 0x1)
                
        except Exception as e:
            print(f"Lỗi thread: {e}")

        # 4. Ngủ 10 giây rồi kiểm tra tiếp (đồ án yêu cầu 60s, nhưng để 10s test cho nhanh)
        time.sleep(10)

# Kích hoạt luồng chạy ngầm (Chỉ chạy 1 lần duy nhất khi app khởi động)
if 'reminder_thread_started' not in st.session_state:
    import sqlite3 # Import lại trong scope này cho chắc
    t = threading.Thread(target=check_reminders_loop, daemon=True)
    t.start()
    st.session_state.reminder_thread_started = True
    print("--> Đã khởi động luồng nhắc nhở ngầm!")

# Tiêu đề ứng dụng
st.title("🤖 Trợ lý Lịch trình Thông minh")
st.markdown("---")

# --- KHU VỰC NHẬP LỆNH ---
st.subheader("💬 Nhập yêu cầu của bạn")
user_input = st.text_input("Ví dụ: Nhắc tôi đi họp lúc 9h sáng mai tại phòng 302", key="input_text")

if st.button("Thêm sự kiện", type="primary"):
    if user_input:
        with st.spinner("Đang phân tích..."):
            # A. Gọi bộ não NLP xử lý
            data = st.session_state.processor.process(user_input)
            
            # B. Kiểm tra kết quả
            if data.get('start_time'):
                # C. Lưu vào bộ nhớ Database
                add_event(data)
                st.success(f"✅ Đã thêm: {data['event']} vào lúc {data['start_time']}")
                # D. Refresh lại trang để hiện lịch mới (trick nhỏ trong Streamlit)
                time.sleep(1) 
                st.rerun()
            else:
                st.error("⚠️ Không tìm thấy thời gian cụ thể trong câu. Vui lòng thử lại!")
    else:
        st.warning("Bạn chưa nhập nội dung gì cả.")


        # --- KHU VỰC HIỂN THỊ LỊCH ---
st.markdown("---")
st.subheader("📅 Danh sách công việc")

# 1. Lấy dữ liệu từ Database
events = get_all_events()

if events:
    # 2. Chuyển đổi sang dạng bảng đẹp (DataFrame)
    df = pd.DataFrame(events, columns=["ID", "Sự kiện", "Thời gian", "Địa điểm", "Nhắc trước (phút)"])
    
    # 3. Hiển thị bảng
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 4. Chức năng Xóa sự kiện
    with st.expander("🗑️ Xóa sự kiện"):
        col1, col2 = st.columns([3, 1])
        with col1:
            # Chọn ID để xóa
            id_to_delete = st.selectbox("Chọn ID sự kiện muốn xóa:", df["ID"].tolist())
        with col2:
            if st.button("Xóa ngay"):
                delete_event(id_to_delete)
                st.success("Đã xóa thành công!")
                time.sleep(1)
                st.rerun()
else:
    st.info("Hiện chưa có lịch trình nào. Hãy thêm thử xem!")

# Footer
st.markdown("---")
st.caption("Đồ án môn học - Xây dựng ứng dụng quản lý lịch trình với NLP Tiếng Việt")