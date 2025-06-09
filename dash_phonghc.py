import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import os
from pathlib import Path
import json
import requests
import base64
import hashlib
import time

# Cấu hình trang
st.set_page_config(
    page_title="Dashboard Báo Cáo Hành Chính - Pivot Table",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS tùy chỉnh
st.markdown("""
<style>
    .stDataFrame {
        font-size: 12px;
    }
    .stDataFrame table {
        width: 100% !important;
    }
    .stDataFrame td, .stDataFrame th {
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        max-width: none !important;
        min-width: 120px !important;
    }
    .pivot-table {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .metric-card {
        background-color: #e9ecef;
        padding: 15px;
        border-radius: 8px;
        margin: 5px 0;
        text-align: center;
    }
    .sparkline {
        height: 30px;
        margin: 0;
        padding: 0;
    }
    .category-header {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        border-left: 4px solid #1f77b4;
        font-weight: bold;
    }
    .sub-category {
        padding-left: 20px;
        margin: 2px 0;
    }
    .positive-change {
        color: #28a745 !important;
        font-weight: bold !important;
        background-color: rgba(40, 167, 69, 0.1) !important;
        padding: 2px 4px !important;
        border-radius: 3px !important;
    }
    .negative-change {
        color: #dc3545 !important;
        font-weight: bold !important;
        background-color: rgba(220, 53, 69, 0.1) !important;
        padding: 2px 4px !important;
        border-radius: 3px !important;
    }
    .no-change {
        color: #6c757d !important;
        font-weight: bold !important;
        background-color: rgba(108, 117, 125, 0.1) !important;
        padding: 2px 4px !important;
        border-radius: 3px !important;
    }
    .full-width-table {
        overflow-x: auto;
        width: 100%;
        position: relative;
    }
    .full-width-table table {
        min-width: 100%;
        table-layout: auto;
    }
    .full-width-table td {
        white-space: nowrap;
        padding: 8px 12px;
        min-width: 150px;
    }
    .full-width-table th:first-child,
    .full-width-table td:first-child {
        position: sticky;
        left: 0;
        background-color: #f8f9fa;
        z-index: 10;
        border-right: 2px solid #dee2e6;
        min-width: 250px !important;
        max-width: 250px !important;
    }
    .full-width-table th:last-child,
    .full-width-table td:last-child {
        position: sticky;
        right: 0;
        background-color: #e9ecef;
        z-index: 10;
        border-left: 2px solid #dee2e6;
        font-weight: bold;
        min-width: 120px !important;
    }
    .number-cell {
        text-align: right;
        font-family: 'Courier New', monospace;
        font-weight: bold;
    }
    
    /* Mobile optimizations */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 0.5rem;
        }
        
        .stButton > button {
            width: 100%;
            margin: 2px 0;
        }
        
        .stDataFrame {
            font-size: 10px;
        }
    }
    
    /* Weekly upload specific styles */
    .upload-header {
        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
    }
    
    .upload-title {
        color: white;
        font-size: 1.8rem;
        font-weight: bold;
        margin: 0;
    }
    
    .upload-subtitle {
        color: #f0f0f0;
        font-size: 0.9rem;
        margin: 10px 0 0 0;
    }
    
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-online { background-color: #28a745; }
    .status-loading { background-color: #ffc107; }
    .status-offline { background-color: #dc3545; }
</style>
""", unsafe_allow_html=True)

# ================== WEEKLY UPLOAD MANAGER CLASS ==================
class WeeklyUploadManager:
    """
    Quản lý upload hàng tuần với auto-cleanup
    - 1 file duy nhất mỗi thời điểm
    - Auto xóa file cũ khi upload mới
    - Optimized cho storage
    """
    
    def __init__(self):
        self.github_token = st.secrets.get("github_token", None)
        self.github_owner = st.secrets.get("github_owner", None)
        self.github_repo = st.secrets.get("github_repo", None)
        
        # File naming strategy
        self.current_data_file = "current_dashboard_data.json"
        self.metadata_file = "upload_metadata.json"
        self.backup_prefix = "backup_"
        
        # Settings
        self.keep_backups = 2
        self.max_file_size_mb = 25
    
    def check_github_connection(self):
        """Kiểm tra kết nối GitHub"""
        if not all([self.github_token, self.github_owner, self.github_repo]):
            return False, "❌ Chưa cấu hình GitHub credentials"
        
        try:
            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}"
            headers = {"Authorization": f"token {self.github_token}"}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return True, "✅ GitHub kết nối thành công"
            else:
                return False, f"❌ GitHub error: {response.status_code}"
                
        except Exception as e:
            return False, f"❌ Lỗi kết nối: {str(e)}"
    
    def get_current_file_info(self):
        """Lấy thông tin file hiện tại"""
        try:
            metadata_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{self.metadata_file}"
            headers = {"Authorization": f"token {self.github_token}"}
            
            response = requests.get(metadata_url, headers=headers)
            
            if response.status_code == 200:
                file_data = response.json()
                content = base64.b64decode(file_data['content']).decode()
                metadata = json.loads(content)
                return metadata
            
        except Exception as e:
            st.warning(f"Không thể đọc metadata: {str(e)}")
        
        return None
    
    def create_backup_of_current_file(self):
        """Backup file hiện tại trước khi xóa"""
        try:
            current_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{self.current_data_file}"
            headers = {"Authorization": f"token {self.github_token}"}
            
            response = requests.get(current_url, headers=headers)
            
            if response.status_code == 200:
                file_data = response.json()
                
                current_metadata = self.get_current_file_info()
                if current_metadata:
                    upload_time = current_metadata.get('upload_time', datetime.now().isoformat())
                    backup_timestamp = upload_time[:19].replace(':', '-').replace(' ', '_')
                else:
                    backup_timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                
                backup_filename = f"{self.backup_prefix}{backup_timestamp}.json"
                
                backup_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{backup_filename}"
                
                backup_payload = {
                    "message": f"📦 Backup before new upload - {backup_timestamp}",
                    "content": file_data['content'],
                    "branch": "main"
                }
                
                backup_response = requests.put(backup_url, headers=headers, json=backup_payload)
                
                if backup_response.status_code == 201:
                    st.info(f"📦 Đã backup file cũ: {backup_filename}")
                    return backup_filename
                    
        except Exception as e:
            st.warning(f"Không thể backup file cũ: {str(e)}")
        
        return None
    
    def cleanup_old_backups(self):
        """Xóa các backup cũ, chỉ giữ lại số lượng nhất định"""
        try:
            contents_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents"
            headers = {"Authorization": f"token {self.github_token}"}
            
            response = requests.get(contents_url, headers=headers)
            
            if response.status_code == 200:
                files = response.json()
                
                backup_files = [f for f in files if f['name'].startswith(self.backup_prefix)]
                backup_files.sort(key=lambda x: x['name'], reverse=True)
                files_to_delete = backup_files[self.keep_backups:]
                
                deleted_count = 0
                for file_to_delete in files_to_delete:
                    try:
                        delete_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{file_to_delete['name']}"
                        
                        delete_payload = {
                            "message": f"🗑️ Auto cleanup old backup: {file_to_delete['name']}",
                            "sha": file_to_delete['sha'],
                            "branch": "main"
                        }
                        
                        delete_response = requests.delete(delete_url, headers=headers, json=delete_payload)
                        
                        if delete_response.status_code == 200:
                            deleted_count += 1
                            
                    except Exception as e:
                        continue
                
                if deleted_count > 0:
                    st.info(f"🗑️ Đã xóa {deleted_count} backup cũ")
                    
        except Exception as e:
            st.warning(f"Không thể cleanup backups: {str(e)}")
    
    def upload_new_file(self, data, filename):
        """Upload file mới với auto-cleanup"""
        
        try:
            connected, message = self.check_github_connection()
            if not connected:
                st.error(message)
                return False
            
            st.info("🔄 Bắt đầu upload file mới...")
            
            with st.spinner("📦 Đang backup file cũ..."):
                backup_filename = self.create_backup_of_current_file()
            
            with st.spinner("📊 Đang chuẩn bị dữ liệu..."):
                new_data_package = {
                    'data': data.to_dict('records'),
                    'columns': list(data.columns),
                    'metadata': {
                        'filename': filename,
                        'upload_time': datetime.now().isoformat(),
                        'week_number': datetime.now().isocalendar()[1],
                        'year': datetime.now().year,
                        'row_count': len(data),
                        'file_size_mb': round(len(str(data)) / (1024*1024), 2),
                        'uploader': 'weekly_admin',
                        'replaced_backup': backup_filename
                    }
                }
                
                json_content = json.dumps(new_data_package, ensure_ascii=False, indent=2)
                size_mb = len(json_content.encode()) / (1024*1024)
                
                if size_mb > self.max_file_size_mb:
                    st.error(f"❌ File quá lớn ({size_mb:.1f}MB). Giới hạn {self.max_file_size_mb}MB")
                    return False
            
            with st.spinner("☁️ Đang upload file mới..."):
                content_encoded = base64.b64encode(json_content.encode()).decode()
                
                current_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{self.current_data_file}"
                headers = {"Authorization": f"token {self.github_token}"}
                
                current_response = requests.get(current_url, headers=headers)
                current_sha = None
                if current_response.status_code == 200:
                    current_sha = current_response.json()['sha']
                
                upload_payload = {
                    "message": f"📊 Weekly data update - Tuần {new_data_package['metadata']['week_number']}/{new_data_package['metadata']['year']}",
                    "content": content_encoded,
                    "branch": "main"
                }
                
                if current_sha:
                    upload_payload["sha"] = current_sha
                
                upload_response = requests.put(current_url, headers=headers, json=upload_payload)
                
                if upload_response.status_code not in [200, 201]:
                    st.error(f"❌ Lỗi upload: {upload_response.status_code}")
                    return False
            
            with st.spinner("📝 Đang cập nhật metadata..."):
                self.update_metadata(new_data_package['metadata'])
            
            with st.spinner("🗑️ Đang dọn dẹp backup cũ..."):
                self.cleanup_old_backups()
            
            st.success(f"""
            🎉 **UPLOAD THÀNH CÔNG!**
            
            ✅ **File mới:** {filename}
            ✅ **Dữ liệu:** {len(data):,} dòng ({size_mb:.1f}MB)
            ✅ **Tuần:** {new_data_package['metadata']['week_number']}/{new_data_package['metadata']['year']}
            ✅ **Backup:** {backup_filename if backup_filename else 'Không có file cũ'}
            
            📱 **Sếp có thể xem ngay trên điện thoại!**
            """)
            
            return True
            
        except Exception as e:
            st.error(f"❌ Lỗi upload: {str(e)}")
            return False
    
    def update_metadata(self, metadata):
        """Cập nhật file metadata"""
        try:
            metadata_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{self.metadata_file}"
            headers = {"Authorization": f"token {self.github_token}"}
            
            current_response = requests.get(metadata_url, headers=headers)
            current_sha = None
            if current_response.status_code == 200:
                current_sha = current_response.json()['sha']
            
            metadata_content = json.dumps(metadata, ensure_ascii=False, indent=2)
            content_encoded = base64.b64encode(metadata_content.encode()).decode()
            
            payload = {
                "message": f"📝 Update metadata - Tuần {metadata['week_number']}/{metadata['year']}",
                "content": content_encoded,
                "branch": "main"
            }
            
            if current_sha:
                payload["sha"] = current_sha
            
            requests.put(metadata_url, headers=headers, json=payload)
            
        except Exception as e:
            st.warning(f"Không thể update metadata: {str(e)}")
    
    def load_current_data(self):
        """Load dữ liệu hiện tại"""
        try:
            current_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{self.current_data_file}"
            headers = {"Authorization": f"token {self.github_token}"}
            
            response = requests.get(current_url, headers=headers)
            
            if response.status_code == 200:
                file_data = response.json()
                content = base64.b64decode(file_data['content']).decode()
                data_package = json.loads(content)
                
                df = pd.DataFrame(data_package['data'], columns=data_package['columns'])
                
                return df, data_package['metadata']
            
        except Exception as e:
            st.warning(f"Không thể load dữ liệu: {str(e)}")
        
        return None, None
    
    def get_storage_info(self):
        """Lấy thông tin storage usage"""
        try:
            contents_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents"
            headers = {"Authorization": f"token {self.github_token}"}
            
            response = requests.get(contents_url, headers=headers)
            
            if response.status_code == 200:
                files = response.json()
                
                total_size = sum(f.get('size', 0) for f in files)
                backup_files = [f for f in files if f['name'].startswith(self.backup_prefix)]
                
                return {
                    'total_files': len(files),
                    'backup_files': len(backup_files),
                    'total_size_mb': round(total_size / (1024*1024), 2),
                    'files': files
                }
                
        except Exception as e:
            pass
        
        return None

