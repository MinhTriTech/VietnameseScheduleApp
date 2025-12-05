import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import time
import threading
import ctypes
from datetime import datetime, timedelta
import platform

# --- IMPORT MODULE ---
from database import init_db, add_event, get_all_events, delete_event
from nlp_engine import NLPProcessor

# Khởi tạo
init_db()
nlp = NLPProcessor()
# Lưu các mục vừa thêm nhanh để hiển thị ngay phía dưới form
if 'recent_added' not in st.session_state:
    st.session_state['recent_added'] = []

# ---------------------------------------------------------
# PHẦN 1: HỆ THỐNG NHẮC NHỞ (ĐÃ NÂNG CẤP)
# ---------------------------------------------------------

# Biến global cho thread (Thay set bằng dict để lưu trạng thái)
# Cấu trúc: { event_id: "timestamp_string" }
notified_state = {} 

def check_reminders_loop():
    while True:
        try:
            events = get_all_events()
            now = datetime.now()
            
            # Danh sách các ID hiện có trong DB (dùng để dọn dẹp rác)
            current_db_ids = set()

            for ev in events:
                # Cấu trúc ev: (0: id, 1: event_name, 2: start_time, 3: end_time, 4: loc, 5: remind)
                ev_id = ev[0]
                ev_name = ev[1]
                time_str = ev[2]
                remind_min = ev[5] if ev[5] else 0
                loc = ev[4] if ev[4] else ""
                
                current_db_ids.add(ev_id)

                if time_str:
                    event_time = datetime.fromisoformat(time_str)
                    remind_time = event_time - timedelta(minutes=remind_min)
                    
                    # Tính khoảng cách thời gian (giây)
                    diff_seconds = (now - remind_time).total_seconds()
                    
                    # Tạo "chữ ký" duy nhất cho trạng thái nhắc nhở này
                    # Nếu người dùng đổi giờ (time_str) hoặc đổi phút nhắc (remind_min), chữ ký sẽ thay đổi
                    current_signature = f"{time_str}_{remind_min}"

                    # LOGIC KIỂM TRA MỚI:
                    # 1. Đúng thời điểm (trong vòng 60s)
                    # 2. VÀ (Chưa từng báo ID này HOẶC Đã báo nhưng thông tin giờ/nhắc nhở đã bị thay đổi)
                    if 0 <= diff_seconds <= 60:
                        last_notified_sig = notified_state.get(ev_id)
                        
                        if last_notified_sig != current_signature:
                            location_txt = f"\nTại: {loc}" if loc else ""
                            msg = f"Sự kiện: {ev_name}{location_txt}\nDiễn ra lúc: {event_time.strftime('%H:%M')}"
                            
                            # Chỉ dùng MessageBox trên Windows
                            if platform.system() == "Windows":
                                flags = 0x40 | 0x1000 | 0x40000 | 0x10000
                                ctypes.windll.user32.MessageBoxW(0, msg, "⏰ NHẮC LỊCH (QUAN TRỌNG)", flags)
                            else:
                                print(f"ALARM: {msg}") 
                            
                            # Cập nhật trạng thái đã nhắc cho ID này với chữ ký mới
                            notified_state[ev_id] = current_signature
            
            # Dọn dẹp bộ nhớ: Xóa các key trong notified_state nếu ID đó không còn trong DB (đã bị xóa)
            # Giúp dictionary không bị phình to vô hạn nếu chạy lâu dài
            for old_id in list(notified_state.keys()):
                if old_id not in current_db_ids:
                    del notified_state[old_id]
            
        except Exception:
            pass
        
        # Delay 5 giây
        time.sleep(5)

# ... (Đoạn hàm check_reminders_loop giữ nguyên) ...

# ---------------------------------------------------------
# KHỞI TẠO LUỒNG CHẠY NGẦM (FIX LỖI SPAM THREAD)
# ---------------------------------------------------------
# Đặt tên riêng cho thread để nhận diện
THREAD_NAME = "ScheduleReminderThread"

