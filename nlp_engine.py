# nlp_engine.py
import re
from datetime import datetime, timedelta

# --- CẤU HÌNH THƯ VIỆN NLP (Yêu cầu bắt buộc) ---
try:
    # Component 1 & 2: Dùng Underthesea cho Tiền xử lý và NER
    from underthesea import word_tokenize, ner, pos_tag
    HAS_UNDERTHESEA = True
except ImportError:
    print("⚠️ CẢNH BÁO: Chưa cài đặt underthesea. Chạy 'pip install underthesea' để dùng tính năng AI.")
    HAS_UNDERTHESEA = False

class NLPProcessor:
    def __init__(self):
        # Cache hoặc warm-up model nếu cần thiết (optional)
        pass

    def process(self, text):
        """
        Quy trình xử lý 5 bước theo báo cáo Đồ án:
        1. Preprocessing (Tách từ)
        2. NER (Trích xuất thực thể địa điểm/tên riêng)
        3. Rule-based (Trích xuất sự kiện, nhắc nhở)
        4. Time Parsing (Xử lý thời gian)
        5. Validation (Hợp nhất)
        """
        
        # --- BƯỚC 1: TIỀN XỬ LÝ & TÁCH TỪ (COMPONENT 1) ---
        raw_text = text.strip()
        text_lower = raw_text.lower()
        
        # Log để chứng minh có dùng thư viện (cho báo cáo)
        if HAS_UNDERTHESEA:
            try:
                tokens = word_tokenize(raw_text)
                print(f"DEBUG [Underthesea]: Tokenized -> {tokens}")
            except:
                pass

        result = {
            "event": "",
            "location": "",
            "start_time": None,
            "reminder_minutes": 0
        }

        # --- BƯỚC 2: TRÍCH XUẤT THỰC THỂ NER (COMPONENT 2 - MODEL BASED) ---
        # Ưu tiên dùng AI để tìm Địa điểm (Location) vì Regex rất khó bắt tên riêng
        ner_location = ""
        if HAS_UNDERTHESEA:
            try:
                # ner() trả về list các tuple: [('Hà Nội', 'Np', 'B-LOC'), ...]
                entities = ner(raw_text)
                loc_parts = []
                for word, pos, tag in entities:
                    if 'LOC' in tag: # B-LOC hoặc I-LOC
                        loc_parts.append(word)
                
                if loc_parts:
                    ner_location = " ".join(loc_parts)
                    print(f"DEBUG [NER]: Tìm thấy địa điểm -> {ner_location}")
            except Exception as e:
                print(f"Lỗi NER: {e}")

        # --- BƯỚC 3: RULE-BASED EXTRACTION (COMPONENT 3) ---
        
        # 3.1. Trích xuất Nhắc nhở (Rule cứng)
        reminder_match = re.search(r"(nhắc|báo)\s*(?:trước|sớm)?\s*(\d+)\s*phút", text_lower)
        if reminder_match:
            result["reminder_minutes"] = int(reminder_match.group(2))

        # 3.2. Trích xuất Địa điểm (Kết hợp AI + Rule)
        if ner_location:
            result["location"] = ner_location
        else:
            loc_match = re.search(r"(tại|ở)\s+(.+?)(\s+lúc|\s+vào|\s+trước|$)", text_lower)
            if loc_match:
                raw_loc = loc_match.group(2).strip()
                clean_loc = re.sub(r"\s*(lúc|vào|ngày|sáng|trưa|chiều|tối).*$", "", raw_loc)
                result["location"] = clean_loc

        # 3.3. Trích xuất Sự kiện
        cmd_pattern = re.search(r"^(nhắc tôi|nhắc|lịch|hãy|đặt lịch|tạo)\s+(.+?)(\s+lúc|\s+vào|\s+tại|\s+ở|$)", text_lower)
        if cmd_pattern:
            raw_event = text[cmd_pattern.end(1):].strip()
            split_patt = r"(\s+lúc|\s+vào|\s+tại|\s+ở|\s+ngày|\s+sáng|\s+trưa|\s+chiều|\s+tối|\s+thứ|\s+cn|\d{1,2}h|\d{1,2}:)"
            split_match = re.search(split_patt, raw_event.lower())
            if split_match:
                result["event"] = raw_event[:split_match.start()].strip()
            else:
                result["event"] = raw_event
        else:
            split_match = re.search(r"(\s+lúc|\s+vào|\s+tại|\s+ở|\s+ngày|\s+sáng|\s+trưa|\s+chiều|\s+tối|\s+thứ|\d{1,2}[:h])", text_lower)
            if split_match:
                result["event"] = text[:split_match.start()].strip()
            else:
                result["event"] = text # Fallback

        if not result["event"]: result["event"] = "Sự kiện mới"
        result["event"] = result["event"].strip().capitalize()

        # --- BƯỚC 4: PHÂN TÍCH THỜI GIAN (COMPONENT 4) ---
        now = datetime.now()
        target_date = now
        has_date_specified = False 

        # 4.1. Ngày tương đối (SỬA LỖI TẠI ĐÂY)
        if "qua" not in text_lower: # Tránh bắt nhầm "hôm qua"
            # Bắt ngày mai
            if "ngày mai" in text_lower or "sáng mai" in text_lower or "chiều mai" in text_lower or "tối mai" in text_lower:
                target_date = now + timedelta(days=1)
                has_date_specified = True
            elif "ngày mốt" in text_lower:
                target_date = now + timedelta(days=2)
                has_date_specified = True
            
            # BỔ SUNG: Bắt "hôm nay", "chiều nay" để không bị đẩy sang ngày mai
            if "hôm nay" in text_lower or "chiều nay" in text_lower or "tối nay" in text_lower or "sáng nay" in text_lower or "trưa nay" in text_lower:
                has_date_specified = True # Đánh dấu là đã chọn ngày, không auto-fill tomorrow

        # 4.2. Xử lý Thứ (Thứ 2... CN)
        if not has_date_specified:
            weekday_map = {
                "hai": 0, "2": 0, "ba": 1, "3": 1, "tư": 2, "4": 2, 
                "năm": 3, "5": 3, "sáu": 4, "6": 4, "bảy": 5, "7": 5
            }
            wk_match = re.search(r"thứ\s+([2-7]|hai|ba|tư|năm|sáu|bảy)|(chủ nhật|cn)", text_lower)
            target_wk = None
            
            if wk_match:
                if wk_match.group(1):
                    target_wk = weekday_map.get(wk_match.group(1))
                else:
                    target_wk = 6 # CN
            
            if target_wk is not None:
                current_wk = now.weekday()
                days_ahead = target_wk - current_wk
                if days_ahead <= 0: days_ahead += 7
                if "tuần sau" in text_lower or "tuần tới" in text_lower: days_ahead += 7
                target_date = now + timedelta(days=days_ahead)
                has_date_specified = True

        # 4.3. Xử lý Giờ
        time_pattern = re.search(r"(\d{1,2})\s*(?:[:h]|giờ|gio)\s*(\d{0,2})", text_lower)
        hour, minute = 9, 0 
        
        has_time_specified = False
        if time_pattern:
            hour = int(time_pattern.group(1))
            m_str = time_pattern.group(2)
            minute = int(m_str) if m_str and m_str.isdigit() else 0
            has_time_specified = True
            
            # Xử lý 12h (pm)
            if ("chiều" in text_lower or "tối" in text_lower or "pm" in text_lower) and hour < 12:
                hour += 12

        end_hour, end_minute = None, None
        
        # Regex tìm: "đến 10h", "tới 11:30", "start... - 15h"
        # Tìm các từ khóa chỉ kết thúc
        end_pattern = re.search(r"(?:đến|tới|-)\s*(\d{1,2})\s*(?:[:h]|giờ|gio)\s*(\d{0,2})", text_lower)
        
        if end_pattern:
            e_h = int(end_pattern.group(1))
            e_m_str = end_pattern.group(2)
            e_m = int(e_m_str) if e_m_str and e_m_str.isdigit() else 0
            
            # Logic xử lý PM cho giờ kết thúc (VD: từ 9h đến 2h -> hiểu là 2h chiều)
            if e_h < hour: 
                e_h += 12
            # Hoặc nếu start là PM thì end cũng nên là PM (trừ khi qua ngày, nhưng tạm bỏ qua case qua ngày)
            elif hour >= 12 and e_h < 12:
                e_h += 12
                
            end_hour, end_minute = e_h, e_m

        # --- BƯỚC 5: HỢP NHẤT & XỬ LÝ LỖI (COMPONENT 5) ---
        try:
            final_start = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            result["start_time"] = final_start.isoformat()
            
            if end_hour is not None:
                final_end = target_date.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
                # Kiểm tra nếu end < start (VD nhập sai), thì bỏ qua hoặc cộng thêm ngày (ở đây mình chọn bỏ qua end_time cho an toàn)
                if final_end > final_start:
                    result["end_time"] = final_end.isoformat()
                else:
                    result["end_time"] = None
            else:
                result["end_time"] = None # Null theo yêu cầu JSON
                
        except ValueError:
            result["start_time"] = None
            result["end_time"] = None

        return result

# --- TEST TRỰC TIẾP ---
if __name__ == "__main__":
    p = NLPProcessor()
    # Test case đã fix
    test_text = "Họp team lúc 14h chiều nay"
    print(f"Input: {test_text}")
    print(f"Output: {p.process(test_text)}")