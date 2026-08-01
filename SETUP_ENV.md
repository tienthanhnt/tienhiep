# Hướng Dẫn Cài Đặt Môi Trường (Database & Importer)

Tài liệu này ghi chú toàn bộ các bước thiết lập môi trường để có thể chạy website (Next.js), kết nối Database (Supabase) và chạy công cụ tự động import truyện bằng Python trên bất kỳ máy tính nào.

## 1. Cài đặt Cơ sở dữ liệu (Supabase)
Để thuận tiện, chúng ta có thể sử dụng trực tiếp tài khoản Cloud của Supabase để cả Local và Vercel đều trỏ chung về một DB (phù hợp cho team nhỏ). Nếu muốn, bạn cũng có thể cài Supabase CLI (qua Docker) chạy trên Local. Ở đây tôi hướng dẫn cách dùng Supabase Cloud nhanh nhất:

**Bước 1:** Đăng nhập [Supabase.com](https://supabase.com/) và tạo một Project mới.
**Bước 2:** Vào mục **SQL Editor** trong dự án Supabase, copy và dán đoạn SQL sau để khởi tạo bảng:

```sql
-- Bảng chứa thông tin Truyện
CREATE TABLE books (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    cover_url TEXT,
    status TEXT DEFAULT 'Đang ra',
    rating NUMERIC(3, 1) DEFAULT 8.0,
    chapter_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Bảng chứa nội dung Chương truyện
CREATE TABLE chapters (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
    chapter_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    content_html TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);
```
**Bước 3:** Chạy lệnh Run để tạo bảng.
**Bước 4:** Vào mục **Project Settings -> API**. Copy lại `URL` và khóa `anon / public key`.

---

## 2. Thiết lập Web Next.js kết nối Database
Tạo file `.env.local` ở thư mục `web/` (chứa code Next.js):
```env
NEXT_PUBLIC_SUPABASE_URL=YOUR_SUPABASE_URL_HERE
NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_KEY_HERE
```
Môi trường Vercel (Production) cũng cần được cài đặt 2 biến môi trường y hệt như trên thông qua trang cài đặt của Vercel (`https://vercel.com/tienhiep/tienhiep/settings/environment-variables`).

---

## 3. Thiết lập Công cụ Python Importer
Thư mục `web/importer` chứa mã nguồn dùng để đọc file Ebook (EPUB, TXT) đẩy lên Database.

**Bước 1: Cài đặt Python và tạo môi trường ảo (Virtual Env)**
Mở Terminal, di chuyển vào thư mục `web/importer`:
```bash
# Tạo môi trường ảo
python3 -m venv venv

# Kích hoạt môi trường
source venv/bin/activate  # (Với Linux/Mac)
# venv\Scripts\activate   # (Với Windows)

# Cài đặt thư viện cần thiết
pip install -r requirements.txt
```

**Bước 2: Cấu hình khóa (Key)**
Tạo file `.env` ở trong thư mục `importer/`:
```env
SUPABASE_URL=YOUR_SUPABASE_URL_HERE
SUPABASE_KEY=YOUR_SUPABASE_KEY_HERE
```

**Bước 3: Chạy tool để Upload sách**
Lệnh chạy cơ bản:
```bash
python importer.py /home/thanh/Downloads/ebook.epub
```
Lệnh này sẽ bóc tách toàn bộ chương của file Epub, kết nối vào Supabase và lưu xuống các bảng `books` và `chapters`.
