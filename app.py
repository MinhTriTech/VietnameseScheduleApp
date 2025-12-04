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
# PHẦN 1: HỆ THỐNG NHẮC NHỞ (GIỮ NGUYÊN)
# ---------------------------------------------------------
def check_reminders_loop():
    while True:
        try:
            events = get_all_events()
            now = datetime.now()
            for ev in events:
                ev_name, time_str, remind_min = ev[1], ev[2], ev[5] if ev[5] else 0
                if time_str:
                    event_time = datetime.fromisoformat(time_str)
                    remind_time = event_time - timedelta(minutes=remind_min)
                    if 0 <= (now - remind_time).total_seconds() <= 35:
                        msg = f"Sắp đến: {ev_name}\nLúc: {event_time.strftime('%H:%M')}"
                        
                        # Chỉ dùng MessageBox trên Windows
                        if platform.system() == "Windows":
                            ctypes.windll.user32.MessageBoxW(0, msg, "⏰ NHẮC LỊCH", 0x40 | 0x1)
                        else:
                            print(f"ALARM: {msg}") # Log ra terminal nếu không phải Windows
        except Exception:
            pass
        time.sleep(30)

if 'monitor_started' not in st.session_state:
    t = threading.Thread(target=check_reminders_loop, daemon=True)
    t.start()
    st.session_state['monitor_started'] = True

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
                    
                    if extracted_data.get('start_time'):
                        event_time = datetime.fromisoformat(extracted_data['start_time'])
                        now = datetime.now()
                        
                        # Import hàm check conflict mới
                        from database import check_overlap
                        is_conflict, conflict_name = check_overlap(extracted_data['start_time'], extracted_data.get('end_time'))
                        
                        # LOGIC KIỂM TRA: Quá khứ HOẶC Trùng lịch
                        warning_msg = ""
                        if event_time < now:
                            warning_msg = f"⚠️ Sự kiện này đã qua: **{event_time.strftime('%H:%M %d-%m-%Y')}**"
                        
                        if is_conflict:
                            conflict_txt = f"\n\n⛔ **TRÙNG LỊCH:** Đang cấn với sự kiện **'{conflict_name}'**."
                            warning_msg += conflict_txt
                        
                        # Nếu có cảnh báo (Quá khứ hoặc Trùng) -> Đưa vào Pending để xác nhận
                        if warning_msg:
                            extracted_data['warning_msg'] = warning_msg # Lưu lời nhắc để hiển thị
                            st.session_state['pending_event'] = extracted_data
                            st.rerun()
                        else:
                            # Tương lai & Không trùng -> Lưu luôn
                            add_event(extracted_data)
                            # ... (Giữ nguyên phần thêm vào recent_added) ...
                            new_card = {
                                "event": extracted_data.get('event'),
                                "start_time": extracted_data.get('start_time'),
                                "end_time": extracted_data.get('end_time'), # Thêm dòng này
                                "location": extracted_data.get('location'),
                                "reminder_minutes": extracted_data.get('reminder_minutes')
                            }
                            st.session_state['recent_added'].append(new_card)
                            st.success(f"✅ Xong: {extracted_data['event']}")
                            time.sleep(0.5)
                            st.rerun()
                    else:
                        st.error("⚠️ Không xác định được thời gian!")

    # Hiển thị số lượng sự kiện nhỏ gọn
    st.caption(f"🗓️ Sự kiện sắp tới: **{len(db_events)}**")

    # Hiển thị các mục vừa thêm nhanh (nằm dưới form)
    if st.session_state.get('recent_added'):
        st.markdown("---")
        st.caption("🔔 Mục vừa thêm (Quick-add)")
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
            # Chỉ hiển thị nếu có thời gian (ev[2] là start_time)
            if ev[2]: 
                calendar_events.append({
                    "id": ev[0],
                    "title": f"{ev[1]} ({ev[3]})" if ev[3] else ev[1],
                    "start": ev[2],
                    # Tô màu đỏ nếu là sự kiện "họp", ngược lại màu xanh
                    "backgroundColor": "#3788d8" if "họp" not in ev[1].lower() else "#d8374d",
                    "borderColor": "transparent"
                })
        
        # Chuyển đổi list Python sang chuỗi JSON để JS đọc được
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
                    
                    /* Tùy chỉnh nút bấm cho gọn */
                    .fc-button {{ padding: 0.2em 0.5em !important; }}
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
                            // [CẬP NHẬT] Thêm 'timeGridDay' vào danh sách nút bên phải
                            headerToolbar: {{ 
                                left: 'prev,next today', 
                                center: 'title', 
                                right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek' 
                            }},
                            buttonText: {{
                                day: 'Ngày',    // Đổi tên hiển thị nút 'timeGridDay' thành 'Ngày'
                                month: 'Tháng',
                                week: 'Tuần',
                                list: 'Lịch biểu'
                            }},
                            events: {events_json},
                            height: '100%', 
                            expandRows: true,
                            nowIndicator: true, // Hiển thị vạch đỏ chỉ giờ hiện tại
                            eventTimeFormat: {{ hour: '2-digit', minute: '2-digit', hour12: false }},
                            slotMinTime: "00:00:00", // Bắt đầu lịch ngày từ 0h sáng
                            slotMaxTime: "23:59:59"  // Kết thúc lúc 11h59 đêm
                        }});
                        calendar.render();
                    }});
                </script>
            </body>
        </html>
        """
        # Hiển thị lịch
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
            search_term = st.text_input("🔍 Tìm nhanh", placeholder="Nhập từ khóa...", label_visibility="collapsed")
            
            # [FIX] Thêm cột "Thời gian kết thúc" vào cuối danh sách columns
            df = pd.DataFrame(db_events, columns=["ID", "Sự kiện", "Thời gian bắt đầu", "Thời gian kết thúc", "Địa điểm", "Nhắc (phút)"])
            df["Thời gian bắt đầu"] = df["Thời gian bắt đầu"].apply(
                lambda x: datetime.fromisoformat(x).strftime("%H:%M %d-%m-%Y") if x else ""
            )
            df["Thời gian kết thúc"] = df["Thời gian kết thúc"].apply(
                lambda x: datetime.fromisoformat(x).strftime("%H:%M %d-%m-%Y") if x else ""
            )

            if search_term:
                df = df[df["Sự kiện"].str.contains(search_term, case=False, na=False)]

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
                    new_loc = c_e2.text_input("Địa điểm", value=current_row["Địa điểm"] if current_row["Địa điểm"] else "")
                    
                    c_e3, c_e4 = st.columns(2)
                    new_start_time = c_e3.text_input("Thời gian bắt đầu (Ví dụ: 2025-12-05T14:30)", value=current_row["Thời gian bắt đầu"], help="Format: YYYY-MM-DDTHH:MM:SS")
                    new_end_time = c_e4.text_input("Thời gian kết thúc (Ví dụ: 2025-12-05T15:30)", value=current_row["Thời gian kết thúc"], help="Format: YYYY-MM-DDTHH:MM:SS")
                    
                    c_e5, c_e6 = st.columns(2)
                    # [FIX] Kiểm tra nếu giá trị là NaN thì gán bằng 0 để tránh lỗi crash
                    val_remind = current_row["Nhắc (phút)"]
                    safe_remind = int(val_remind) if pd.notna(val_remind) else 0
                    
                    new_remind = c_e5.number_input("Nhắc trước (phút)", value=safe_remind, min_value=0)
                    
                    # Nút Cập nhật
                    if st.form_submit_button("Lưu thay đổi", type="primary", use_container_width=True):
                        from database import update_event
                        try:
                            datetime.fromisoformat(new_start_time)
                            datetime.fromisoformat(new_end_time)
                            update_event(selected_id, new_name, new_start_time, new_end_time, new_loc, new_remind)
                            st.success("✅ Đã cập nhật thành công!")
                            time.sleep(2)
                            st.rerun()
                        except ValueError:
                            st.error("❌ Lỗi: Thời gian không đúng định dạng ISO.")
                
                st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
                
                # Nút Xóa (Để ngoài form)
                col_del_1, col_del_2 = st.columns([0.7, 0.3])
                with col_del_2:
                    if st.button("Xóa sự kiện này", type="secondary", use_container_width=True):
                         delete_event(selected_id)
                         st.toast("Đã xóa sự kiện!", icon="🗑️")
                         time.sleep(2)
                         st.rerun()
        else:
            st.warning("Danh sách trống. Vui lòng thêm sự kiện hoặc nhập dữ liệu trước.")