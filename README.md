# Trợ Lý Lịch Trình Cá Nhân (AI Personal Schedule)

Ứng dụng quản lý lịch trình tích hợp xử lý ngôn ngữ tự nhiên tiếng Việt, giúp thêm sự kiện nhanh chóng bằng câu lệnh.

## Tính năng chính
- Xử lý câu lệnh tiếng Việt tự nhiên (VD: "Họp team lúc 9h sáng mai").
- Tự động trích xuất: Sự kiện, Thời gian, Địa điểm, Thời gian nhắc trước.
- Lưu trữ dữ liệu cục bộ (SQLite).
- Hệ thống nhắc nhở Pop-up chạy ngầm.

## Cài đặt
1. Cài đặt Python 3.8+.
2. Cài thư viện: `pip install -r requirements.txt`
3. Chạy ứng dụng: `streamlit run app.py`

## Công nghệ sử dụng
- Ngôn ngữ: Python
- Giao diện: Streamlit
- NLP: Underthesea + Regex (Hybrid Model)
- Database: SQLite