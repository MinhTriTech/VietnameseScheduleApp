# nlp_engine.py
import re
from datetime import datetime, timedelta

# Khối try-except để tránh sập chương trình nếu thư viện lỗi
try:
    from underthesea import word_tokenize, ner
    HAS_UNDERTHESEA = True
except Exception as e:
    print(f"Cảnh báo: Không load được Underthesea ({e}). Sẽ dùng chế độ cơ bản.")
    HAS_UNDERTHESEA = False

class NLPProcessor:
    def __init__(self):
        pass

    def process(self, text):
        # --- BƯỚC 1: TIỀN XỬ LÝ ---
        text = text.lower().strip()
        
        # --- BƯỚC 2 & 3: TRÍCH XUẤT (HYBRID MODEL) ---
        result = {
            "event": "Sự kiện mới",
            "location": "",
            "start_time": None,
            "reminder_minutes": 0,
            "raw_time": ""
        }

        # 1. Trích xuất thời gian nhắc (Rule-based - Regex)
        reminder_match = re.search(r"nhắc.*trước\s+(\d+)\s+phút", text)
        if reminder_match:
            result["reminder_minutes"] = int(reminder_match.group(1))

        # 2. Trích xuất địa điểm (Ưu tiên Regex -> Fallback NER)
        loc_match = re.search(r"(tại|ở)\s+(.+?)(\s+lúc|\s+nhắc|$)", text)
        if loc_match:
            result["location"] = loc_match.group(2).strip()
        elif HAS_UNDERTHESEA: # Chỉ chạy NER nếu thư viện hoạt động
            try:
                entities = ner(text)
                for ent in entities:
                    if ent[1] == 'L' or ent[1] == 'B-LOC':
                        result["location"] = ent[0]
                        break
            except:
                pass # Bỏ qua nếu lỗi model

        # 3. Trích xuất sự kiện
        event_match = re.search(r"(nhắc tôi|lịch)\s+(.+?)(\s+lúc|\s+vào|\s+tại|\s+ở|$)", text)
        if event_match:
            result["event"] = event_match.group(2).strip()

        # 4. Trích xuất thời gian (Quan trọng nhất)
        # Regex bắt giờ: 9h, 9:30
        time_pattern = re.search(r"(\d{1,2})[:h](\d{0,2})", text)
        
        # Mặc định giờ hiện tại nếu không tìm thấy
        now = datetime.now()
        hour, minute = now.hour, now.minute 
        
        if time_pattern:
            hour = int(time_pattern.group(1))
            minute = int(time_pattern.group(2)) if time_pattern.group(2) else 0

        # Xử lý ngày tương đối: "mai", "mốt"
        target_date = datetime.now()
        if "mai" in text:
            target_date = target_date + timedelta(days=1)
        elif "mốt" in text:
            target_date = target_date + timedelta(days=2)
        
        # Tạo kết quả thời gian cuối cùng
        try:
            final_time = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            # Nếu giờ đã qua trong ngày hôm nay -> tự động hiểu là ngày mai
            if "mai" not in text and "mốt" not in text and final_time < datetime.now():
                 final_time = final_time + timedelta(days=1)
                 
            result["start_time"] = final_time.isoformat()
        except:
            result["start_time"] = None

        return result

# --- TEST ---
if __name__ == "__main__":
    processor = NLPProcessor()
    print("--- Đang test chế độ chống lỗi ---")
    text = "Nhắc tôi họp nhóm lúc 9h sáng mai tại phòng 302"
    print(f"Input: {text}")
    print(f"Output: {processor.process(text)}")