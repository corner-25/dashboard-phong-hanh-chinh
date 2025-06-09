# 📊 Dashboard Báo Cáo Hành Chính - Enhanced với Weekly Upload

## Tác giả
- **Dương Hữu Quang**
- **Contact:** 0789106201 (Zalo/Telegram)
- **LinkedIn:** https://www.linkedin.com/in/huuquang-hcmut/
- **Vị trí:** Thực tập sinh Phòng Hành Chính, Bệnh viện Đại học Y Dược (UMC)

## 🎯 Tính năng chính:

### ✨ **New: Weekly Upload với GitHub Storage**
- ✅ **Upload 1 lần/tuần** → Sếp xem mãi mãi trên điện thoại
- ✅ **Auto-backup & cleanup** → File cũ được backup, storage luôn gọn nhẹ
- ✅ **Cross-device access** → Sếp xem trên mọi thiết bị (phone, tablet, laptop)
- ✅ **Zero maintenance** → Hệ thống tự quản lý, không cần can thiệp thủ công

### 📊 **Core Dashboard Features**
- ✅ **Pivot Table** với thứ tự ưu tiên cố định (13 danh mục, 70+ nội dung)
- ✅ **Biến động theo tuần** (%) với màu sắc trực quan: `1.234.567 (↑15%)`
- ✅ **Sticky columns** - Cột "Nội dung" và "Tổng" đóng băng khi scroll
- ✅ **Mobile responsive** - Tối ưu cho điện thoại/tablet
- ✅ **Export Excel/CSV** với báo cáo đa định dạng

## 🏥 Dành cho:
**Dashboard chuyên biệt cho Phòng Hành Chính Bệnh viện**

## 📂 Cấu trúc dữ liệu yêu cầu:
File Excel với các cột:
- **Tuần**: Số tuần (1, 2, 3...)
- **Tháng**: Số tháng (1-12)
- **Danh mục**: Tên danh mục công việc
- **Nội dung**: Chi tiết nội dung công việc
- **Số liệu**: Giá trị số liệu

## 🚀 Setup và Deploy:

### **Bước 1: Tạo GitHub Repository cho Storage**
```bash
# Tạo repo private: "dashboard-storage"
# Dùng để lưu trữ dữ liệu upload
```

### **Bước 2: Tạo GitHub Personal Access Token**
1. GitHub → Settings → Developer settings → Personal access tokens
2. Generate token với quyền `repo`
3. Copy token: `ghp_xxxxxxxxxxxx`

### **Bước 3: Cấu hình Streamlit Secrets**
Tạo file `.streamlit/secrets.toml`:
```toml
github_token = "ghp_xxxxxxxxxxxx"
github_owner = "your-github-username"
github_repo = "dashboard-storage"
```

### **Bước 4: Deploy lên Streamlit Cloud**
1. Push code lên GitHub
2. Streamlit Cloud → Import from GitHub
3. Settings → Secrets → Paste nội dung secrets.toml
4. Deploy!

## 💡 Workflow sử dụng:

### **📤 Cho Admin (Nhân viên):**
1. **Upload file Excel** hàng tuần vào dashboard
2. **Hệ thống tự động:**
   - Backup file cũ
   - Upload file mới lên GitHub storage
   - Cleanup backup cũ (giữ 2 backup gần nhất)
   - Notify thành công

### **📱 Cho Sếp:**
1. **Bookmark link dashboard** vào điện thoại
2. **Mở link bất cứ lúc nào** → Thấy dữ liệu mới nhất
3. **Không cần download file** hay làm gì thêm
4. **Xem trên mọi thiết bị** - data được sync tự động

## 📊 Dashboard Features:

### **🎯 Thứ tự ưu tiên cố định:**
1. **Văn bản đến** - Quản lý văn bản đến
2. **Văn bản phát hành** - Quản lý văn bản đi  
3. **Chăm sóc khách VIP** - Dịch vụ VIP
4. **Lễ tân** - Hỗ trợ sự kiện
5. **Tiếp khách trong nước** - Đón tiếp khách
6. **Sự kiện** - Tổ chức sự kiện
7. **Đón tiếp khách VIP** - Dịch vụ đặc biệt
8. **Tổ chức cuộc họp trực tuyến** - Họp online
9. **Trang điều hành tác nghiệp** - ĐHTN
10. **Tổ xe** - Quản lý vận tải
11. **Tổng đài** - Dịch vụ điện thoại
12. **Hệ thống thư ký Bệnh viện** - Quản lý thư ký
13. **Bãi giữ xe** - Dịch vụ đậu xe

### **📱 Mobile Optimization:**
- **Responsive design** - Tối ưu cho mọi màn hình
- **Touch-friendly** - Dễ sử dụng trên điện thoại
- **Fast loading** - Tải nhanh trên 3G/4G
- **Offline-ready** - Cache data cho truy cập nhanh

## 🔧 Requirements:
```txt
streamlit==1.28.0
pandas==2.1.0
plotly==5.15.0
openpyxl==3.1.2
numpy==1.24.3
requests==2.31.0
```

## 🌟 New Architecture:

```
📤 Admin uploads Excel
    ↓
☁️ GitHub Storage (Private repo)
    ↓
📱 Boss opens link → Instant access
```

### **📁 GitHub Storage Structure:**
```
dashboard-storage/ (Private repo)
├── current_dashboard_data.json     ← Active data file  
├── upload_metadata.json           ← Upload tracking
├── backup_2024-06-09_10-15-30.json ← Backup (tuần trước)
├── backup_2024-06-02_14-20-15.json ← Backup (2 tuần trước)
└── (older backups auto-deleted)
```

## 💻 Local Development:
```bash
# Clone repo
git clone https://github.com/your-username/dashboard-phong-hanh-chinh.git
cd dashboard-phong-hanh-chinh

# Install dependencies  
pip install -r requirements.txt

# Run locally
streamlit run dash_phonghc.py
```

## 🎉 Key Benefits:

### **✅ Cho Phòng Hành Chính:**
- **Automation 100%** - Không cần setup thủ công
- **Zero maintenance** - Hệ thống tự quản lý
- **Professional reports** - Dashboard đẹp, đầy đủ tính năng
- **Cost effective** - Sử dụng free tier GitHub + Streamlit

### **✅ Cho Lãnh đạo:**
- **Instant access** - Xem ngay trên điện thoại
- **Always updated** - Luôn có dữ liệu mới nhất  
- **No training needed** - Chỉ cần bookmark link
- **Cross-platform** - Hoạt động trên mọi thiết bị

## 🛡️ Security & Privacy:
- **Private GitHub repo** - Dữ liệu được bảo mật
- **Access control** - Chỉ admin có quyền upload
- **Encrypted storage** - GitHub sử dụng HTTPS/TLS
- **Backup strategy** - Luôn có backup để restore

## 📞 Support:
- **Issues:** Tạo issue trên GitHub repo
- **Contact:** Zalo/Telegram 0789106201
- **Email:** huuquang.data@gmail.com


---

**🏥 Phòng Hành Chính - Bệnh Viện Đại học Y Dược**  
*Phát triển bởi Dương Hữu Quang - 2025*
