# Trợ lý Quản lý Lịch trình Cá nhân (Personal Schedule Assistant)

> **Đồ án Môn học / Chuyên ngành**  
> **Sinh viên thực hiện:** Ngô Hoàng Minh Trí - 3121410522  
> **Lớp:** DCT1211  
> **Giảng viên hướng dẫn:** Nguyễn Tuấn Đăng

---

## 📖 Giới thiệu

**Vietnamese Schedule App** là ứng dụng quản lý lịch trình cá nhân thông minh chạy trên nền tảng Desktop (Localhost). Điểm đặc biệt của ứng dụng là khả năng tích hợp công nghệ **Xử lý ngôn ngữ tự nhiên (NLP)** tiếng Việt, cho phép người dùng thêm sự kiện bằng các câu lệnh tự nhiên thay vì nhập liệu thủ công vào từng ô biểu mẫu.

Hệ thống hoạt động độc lập (offline), sử dụng mô hình lai (Hybrid Model) kết hợp giữa Học máy (Underthesea) và Hệ luật (Regex) để trích xuất thông tin chính xác từ câu nói của người dùng.

## ✨ Tính năng chính

### 1. Xử lý ngôn ngữ tự nhiên (NLP)
- **Hiểu câu lệnh tiếng Việt:** Hỗ trợ nhập liệu tự do, hiểu được tiếng Việt có dấu, viết tắt (VD: "p", "phút").
- **Trích xuất thông tin tự động:**
  - Tên sự kiện.
  - Thời gian bắt đầu & kết thúc.
  - Địa điểm (Location).
  - Thời gian nhắc nhở (Reminder).
- **Xử lý thời gian thông minh:** Hiểu các mốc thời gian tương đối như *"sáng mai"*, *"tuần sau"*, *"thứ 2 tới"*, *"hôm qua"* và tự động chuyển đổi sang ngày giờ cụ thể.

### 2. Quản lý lịch trình
- **Lịch biểu trực quan:** Tích hợp **FullCalendar**, cho phép xem lịch theo Tháng, Tuần, Ngày.
- **Thao tác CRUD:** Thêm, Xem danh sách, Chỉnh sửa, Xóa sự kiện.
- **Tìm kiếm & Lọc:** Tìm kiếm sự kiện theo từ khóa hoặc thời gian.
- **Cảnh báo xung đột:** Tự động phát hiện và cảnh báo nếu sự kiện mới trùng giờ với sự kiện đã có.

### 3. Hệ thống nhắc nhở & Lưu trữ
- **Nhắc nhở tự động:** Hệ thống chạy tiến trình ngầm (Background Thread), tự động hiển thị **Pop-up Windows (MessageBox)** khi đến giờ hẹn hoặc giờ nhắc trước.
- **Lưu trữ cục bộ:** Dữ liệu được lưu an toàn trong `SQLite`, không cần kết nối Internet.
- **Sao lưu dữ liệu:** Hỗ trợ Xuất (Export) và Nhập (Import) lịch trình qua file `.json`.

## 🛠 Công nghệ sử dụng

| Thành phần | Công nghệ / Thư viện |
|------------|----------------------|
| **Ngôn ngữ** | Python 3.8+ |
| **Giao diện (Frontend)** | [Streamlit](https://streamlit.io/) (v1.51.0) |
| **NLP Engine** | [Underthesea](https://github.com/underthesea/underthesea) (v8.3.0), Regex |
| **Cơ sở dữ liệu** | SQLite3 |
| **Thư viện hỗ trợ** | `pandas`, `streamlit-components`, `ctypes` (Windows API) |

## 📂 Cấu trúc dự án

```
VietnameseScheduleApp/
├── app.py                # File chính: Giao diện Streamlit, Thread nhắc nhở
├── database.py           # Module Database: Kết nối SQLite, CRUD, Check trùng lặp
├── nlp_engine.py         # Module NLP: Xử lý chuỗi, Regex, Underthesea
├── requirements.txt      # Danh sách thư viện phụ thuộc
├── mau_test_case_30_cau.txt # File chứa các câu test mẫu
├── schedule.db           # File CSDL SQLite (Tự sinh khi chạy app)
└── README.md             # Tài liệu hướng dẫn
```

## 🚀 Hướng dẫn cài đặt & Sử dụng

### Bước 1: Chuẩn bị môi trường
Yêu cầu máy tính đã cài đặt **Python** (phiên bản 3.8 trở lên).

### Bước 2: Clone dự án
```bash
git clone https://github.com/MinhTriTech/VietnameseScheduleApp.git
cd VietnameseScheduleApp
```

### Bước 3: Tạo và kích hoạt môi trường ảo (Khuyến nghị)
**Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```
**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Bước 4: Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### Bước 5: Chạy ứng dụng
```bash
streamlit run app.py
```
Ứng dụng sẽ tự động mở trên trình duyệt mặc định tại địa chỉ: `http://localhost:8501`

## 📝 Cơ chế xử lý NLP (Hybrid Model)

Hệ thống xử lý câu lệnh đầu vào qua 5 bước (chi tiết trong `nlp_engine.py`):

1. **Tiền xử lý:** Chuẩn hóa chuỗi, tách từ (Word Tokenization).
2. **Trích xuất thực thể (NER):** Sử dụng model của Underthesea để tìm địa điểm (LOC).
3. **Rule-based:** Sử dụng Regex để bắt các mẫu câu nhắc nhở ("nhắc trước X phút") và địa điểm nếu NER bỏ sót.
4. **Phân tích thời gian:** Chuyển đổi các từ ngữ chỉ thời gian ("mai", "mốt", "10h") thành đối tượng datetime thực tế.
5. **Validation:** Kiểm tra logic (End > Start, không phải quá khứ) và đóng gói dữ liệu JSON.

### Ví dụ sử dụng
**Câu lệnh mẫu:**
> "Nhắc tôi họp nhóm đồ án tại phòng 302 lúc 9h sáng mai, nhắc trước 15 phút"

**Kết quả trích xuất:**
```json
{
  "event": "Họp nhóm đồ án",
  "start_time": "2025-12-07T09:00:00",
  "end_time": null,
  "location": "phòng 302",
  "reminder_minutes": 15
}
```

## ⚠️ Lưu ý
- Tính năng **Pop-up thông báo** sử dụng `ctypes.windll.user32.MessageBoxW` nên chỉ hoạt động tốt nhất trên hệ điều hành **Windows**.
- Khi chạy lần đầu, thư viện `underthesea` có thể cần tải model ngôn ngữ về máy (quá trình này tự động, cần kết nối mạng lần đầu).

