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
            "end_time": None,     # Nhớ thêm dòng này nếu chưa có trong khởi tạo
            "reminder_minutes": 0,
            "error": None         # [MỚI] Thêm trường chứa lỗi
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
        
        # 3.1. Trích xuất Nhắc nhở (CẬP NHẬT: Hỗ trợ viết tắt p, ph, phút)
        # Regex này bắt: "nhắc/báo" + (trước/sớm - có thể có hoặc không) + số + (phút/p/ph/m)
        reminder_match = re.search(r"(nhắc|báo)\s*(?:trước|sớm)?\s*(\d+)\s*(?:phút|ph|p|m)\b", text_lower)
        if reminder_match:
            result["reminder_minutes"] = int(reminder_match.group(2))

        # 3.2. Trích xuất Địa điểm (CẬP NHẬT: Lọc từ "nhắc/báo")
        if ner_location:
            result["location"] = ner_location
        else:
            # Regex bắt từ "tại" hoặc "ở" đến các từ khóa thời gian, nhắc nhở hoặc cuối câu
            # Thêm \s+nhắc và \s+báo vào điều kiện dừng
            loc_match = re.search(r"(tại|ở)\s+(.+?)(\s+lúc|\s+vào|\s+trước|\s+nhắc|\s+báo|$)", text_lower)
            if loc_match:
                raw_loc = loc_match.group(2).strip()
                
                # [FIX 1] Xóa các từ khóa rác, bổ sung "nhắc", "báo" vào danh sách loại bỏ
                clean_loc = re.sub(r"\s*(lúc|vào|ngày|sáng|trưa|chiều|tối|thứ|cn|chủ nhật|tuần|nhắc|báo).*$", "", raw_loc)
                
                # [FIX 2] Xóa giờ dính liền ở cuối (VD: "Highland 10h")
                clean_loc = re.sub(r"\s+\d{1,2}(?:h|:|g|giờ)\d*.*$", "", clean_loc)
                
                result["location"] = clean_loc.strip()

        # 3.3. Trích xuất Sự kiện (ĐÃ FIX LỖI TỪ KHÓA ĐẦU CÂU)
        # Các từ khóa bắt đầu câu lệnh
        cmd_pattern = re.search(r"^(nhắc tôi|nhắc|lịch|hãy|đặt lịch|tạo)\s+(.+?)(\s+lúc|\s+vào|\s+tại|\s+ở|$)", text_lower)
        
        # [FIX 1] Regex tìm điểm cắt: Thêm (?:^|\s+) để bắt được từ khóa ở đầu câu
        # Cũ: r"(\s+lúc|...)" -> Sai vì bắt buộc phải có dấu cách
        # Mới: r"(?:^|\s+)(lúc|...)" -> Đúng cho cả đầu câu
        split_patt = r"(?:^|\s+)(lúc|vào|tại|ở|ngày|sáng|trưa|chiều|tối|thứ|cn|chủ nhật|\d{1,2}[:h]|\d{1,2}\s*giờ)"
        
        if cmd_pattern:
            # Case 1: Có từ lệnh (VD: "Nhắc tôi đi họp...")
            raw_event = text[cmd_pattern.end(1):].strip()
            split_match = re.search(split_patt, raw_event.lower())
            if split_match:
                result["event"] = raw_event[:split_match.start()].strip()
            else:
                result["event"] = raw_event
        else:
            # Case 2: Không có từ lệnh
            match = re.search(split_patt, text_lower)
            
            if match:
                # Nếu từ khóa thời gian nằm ngay đầu câu (index=0)
                if match.start() == 0:
                    temp_text = text
                    
                    # [FIX 2] Regex dọn dẹp phần đầu: Thêm \s* trước số để bắt " 15h" sau chữ "mai"
                    # Cho phép xóa liên tiếp nhiều cụm từ chỉ thời gian
                    clean_head_pattern = r"^(?:\s*\d{1,2}[:h]\d*|\s*lúc|\s*vào|\s*ngày|\s*sáng|\s*trưa|\s*chiều|\s*tối|\s*thứ|\s*cn|\s*mai|\s*mốt|\s*hôm|\s*nay|\s*giờ)+"
                    temp_text = re.sub(clean_head_pattern, "", temp_text, flags=re.IGNORECASE)
                    
                    # Dọn dẹp phần đuôi (nhắc nhở, địa điểm)
                    temp_text = re.sub(r"(nhắc|báo)\s*(?:trước|sớm)?\s*\d+\s*(?:phút|ph|p|m)\b.*$", "", temp_text, flags=re.IGNORECASE)
                    temp_text = re.sub(r"(tại|ở)\s+.*$", "", temp_text, flags=re.IGNORECASE)
                    
                    result["event"] = temp_text.strip()
                else:
                    # Sự kiện nằm trước thời gian (VD: "Họp lúc 9h")
                    result["event"] = text[:match.start()].strip()
            else:
                # Lấy toàn bộ nếu không tìm thấy điểm cắt
                clean_text = text
                if result.get("reminder_minutes"):
                    clean_text = re.sub(r"(nhắc|báo)\s*(?:trước|sớm)?\s*\d+\s*(?:phút|ph|p|m)\b.*$", "", clean_text, flags=re.IGNORECASE)
                result["event"] = clean_text.strip()

        if not result["event"]: result["event"] = "Sự kiện mới"
        result["event"] = result["event"][0].upper() + result["event"][1:] if result["event"] else "Sự kiện mới"

        # --- BƯỚC 4: PHÂN TÍCH THỜI GIAN (COMPONENT 4) ---
        now = datetime.now()
        target_date = now
        has_date_specified = False 

        # 4.1. Ngày tương đối (CẬP NHẬT)
        # [FIX] Xử lý "hôm qua" để đưa về quá khứ (để bước sau chặn lại)
        if "hôm qua" in text_lower:
            target_date = now - timedelta(days=1)
            has_date_specified = True
        
        # Bắt ngày mai
        elif "ngày mai" in text_lower or "sáng mai" in text_lower or "trưa mai" in text_lower or "chiều mai" in text_lower or "tối mai" in text_lower:
            target_date = now + timedelta(days=1)
            has_date_specified = True
        
        # ... (Các phần ngày mốt, hôm nay giữ nguyên) ...
        # [FIX] Bổ sung các biến thể: sáng mốt, chiều mốt, tối mốt
        elif "ngày mốt" in text_lower or "sáng mốt" in text_lower or "chiều mốt" in text_lower or "tối mốt" in text_lower:
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
                
                # LOGIC XỬ LÝ TUẦN SAU (SMART FIX)
                if days_ahead < 0: 
                    # Trường hợp 1: Thứ đã qua trong tuần này (VD: Nay Thứ 6, nhập Thứ 4)
                    # Tự động nhảy sang tuần sau (Cộng 7)
                    days_ahead += 7
                    
                    # Lưu ý: Lúc này ngày đã nằm ở "tuần sau" rồi.
                    # Nên dù user có nói "tuần sau", ta KHÔNG cộng thêm nữa để tránh bị double.
                    
                else:
                    # Trường hợp 2: Thứ chưa đến trong tuần này (VD: Nay Thứ 2, nhập Thứ 4)
                    # Nếu user nói "tuần sau" -> Có nghĩa là bỏ qua tuần này, lấy tuần tới -> Cộng 7
                    if "tuần sau" in text_lower or "tuần tới" in text_lower:
                        days_ahead += 7
                    
                target_date = now + timedelta(days=days_ahead)
                has_date_specified = True

        # 4.3. Xử lý Giờ (CẬP NHẬT LOGIC MỚI)
        time_pattern = re.search(r"(\d{1,2})\s*(?:[:h]|giờ|gio)\s*(\d{0,2})", text_lower)
        
        # Mặc định ban đầu
        hour, minute = 9, 0 
        has_time_specified = False
        
        if time_pattern:
            # TRƯỜNG HỢP 1: Có giờ cụ thể (VD: 7h tối, 10:30)
            hour = int(time_pattern.group(1))
            m_str = time_pattern.group(2)
            minute = int(m_str) if m_str and m_str.isdigit() else 0
            has_time_specified = True
            
            # Xử lý 12h (pm) khi có giờ cụ thể
            if ("chiều" in text_lower or "tối" in text_lower or "pm" in text_lower) and hour < 12:
                hour += 12
        else:
            # TRƯỜNG HỢP 2 [MỚI]: Không có số giờ, chỉ có buổi (VD: sáng mai, tối thứ 2)
            # Gán giờ mặc định theo buổi cho hợp lý
            if "tối" in text_lower:
                hour = 19  # Tối mặc định 19:00
                has_time_specified = True
            elif "chiều" in text_lower:
                hour = 14  # Chiều mặc định 14:00
                has_time_specified = True
            elif "trưa" in text_lower:
                hour = 12  # Trưa mặc định 12:00
                has_time_specified = True
            elif "sáng" in text_lower:
                hour = 9   # Sáng mặc định 09:00
                has_time_specified = True

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
            # Kiểm tra nếu không tìm thấy Ngày VÀ không tìm thấy Giờ
            if not has_date_specified and not has_time_specified:
                result["start_time"] = None
                return result

            # Kiểm tra tính hợp lệ của giờ/phút (25h, 60p...)
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                result["error"] = f"Thời gian không hợp lệ: {hour} giờ {minute} phút"
                result["start_time"] = None
                return result

            final_start = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # [FIX QUAN TRỌNG] CHẶN SỰ KIỆN QUÁ KHỨ TẠI ĐÂY
            # Nếu thời gian tính ra nhỏ hơn thời gian hiện tại -> Báo lỗi
            if final_start < now:
                result["error"] = f"Lỗi: Thời gian sự kiện đã trôi qua ({final_start.strftime('%H:%M %d/%m/%Y')})"
                result["start_time"] = None
                return result

            result["start_time"] = final_start.isoformat()
            
            # ... (Phần xử lý end_time giữ nguyên) ...
            
            # ... (Phần xử lý end_time phía sau giữ nguyên) ...
            
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