# Kiểm tra trong toàn bộ process xem có thread nào tên như vậy đang chạy không
is_running = False
for t in threading.enumerate():
    if t.name == THREAD_NAME:
        is_running = True
        break

if not is_running:
    # Nếu chưa chạy thì mới khởi tạo
    t = threading.Thread(target=check_reminders_loop, name=THREAD_NAME, daemon=True)
    t.start()
    print("--- ✅ Thread Nhắc nhở đã khởi động ---")
else:
    print("--- ⚠️ Thread Nhắc nhở đang chạy, bỏ qua khởi tạo lại ---")

# (Bỏ đoạn if 'monitor_started' not in st.session_state cũ đi)

# ---------------------------------------------------------
# PHẦN 2: CẤU HÌNH GIAO DIỆN & CSS (TỐI ƯU ONE-SCREEN)
# ---------------------------------------------------------
st.set_page_config(page_title="Trợ lý lịch trình AI", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.stMainBlockContainer {
    padding-bottom: 2rem !important;
}
/* 1. Xóa padding mặc định của Streamlit */
div[data-testid="stAppViewContainer"] > section > div {
    padding-top: 0rem !important;
    padding-bottom: 0rem !important;
}

/* 2. Ẩn header thật sự */
div[data-testid="stHeader"] {
    height: 0px !important;
    padding: 0px !important;
}

/* 3. Xóa margin của tiêu đề */
h1, h2, h3, [data-testid="stMarkdownContainer"] h1 {
    margin-top: 0rem !important;
    padding-top: 0rem !important;
}

/* 4. Giữ nguyên sidebar tắt */
section[data-testid="stSidebar"] > div {display: none;}

/* 5. Tối ưu tabs sát lên trên */
.stTabs { margin-top: 0rem !important; }

/* 6. Cố định chiều cao toàn trang - không cuộn */
body, html {
    overflow: hidden !important;
}
</style>
""", unsafe_allow_html=True)


# Tiêu đề ứng dụng
st.title("🗓️ Trợ lý lịch trình thông minh")

# Chia layout
c1, c2 = st.columns([0.25, 0.75], gap="small")
db_events = get_all_events()

# ---------------------------------------------------------
# CỘT TRÁI: NHẬP LIỆU (Gọn gàng hơn)
# ---------------------------------------------------------
with c1:
    with st.container(border=True):
        st.caption("**Thêm sự kiện**")

        # --- LOGIC XÁC NHẬN (GIỮ LẠI ĐOẠN NÀY VÌ NÓ XỊN HƠN) ---
        if 'pending_event' in st.session_state:
            pending = st.session_state['pending_event']
            
            # [MỚI]: Chuyển đổi format thời gian cho dễ đọc
            try:
                dt_obj = datetime.fromisoformat(pending['start_time'])
                vn_time_str = dt_obj.strftime("%H:%M:%S %d-%m-%Y")
            except ValueError:
                vn_time_str = pending['start_time']

            # Lấy thông báo lỗi (nếu có) hoặc dùng mặc định
            warning_text = pending.get('warning_msg', f"⚠️ Sự kiện này đã qua: **{vn_time_str}**")
            
            st.warning(f"{warning_text}\n\nBạn có chắc muốn lưu?")
            
            col_yes, col_no = st.columns(2)
            # Thêm key để tránh lỗi trùng lặp nếu lỡ có nút khác giống tên
            if col_yes.button("✅ Vẫn lưu", use_container_width=True, key="btn_confirm_yes"):
                add_event(pending)
                
                new_card = {
                    "event": pending.get('event', 'Sự kiện mới'),
                    "start_time": pending.get('start_time'),
                    "end_time": pending.get('end_time', None),
                    "location": pending.get('location', ''),
                    "reminder_minutes": pending.get('reminder_minutes', 0)
                }
                st.session_state['recent_added'].append(new_card)
                
                del st.session_state['pending_event']
                st.success("Đã lưu sự kiện!")
                time.sleep(0.5)
                st.rerun()
                
            if col_no.button("❌ Hủy", use_container_width=True, key="btn_confirm_no"):
                del st.session_state['pending_event']
                st.rerun()

        # --- FORM NHẬP LIỆU ---
        # Chỉ hiện form khi không có sự kiện nào đang chờ xác nhận
        else:
            with st.form("add_form", clear_on_submit=True):
                user_input = st.text_input("Input", placeholder="VD: Họp 9h sáng nay...", label_visibility="collapsed")
                submitted = st.form_submit_button("Thêm", use_container_width=True, type="primary")
                
                if submitted and user_input:
                    with st.spinner("⏳ Đang xử lý..."):
                        extracted_data = nlp.process(user_input)
                    
                    # [MỚI] Ưu tiên kiểm tra lỗi cụ thể từ NLP trả về trước
                    if extracted_data.get('error'):
                        st.error(f"{extracted_data['error']}")
                    
                    # ... (Phần hiển thị lỗi extracted_data.get('error') giữ nguyên) ...
                    
                    elif extracted_data.get('start_time'):
                        # event_time = datetime.fromisoformat(extracted_data['start_time']) # <-- Dòng này không cần check quá khứ nữa
                        
                        # Import hàm check conflict
                        from database import check_overlap
                        is_conflict, conflict_name = check_overlap(extracted_data['start_time'], extracted_data.get('end_time'))
                        
                        warning_msg = ""
                        # [ĐÃ XÓA] Đoạn check if event_time < now ...
                        
                        if is_conflict:
                            # [MỚI] Xử lý hiển thị danh sách sự kiện trùng
                            # conflict_names bây giờ là một list (VD: ['Họp A', 'Họp B'])
                            # Nối chúng lại thành chuỗi: "Họp A, Họp B"
                            names_str = ", ".join([f"**'{n}'**" for n in conflict_name])
                            
                            conflict_txt = f"\n\n⛔ **TRÙNG LỊCH:** Đang cấn với các sự kiện: {names_str}."
                            warning_msg += conflict_txt
                        
                        # ... (Giữ nguyên logic conflict) ...
                        
                        if warning_msg:
                            extracted_data['warning_msg'] = warning_msg
                            st.session_state['pending_event'] = extracted_data
                            st.rerun()
                        else:
                            add_event(extracted_data)
                            new_card = {
                                "event": extracted_data.get('event'),
                                "start_time": extracted_data.get('start_time'),
                                "end_time": extracted_data.get('end_time'),
                                "location": extracted_data.get('location'),
                                "reminder_minutes": extracted_data.get('reminder_minutes')
                            }
                            st.session_state['recent_added'].append(new_card)
                            st.success(f"✅ Xong: {extracted_data['event']}")
                            time.sleep(0.5)
                            st.rerun()
                            
                    else:
                        # Trường hợp không có lỗi cụ thể nhưng cũng không có start_time (VD: nhập "Đi chơi")
                        st.error("Không xác định được thời gian! Vui lòng nhập rõ ngày giờ.")

    # Hiển thị số lượng sự kiện nhỏ gọn
    # [CẬP NHẬT] Tính toán chỉ đếm sự kiện trong tương lai
    now = datetime.now()
    future_count = 0
    for ev in db_events:
        # ev[2] là start_time
        if ev[2]:
            try:
                ev_time = datetime.fromisoformat(ev[2])
                # Chỉ đếm nếu thời gian bắt đầu lớn hơn thời gian hiện tại
                if ev_time > now:
                    future_count += 1
            except ValueError:
                continue

    # Hiển thị số lượng sự kiện thực tế sắp tới
    # ... (Đoạn code đếm future_count phía trên giữ nguyên) ...
    st.caption(f"🗓️ Sự kiện sắp tới: **{future_count}**")

    # --- [MỚI] ĐỒNG HỒ REAL-TIME (Dùng HTML/JS để nhảy giây) ---
    # Styles: Font chữ hệ thống, căn chỉnh gọn gàng
    clock_html = """
    <div style="
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        padding: 10px 0px;
        text-align: left;
    ">
        <div style="
            font-size: 2.2em; 
            font-weight: 700; 
            color: #FF4B4B; /* Màu đỏ chủ đạo của Streamlit */
            line-height: 1;
        ">
            <span id="time">--:--:--</span>
        </div>
        <div style="
            font-size: 0.9em; 
            color: #555; 
            margin-top: 5px; 
            text-transform: capitalize;
            font-weight: 500;
        ">
            <span id="date">...</span>
        </div>
    </div>

    <script>
    function updateClock() {
        const now = new Date();
        
        // Cấu hình định dạng giờ Việt Nam
        const optionsTime = { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' };
        const optionsDate = { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' };
        
        // Lấy giờ theo locale vi-VN
        const timeStr = now.toLocaleTimeString('vi-VN', optionsTime);
        const dateStr = now.toLocaleDateString('vi-VN', optionsDate);

        document.getElementById('time').innerText = timeStr;
        document.getElementById('date').innerText = dateStr;
    }
    
    // Cập nhật mỗi 1000ms (1 giây)
    setInterval(updateClock, 1000);
    updateClock(); // Chạy ngay lần đầu
    </script>
    """
    
    # Render HTML với chiều cao cố định để không bị thanh cuộn
    components.html(clock_html, height=100)

    # Hiển thị các mục vừa thêm nhanh (nằm dưới form)
    if st.session_state.get('recent_added'):
        st.markdown("---")
        st.caption("Mục vừa thêm")
        # Hiển thị mới nhất ở trên
        for card in reversed(st.session_state['recent_added']):
            with st.container():
                st.json(card)
                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# CỘT PHẢI: TABS (FULL HEIGHT)
# ---------------------------------------------------------
# ---------------------------------------------------------
# CỘT PHẢI: TABS (FULL HEIGHT)
# ---------------------------------------------------------
with c2:
    # [CẬP NHẬT] Chia thành 3 Tabs: Lịch biểu, Danh sách, Chỉnh sửa
    tab_calendar, tab_list, tab_edit = st.tabs(["🗓️ Lịch biểu", "📋 Danh sách", "🛠️ Chỉnh sửa"])
    
    # --- TAB 1: CALENDAR (GIỮ NGUYÊN) ---
    # --- TAB 1: CALENDAR (Đã thêm chế độ xem Ngày) ---
    with tab_calendar:
        calendar_events = []
        for ev in db_events:
            # Cấu trúc ev sau khi sửa DB: 
            # 0: id, 1: name, 2: start, 3: end, 4: loc, 5: remind
            
            if ev[2]: # Nếu có start_time
                # Tạo title hiển thị: "Tên sự kiện (Địa điểm)"
                # Lưu ý: FullCalendar sẽ tự động ghép giờ vào trước Title
                event_title = f"{ev[1]}"
                if ev[4]: # Nếu có địa điểm thì thêm vào sau tên
                    event_title += f" ({ev[4]})"

                event_item = {
                    "id": ev[0],
                    "title": event_title,
                    "start": ev[2],
                    "backgroundColor": "#3788d8" if "họp" not in ev[1].lower() else "#d8374d",
                    "borderColor": "transparent"
                }
                
                # [MỚI] Thêm thời gian kết thúc nếu có
                # FullCalendar sẽ tự động hiển thị dạng "09:00 - 10:30 Tên sự kiện"
                if ev[3]: 
                    event_item["end"] = ev[3]
                
                calendar_events.append(event_item)
        
        events_json = json.dumps(calendar_events)

        calendar_html = f"""
        <!doctype html>
        <html>
            <head>
                <meta charset='utf-8' />
                <link href='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.css' rel='stylesheet' />
                <script src='https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.js'></script>
                <script src="https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/locales/vi.js"></script>
                <style>
                    html, body {{ margin: 0; padding: 0; height: 100%; overflow: hidden; font-family: sans-serif; }}
                    #calendar {{ height: 100%; width: 100%; }}
                    .fc {{ font-size: 0.85em; }}
                    .fc-header-toolbar {{ margin-bottom: 0.5em !important; }}
                    .fc-toolbar-title {{ font-size: 1.1em !important; }}
                    .fc-button {{ padding: 0.2em 0.5em !important; }}
                    
                    /* Tùy chỉnh hiển thị sự kiện trong Month View để hiện cả giờ kết thúc */
                    .fc-event-time {{ font-weight: bold; margin-right: 4px; }}
                </style>
            </head>
            <body>
                <div id='calendar'></div>
                <script>
                    document.addEventListener('DOMContentLoaded', function() {{
                        var calendarEl = document.getElementById('calendar');
                        var calendar = new FullCalendar.Calendar(calendarEl, {{
                            locale: 'vi',
                            initialView: 'dayGridMonth',
                            headerToolbar: {{ 
                                left: 'prev,next today', 
                                center: 'title', 
                                right: 'dayGridMonth,timeGridWeek,timeGridDay' 
                            }},
                            buttonText: {{
                                day: 'Ngày',
                                month: 'Tháng',
                                week: 'Tuần',
                            }},
                            events: {events_json},
                            height: '100%', 
                            expandRows: true,
                            nowIndicator: true,
                            // [QUAN TRỌNG] Cấu hình hiển thị giờ
                            eventTimeFormat: {{
                                hour: '2-digit',
                                minute: '2-digit',
                                hour12: false,
                                meridiem: false
                            }},
                            displayEventEnd: true, // Ép hiển thị giờ kết thúc (VD: 09:00 - 10:00)
                            slotMinTime: "00:00:00",
                            slotMaxTime: "23:59:59"
                        }});
                        calendar.render();
                    }});
                </script>
            </body>
        </html>
        """
        components.html(calendar_html, height=500, scrolling=False)

    # --- TAB 2: DANH SÁCH & IMPORT/EXPORT (Chỉ Xem & Nhập xuất) ---
    with tab_list:
        # KHU VỰC NHẬP/XUẤT DỮ LIỆU
        with st.expander("Nhập/xuất dữ liệu", expanded=False):
            st.caption("**Xuất dữ liệu**")
            col_template, col_backup = st.columns(2)
            
            # A. Xuất File Mẫu
            with col_template:
                sample_data = [{
                    "event": "Họp nhóm đồ án",
                    "start_time": "2025-11-01T10:00:00",
                    "end_time": None,
                    "location": "Phòng 302",
                    "reminder_minutes": 15
                }]
                json_sample = json.dumps(sample_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="📄 Tải file mẫu",
                    data=json_sample,
                    file_name="mau_nhap_lieu.json",
                    mime="application/json",
                    use_container_width=True
                )

            # B. Xuất Backup
            with col_backup:
                export_data = []
                if db_events:
                    for row in db_events:
                        item = {
                            "event": row[1],
                            "start_time": row[2],
                            "end_time": row[3],
                            "location": row[4] if row[4] else "",
                            "reminder_minutes": row[5] if row[5] else 0
                        }
                        export_data.append(item)
                    json_backup = json.dumps(export_data, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="📄 Tải lịch trình hiện có",
                        data=json_backup,
                        file_name="full_backup.json",
                        mime="application/json",
                        use_container_width=True,
                        type="primary"
                    )
                else:
                    st.button("📄 Tải lịch trình hiện có", disabled=True, use_container_width=True)

            st.markdown("---")

            # Nhập dữ liệu
            st.caption("**Nhập dữ liệu**")
            uploaded_file = st.file_uploader("Chọn file JSON", type=['json'], label_visibility="collapsed")
            if uploaded_file is not None:
                if st.button("🚀 Bắt đầu nhập", use_container_width=True):
                    try:
                        imported_data = json.load(uploaded_file)
                        if isinstance(imported_data, list):
                            count = 0
                            valid_keys = ["event", "start_time"]
                            progress_bar = st.progress(0)
                            total = len(imported_data)
                            for i, item in enumerate(imported_data):
                                if all(k in item for k in valid_keys) and item["start_time"]:
                                    add_event(item) 
                                    count += 1
                                if total > 0: progress_bar.progress((i + 1) / total)
                            st.success(f"✅ Đã nhập {count} sự kiện!")
                            time.sleep(1.0)
                            st.rerun()
                        else:
                            st.error("⚠️ File JSON lỗi format.")
                    except Exception as e:
                        st.error(f"❌ Lỗi: {e}")

        # HIỂN THỊ DANH SÁCH (READ-ONLY)
        if db_events:
            st.markdown("#### 📋 Danh sách sự kiện")
            search_term = st.text_input("🔍 Tìm nhanh", placeholder="Nhập từ khóa... (tên sự kiện hoặc ngày bắt đầu hoặc địa điểm)", label_visibility="collapsed")
            
            # [FIX] Thêm cột "Thời gian kết thúc" vào cuối danh sách columns
            df = pd.DataFrame(db_events, columns=["ID", "Sự kiện", "Thời gian bắt đầu", "Thời gian kết thúc", "Địa điểm", "Nhắc (phút)"])
            df["Thời gian bắt đầu"] = df["Thời gian bắt đầu"].apply(
                lambda x: datetime.fromisoformat(x).strftime("%H:%M %d-%m-%Y") if x else ""
            )
            df["Thời gian kết thúc"] = df["Thời gian kết thúc"].apply(
                lambda x: datetime.fromisoformat(x).strftime("%H:%M %d-%m-%Y") if x else ""
            )

            if search_term:
                df = df[
                    df["Sự kiện"].str.contains(search_term, case=False, na=False) |
                    df["Thời gian bắt đầu"].str.contains(search_term, case=False, na=False) |
                    df["Địa điểm"].str.contains(search_term, case=False, na=False)
                ]

            st.dataframe(
                df[["ID", "Sự kiện", "Thời gian bắt đầu", "Thời gian kết thúc", "Địa điểm", "Nhắc (phút)"]], 
                height=400, # Tăng chiều cao vì đã bỏ phần edit ở dưới
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "ID": st.column_config.NumberColumn(width="small"),
                    "Sự kiện": st.column_config.TextColumn(width="large"),
                    "Thời gian": st.column_config.TextColumn(width="medium"),
                }
            )
        else:
            st.info("Chưa có sự kiện nào.")

    # --- TAB 3: CHỈNH SỬA (QUẢN LÝ RIÊNG) ---
    with tab_edit:
        if db_events:
            # Cần tạo lại DF ở đây để lấy dữ liệu cho form
            # [FIX] Thêm cột "Thời gian kết thúc" tương tự
            df_edit = pd.DataFrame(db_events, columns=["ID", "Sự kiện", "Thời gian bắt đầu", "Thời gian kết thúc", "Địa điểm", "Nhắc (phút)"])
            
            # Tạo list hiển thị trong Selectbox cho dễ chọn: "ID - Tên sự kiện"
            options = df_edit.apply(lambda x: f"{x['ID']} - {x['Sự kiện']}", axis=1).tolist()
            selected_option = st.selectbox("Chọn sự kiện cần sửa/xóa:", options)
            
            if selected_option:
                # Lấy ID từ chuỗi "ID - Tên"
                selected_id = int(selected_option.split(" - ")[0])
                current_row = df_edit[df_edit["ID"] == selected_id].iloc[0]
                
                st.markdown("---")
                with st.form("edit_form_tab3"):
                    st.caption(f"Đang chỉnh sửa ID: **{selected_id}**")
                    
                    c_e1, c_e2 = st.columns(2)
                    new_name = c_e1.text_input("Tên sự kiện", value=current_row["Sự kiện"])
                    
                    # Xử lý an toàn cho Địa điểm
                    val_loc = current_row["Địa điểm"]
                    safe_loc = val_loc if pd.notna(val_loc) and val_loc else ""
                    new_loc = c_e2.text_input("Địa điểm", value=safe_loc)
                    
                    c_e3, c_e4 = st.columns(2)
                    
                    # --- [LOGIC MỚI] XỬ LÝ HIỂN THỊ THỜI GIAN VIỆT NAM ---
                    
                    # 1. Xử lý Start Time (ISO -> VN Format)
                    try:
                        db_start_iso = current_row["Thời gian bắt đầu"]
                        # Chuyển từ ISO sang datetime object
                        start_dt_obj = datetime.fromisoformat(db_start_iso)
                        # Format thành chuỗi dễ đọc: 14:30 05-12-2025
                        start_val_display = start_dt_obj.strftime("%H:%M %d-%m-%Y")
                    except (ValueError, TypeError):
                        start_val_display = ""

                    new_start_time_vn = c_e3.text_input(
                        "Thời gian bắt đầu", 
                        value=start_val_display, 
                        help="Nhập theo định dạng: Giờ:Phút Ngày-Tháng-Năm (VD: 14:30 05-12-2025)"
                    )
                    
                    # 2. Xử lý End Time (ISO -> VN Format)
                    val_end = current_row["Thời gian kết thúc"]
                    end_val_display = ""
                    if pd.notna(val_end) and val_end:
                        try:
                            end_dt_obj = datetime.fromisoformat(val_end)
                            end_val_display = end_dt_obj.strftime("%H:%M %d-%m-%Y")
                        except ValueError:
                            pass
                    
                    new_end_time_vn = c_e4.text_input(
                        "Thời gian kết thúc (nếu có)", 
                        value=end_val_display, 
                        help="Để trống nếu không có. Định dạng: HH:MM DD-MM-YYYY"
                    )
                    
                    c_e5, c_e6 = st.columns(2)
                    val_remind = current_row["Nhắc (phút)"]
                    safe_remind = int(val_remind) if pd.notna(val_remind) else 0
                    
                    new_remind = c_e5.number_input("Nhắc trước (phút)", value=safe_remind, min_value=0)
                    
                    # Nút Cập nhật
                    if st.form_submit_button("Lưu thay đổi", type="primary", use_container_width=True):
                        from database import update_event
                        try:
                            # --- [LOGIC MỚI] VALIDATE & CONVERT NGƯỢC VỀ ISO ---
                            
                            # 1. Validate & Convert Start Time
                            # Dùng strptime để ép kiểu theo format Việt Nam
                            parsed_start = datetime.strptime(new_start_time_vn, "%H:%M %d-%m-%Y")
                            final_start_iso = parsed_start.isoformat()
                            
                            # 2. Validate & Convert End Time (nếu có nhập)
                            final_end_iso = None
                            if new_end_time_vn and new_end_time_vn.strip():
                                parsed_end = datetime.strptime(new_end_time_vn, "%H:%M %d-%m-%Y")
                                
                                # Kiểm tra logic: End phải lớn hơn Start
                                if parsed_end <= parsed_start:
                                    st.error("❌ Lỗi: Thời gian kết thúc phải diễn ra sau thời gian bắt đầu!")
                                    st.stop() # Dừng xử lý
                                    
                                final_end_iso = parsed_end.isoformat()
                            
                            # 3. Lưu vào DB (Lúc này đã là chuẩn ISO)
                            update_event(selected_id, new_name, final_start_iso, final_end_iso, new_loc, new_remind)
                            st.toast("Đã cập nhật thành công!", icon="✅")
                            time.sleep(2)
                            st.rerun()
                            
                        except ValueError:
                            st.error("❌ Lỗi định dạng ngày giờ! Vui lòng nhập đúng mẫu: HH:MM DD-MM-YYYY (Ví dụ: 09:30 06-12-2025)")

                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                
                # Nút Xóa (Để ngoài form)
                col_del_1, col_del_2 = st.columns([0.7, 0.3])
                with col_del_2:
                    if st.button("Xóa sự kiện này", type="secondary", use_container_width=True):
                         from database import delete_event
                         delete_event(selected_id)
                         st.toast("Đã xóa sự kiện!", icon="🗑️")
                         time.sleep(2)
                         st.rerun()
        else:
            st.warning("Danh sách trống. Vui lòng thêm sự kiện hoặc nhập dữ liệu trước.")