# ================== PIVOT TABLE DASHBOARD CLASS (FULL ORIGINAL) ==================
class PivotTableDashboard:
    def __init__(self):
        self.data = None
        
        # CẤU HÌNH THỨ TỰ ƯU TIÊN CỐ ĐỊNH THEO YÊU CẦU MỚI
        self.category_priority = {
            "Văn bản đến": 1,
            "Văn bản phát hành": 2,
            "Chăm sóc khách vip": 3,
            "Lễ tân": 4,
            "Tiếp khách trong nước": 5,
            "Sự kiện": 6,
            "Đón tiếp khách VIP": 7,
            "Tổ chức cuộc họp trực tuyến": 8,
            "Trang điều hành tác nghiệp": 9,
            "Tổ xe": 10,
            "Tổng đài": 11,
            "Hệ thống thư ký Bệnh viện": 12,
            "Bãi giữ xe": 13
        }
        
        self.content_priority = {
            # Văn bản đến
            "Tổng số văn bản đến, trong đó:": 1,
            "Số văn bản không yêu cầu phản hồi": 2,
            "Số văn bản yêu cầu phản hồi": 3,
            "Xử lý đúng hạn": 4,
            "Xử lý trễ hạn": 5,
            
            # Văn bản phát hành
            "Văn bản đi": 6,
            "Hợp đồng": 7,
            "Quyết định": 8,
            "Quy chế": 9,
            "Quy định": 10,
            "Quy trình": 11,
            
            # Chăm sóc khách vip
            "Tiếp đón, hướng dẫn và phục vụ khách VIP": 12,
            
            # Lễ tân
            "Hỗ trợ lễ tân cho hội nghị/hội thảo": 13,
            
            # Tiếp khách trong nước
            "Tổng số đoàn khách trong nước, trong đó:": 14,
            "Tham quan, học tập": 15,
            "Làm việc": 16,
            
            # Sự kiện
            "Tổng số sự kiện hành chính của Bệnh viện, trong đó:": 17,
            "Phòng Hành chính chủ trì": 18,
            "Phòng Hành chính phối hợp": 19,
            
            # Đón tiếp khách VIP
            "Số lượt khách VIP được lễ tân tiếp đón, hỗ trợ khám chữa bệnh": 20,
            
            # Tổ chức cuộc họp trực tuyến
            "Tổng số cuộc họp trực tuyến do Phòng Hành chính chuẩn bị": 21,
            
            # Trang điều hành tác nghiệp
            "Số lượng tin đăng ĐHTN": 22,
            
            # Tổ xe
            "Số chuyến xe": 23,
            "Tổng số nhiên liệu tiêu thụ": 24,
            "Tổng km chạy": 25,
            "Xe hành chính": 26,
            "Xe cứu thương": 27,
            "Chi phí bảo dưỡng": 28,
            "Doanh thu": 29,
            "Tổ xe": 30,
            "Số phiếu khảo sát hài lòng": 31,
            "Tỷ lệ hài lòng của khách hàng": 32,
            
            # Tổng đài
            "Tổng số cuộc gọi đến Bệnh viện": 33,
            "Tổng số cuộc gọi nhỡ do từ chối": 34,
            "Tổng số cuộc gọi nhỡ do không bắt máy": 35,
            "Số cuộc gọi đến (Nhánh 0-Tổng đài viên)": 36,
            "Nhỡ do từ chối (Nhánh 0-Tổng đài viên)": 37,
            "Nhỡ do không bắt máy (Nhánh 0-Tổng đài viên)": 38,
            "Số cuộc gọi đến (Nhánh 1-Cấp cứu)": 39,
            "Nhỡ do từ chối (Nhánh 1-Cấp cứu)": 40,
            "Nhỡ do không bắt máy (Nhánh 1-Cấp cứu)": 41,
            "Số cuộc gọi đến (Nhánh 2-Tư vấn Thuốc)": 42,
            "Nhỡ do từ chối (Nhánh 2- Tư vấn Thuốc)": 43,
            "Nhỡ do không bắt máy (Nhánh 2-Tư vấn Thuốc)": 44,
            "Số cuộc gọi đến (Nhánh 3-PKQT)": 45,
            "Nhỡ do từ chối (Nhánh 3-PKQT)": 46,
            "Nhỡ do không bắt máy  (Nhánh 3-PKQT)": 47,
            "Số cuộc gọi đến (Nhánh 4-Vấn đề khác)": 48,
            "Nhỡ do từ chối (Nhánh 4-Vấn đề khác)": 49,
            "Nhỡ do không bắt máy (Nhánh 4-Vấn đề khác)": 50,
            "Hottline": 51,
            
            # Hệ thống thư ký Bệnh viện
            "Số thư ký được sơ tuyển": 52,
            "Số thư ký được tuyển dụng": 53,
            "Số thư ký nhận việc": 54,
            "Số thư ký nghỉ việc": 55,
            "Số thư ký được điều động": 56,
            "Tổng số thư ký": 57,
            "- Thư ký hành chính": 58,
            "- Thư ký chuyên môn": 59,
            "Số buổi sinh hoạt cho thư ký": 60,
            "Số thư ký tham gia sinh hoạt": 61,
            "Số buổi tập huấn, đào tạo cho thư ký": 62,
            "Số thư ký tham gia tập huấn, đào tạo": 63,
            "Số buổi tham quan, học tập": 64,
            "Số thư ký tham gia tham quan, học tập": 65,
            
            # Bãi giữ xe
            "Tổng số lượt vé ngày": 66,
            "Tổng số lượt vé tháng": 67,
            "Công suất trung bình/ngày": 68,
            "Doanh thu": 69,
            "Số phản ánh khiếu nại": 70
        }
        
    def load_data(self, file_path):
        """Đọc dữ liệu từ file Excel và áp dụng thứ tự ưu tiên"""
        try:
            # Đọc file từ đường dẫn local
            if isinstance(file_path, str):
                self.data = pd.read_excel(file_path)
            else:
                # Nếu là uploaded file
                self.data = pd.read_excel(file_path)
                
            self.data.columns = self.data.columns.str.strip()
            
            # Chuyển đổi kiểu dữ liệu
            self.data['Tuần'] = pd.to_numeric(self.data['Tuần'], errors='coerce')
            self.data['Tháng'] = pd.to_numeric(self.data['Tháng'], errors='coerce')
            self.data['Số liệu'] = pd.to_numeric(self.data['Số liệu'], errors='coerce')
            
            # Thêm cột năm (có thể điều chỉnh theo dữ liệu thực tế)
            if 'Năm' not in self.data.columns:
                self.data['Năm'] = datetime.now().year
            
            # Tạo cột Quý từ Tháng
            self.data['Quý'] = ((self.data['Tháng'] - 1) // 3) + 1
            
            # Tạo cột kết hợp để dễ filter
            self.data['Tháng_Năm'] = self.data.apply(lambda x: f"T{int(x['Tháng'])}/{int(x['Năm'])}", axis=1)
            self.data['Tuần_Tháng'] = self.data.apply(lambda x: f"W{int(x['Tuần'])}-T{int(x['Tháng'])}", axis=1)
            
            # ÁP DỤNG THỨ TỰ ƯU TIÊN
            self._apply_priority_order()
            
            # TÍNH TỶ LỆ SO VỚI TUẦN TRƯỚC
            self._calculate_week_over_week_ratio()
            
            return True
        except Exception as e:
            st.error(f"Lỗi khi đọc file: {str(e)}")
            return False
    
    def _apply_priority_order(self):
        """Áp dụng thứ tự ưu tiên cho danh mục và nội dung"""
        # Thêm cột thứ tự ưu tiên cho danh mục
        self.data['Danh_mục_thứ_tự'] = self.data['Danh mục'].map(self.category_priority)
        
        # Thêm cột thứ tự ưu tiên cho nội dung
        self.data['Nội_dung_thứ_tự'] = self.data['Nội dung'].map(self.content_priority)
        
        # Gán thứ tự cao (999) cho các danh mục/nội dung không có trong danh sách ưu tiên
        self.data['Danh_mục_thứ_tự'] = self.data['Danh_mục_thứ_tự'].fillna(999)
        self.data['Nội_dung_thứ_tự'] = self.data['Nội_dung_thứ_tự'].fillna(999)
        
        # Sắp xếp dữ liệu theo thứ tự ưu tiên
        self.data = self.data.sort_values([
            'Danh_mục_thứ_tự', 
            'Nội_dung_thứ_tự', 
            'Năm', 
            'Tháng', 
            'Tuần'
        ]).reset_index(drop=True)
    
    def _calculate_week_over_week_ratio(self):
        """Tính tỷ lệ so với tuần trước - LOGIC MỚI"""
        # Khởi tạo cột
        self.data['Tỷ_lệ_tuần_trước'] = None
        self.data['Thay_đổi_tuần_trước'] = None
        
        # Group theo danh mục và nội dung, sau đó tính biến động
        for (category, content), group in self.data.groupby(['Danh mục', 'Nội dung']):
            # Sắp xếp theo năm, tháng, tuần
            group_sorted = group.sort_values(['Năm', 'Tháng', 'Tuần']).reset_index()
            
            # Bỏ qua tuần đầu tiên (không có tuần trước để so sánh)
            for i in range(1, len(group_sorted)):
                current_idx = group_sorted.loc[i, 'index']  # index gốc trong data
                current_value = group_sorted.loc[i, 'Số liệu']
                previous_value = group_sorted.loc[i-1, 'Số liệu']
                
                # Tính biến động
                if pd.notna(current_value) and pd.notna(previous_value):
                    if previous_value != 0:
                        # Công thức: (tuần hiện tại - tuần trước) / tuần trước * 100
                        ratio = ((current_value - previous_value) / previous_value) * 100
                        change = current_value - previous_value
                        
                        self.data.loc[current_idx, 'Tỷ_lệ_tuần_trước'] = ratio
                        self.data.loc[current_idx, 'Thay_đổi_tuần_trước'] = change
                    elif previous_value == 0 and current_value > 0:
                        # Tăng từ 0 lên số dương
                        self.data.loc[current_idx, 'Tỷ_lệ_tuần_trước'] = 999.0  # Vô hạn
                        self.data.loc[current_idx, 'Thay_đổi_tuần_trước'] = current_value
                    # Trường hợp khác (0->0, hoặc giá trị âm) giữ None
    
    def create_pivot_settings(self):
        """Tạo cài đặt cho pivot table"""
        st.sidebar.header("⚙️ Cài đặt Pivot Table")
        
        # Chọn kiểu báo cáo
        report_type = st.sidebar.selectbox(
            "Kiểu báo cáo",
            ["Theo Tuần", "Theo Tháng", "Theo Quý", "Theo Năm", "Tùy chỉnh"]
        )
        
        # Chọn dòng và cột cho pivot
        col1, col2 = st.sidebar.columns(2)
        
        available_dims = ['Tuần', 'Tháng', 'Quý', 'Năm', 'Danh mục', 'Nội dung']
        
        with col1:
            rows = st.multiselect(
                "Chọn dòng (Rows)",
                available_dims,
                default=['Danh mục'] if report_type == "Tùy chỉnh" else self._get_default_rows(report_type)
            )
        
        with col2:
            cols = st.multiselect(
                "Chọn cột (Columns)",
                [dim for dim in available_dims if dim not in rows],
                default=self._get_default_cols(report_type)
            )
        
        # Chọn giá trị và phép tính
        values = st.sidebar.selectbox(
            "Giá trị hiển thị",
            ["Số liệu"]
        )
        
        agg_func = st.sidebar.selectbox(
            "Phép tính",
            ["sum", "mean", "count", "min", "max"],
            format_func=lambda x: {
                'sum': 'Tổng',
                'mean': 'Trung bình',
                'count': 'Đếm',
                'min': 'Nhỏ nhất',
                'max': 'Lớn nhất'
            }.get(x, x)
        )
        
        # Hiển thị biến động gộp vào giá trị
        show_ratio_inline = st.sidebar.checkbox("Hiển thị biến động trong giá trị", value=True)
        
        return report_type, rows, cols, values, agg_func, show_ratio_inline
    
    def _get_default_rows(self, report_type):
        """Lấy dòng mặc định theo kiểu báo cáo"""
        defaults = {
            "Theo Tuần": ['Danh mục', 'Nội dung'],
            "Theo Tháng": ['Danh mục'],
            "Theo Quý": ['Danh mục'],
            "Theo Năm": ['Danh mục']
        }
        return defaults.get(report_type, ['Danh mục'])
    
    def _get_default_cols(self, report_type):
        """Lấy cột mặc định theo kiểu báo cáo"""
        defaults = {
            "Theo Tuần": ['Tuần'],
            "Theo Tháng": ['Tháng'],
            "Theo Quý": ['Quý'],
            "Theo Năm": ['Năm']
        }
        return defaults.get(report_type, ['Tháng'])
    
    def create_filters(self):
        """Tạo bộ lọc dữ liệu"""
        st.sidebar.header("🔍 Lọc dữ liệu")
        
        # Lọc theo thời gian
        time_range = st.sidebar.select_slider(
            "Khoảng thời gian",
            options=["1 Tuần", "1 Tháng", "3 Tháng", "6 Tháng", "1 Năm", "Tất cả"],
            value="1 Tháng"
        )
        
        # Lọc theo năm
        years = sorted(self.data['Năm'].unique())
        selected_years = st.sidebar.multiselect(
            "Chọn năm",
            years,
            default=[max(years)]
        )
        
        # Lọc theo tháng
        if len(selected_years) == 1:
            months = sorted(self.data[self.data['Năm'].isin(selected_years)]['Tháng'].unique())
            selected_months = st.sidebar.multiselect(
                "Chọn tháng",
                months,
                default=months
            )
        else:
            selected_months = list(range(1, 13))
        
        # Lọc theo tuần
        if len(selected_years) == 1 and len(selected_months) == 1:
            available_weeks = sorted(self.data[
                (self.data['Năm'].isin(selected_years)) & 
                (self.data['Tháng'].isin(selected_months))
            ]['Tuần'].unique())
            
            selected_weeks = st.sidebar.multiselect(
                "Chọn tuần",
                available_weeks,
                default=available_weeks
            )
        else:
            selected_weeks = list(range(1, 53))
        
        # Lọc theo danh mục - Hiển thị theo thứ tự ưu tiên
        unique_categories = self.data['Danh mục'].unique()
        
        # Sắp xếp danh mục theo thứ tự ưu tiên
        sorted_categories = sorted(unique_categories, 
                                 key=lambda x: self.category_priority.get(x, 999))
        
        selected_categories = []
        
        with st.sidebar.expander("📂 Chọn danh mục", expanded=True):
            select_all = st.checkbox("Chọn tất cả danh mục", value=True)
            
            if select_all:
                selected_categories = list(sorted_categories)
            else:
                for category in sorted_categories:
                    # Lấy danh sách nội dung trong danh mục này (đã sắp xếp)
                    contents_in_category = self.data[self.data['Danh mục'] == category]['Nội dung'].unique()
                    sorted_contents = sorted(contents_in_category, 
                                           key=lambda x: self.content_priority.get(x, 999))
                    
                    # Checkbox cho danh mục cha
                    category_selected = st.checkbox(
                        f"📁 {category}", 
                        value=False,
                        key=f"cat_{category}"
                    )
                    
                    if category_selected:
                        selected_categories.append(category)
                        
                        # Hiển thị nội dung con theo thứ tự ưu tiên
                        st.markdown(f"**Nội dung trong {category}:**")
                        for content in sorted_contents:
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;📄 {content}", unsafe_allow_html=True)
        
        return time_range, selected_years, selected_months, selected_weeks, selected_categories
    
    def filter_data(self, time_range, years, months, weeks, categories):
        """Áp dụng bộ lọc"""
        filtered = self.data.copy()
        
        # Lọc theo năm, tháng, tuần, danh mục
        filtered = filtered[
            (filtered['Năm'].isin(years)) &
            (filtered['Tháng'].isin(months)) &
            (filtered['Tuần'].isin(weeks)) &
            (filtered['Danh mục'].isin(categories))
        ]
        
        return filtered
    
    def format_value_with_change(self, value, ratio, change):
        """Định dạng giá trị với biến động inline - CẢI TIẾN ĐỂ HIỂN THỊ RÕ RÀNG HƠN"""
        # Đảm bảo hiển thị số đầy đủ
        value_str = f"{value:,.0f}".replace(',', '.')
        
        if pd.isna(ratio) or ratio == 0:
            return value_str
        
        if ratio == 999:  # Vô hạn
            return f"{value_str} <span class='positive-change'>↑∞%</span>"
        
        if ratio > 0:
            symbol = "↑"
            color_class = "positive-change"
        elif ratio < 0:
            symbol = "↓"  
            color_class = "negative-change"
        else:
            symbol = "→"
            color_class = "no-change"
            
        ratio_text = f"{abs(ratio):.1f}%"
        
        # FORMAT RÕ RÀNG: số (biến động)
        return f"{value_str} <span class='{color_class}'>({symbol}{ratio_text})</span>"
    
    def create_hierarchical_pivot_table_with_ratio(self, data, rows, cols, values, agg_func, show_ratio_inline):
        """Tạo pivot table với hiển thị phân cấp và biến động inline"""
        try:
            if not rows and not cols:
                st.warning("Vui lòng chọn ít nhất một chiều cho dòng hoặc cột")
                return None
            
            # Đảm bảo dữ liệu đã được sắp xếp theo thứ tự ưu tiên
            if 'Danh mục' in rows:
                data = data.sort_values(['Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'])
            
            # Tạo pivot table cho giá trị chính (KHÔNG margins=True để bỏ tổng chung)
            if cols:
                pivot = pd.pivot_table(
                    data,
                    index=rows if rows else None,
                    columns=cols,
                    values=values,
                    aggfunc=agg_func,
                    fill_value=0,
                    margins=False  # BỎ TỔNG CHUNG
                )
                
                # Sửa lỗi mixed column types
                if isinstance(pivot.columns, pd.MultiIndex):
                    pivot.columns = pivot.columns.map(str)
                else:
                    pivot.columns = [str(col) for col in pivot.columns]
                    
            else:
                pivot = data.groupby(rows)[values].agg(agg_func)
            
            # Nếu cần hiển thị biến động inline
            if show_ratio_inline and cols:
                # Lọc dữ liệu có biến động (không phải tuần đầu tiên)
                ratio_data = data[pd.notna(data['Tỷ_lệ_tuần_trước'])].copy()
                
                st.sidebar.success(f"🔍 Debug: {len(ratio_data)} dòng có biến động từ {len(data)} dòng tổng")
                
                if not ratio_data.empty:
                    try:
                        # Tạo pivot table cho giá trị gốc
                        main_pivot = pd.pivot_table(
                            data,
                            index=rows if rows else None,
                            columns=cols,
                            values='Số liệu',
                            aggfunc=agg_func,
                            fill_value=0,
                            margins=False
                        )
                        
                        # Tạo pivot table cho tỷ lệ biến động
                        ratio_pivot = pd.pivot_table(
                            ratio_data,
                            index=rows if rows else None,
                            columns=cols,
                            values='Tỷ_lệ_tuần_trước',
                            aggfunc='mean',  # Trung bình nếu có nhiều giá trị
                            fill_value=None
                        )
                        
                        st.sidebar.success(f"🔍 Ratio pivot: {ratio_pivot.shape}, Main pivot: {main_pivot.shape}")
                        
                        # Tạo combined pivot với biến động
                        combined_pivot = main_pivot.copy()
                        
                        # Áp dụng biến động cho từng ô
                        for idx in main_pivot.index:
                            for col in main_pivot.columns:
                                main_value = main_pivot.loc[idx, col]
                                
                                # Kiểm tra có biến động không
                                if idx in ratio_pivot.index and col in ratio_pivot.columns:
                                    ratio_val = ratio_pivot.loc[idx, col]
                                    if pd.notna(ratio_val):
                                        # Có biến động - format với %
                                        combined_pivot.loc[idx, col] = self.format_value_with_change(main_value, ratio_val, 0)
                                        continue
                                
                                # Không có biến động - chỉ hiển thị số
                                combined_pivot.loc[idx, col] = f"{main_value:,.0f}".replace(',', '.')
                        
                        # THÊM CỘT TỔNG
                        combined_pivot['Tổng'] = ""
                        for idx in combined_pivot.index:
                            row_total = 0
                            for col in main_pivot.columns:  # Dùng main_pivot để tính tổng
                                val = main_pivot.loc[idx, col]
                                if pd.notna(val):
                                    row_total += float(val)
                            combined_pivot.loc[idx, 'Tổng'] = f"{row_total:,.0f}".replace(',', '.')
                        
                        return combined_pivot
                        
                    except Exception as e:
                        st.sidebar.error(f"Lỗi tạo biến động: {str(e)}")
                        st.sidebar.error(f"Chi tiết: {type(e).__name__}")
                        pass
            
            # Nếu không có biến động, vẫn thêm cột tổng
            if isinstance(pivot, pd.DataFrame):
                pivot_with_total = pivot.copy()
                pivot_with_total['Tổng'] = 0
                for idx in pivot_with_total.index:
                    row_total = 0
                    for col in pivot_with_total.columns:
                        if col != 'Tổng':
                            val = pivot.loc[idx, col]
                            if pd.notna(val):
                                row_total += float(val)
                    pivot_with_total.loc[idx, 'Tổng'] = f"{row_total:,.0f}".replace(',', '.')
                return pivot_with_total
            
            return pivot
            
        except Exception as e:
            st.error(f"Lỗi tạo pivot table: {str(e)}")
            return None
    
    def display_category_sparklines(self, category_data, category_name, report_type):
        """Hiển thị sparklines cho từng nội dung trong danh mục"""
        try:
            if not isinstance(category_data, pd.DataFrame):
                return
            
            # Tạo sparklines cho từng nội dung trong danh mục
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown("**Nội dung**")
            with col2:
                st.markdown("**Xu hướng**")
            with col3:
                st.markdown("**Tổng hàng**")
            
            for content in category_data.index:
                # Lấy dữ liệu cho nội dung này
                content_values = []
                for col in category_data.columns:
                    val = category_data.loc[content, col]
                    if isinstance(val, str):
                        # Extract số từ HTML
                        import re
                        numbers = re.findall(r'[\d.]+', val.replace('.', ''))
                        if numbers:
                            content_values.append(int(numbers[0].replace('.', '')))
                        else:
                            content_values.append(0)
                    else:
                        content_values.append(val if pd.notna(val) else 0)
                
                # Tạo sparkline
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    y=content_values,
                    mode='lines+markers',
                    line=dict(width=2, color='royalblue'),
                    marker=dict(size=3),
                    showlegend=False
                ))
                
                # Highlight max/min
                if content_values and max(content_values) > 0:
                    max_idx = np.argmax(content_values)
                    min_idx = np.argmin(content_values)
                    
                    fig.add_trace(go.Scatter(
                        x=[max_idx], y=[content_values[max_idx]],
                        mode='markers', marker=dict(size=5, color='green'),
                        showlegend=False
                    ))
                    fig.add_trace(go.Scatter(
                        x=[min_idx], y=[content_values[min_idx]],
                        mode='markers', marker=dict(size=5, color='red'),
                        showlegend=False
                    ))
                
                fig.update_layout(
                    margin=dict(l=0, r=0, t=0, b=0),
                    height=40, width=200,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                    yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                    hovermode=False
                )
                
                # Tính tổng hàng
                row_total = sum(content_values)
                
                # Hiển thị
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"📄 {content}")
                with col2:
                    st.plotly_chart(fig, use_container_width=True, key=f"spark_{category_name}_{content}")
                with col3:
                    st.markdown(f"**{row_total:,.0f}**".replace(',', '.'))
                    
        except Exception as e:
            st.error(f"Lỗi tạo sparkline cho {category_name}: {str(e)}")
    
    def display_hierarchical_pivot_improved(self, pivot, data):
        """Hiển thị pivot table với cấu trúc phân cấp cải tiến"""
        if pivot is None:
            return
        
        # Kiểm tra xem có phải pivot table với Danh mục không
        if isinstance(pivot.index, pd.MultiIndex) and 'Danh mục' in pivot.index.names:
            # Hiển thị theo cấu trúc phân cấp
            st.subheader("📊 Pivot Table theo thứ tự ưu tiên (có biến động)")
            
            # Lấy danh sách các danh mục theo thứ tự ưu tiên
            categories = pivot.index.get_level_values('Danh mục').unique()
            sorted_categories = sorted(categories, key=lambda x: self.category_priority.get(x, 999))
            
            for category in sorted_categories:
                # Tạo expander cho mỗi danh mục (BỎ HIỂN THỊ SỐ ƯU TIÊN)
                with st.expander(f"📁 {category}", expanded=True):
                    # Lọc dữ liệu cho danh mục này
                    category_data = pivot.xs(category, level='Danh mục')
                    
                    # Sắp xếp theo thứ tự ưu tiên nội dung
                    if isinstance(category_data.index, pd.Index):
                        # Lấy danh sách nội dung và sắp xếp
                        contents = category_data.index.tolist()
                        sorted_contents = sorted(contents, key=lambda x: self.content_priority.get(x, 999))
                        category_data = category_data.reindex(sorted_contents)
                    
                    # Tạo HTML table để hiển thị đầy đủ số và biến động
                    if isinstance(category_data, pd.DataFrame):
                        # Tạo HTML table để hiển thị đầy đủ số và biến động
                        html_table = "<div class='full-width-table'>"
                        html_table += "<table style='width:100%; border-collapse: collapse; font-size: 12px;'>"
                        
                        # Header
                        html_table += "<tr style='background-color: #f0f2f6;'>"
                        html_table += "<th style='border: 1px solid #ddd; padding: 8px; text-align: left; min-width: 250px; position: sticky; left: 0; background-color: #f0f2f6; z-index: 10;'>Nội dung</th>"
                        for col in category_data.columns:
                            if col == 'Tổng':
                                html_table += f"<th style='border: 1px solid #ddd; padding: 8px; text-align: center; min-width: 120px; position: sticky; right: 0; background-color: #f0f2f6; z-index: 10; font-weight: bold;'>{col}</th>"
                            else:
                                html_table += f"<th style='border: 1px solid #ddd; padding: 8px; text-align: center; min-width: 150px;'>{col}</th>"
                        html_table += "</tr>"
                        
                        # Data rows
                        for content in category_data.index:
                            html_table += "<tr>"
                            html_table += f"<td style='border: 1px solid #ddd; padding: 8px; font-weight: bold; position: sticky; left: 0; background-color: #f8f9fa; z-index: 10;'>{content}</td>"
                            
                            for col in category_data.columns:
                                value = category_data.loc[content, col]
                                if col == 'Tổng':
                                    html_table += f"<td style='border: 1px solid #ddd; padding: 8px; text-align: right; position: sticky; right: 0; background-color: #e9ecef; z-index: 10; font-weight: bold;' class='number-cell'>{value}</td>"
                                else:
                                    html_table += f"<td style='border: 1px solid #ddd; padding: 8px; text-align: right;' class='number-cell'>{value}</td>"
                            
                            html_table += "</tr>"
                        
                        html_table += "</table></div>"
                        st.markdown(html_table, unsafe_allow_html=True)
                        
                        # SPARKLINE CHO DANH MỤC
                        st.markdown("**📊 Xu hướng cho danh mục này:**")
                        
                        # Hiển thị sparklines inline cho danh mục này
                        try:
                            # Header
                            html_table += "<tr style='background-color: #f0f2f6;'>"
                            html_table += "<th style='border: 1px solid #ddd; padding: 8px; text-align: left; min-width: 250px; position: sticky; left: 0; background-color: #f0f2f6; z-index: 10;'>Nội dung</th>"
                            html_table += "<th style='border: 1px solid #ddd; padding: 8px; text-align: center; min-width: 150px;'>Xu hướng</th>"
                            html_table += "<th style='border: 1px solid #ddd; padding: 8px; text-align: center; min-width: 120px; position: sticky; right: 0; background-color: #f0f2f6; z-index: 10;'>Tổng hàng</th>"
                            html_table += "</tr>"
                            
                            # Tạo bảng HTML cho sparklines
                            sparkline_html = "<div class='full-width-table'>"
                            sparkline_html += "<table style='width:100%; border-collapse: collapse; font-size: 12px;'>"
                            
                            # Header
                            sparkline_html += "<tr style='background-color: #f0f2f6;'>"
                            sparkline_html += "<th style='border: 1px solid #ddd; padding: 8px; text-align: left; min-width: 250px; position: sticky; left: 0; background-color: #f0f2f6; z-index: 10;'>Nội dung</th>"
                            sparkline_html += "<th style='border: 1px solid #ddd; padding: 8px; text-align: center; min-width: 150px;'>Xu hướng</th>"
                            sparkline_html += "<th style='border: 1px solid #ddd; padding: 8px; text-align: center; min-width: 120px; position: sticky; right: 0; background-color: #f0f2f6; z-index: 10;'>Tổng hàng</th>"
                            sparkline_html += "</tr>"
                            
                            sparkline_rows = []
                            
                            for content in category_data.index:
                                # Lấy dữ liệu cho nội dung này
                                content_values = []
                                for col in category_data.columns:
                                    if col != 'Tổng':  # Bỏ qua cột Tổng khi tính sparkline
                                        val = category_data.loc[content, col]
                                        if isinstance(val, str):
                                            # Extract số từ HTML
                                            import re
                                            numbers = re.findall(r'[\d.]+', val.replace('.', ''))
                                            if numbers:
                                                content_values.append(int(numbers[0].replace('.', '')))
                                            else:
                                                content_values.append(0)
                                        else:
                                            content_values.append(val if pd.notna(val) else 0)
                                
                                # Tạo sparkline
                                fig = go.Figure()
                                fig.add_trace(go.Scatter(
                                    y=content_values,
                                    mode='lines+markers',
                                    line=dict(width=2, color='royalblue'),
                                    marker=dict(size=3),
                                    showlegend=False
                                ))
                                
                                # Highlight max/min
                                if content_values and max(content_values) > 0:
                                    max_idx = np.argmax(content_values)
                                    min_idx = np.argmin(content_values)
                                    
                                    fig.add_trace(go.Scatter(
                                        x=[max_idx], y=[content_values[max_idx]],
                                        mode='markers', marker=dict(size=5, color='green'),
                                        showlegend=False
                                    ))
                                    fig.add_trace(go.Scatter(
                                        x=[min_idx], y=[content_values[min_idx]],
                                        mode='markers', marker=dict(size=5, color='red'),
                                        showlegend=False
                                    ))
                                
                                fig.update_layout(
                                    margin=dict(l=0, r=0, t=0, b=0),
                                    height=40, width=200,
                                    paper_bgcolor='rgba(0,0,0,0)',
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                                    yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                                    hovermode=False
                                )
                                
                                # Lấy tổng hàng từ cột Tổng
                                row_total = category_data.loc[content, 'Tổng'] if 'Tổng' in category_data.columns else sum(content_values)
                                
                                # Tạo row cho bảng và lưu figure
                                sparkline_rows.append({
                                    'content': content,
                                    'fig': fig,
                                    'total': row_total
                                })
                            
                            # Kết thúc HTML table header
                            sparkline_html += "</table></div>"
                            st.markdown(sparkline_html, unsafe_allow_html=True)
                            
                            # Hiển thị từng row với sparkline
                            for row_data in sparkline_rows:
                                col1, col2, col3 = st.columns([3, 2, 1])
                                with col1:
                                    st.markdown(f"📄 {row_data['content']}")
                                with col2:
                                    st.plotly_chart(row_data['fig'], use_container_width=True, key=f"spark_{category}_{row_data['content']}")
                                with col3:
                                    if isinstance(row_data['total'], str):
                                        st.markdown(f"**{row_data['total']}**")
                                    else:
                                        st.markdown(f"**{row_data['total']:,.0f}**".replace(',', '.'))
                                    
                        except Exception as e:
                            st.error(f"Lỗi tạo sparkline cho {category}: {str(e)}")
                        
                    else:
                        # Nếu là Series
                        html_table = "<div class='full-width-table'>"
                        html_table += "<table style='width:100%; border-collapse: collapse; font-size: 12px;'>"
                        html_table += "<tr style='background-color: #f0f2f6;'>"
                        html_table += "<th style='border: 1px solid #ddd; padding: 8px;'>Danh mục</th>"
                        html_table += "<th style='border: 1px solid #ddd; padding: 8px;'>Giá trị</th>"
                        html_table += "</tr>"
                        html_table += "<tr>"
                        html_table += f"<td style='border: 1px solid #ddd; padding: 8px;'>{category}</td>"
                        html_table += f"<td style='border: 1px solid #ddd; padding: 8px; text-align: right;' class='number-cell'>{category_data}</td>"
                        html_table += "</tr>"
                        html_table += "</table></div>"
                        st.markdown(html_table, unsafe_allow_html=True)
                    
                    # BỎ TỔNG THEO DANH MỤC - chỉ giữ tổng theo nội dung (hàng)
        
        elif 'Danh mục' in pivot.index.names:
            # Hiển thị pivot table đơn giản với Danh mục
            st.subheader("📊 Pivot Table theo Danh mục (theo thứ tự ưu tiên)")
            
            # Nhóm theo danh mục và sắp xếp theo thứ tự ưu tiên
            categories = pivot.index.unique()
            sorted_categories = sorted(categories, key=lambda x: self.category_priority.get(x, 999))
            
            for category in sorted_categories:
                with st.expander(f"📁 {category}", expanded=True):
                    category_data = pivot.loc[category]
                    
                    if isinstance(category_data, pd.Series):
                        html_table = "<table style='width:100%; border-collapse: collapse;'>"
                        html_table += "<tr style='background-color: #f0f2f6;'>"
                        html_table += "<th style='border: 1px solid #ddd; padding: 8px;'>Danh mục</th>"
                        html_table += "<th style='border: 1px solid #ddd; padding: 8px;'>Giá trị</th>"
                        html_table += "</tr>"
                        html_table += "<tr>"
                        html_table += f"<td style='border: 1px solid #ddd; padding: 8px;'>{category}</td>"
                        html_table += f"<td style='border: 1px solid #ddd; padding: 8px; text-align: right;' class='number-cell'>{category_data:,.0f}".replace(',', '.') + "</td>"
                        html_table += "</tr>"
                        html_table += "</table>"
                        st.markdown(html_table, unsafe_allow_html=True)
                    else:
                        # DataFrame case
                        html_table = "<div class='full-width-table'>"
                        html_table += "<table style='width:100%; border-collapse: collapse; font-size: 12px;'>"
                        html_table += "<tr style='background-color: #f0f2f6;'>"
                        html_table += "<th style='border: 1px solid #ddd; padding: 8px;'>Nội dung</th>"
                        for col in category_data.columns:
                            html_table += f"<th style='border: 1px solid #ddd; padding: 8px; text-align: center;'>{col}</th>"
                        html_table += "</tr>"
                        
                        for idx in category_data.index:
                            html_table += "<tr>"
                            html_table += f"<td style='border: 1px solid #ddd; padding: 8px;'>{idx}</td>"
                            for col in category_data.columns:
                                value = category_data.loc[idx, col]
                                html_table += f"<td style='border: 1px solid #ddd; padding: 8px; text-align: right;' class='number-cell'>{value}</td>"
                            html_table += "</tr>"
                        
                        html_table += "</table></div>"
                        st.markdown(html_table, unsafe_allow_html=True)
        
        else:
            # Hiển thị pivot table thông thường
            st.subheader("📊 Pivot Table")
            
            # Tạo HTML table cho pivot thông thường
            html_table = "<div class='full-width-table'>"
            html_table += "<table style='width:100%; border-collapse: collapse; font-size: 12px;'>"
            
            # Header
            html_table += "<tr style='background-color: #f0f2f6;'>"
            html_table += "<th style='border: 1px solid #ddd; padding: 8px;'>Index</th>"
            if isinstance(pivot, pd.DataFrame):
                for col in pivot.columns:
                    html_table += f"<th style='border: 1px solid #ddd; padding: 8px; text-align: center;'>{col}</th>"
            else:
                html_table += "<th style='border: 1px solid #ddd; padding: 8px; text-align: center;'>Giá trị</th>"
            html_table += "</tr>"
            
            # Data
            if isinstance(pivot, pd.DataFrame):
                for idx in pivot.index:
                    html_table += "<tr>"
                    html_table += f"<td style='border: 1px solid #ddd; padding: 8px;'>{idx}</td>"
                    for col in pivot.columns:
                        value = pivot.loc[idx, col]
                        html_table += f"<td style='border: 1px solid #ddd; padding: 8px; text-align: right;' class='number-cell'>{value}</td>"
                    html_table += "</tr>"
            else:
                for idx in pivot.index:
                    html_table += "<tr>"
                    html_table += f"<td style='border: 1px solid #ddd; padding: 8px;'>{idx}</td>"
                    value_formatted = f"{pivot.loc[idx]:,.0f}".replace(',', '.')
                    html_table += f"<td style='border: 1px solid #ddd; padding: 8px; text-align: right;' class='number-cell'>{value_formatted}</td>"
                    html_table += "</tr>"
            
            html_table += "</table></div>"
            st.markdown(html_table, unsafe_allow_html=True)
    
            html_table += "</table></div>"
            st.markdown(html_table, unsafe_allow_html=True)
    
    def create_sparkline_charts(self, pivot, report_type):
        """Tạo biểu đồ sparkline cho mỗi dòng trong pivot table"""
        if pivot is None or not isinstance(pivot, pd.DataFrame):
            return None
        
        # Xác định cột thời gian dựa vào report_type
        time_column_name = {
            "Theo Tuần": "Tuần",
            "Theo Tháng": "Tháng",
            "Theo Quý": "Quý",
            "Theo Năm": "Năm"
        }.get(report_type, "Tháng")
        
        # Tạo dataframe cho biểu đồ
        sparklines_data = {}
        
        # Reset index để dễ dàng xử lý
        if isinstance(pivot.index, pd.MultiIndex):
            pivot_reset = pivot.reset_index()
        else:
            pivot_reset = pivot.reset_index()
            
        # Lấy tên của các cột chứa giá trị
        value_columns = [col for col in pivot.columns 
                         if not isinstance(col, tuple) or time_column_name in col]
        
        # Tạo sparkline cho mỗi dòng
        for idx, row in pivot_reset.iterrows():
                
            # Lấy tên hàng
            if isinstance(pivot.index, pd.MultiIndex):
                row_key = tuple(row[list(pivot.index.names)])
            else:
                row_key = row[pivot.index.name]
                
            # Lấy giá trị cho sparkline (extract từ HTML nếu cần)
            values = []
            for col in value_columns:
                try:
                    if col in pivot.columns:
                        val = pivot.loc[row_key, col]
                        # Nếu là chuỗi HTML, lấy số đầu tiên
                        if isinstance(val, str):
                            import re
                            numbers = re.findall(r'[\d.]+', val.replace('.', ''))
                            if numbers:
                                values.append(int(numbers[0].replace('.', '')))
                            else:
                                values.append(0)
                        else:
                            values.append(val)
                except:
                    values.append(0)
            
            # Tạo sparkline figure
            fig = go.Figure()
            
            # Thêm line chart
            fig.add_trace(go.Scatter(
                y=values,
                mode='lines+markers',
                line=dict(width=2, color='royalblue'),
                marker=dict(size=4),
                showlegend=False
            ))
            
            # Highlight điểm cao nhất
            if values:
                max_idx = np.argmax(values)
                fig.add_trace(go.Scatter(
                    x=[max_idx],
                    y=[values[max_idx]],
                    mode='markers',
                    marker=dict(size=6, color='green'),
                    showlegend=False
                ))
                
                # Highlight điểm thấp nhất
                min_idx = np.argmin(values)
                fig.add_trace(go.Scatter(
                    x=[min_idx],
                    y=[values[min_idx]],
                    mode='markers',
                    marker=dict(size=6, color='red'),
                    showlegend=False
                ))
            
            # Định dạng figure
            fig.update_layout(
                margin=dict(l=0, r=0, t=0, b=0),
                height=30,
                width=150,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(
                    showticklabels=False,
                    showgrid=False,
                    zeroline=False
                ),
                yaxis=dict(
                    showticklabels=False,
                    showgrid=False,
                    zeroline=False
                ),
                hovermode=False
            )
            
            # Lưu figure
            sparklines_data[row_key] = fig
            
        return sparklines_data
    
    def create_individual_trend_chart(self, data, content_item, time_col, chart_type="Đường", normalize=False):
        """Tạo biểu đồ xu hướng riêng cho một nội dung cụ thể"""
        try:
            # Lọc dữ liệu cho nội dung được chọn
            content_data = data[data['Nội dung'] == content_item]
            
            if content_data.empty:
                return None
                
            # Tạo pivot table cho nội dung này
            pivot_data = pd.pivot_table(
                content_data,
                index='Nội dung',
                columns=time_col,
                values='Số liệu',
                aggfunc='sum',
                fill_value=0
            )
            
            # Lấy giá trị cho biểu đồ
            time_values = list(pivot_data.columns)
            data_values = pivot_data.iloc[0].values
            
            # Chuẩn hóa dữ liệu nếu cần
            if normalize and max(data_values) > 0:
                data_values = data_values / max(data_values) * 100
            
            # BỎ HIỂN THỊ SỐ ƯU TIÊN
            title = f"{content_item}"
            
            # Tạo biểu đồ tương ứng với loại đã chọn
            if chart_type == "Đường":
                fig = px.line(
                    x=time_values,
                    y=data_values,
                    markers=True,
                    title=title
                )
                
                # Thêm điểm cao nhất và thấp nhất
                if len(data_values) > 0:
                    max_idx = np.argmax(data_values)
                    fig.add_trace(go.Scatter(
                        x=[time_values[max_idx]],
                        y=[data_values[max_idx]],
                        mode='markers',
                        marker=dict(size=10, color='green', symbol='circle'),
                        name='Cao nhất',
                        showlegend=False
                    ))
                    
                    min_idx = np.argmin(data_values)
                    fig.add_trace(go.Scatter(
                        x=[time_values[min_idx]],
                        y=[data_values[min_idx]],
                        mode='markers',
                        marker=dict(size=10, color='red', symbol='circle'),
                        name='Thấp nhất',
                        showlegend=False
                    ))
                
            elif chart_type == "Cột":
                fig = px.bar(
                    x=time_values,
                    y=data_values,
                    title=title
                )
                
                # Highlight cột cao nhất và thấp nhất
                if len(data_values) > 0:
                    max_idx = np.argmax(data_values)
                    min_idx = np.argmin(data_values)
                    
                    bar_colors = ['royalblue'] * len(data_values)
                    bar_colors[max_idx] = 'green'
                    bar_colors[min_idx] = 'red'
                    
                    fig.update_traces(marker_color=bar_colors)
                
            else:  # Vùng
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=time_values,
                    y=data_values,
                    mode='lines',
                    fill='tozeroy',
                    line=dict(color='royalblue'),
                    name=content_item
                ))
                
                # Thêm điểm cao nhất và thấp nhất
                if len(data_values) > 0:
                    max_idx = np.argmax(data_values)
                    fig.add_trace(go.Scatter(
                        x=[time_values[max_idx]],
                        y=[data_values[max_idx]],
                        mode='markers',
                        marker=dict(size=10, color='green', symbol='circle'),
                        name='Cao nhất',
                        showlegend=False
                    ))
                    
                    min_idx = np.argmin(data_values)
                    fig.add_trace(go.Scatter(
                        x=[time_values[min_idx]],
                        y=[data_values[min_idx]],
                        mode='markers',
                        marker=dict(size=10, color='red', symbol='circle'),
                        name='Thấp nhất',
                        showlegend=False
                    ))
                
                fig.update_layout(title=title)
            
            # Cập nhật layout
            y_title = "% (so với giá trị cao nhất)" if normalize else "Giá trị"
            time_col_display = {"Tuần": "Tuần", "Tháng": "Tháng", "Quý": "Quý", "Năm": "Năm"}.get(time_col, time_col)
            
            fig.update_layout(
                xaxis_title=time_col_display,
                yaxis_title=y_title,
                height=300,
                margin=dict(l=10, r=10, t=40, b=40),
                hovermode="x",
                plot_bgcolor='rgba(240,240,240,0.1)'
            )
            
            # Thêm đường xu hướng nếu có đủ dữ liệu
            if len(data_values) > 2:
                x_values = list(range(len(data_values)))
                coeffs = np.polyfit(x_values, data_values, 1)
                trend_line = np.poly1d(coeffs)(x_values)
                
                # Xác định màu đường xu hướng
                trend_color = 'green' if coeffs[0] > 0 else 'red'
                
                if chart_type in ["Đường", "Vùng"]:
                    fig.add_trace(go.Scatter(
                        x=time_values,
                        y=trend_line,
                        mode='lines',
                        line=dict(color=trend_color, dash='dash', width=2),
                        name='Xu hướng',
                        showlegend=False
                    ))
            
            return fig
            
        except Exception as e:
            st.error(f"Lỗi khi tạo biểu đồ cho {content_item}: {str(e)}")
            return None

