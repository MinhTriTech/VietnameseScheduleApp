import re
from datetime import datetime, timedelta

# Sử dụng Underthesea cho các tác vụ xử lý ngôn ngữ tiếng Việt
try:
    from underthesea import word_tokenize, ner
    HAS_UNDERTHESEA = True
except ImportError:
    HAS_UNDERTHESEA = False

class NLPProcessor:
    """
    Lớp xử lý ngôn ngữ tự nhiên.
    Thực hiện quy trình 5 bước để trích xuất thông tin sự kiện từ văn bản tiếng Việt.
    """
    
    def __init__(self):
        pass

    def process(self, text):
        """
        Hàm xử lý chính.

        text (str): Câu nhập liệu của người dùng.
            
        Returns: dict: Dictionary chứa thông tin đã trích xuất (event, start_time, end_time, location, reminder, error).
        """
        
        # Bước 1: Tiền xử lý 
        raw_text = text.strip()
        text_lower = raw_text.lower()
        
        # Gọi word_tokenize để chuẩn hóa từ ngữ 
        if HAS_UNDERTHESEA:
            try:
                word_tokenize(raw_text)
            except:
                pass

        # Cấu trúc dữ liệu đầu ra chuẩn
        result = {
            "event": "",
            "location": "",
            "start_time": None,
            "end_time": None,
            "reminder_minutes": 0,
            "error": None 
        }

        # Bước 2: Trích xuất thực thể 
        # Sử dụng mô hình học máy để nhận diện tên riêng, địa điểm
        ner_location = ""
        if HAS_UNDERTHESEA:
            try:
                entities = ner(raw_text)
                loc_parts = []
                for word, pos, tag in entities:
                    if 'LOC' in tag: # Lọc các thực thể là địa điểm (location)
                        loc_parts.append(word)
                
                if loc_parts:
                    ner_location = " ".join(loc_parts)
            except Exception:
                pass

        # Bước 3: Trích xuất dựa trên luật
        
        # 3.1. Trích xuất thông tin nhắc nhở
        # Pattern: bắt các cụm từ như "nhắc trước 15 phút", "báo sớm 30p"
        reminder_match = re.search(r"(nhắc|báo)\s*(?:trước|sớm)?\s*(\d+)\s*(?:phút|ph|p|m)\b", text_lower)
        if reminder_match:
            result["reminder_minutes"] = int(reminder_match.group(2))

        # 3.2. Trích xuất địa điểm
        # Ưu tiên kết quả từ NER, nếu không có thì dùng Regex fallback
        if ner_location:
            result["location"] = ner_location
        else:
            # Pattern: Lấy nội dung sau từ "tại/ở" cho đến khi gặp từ khóa thời gian hoặc kết thúc câu
            loc_match = re.search(r"(tại|ở)\s+(.+?)(\s+lúc|\s+vào|\s+trước|\s+nhắc|\s+báo|$)", text_lower)
            if loc_match:
                raw_loc = loc_match.group(2).strip()
                
                # Làm sạch chuỗi địa điểm: Loại bỏ các từ khóa thời gian bị dính vào
                clean_loc = re.sub(r"\s*(lúc|vào|ngày|sáng|trưa|chiều|tối|thứ|cn|chủ nhật|tuần|nhắc|báo).*$", "", raw_loc)
                # Loại bỏ giờ giấc dính liền (Ví dụ: "highland 10h")
                clean_loc = re.sub(r"\s+\d{1,2}(?:h|:|g|giờ)\d*.*$", "", clean_loc)
                
                result["location"] = clean_loc.strip()

        # 3.3. Trích xuất tên sự kiện
        # Xác định cấu trúc câu để tách tên sự kiện. 
        # Hỗ trợ cả 2 dạng: "sự kiện + thời gian" và "thời gian + sự kiện"
        
        # Kiểm tra từ khóa bắt đầu (câu lệnh)
        cmd_pattern = re.search(r"^(nhắc tôi|nhắc|lịch|hãy|đặt lịch|tạo)\s+(.+?)(\s+lúc|\s+vào|\s+tại|\s+ở|$)", text_lower)
        
        # Regex xác định điểm cắt giữa sự kiện và các thành phần khác
        split_patt = r"(?:^|\s+)(lúc|vào|tại|ở|ngày|sáng|trưa|chiều|tối|thứ|cn|chủ nhật|\d{1,2}[:h]|\d{1,2}\s*giờ)"
        
        if cmd_pattern:
            # Trường hợp có từ lệnh rõ ràng
            raw_event = text[cmd_pattern.end(1):].strip()
            split_match = re.search(split_patt, raw_event.lower())
            if split_match:
                result["event"] = raw_event[:split_match.start()].strip()
            else:
                result["event"] = raw_event
        else:
            # Trường hợp câu tự nhiên, cần phân tích vị trí
            match = re.search(split_patt, text_lower)
            
            if match:
                if match.start() == 0:
                    # Thời gian nằm đầu câu (VD: "Chiều nay đi họp")
                    # Chiến lược: Xóa các cụm từ chỉ thời gian ở đầu, phần còn lại là sự kiện
                    temp_text = text
                    clean_head_pattern = r"^(?:\s*\d{1,2}[:h]\d*|\s*lúc|\s*vào|\s*ngày|\s*sáng|\s*trưa|\s*chiều|\s*tối|\s*thứ|\s*cn|\s*mai|\s*mốt|\s*hôm|\s*nay|\s*giờ)+"
                    temp_text = re.sub(clean_head_pattern, "", temp_text, flags=re.IGNORECASE)
                    
                    # Tiếp tục làm sạch các phần đuôi (nhắc nhở, địa điểm)
                    temp_text = re.sub(r"(nhắc|báo)\s*(?:trước|sớm)?\s*\d+\s*(?:phút|ph|p|m)\b.*$", "", temp_text, flags=re.IGNORECASE)
                    temp_text = re.sub(r"(tại|ở)\s+.*$", "", temp_text, flags=re.IGNORECASE)
                    
                    result["event"] = temp_text.strip()
                else:
                    # Sự kiện nằm đầu câu (VD: "Đi họp lúc 9h")
                    result["event"] = text[:match.start()].strip()
            else:
                # Lấy toàn bộ nếu không tìm thấy điểm cắt (trừ phần nhắc nhở)
                clean_text = text
                if result.get("reminder_minutes"):
                    clean_text = re.sub(r"(nhắc|báo)\s*(?:trước|sớm)?\s*\d+\s*(?:phút|ph|p|m)\b.*$", "", clean_text, flags=re.IGNORECASE)
                result["event"] = clean_text.strip()

        if not result["event"]: result["event"] = "Sự kiện mới"
        # Viết hoa chữ cái đầu tiên
        result["event"] = result["event"][0].upper() + result["event"][1:] if result["event"] else "Sự kiện mới"

        # Bước 4: Phân tích thời gian 
        now = datetime.now()
        target_date = now
        has_date_specified = False 

        # 4.1. Xử lý ngày cụ thể 
        # Bắt định dạng dd/mm hoặc dd-mm
        date_pattern = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?\b", text_lower)
        
        if date_pattern:
            try:
                d = int(date_pattern.group(1))
                m = int(date_pattern.group(2))
                y = int(date_pattern.group(3)) if date_pattern.group(3) else now.year
                target_date = datetime(y, m, d)
                has_date_specified = True
            except ValueError:
                pass # Ngày không hợp lệ (VD: 30/2)

        # 4.2. Xử lý ngày tương đối
        elif "hôm qua" in text_lower:
            target_date = now - timedelta(days=1)
            has_date_specified = True
        elif "ngày mai" in text_lower or "sáng mai" in text_lower or "trưa mai" in text_lower or "chiều mai" in text_lower or "tối mai" in text_lower:
            target_date = now + timedelta(days=1)
            has_date_specified = True
        elif "ngày mốt" in text_lower or "sáng mốt" in text_lower or "chiều mốt" in text_lower or "tối mốt" in text_lower:
            target_date = now + timedelta(days=2)
            has_date_specified = True
        
        # Đánh dấu nếu người dùng nhập cụ thể "hôm nay" để tránh logic tự động đẩy ngày
        if any(x in text_lower for x in ["hôm nay", "chiều nay", "tối nay", "sáng nay", "trưa nay"]):
            has_date_specified = True 

        # 4.3. Xử lý thứ trong tuần
        if not has_date_specified:
            weekday_map = {"hai": 0, "2": 0, "ba": 1, "3": 1, "tư": 2, "4": 2, "năm": 3, "5": 3, "sáu": 4, "6": 4, "bảy": 5, "7": 5}
            wk_match = re.search(r"thứ\s+([2-7]|hai|ba|tư|năm|sáu|bảy)|(chủ nhật|cn)", text_lower)
            target_wk = None
            
            if wk_match:
                if wk_match.group(1):
                    target_wk = weekday_map.get(wk_match.group(1))
                else:
                    target_wk = 6 # Chủ nhật
            
            if target_wk is not None:
                current_wk = now.weekday()
                days_ahead = target_wk - current_wk
                
                # Nếu thứ đã qua trong tuần, tự động chuyển sang tuần sau
                if days_ahead < 0: 
                    days_ahead += 7
                elif "tuần sau" in text_lower or "tuần tới" in text_lower:
                    # Nếu người dùng nói rõ "tuần sau" dù thứ chưa qua
                    days_ahead += 7
                    
                target_date = now + timedelta(days=days_ahead)
                has_date_specified = True

        # 4.4. Xử lý giờ
        # Pattern: Tìm giờ dạng số (7h, 14:30)
        time_pattern = re.search(r"(\d{1,2})\s*(?:[:h]|giờ|gio)\s*(\d{0,2})", text_lower)
        
        hour, minute = 9, 0 # Mặc định
        has_time_specified = False
        
        if time_pattern:
            hour = int(time_pattern.group(1))
            m_str = time_pattern.group(2)
            minute = int(m_str) if m_str and m_str.isdigit() else 0
            has_time_specified = True
            
            # Xử lý 12h PM (Giờ chiều/tối)
            if ("chiều" in text_lower or "tối" in text_lower or "pm" in text_lower) and hour < 12:
                hour += 12
        else:
            # Nếu không có số giờ, đoán giờ dựa trên buổi
            if "tối" in text_lower:
                hour, has_time_specified = 19, True
            elif "chiều" in text_lower:
                hour, has_time_specified = 14, True
            elif "trưa" in text_lower:
                hour, has_time_specified = 12, True
            elif "sáng" in text_lower:
                hour, has_time_specified = 9, True

        # Xử lý giờ kết thúc nếu có từ khóa "đến", "tới"
        end_hour, end_minute = None, None
        end_pattern = re.search(r"(?:đến|tới|-)\s*(\d{1,2})\s*(?:[:h]|giờ|gio)\s*(\d{0,2})", text_lower)
        
        if end_pattern:
            e_h = int(end_pattern.group(1))
            e_m_str = end_pattern.group(2)
            e_m = int(e_m_str) if e_m_str and e_m_str.isdigit() else 0
            
            # Logic PM cho giờ kết thúc
            if e_h < hour: 
                e_h += 12
            elif hour >= 12 and e_h < 12:
                e_h += 12
                
            end_hour, end_minute = e_h, e_m

        # Bước 5: Hợp nhất và kiểm tra hợp lệ
        try:
            # Validate: Phải có ít nhất thông tin ngày hoặc giờ
            if not has_date_specified and not has_time_specified:
                result["start_time"] = None
                return result

            # Validate: Giờ phút phải hợp lệ
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                result["error"] = f"Thời gian không hợp lệ: {hour} giờ {minute} phút"
                result["start_time"] = None
                return result

            final_start = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Validate: Chặn sự kiện quá khứ
            if final_start < now:
                result["error"] = f"Lỗi: Thời gian sự kiện đã trôi qua ({final_start.strftime('%H:%M %d/%m/%Y')})"
                result["start_time"] = None
                return result

            result["start_time"] = final_start.isoformat()
            
            # Xử lý thời gian kết thúc
            if end_hour is not None:
                final_end = target_date.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
                # Chỉ lưu nếu thời gian kết thúc diễn ra sau thời gian bắt đầu
                if final_end > final_start:
                    result["end_time"] = final_end.isoformat()
                else:
                    result["end_time"] = None
            else:
                result["end_time"] = None
                
        except ValueError:
            result["start_time"] = None
            result["end_time"] = None

        return result