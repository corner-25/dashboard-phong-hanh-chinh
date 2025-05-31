# 📊 Dashboard Báo Cáo Hành Chính - Phòng Hành Chính

## Tác giả
- Dương Hữu Quang
- Contact: 0789106201 (Zalo/Telegram)
- Linkedin: https://www.linkedin.com/in/huuquang-hcmut/
- Thực tập sinh Phòng Hành Chính, Bệnh viện Đại học Y Dược (UMC)

## 🎯 Tính năng chính:
- ✅ Pivot Table với thứ tự ưu tiên cố định (13 danh mục, 70+ nội dung)
- ✅ Hiển thị biến động theo tuần (%) với màu sắc trực quan
- ✅ Cột "Nội dung" và "Tổng" đóng băng khi scroll ngang
- ✅ Tính tổng theo hàng tự động
- ✅ Sparkline xu hướng cho từng danh mục
- ✅ Xuất báo cáo Excel đa sheet và CSV

## 🏥 Dành cho:
Dashboard chuyên biệt cho Phòng Hành Chính Bệnh viện

## 📂 Cấu trúc dữ liệu yêu cầu:
File Excel với các cột:
- **Tuần**: Số tuần (1, 2, 3...)
- **Tháng**: Số tháng (1-12)
- **Danh mục**: Tên danh mục công việc
- **Nội dung**: Chi tiết nội dung công việc
- **Số liệu**: Giá trị số liệu

## 🎨 Giao diện:
- Thứ tự ưu tiên cố định theo tầm quan trọng
- Biến động tuần so với tuần trước: `1.234.567 (↑15.0%)`
- Sparkline xu hướng trong từng danh mục
- Xuất báo cáo đầy đủ
- 
## 💻 Chạy local:
```bash
pip install -r requirements.txt
streamlit run dash_phonghc.py