def main():
    # HEADER VỚI LOGO THẬT
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        # Tự động tìm đường dẫn đúng
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "assets", "logo.png")
        
        # Hiển thị logo từ file
        try:
            if os.path.exists(logo_path):
                # Header với logo căn giữa
                st.markdown("""
                <div style='text-align: center; padding: 30px 0;'>
                """, unsafe_allow_html=True)
                
                # Logo to hơn, căn giữa
                col_left, col_center, col_right = st.columns([1, 1, 1])
                with col_center:
                    st.image(logo_path, width=150)  # Logo to hơn nữa
                
                # Title căn giữa, đơn giản
                st.markdown("""
                    <div style='text-align: center; margin-top: 20px;'>
                        <h1 style='color: #1f77b4; margin: 0; font-size: 3rem; font-weight: bold;'>
                            DASHBOARD PHÒNG HÀNH CHÍNH
                        </h1>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Fallback nếu không có logo - header đẹp với emoji
                st.markdown("""
                <div style='text-align: center; padding: 30px 0;'>
                    <div style='font-size: 5rem; margin-bottom: 20px;'>🏥</div>
                    <h1 style='color: #1f77b4; margin: 0; font-size: 3rem; font-weight: bold;'>
                        DASHBOARD PHÒNG HÀNH CHÍNH
                    </h1>
                </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            # Nếu có lỗi, dùng emoji logo đẹp
            st.markdown("""
            <div style='text-align: center; padding: 30px 0;'>
                <div style='font-size: 5rem; margin-bottom: 20px;'>🏥</div>
                <h1 style='color: #1f77b4; margin: 0; font-size: 3rem; font-weight: bold;'>
                    DASHBOARD PHÒNG HÀNH CHÍNH
                </h1>
            </div>
            """, unsafe_allow_html=True)
        
        # Subtitle chung
        st.markdown("""
        <div style='text-align: center;'>
            <p style='color: #888; font-style: italic; margin-top: 10px;'>
                📊 Với thứ tự ưu tiên cố định và biến động inline
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Thêm thông tin project
    with st.expander("ℹ️ Thông tin về Dashboard", expanded=False):
        st.markdown("""
        **🏥 Dashboard chuyên biệt cho Phòng Hành Chính Bệnh viện**
        
        **✨ Tính năng nổi bật:**
        - 📋 13 danh mục và 70+ nội dung theo thứ tự ưu tiên cố định
        - 📈 Hiển thị biến động tuần (%) ngay trong giá trị: `1.234.567 (↑15%)`
        - 🔒 Cột "Nội dung" và "Tổng" đóng băng khi scroll
        - 📊 Sparkline xu hướng cho từng danh mục
        - 💾 Xuất báo cáo Excel đa sheet và CSV
        
        **👨‍💻 Phát triển bởi:** Dương Hữu Quang - Phòng Hành Chính
        **📅 Phiên bản:** 1.0 - 2025
        **🌐 GitHub:** https://github.com/corner-25/dashboard-phong-hanh-chinh
        """)
    
    # Footer chuyên nghiệp
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 15px; background-color: #f8f9fa; border-radius: 10px; margin-top: 20px;'>
        <p style='margin: 0; font-size: 14px;'>
            🏥 <strong>Phòng Hành Chính - Bệnh Viện</strong> | 
            🌐 <a href="https://github.com/corner-25/dashboard-phong-hanh-chinh" target="_blank" style="text-decoration: none; color: #1f77b4;">GitHub Project</a>
        </p>
        <p style='margin: 5px 0 0 0; font-size: 12px; color: #888;'>
            © 2025 Dashboard Phòng Hành Chính - Phát triển bởi <strong>Dương Hữu Quang</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Khởi tạo dashboard
    dashboard = PivotTableDashboard()
    
    # Load dữ liệu
    st.sidebar.header("📁 Dữ liệu")
    
    # Chọn cách nhập dữ liệu
    data_source = st.sidebar.radio(
        "Chọn nguồn dữ liệu",
        ["Upload file", "Nhập đường dẫn file"]
    )
    
    file_loaded = False
    
    if data_source == "Upload file":
        uploaded_file = st.sidebar.file_uploader("Chọn file Excel", type=['xlsx', 'xls'])
        if uploaded_file is not None:
            if dashboard.load_data(uploaded_file):
                st.sidebar.success("✅ Đã tải dữ liệu thành công!")
                file_loaded = True
    else:
        # Nhập đường dẫn file
        file_path = st.sidebar.text_input(
            "Đường dẫn file Excel",
            value="",
            help="Để trống và sử dụng Upload file ở trên"
        )
        
        if st.sidebar.button("Tải file", use_container_width=True):
            if os.path.exists(file_path):
                if dashboard.load_data(file_path):
                    st.sidebar.success("✅ Đã tải dữ liệu thành công!")
                    file_loaded = True
                    # Lưu đường dẫn vào session state
                    st.session_state['file_path'] = file_path
            else:
                st.sidebar.error(f"❌ Không tìm thấy file: {file_path}")
        
        # Tự động load lại nếu đã có đường dẫn trong session
        if 'file_path' in st.session_state:
            if os.path.exists(st.session_state['file_path']):
                dashboard.load_data(st.session_state['file_path'])
                file_loaded = True
    
    if file_loaded and dashboard.data is not None:
        # Tạo các cài đặt và bộ lọc
        report_type, rows, cols, values, agg_func, show_ratio_inline = dashboard.create_pivot_settings()
        time_range, years, months, weeks, categories = dashboard.create_filters()
        
        # Áp dụng bộ lọc
        filtered_data = dashboard.filter_data(time_range, years, months, weeks, categories)
        
        # Hiển thị thông tin debug
        st.sidebar.info(f"📊 Dữ liệu: {len(filtered_data):,} dòng")
        
        # THÊM DEBUG CHI TIẾT VỀ BIẾN ĐỘNG
        if dashboard.data is not None:
            total_rows = len(dashboard.data)
            ratio_rows = len(dashboard.data[pd.notna(dashboard.data['Tỷ_lệ_tuần_trước'])])
            st.sidebar.success(f"🔄 Biến động: {ratio_rows}/{total_rows} dòng có tỷ lệ")
            
            # Hiển thị sample dữ liệu biến động
            sample_ratio = dashboard.data[pd.notna(dashboard.data['Tỷ_lệ_tuần_trước'])].head(5)
            if not sample_ratio.empty:
                st.sidebar.success(f"📋 Sample biến động:")
                for _, row in sample_ratio.iterrows():
                    ratio_val = row['Tỷ_lệ_tuần_trước']
                    content = row['Nội dung'][:20] + "..." if len(row['Nội dung']) > 20 else row['Nội dung']
                    st.sidebar.text(f"   {content}: {ratio_val:.1f}%")
            
            # Hiển thị sample dữ liệu tuần
            unique_weeks = sorted(dashboard.data['Tuần'].unique())
            st.sidebar.info(f"📅 Các tuần: {unique_weeks}")
            
            # Kiểm tra dữ liệu theo tuần
            if len(unique_weeks) > 1:
                st.sidebar.success(f"✅ Có {len(unique_weeks)} tuần - đủ để tính biến động")
            else:
                st.sidebar.warning(f"⚠️ Chỉ có {len(unique_weeks)} tuần - không đủ để tính biến động")
        
        # Nút làm mới dữ liệu
        if st.sidebar.button("🔄 Làm mới dữ liệu", use_container_width=True):
            if 'file_path' in st.session_state:
                dashboard.load_data(st.session_state['file_path'])
                st.rerun()
        
        # Tabs cho các chế độ xem
        tab1, tab2, tab3 = st.tabs(["📋 Pivot Table", "📊 Xu hướng theo thời gian", "💾 Xuất báo cáo"])
        
        with tab1:
            st.header("Pivot Table với biến động inline")
            
            # Tạo pivot table với biến động
            pivot = dashboard.create_hierarchical_pivot_table_with_ratio(
                filtered_data, rows, cols, values, agg_func, show_ratio_inline
            )
            
            if pivot is not None:
                # Hiển thị pivot table cải tiến
                dashboard.display_hierarchical_pivot_improved(pivot, filtered_data)
                
                # Tùy chọn xuất
                col1, col2 = st.columns(2)
                with col1:
                    # Tạo CSV từ dữ liệu gốc (không có HTML)
                    if show_ratio_inline:
                        st.info("💡 Xuất CSV sẽ chứa dữ liệu gốc (không có biến động HTML)")
                    
                    # Tạo pivot đơn giản cho CSV
                    simple_pivot = pd.pivot_table(
                        filtered_data,
                        index=rows if rows else None,
                        columns=cols if cols else None,
                        values=values,
                        aggfunc=agg_func,
                        fill_value=0,
                        margins=False  # BỎ TỔNG CHUNG
                    )
                    
                    csv = simple_pivot.to_csv(encoding='utf-8-sig')
                    st.download_button(
                        "📥 Tải CSV",
                        csv,
                        f"pivot_table_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv"
                    )
                
                # BỎ PHẦN SPARKLINE Ở CUỐI - đã chuyển vào trong từng danh mục
        
        with tab2:
            st.header("Xu hướng theo thời gian (theo thứ tự ưu tiên)")
            
            # Xác định trường thời gian dựa vào kiểu báo cáo
            time_col = {
                "Theo Tuần": "Tuần", 
                "Theo Tháng": "Tháng", 
                "Theo Quý": "Quý", 
                "Theo Năm": "Năm"
            }.get(report_type, "Tháng")
            
            # Hiển thị tùy chọn cho biểu đồ
            col1, col2, col3 = st.columns(3)
            
            with col1:
                chart_type = st.selectbox(
                    "Loại biểu đồ",
                    ["Đường", "Cột", "Vùng"]
                )
            
            with col2:
                normalize = st.checkbox("Chuẩn hóa (so sánh %)", value=False)
                
            with col3:
                num_cols = st.select_slider(
                    "Số cột hiển thị",
                    options=[1, 2, 3],
                    value=2
                )
            
            # Lọc dữ liệu cho các Nội dung (hiển thị theo thứ tự ưu tiên)
            unique_contents = filtered_data['Nội dung'].unique()
            sorted_contents = sorted(unique_contents, key=lambda x: dashboard.content_priority.get(x, 999))
            
            content_filter = st.multiselect(
                "Chọn Nội dung cần hiển thị (theo thứ tự ưu tiên)",
                sorted_contents,
                default=sorted_contents[:10]  # Mặc định hiển thị 10 nội dung đầu tiên
            )
            
            filtered_for_charts = filtered_data[filtered_data['Nội dung'].isin(content_filter)]
            
            if filtered_for_charts.empty:
                st.warning("Không có dữ liệu phù hợp với bộ lọc đã chọn!")
            else:
                # Hiển thị biểu đồ cho từng nội dung riêng biệt
                st.subheader(f"Biểu đồ xu hướng theo {time_col} cho từng Nội dung")
                
                # Sắp xếp dữ liệu theo thứ tự ưu tiên
                sorted_data = filtered_for_charts.copy()
                sorted_data = sorted_data.sort_values(['Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'])
                
                # Tạo container cho các danh mục
                categories = sorted_data['Danh mục'].unique()
                sorted_categories = sorted(categories, key=lambda x: dashboard.category_priority.get(x, 999))
                
                for category in sorted_categories:
                    # Hiển thị Danh mục với expander (BỎ HIỂN THỊ SỐ ƯU TIÊN)
                    with st.expander(f"📁 {category}", expanded=True):
                        # Lọc dữ liệu cho danh mục này
                        category_data = sorted_data[sorted_data['Danh mục'] == category]
                        
                        # Lấy danh sách nội dung trong danh mục (đã sắp xếp)
                        category_contents = category_data['Nội dung'].unique()
                        sorted_category_contents = sorted(category_contents, 
                                                        key=lambda x: dashboard.content_priority.get(x, 999))
                        
                        # Tạo grid hiển thị biểu đồ
                        cols_container = st.columns(num_cols)
                        
                        # Duyệt qua từng nội dung và tạo biểu đồ riêng
                        for i, content_item in enumerate(sorted_category_contents):
                            # Tạo biểu đồ cho nội dung này
                            fig = dashboard.create_individual_trend_chart(
                                category_data, content_item, time_col, chart_type, normalize
                            )
                            
                            if fig is not None:
                                # Hiển thị trong cột tương ứng
                                col_idx = i % num_cols
                                with cols_container[col_idx]:
                                    st.plotly_chart(fig, use_container_width=True)
                
                # Hiển thị bảng dữ liệu
                with st.expander("Xem dữ liệu chi tiết (theo thứ tự ưu tiên)"):
                    # Tạo pivot cho xem dữ liệu chi tiết
                    detail_pivot = pd.pivot_table(
                        filtered_for_charts,
                        index=['Danh mục', 'Nội dung'],
                        columns=time_col,
                        values='Số liệu',
                        aggfunc='sum',
                        fill_value=0
                    )
                    
                    # Sắp xếp theo thứ tự ưu tiên
                    detail_pivot_sorted = detail_pivot.copy()
                    detail_pivot_sorted['Danh_mục_thứ_tự'] = detail_pivot_sorted.index.get_level_values('Danh mục').map(dashboard.category_priority).fillna(999)
                    detail_pivot_sorted['Nội_dung_thứ_tự'] = detail_pivot_sorted.index.get_level_values('Nội dung').map(dashboard.content_priority).fillna(999)
                    detail_pivot_sorted = detail_pivot_sorted.sort_values(['Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'])
                    detail_pivot_sorted = detail_pivot_sorted.drop(columns=['Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'])
                    
                    # Hiển thị với HTML table để đảm bảo hiển thị đầy đủ số
                    html_table = "<div class='full-width-table'>"
                    html_table += "<table style='width:100%; border-collapse: collapse; font-size: 11px;'>"
                    html_table += "<tr style='background-color: #f0f2f6;'>"
                    html_table += "<th style='border: 1px solid #ddd; padding: 6px;'>Danh mục</th>"
                    html_table += "<th style='border: 1px solid #ddd; padding: 6px;'>Nội dung</th>"
                    for col in detail_pivot_sorted.columns:
                        html_table += f"<th style='border: 1px solid #ddd; padding: 6px; text-align: center;'>{col}</th>"
                    html_table += "</tr>"
                    
                    for idx in detail_pivot_sorted.index:
                        html_table += "<tr>"
                        html_table += f"<td style='border: 1px solid #ddd; padding: 6px;'>{idx[0]}</td>"
                        html_table += f"<td style='border: 1px solid #ddd; padding: 6px;'>{idx[1]}</td>"
                        for col in detail_pivot_sorted.columns:
                            value = detail_pivot_sorted.loc[idx, col]
                            formatted_value = f"{value:,.0f}".replace(',', '.')
                            html_table += f"<td style='border: 1px solid #ddd; padding: 6px; text-align: right;' class='number-cell'>{formatted_value}</td>"
                        html_table += "</tr>"
                    
                    html_table += "</table></div>"
                    st.markdown(html_table, unsafe_allow_html=True)
        
        with tab3:
            st.header("Xuất báo cáo")
            
            # Tạo báo cáo tổng hợp
            report_format = st.selectbox(
                "Chọn định dạng",
                ["Excel đa sheet với thứ tự ưu tiên", "Excel đơn giản", "CSV"]
            )
            
            if st.button("Tạo báo cáo", use_container_width=True):
                if report_format == "Excel đa sheet với thứ tự ưu tiên":
                    # Tạo file Excel với nhiều sheet
                    output_file = f'bao_cao_phong_hanh_chinh_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                        # Sheet 1: Dữ liệu gốc (đã sắp xếp)
                        filtered_data_export = filtered_data.drop(columns=['Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'], errors='ignore')
                        filtered_data_export.to_excel(writer, sheet_name='Dữ liệu gốc', index=False)
                        
                        # Sheet 2: Pivot table (dữ liệu số, không có HTML)
                        simple_pivot = pd.pivot_table(
                            filtered_data,
                            index=rows if rows else None,
                            columns=cols if cols else None,
                            values=values,
                            aggfunc=agg_func,
                            fill_value=0,
                            margins=False  # BỎ TỔNG CHUNG
                        )
                        simple_pivot.to_excel(writer, sheet_name='Pivot Table')
                        
                        # Sheet 3: Tổng hợp theo danh mục (theo thứ tự ưu tiên)
                        category_summary = filtered_data.groupby('Danh mục')['Số liệu'].agg(['sum', 'mean', 'count'])
                        category_summary['Thứ_tự'] = category_summary.index.map(dashboard.category_priority).fillna(999)
                        category_summary = category_summary.sort_values('Thứ_tự').drop(columns=['Thứ_tự'])
                        category_summary.to_excel(writer, sheet_name='Theo danh mục')
                        
                        # Sheet 4: Tổng hợp theo thời gian
                        time_summary = filtered_data.pivot_table(
                            index=time_col,
                            columns='Danh mục',
                            values='Số liệu',
                            aggfunc='sum',
                            fill_value=0
                        )
                        time_summary.to_excel(writer, sheet_name='Theo thời gian')
                        
                        # Sheet 5: Tổng hợp theo nội dung (theo thứ tự ưu tiên)
                        content_summary = filtered_data.pivot_table(
                            index=['Danh mục', 'Nội dung'],
                            values='Số liệu',
                            aggfunc=['sum', 'mean', 'count'],
                            fill_value=0
                        )
                        content_summary.to_excel(writer, sheet_name='Theo nội dung')
                        
                        # Sheet 6: Tỷ lệ thay đổi
                        ratio_data = filtered_data[filtered_data['Tỷ_lệ_tuần_trước'] != 0]
                        if not ratio_data.empty:
                            ratio_summary = ratio_data.pivot_table(
                                index=['Danh mục', 'Nội dung'],
                                columns='Tuần',
                                values=['Tỷ_lệ_tuần_trước', 'Thay_đổi_tuần_trước'],
                                aggfunc='mean',
                                fill_value=None
                            )
                            ratio_summary.to_excel(writer, sheet_name='Tỷ lệ thay đổi')
                        
                        # Sheet 7: Cấu hình thứ tự ưu tiên cố định
                        priority_df = pd.DataFrame([
                            {'Loại': 'Danh mục', 'Tên': k, 'Thứ tự': v} 
                            for k, v in dashboard.category_priority.items()
                        ] + [
                            {'Loại': 'Nội dung', 'Tên': k, 'Thứ tự': v} 
                            for k, v in dashboard.content_priority.items()
                        ])
                        priority_df = priority_df.sort_values(['Loại', 'Thứ tự'])
                        priority_df.to_excel(writer, sheet_name='Thứ tự ưu tiên', index=False)
                    
                    with open(output_file, 'rb') as f:
                        st.download_button(
                            "📥 Tải báo cáo Excel với thứ tự ưu tiên",
                            f.read(),
                            output_file,
                            "application/vnd.ms-excel"
                        )
                    
                    st.success("✅ Đã tạo báo cáo với thứ tự ưu tiên thành công!")
                
                elif report_format == "Excel đơn giản":
                    # Tạo file Excel đơn giản
                    output_file = f'bao_cao_don_gian_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                    with pd.ExcelWriter(output_file) as writer:
                        filtered_data_export = filtered_data.drop(columns=['Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'], errors='ignore')
                        filtered_data_export.to_excel(writer, index=False)
                    
                    with open(output_file, 'rb') as f:
                        st.download_button(
                            "📥 Tải Excel đơn giản",
                            f.read(),
                            output_file,
                            "application/vnd.ms-excel"
                        )
                    
                    st.success("✅ Đã tạo báo cáo đơn giản thành công!")
                
                else:  # CSV
                    filtered_data_export = filtered_data.drop(columns=['Danh_mục_thứ_tự', 'Nội_dung_thứ_tự'], errors='ignore')
                    csv = filtered_data_export.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        "📥 Tải CSV",
                        csv,
                        f"bao_cao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv"
                    )
                    
                    st.success("✅ Đã tạo file CSV thành công!")
    
    else:
        st.info("👆 Vui lòng tải lên file Excel hoặc nhập đường dẫn file để bắt đầu")
        
        # Hướng dẫn
        with st.expander("📖 Hướng dẫn sử dụng Dashboard Phòng Hành Chính"):
            st.markdown("""
            ### 🎯 Dashboard chuyên biệt cho Phòng Hành Chính
            
            #### ✨ **Tính năng đặc biệt:**
            
            **1. Thứ tự ưu tiên cố định:**
            - 🥇 Tự động sắp xếp theo thứ tự quan trọng công việc
            - 📋 13 danh mục chính từ "Văn bản đến" đến "Bãi giữ xe"
            - 📄 70 nội dung được sắp xếp theo thứ tự ưu tiên
            
            **2. Hiển thị số đầy đủ:**
            - 💰 Hiển thị đầy đủ số lớn (ví dụ: 1.234.567)
            - 📊 Bảng HTML tùy chỉnh không bị cắt số
            - 🔍 Scroll ngang để xem đầy đủ dữ liệu
            
            **3. Biến động inline:**
            - 📈 Giá trị và biến động trong cùng một ô
            - 🟢 Tăng: "100.000 (↑15%)" 
            - 🔴 Giảm: "85.000 (↓15%)"
            - ⚪ Không đổi: "100.000 (→0%)"
            
            **4. Bỏ tổng chung:**
            - ❌ Không hiển thị tổng của tất cả danh mục
            - ✅ Chỉ hiển thị tổng theo từng hàng/danh mục
            
            #### 📂 **Danh mục theo thứ tự ưu tiên:**
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
            
            #### 🚀 **Cách sử dụng:**
            1. **Tải dữ liệu**: Upload file Excel hoặc nhập đường dẫn
            2. **Chọn báo cáo**: Theo Tuần/Tháng/Quý/Năm
            3. **Lọc dữ liệu**: Chọn thời gian và danh mục
            4. **Xem kết quả**: Pivot table với biến động inline
            5. **Xuất báo cáo**: Excel/CSV với thứ tự ưu tiên
            
            #### 💡 **Lợi ích:**
            - ⚡ **Tự động 100%**: Không cần sắp xếp thủ công
            - 🎯 **Ưu tiên rõ ràng**: Theo tầm quan trọng công việc  
            - 📊 **Hiển thị đầy đủ**: Không bị mất số liệu
            - 📈 **Biến động trực quan**: Nhìn thấy ngay xu hướng
            - 💾 **Xuất chuyên nghiệp**: Báo cáo đầy đủ thông tin
            
            #### ⚠️ **Lưu ý:**
            - Dữ liệu cần có cột: Tuần, Tháng, Danh mục, Nội dung, Số liệu
            - Thứ tự ưu tiên đã được cố định, không cần điều chỉnh
            - Biến động chỉ hiển thị từ tuần thứ 2 trở đi
            - Biến động được tính so với tuần liền trước
            """)

def weekly_dashboard_main():
    """Main function cho weekly upload dashboard"""
    
    # Initialize manager
    if 'weekly_manager' not in st.session_state:
        st.session_state.weekly_manager = WeeklyUploadManager()
    
    manager = st.session_state.weekly_manager
    
    # Header
    st.markdown("""
    <div style='background: linear-gradient(135deg, #28a745 0%, #20c997 100%); 
                padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center;'>
        <h2 style='color: white; margin: 0;'>📅 Weekly Data Upload</h2>
        <p style='color: #f0f0f0; margin: 10px 0 0 0;'>Upload 1 lần/tuần • Auto xóa file cũ • Giữ storage gọn nhẹ</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Connection status
    connected, status_msg = manager.check_github_connection()
    
    if connected:
        st.success(status_msg)
        
        # Current data status
        current_data, metadata = manager.load_current_data()
        
        if current_data is not None and metadata:
            st.info(f"""
            📊 **File hiện tại:**
            - 📄 {metadata.get('filename', 'Unknown')}
            - 📅 Tuần {metadata.get('week_number', '?')}/{metadata.get('year', '?')}
            - ⏰ {metadata.get('upload_time', '')[:19]}
            - 📈 {metadata.get('row_count', 0):,} dòng
            """)
            
            # Load dashboard với dữ liệu hiện tại
            dashboard = PivotTableDashboard()
            dashboard.data = current_data
            dashboard._apply_priority_order()
            dashboard._calculate_week_over_week_ratio()
            
            # Simple dashboard display
            st.markdown("### 📊 Dashboard Báo Cáo Hành Chính")
            
            # Basic pivot table
            pivot = dashboard.create_hierarchical_pivot_table_with_ratio(
                dashboard.data, ['Danh mục', 'Nội dung'], ['Tuần'], 'Số liệu', 'sum', True
            )
            
            if pivot is not None:
                dashboard.display_hierarchical_pivot_improved(pivot, dashboard.data)
        
        else:
            st.warning("📭 Chưa có dữ liệu. Upload file Excel đầu tiên!")
        
        # Upload section
        st.markdown("---")
        st.markdown("### 📤 Upload File Excel")
        
        uploaded_file = st.file_uploader("Chọn file Excel", type=['xlsx', 'xls'])
        
        if uploaded_file is not None:
            try:
                data = pd.read_excel(uploaded_file)
                st.success(f"✅ Đọc thành công {len(data):,} dòng dữ liệu")
                
                if st.button("🚀 UPLOAD VÀ LƯU", type="primary"):
                    if manager.upload_new_file(data, uploaded_file.name):
                        st.balloons()
                        st.rerun()
                        
            except Exception as e:
                st.error(f"❌ Lỗi đọc file: {str(e)}")
    
    else:
        st.error(status_msg)
        st.info("⚙️ Vui lòng cấu hình GitHub secrets trên Streamlit Cloud")

# Cuối file
if __name__ == "__main__":
    weekly_dashboard_main()
