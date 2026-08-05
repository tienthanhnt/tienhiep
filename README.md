# Tàng Kinh Các — Hướng Dẫn Sử Dụng

> **Domain:** https://vercel.com/tienhiep/tienhiep/settings/domains  
> **Supabase:** https://ebekineyghlxlpljeiww.supabase.co

---

## ⚡ Quick Reference — Python Toolchain

> Tất cả lệnh chạy từ thư mục: `web/importer/`

### 📁 Cấu Trúc Thư Mục

```
web/importer/
├── .env                               ← API keys (SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY, R2_*)
├── chapters/
│   └── Ten_Truyen_Translated/         ← Một bộ truyện (folder kết thúc bằng _Translated)
│       ├── book_info.txt              ← Metadata
│       ├── theme.png                  ← Ảnh bìa
│       ├── 0001_Ten_chuong.md
│       └── 0002_Ten_chuong.md
├── translate_chapters.py              ← Dịch raw → Markdown
├── upload_translated.py               ← Upload lên Supabase
└── manage_books.py                    ← Quản lý / xóa / đồng bộ
```

**Nội dung `book_info.txt`** (bắt buộc trong mỗi thư mục `_Translated`):
```
title=Xích Tâm Tuần Thiên
author=Tình Hà Dĩ Thậm
```
> ⚠️ Giá trị `title=` là tên dùng trong tất cả lệnh `manage_books.py` — **không phải tên folder**.

---

### BƯỚC 1 — Dịch Truyện

```bash
# Dịch toàn bộ file raw sang Markdown (AI translation)
python translate_chapters.py \
  --source-dir chapters/Ten_Truyen_Raw \
  --target-dir chapters/Ten_Truyen_Translated
```

---

### BƯỚC 2 — Upload Lên Supabase + Cloudflare R2

Trước khi upload theo cơ chế tiết kiệm database, tạo thêm 2 cột trong bảng `chapters`:

```sql
ALTER TABLE chapters ADD COLUMN IF NOT EXISTS content_path TEXT;
ALTER TABLE chapters ADD COLUMN IF NOT EXISTS content_url TEXT;
```

Nội dung chương được lưu ở Cloudflare R2 để tiết kiệm Supabase Database/Storage. Trong Cloudflare R2, tạo bucket:

```text
chapter-content
```

Tạo R2 API token có quyền Object Read/Write cho bucket, rồi thêm vào `web/importer/.env`:

```env
R2_ACCOUNT_ID=YOUR_CLOUDFLARE_ACCOUNT_ID
R2_ACCESS_KEY_ID=YOUR_R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY=YOUR_R2_SECRET_ACCESS_KEY
R2_BUCKET=chapter-content
R2_PUBLIC_BASE_URL=https://your-public-r2-domain.example.com
```

`R2_PUBLIC_BASE_URL` là URL public của bucket hoặc custom domain đã gắn với R2, không có dấu `/` ở cuối.

Từ lúc này, nội dung chương mới sẽ được lưu trong R2, còn PostgreSQL chỉ giữ metadata và đường dẫn nội dung.

Nếu môi trường Python đã cài trước đó, cài lại dependency để có `boto3`:

```bash
pip install -r requirements.txt
```

```bash
# Upload TẤT CẢ thư mục *_Translated trong chapters/ (khuyến nghị)
python upload_translated.py

# Upload chỉ 1 bộ truyện
python upload_translated.py --translated-dir chapters/Ten_Truyen_Translated

# Upload từ thư mục cha khác
python upload_translated.py --scan-dir /duong/dan/khac
```
> ✅ Script tự động bỏ qua chương đã tồn tại — chạy nhiều lần không bị trùng.

---

### BƯỚC 3 — Quản Lý Truyện

#### Xem danh sách
```bash
# Tất cả truyện trong DB
python manage_books.py list

# Danh sách chương của 1 truyện
python manage_books.py list-chapters "Xích Tâm Tuần Thiên"
```

#### Xóa chương
```bash
# Xóa 1 chương cụ thể
python manage_books.py delete-chapter "Xích Tâm Tuần Thiên" 5

# Xóa nhiều chương cùng lúc
python manage_books.py delete-chapter "Xích Tâm Tuần Thiên" 5 6 10

# Xóa TOÀN BỘ chương (giữ lại thông tin truyện)
python manage_books.py delete-chapters "Xích Tâm Tuần Thiên"
```

#### Xóa truyện
```bash
# Xóa truyện + toàn bộ chương
python manage_books.py delete-book "Xích Tâm Tuần Thiên"
```

#### Đồng bộ lại (Resync)
```bash
# Xóa chương cũ rồi upload lại 1 truyện từ đầu
python manage_books.py resync --translated-dir chapters/Xich_Tam_Tuan_Thien_Translated

# Đồng bộ lại TẤT CẢ truyện
python manage_books.py resync-all

# Thêm --yes để bỏ qua hỏi xác nhận
python manage_books.py resync-all --yes
```

---

### 🔧 Workflow Khi Gặp Lỗi

**Sửa 1 vài chương bị lỗi:**
```bash
# 1. Xóa chương lỗi
python manage_books.py delete-chapter "Tên Truyện" 3 7

# 2. Upload lại (chỉ chương mới sẽ được thêm)
python upload_translated.py --translated-dir chapters/Ten_Truyen_Translated
```

**Upload lại toàn bộ 1 truyện từ đầu:**
```bash
python manage_books.py resync --translated-dir chapters/Ten_Truyen_Translated
```

**Xóa và tạo lại hoàn toàn:**
```bash
python manage_books.py delete-book "Tên Truyện"
python upload_translated.py --translated-dir chapters/Ten_Truyen_Translated
```

---

### 📌 Bảng Tóm Tắt Nhanh

| Mục đích | Lệnh |
|---|---|
| Dịch truyện | `python translate_chapters.py --source-dir ... --target-dir ...` |
| Upload tất cả | `python upload_translated.py` |
| Upload 1 truyện | `python upload_translated.py --translated-dir chapters/...` |
| Xem truyện trong DB | `python manage_books.py list` |
| Xem chương của truyện | `python manage_books.py list-chapters "Tên"` |
| Xóa 1 chương | `python manage_books.py delete-chapter "Tên" 5` |
| Xóa nhiều chương | `python manage_books.py delete-chapter "Tên" 5 6 10` |
| Xóa toàn bộ chương | `python manage_books.py delete-chapters "Tên"` |
| Xóa cả truyện | `python manage_books.py delete-book "Tên"` |
| Resync 1 truyện | `python manage_books.py resync --translated-dir chapters/...` |
| Resync tất cả | `python manage_books.py resync-all` |

---

## 📐 Tài Liệu Thiết Kế Gốc

> Tham khảo trải nghiệm: [MTruyen](https://mtruyen.net/), nhưng không sao chép thương hiệu, nội dung hoặc tài sản hình ảnh.


## 1. Tổng quan

Dự án xây dựng một website đọc truyện tiếng Việt có giao diện gọn, nhiều nội dung và dễ sử dụng tương tự các website đọc truyện phổ biến. Website tập trung vào ba nhu cầu chính:

1. Duyệt và tìm truyện nhanh.
2. Đọc truyện thuận tiện trên máy tính và điện thoại.
3. Nhập hàng loạt thư viện truyện offline từ EPUB, TXT, DOCX và DOC mà không phải đăng thủ công từng truyện.

Hệ thống được phát triển và kiểm thử hoàn toàn trên máy local trước. Khi ổn định, website có thể chuyển lên Vercel và một dịch vụ PostgreSQL/Storage miễn phí mà không phải viết lại ứng dụng.

Website **không có đăng nhập, đăng ký, bình luận hoặc tài khoản người dùng** trong phiên bản đầu. Tiến độ đọc được lưu trực tiếp trong trình duyệt của từng người dùng.

## 2. Mục tiêu

- Có giao diện tương tự cách tổ chức nội dung của MTruyen nhưng mang nhận diện riêng.
- Hoạt động tốt trên desktop, tablet và mobile.
- Đọc được thư viện truyện lớn với hàng nghìn truyện và nhiều chương.
- Tìm kiếm theo tên truyện, tên tác giả và tên thay thế.
- Lọc theo thể loại, trạng thái và độ dài truyện.
- Nhập tự động nhiều file truyện trong một lần.
- Phát hiện và bỏ qua file đã nhập, tránh tạo dữ liệu trùng.
- Dễ chạy local, sao lưu và chuyển sang host khác.
- Chuẩn bị sẵn các vị trí quảng cáo nhưng chưa tích hợp mạng quảng cáo ở giai đoạn đầu.
- Có cấu trúc SEO cơ bản để công cụ tìm kiếm lập chỉ mục trang truyện và chương.

## 3. Phạm vi phiên bản đầu (MVP)

### 3.1. Có trong MVP

- Trang chủ.
- Danh sách tất cả truyện.
- Danh sách truyện mới cập nhật.
- Danh sách truyện hoàn thành.
- Trang thể loại.
- Tìm kiếm truyện.
- Lọc và sắp xếp truyện.
- Trang thông tin chi tiết truyện.
- Danh sách chương có phân trang hoặc tải thêm.
- Trang đọc chương.
- Chuyển chương trước/sau.
- Chọn chương từ trang đọc.
- Điều chỉnh cỡ chữ, font chữ, chiều rộng và màu nền.
- Chế độ sáng/tối.
- Tự lưu chương đang đọc và cài đặt đọc bằng `localStorage`.
- Hiển thị truyện đã đọc gần đây trên trang chủ.
- Bộ nhập truyện hàng loạt từ thư mục local.
- Trang báo cáo kết quả nhập dữ liệu dành cho người vận hành hoặc báo cáo dạng file.
- Vị trí quảng cáo rỗng, có thể bật sau bằng cấu hình.
- Sitemap, metadata và URL thân thiện.

### 3.2. Chưa có trong MVP

- Đăng nhập và đăng ký.
- Đồng bộ tiến độ đọc giữa nhiều thiết bị.
- Bình luận.
- Người dùng chấm điểm/rating.
- Người dùng tự upload truyện.
- Thanh toán hoặc chương VIP.
- Ứng dụng điện thoại.
- Hệ thống gợi ý bằng AI.
- Tự động lấy truyện từ website bên ngoài.

Các mục này chỉ được bổ sung khi có yêu cầu rõ ràng trong giai đoạn sau.

## 4. Công nghệ đề xuất

### 4.1. Website

- **Next.js (App Router):** giao diện và phần xử lý server trong cùng một dự án.
- **TypeScript:** giảm lỗi dữ liệu giữa giao diện, API và database.
- **Tailwind CSS:** xây giao diện responsive nhanh, dễ giữ phong cách nhất quán.
- **Zod:** kiểm tra dữ liệu đầu vào và biến môi trường.

Không dùng Redux ở MVP. Trạng thái giao diện đơn giản được quản lý bằng React và URL query parameters.

### 4.2. Database và lưu file

- **PostgreSQL:** lưu metadata truyện, tác giả, thể loại, chương và nội dung chương.
- **Supabase Local:** chạy PostgreSQL, Storage và giao diện quản lý trên máy thông qua Docker.
- **Supabase Cloud:** lựa chọn mặc định khi đưa website lên Internet.

PostgreSQL được chọn thay vì SQLite để môi trường local và cloud dùng cùng một loại database, tránh phải chuyển đổi schema sau này.

Trong MVP, nội dung chữ của chương được lưu trong PostgreSQL. Storage dùng cho:

- Ảnh bìa.
- File gốc EPUB/TXT/DOCX/DOC nếu bật tùy chọn lưu bản gốc.
- File báo cáo import lớn nếu cần.

Nếu thư viện vượt quá khả năng của gói database miễn phí, nội dung chương có thể chuyển sang object storage mà không thay đổi URL và giao diện phía người đọc.

### 4.3. Công cụ nhập truyện

- **Python 3**.
- `ebooklib` và `BeautifulSoup` cho EPUB.
- `charset-normalizer` cho TXT nhiều encoding.
- `python-docx` cho DOCX.
- LibreOffice chạy headless để chuyển DOC cũ sang DOCX/TXT.
- Supabase Python SDK hoặc kết nối PostgreSQL trực tiếp.

Python phù hợp với việc xử lý nhiều định dạng tài liệu và cũng thống nhất với các công cụ Python đang có trong repository.

### 4.4. Triển khai

- **Local:** Next.js + Supabase Local/Docker.
- **Source code:** GitHub.
- **Frontend/server:** Vercel với tên miền miễn phí `ten-du-an.vercel.app`.
- **Database/storage mặc định:** Supabase Free.

Ứng dụng không phụ thuộc độc quyền vào Vercel. Khi cần, Next.js có thể chạy bằng Node.js/Docker trên host khác và PostgreSQL có thể chuyển sang nhà cung cấp khác.

## 5. Kiến trúc hệ thống

```text
Thư viện truyện offline
EPUB / TXT / DOCX / DOC
          |
          v
Python Importer
- quét thư mục
- đọc metadata
- tách chương
- làm sạch nội dung
- tạo hash chống trùng
- trích xuất ảnh bìa
          |
          v
PostgreSQL + Storage
          |
          v
Next.js
- trang chủ
- tìm kiếm/lọc
- chi tiết truyện
- trang đọc chương
          |
          v
Trình duyệt người đọc
- localStorage lưu tiến độ/cài đặt
```

### Nguyên tắc kiến trúc

- Importer và website dùng chung schema dữ liệu nhưng là hai chương trình độc lập.
- Website không đọc trực tiếp đường dẫn file trên máy tính.
- Không lưu đường dẫn tuyệt đối như `/home/user/books/...` trong database.
- Mọi cấu hình môi trường nằm trong biến môi trường, không ghi khóa bí mật vào source code.
- Schema database được quản lý bằng migration để có thể tạo lại ở bất kỳ máy hoặc host nào.
- File truyện không được commit vào Git.

## 6. Thiết kế giao diện

### 6.1. Phong cách chung

- Bố cục sáng, sạch và có mật độ thông tin tương tự trang tham khảo.
- Màu nhấn mặc định: xanh dương.
- Nền sáng cho trang danh sách; trang đọc hỗ trợ nhiều màu nền.
- Card truyện dùng chung một tỷ lệ ảnh bìa để không làm lệch lưới.
- Không sử dụng logo, tên, icon thương hiệu hoặc ảnh của MTruyen.

### 6.2. Header

- Logo/tên website.
- Liên kết “Danh sách”.
- Dropdown “Thể loại”.
- Liên kết “Mới cập nhật” và “Hoàn thành”.
- Ô tìm kiếm nhanh.
- Không có nút đăng nhập/đăng ký.

Trên mobile, header được rút gọn thành logo, nút tìm kiếm và menu. Có thể dùng thanh điều hướng dưới màn hình cho Trang chủ, Thể loại, Tìm kiếm và Gần đây.

### 6.3. Trang chủ

```text
Header
Breadcrumb (nếu cần)
Khối Truyện đã đọc gần đây (chỉ hiện khi có dữ liệu local)
Main content                        Sidebar
|- Mới cập nhật                    |- Thể loại phổ biến
|- Truyện hoàn thành               |- Lọc theo số chương
|- Nội dung giới thiệu/SEO         |- Liên kết nhanh
Footer
```

Card truyện hiển thị:

- Ảnh bìa.
- Trạng thái `Đang ra` hoặc `Hoàn thành`.
- Số chương.
- Tên truyện.
- Tác giả.
- Tối đa 2 thể loại chính.

Không hiển thị rating trong MVP vì chưa có cơ chế người dùng đánh giá. Trường rating có thể được thêm sau mà không cần thiết kế lại card.

### 6.4. Trang danh sách và thể loại

- Tiêu đề và tổng số truyện.
- Sắp xếp theo: mới cập nhật, mới đăng, nhiều chương, tên A–Z.
- Lọc trạng thái: tất cả, đang ra, hoàn thành.
- Lọc số chương: dưới 100, 100–500, 500–1000, trên 1000.
- Lọc một hoặc nhiều thể loại.
- URL phản ánh bộ lọc để có thể chia sẻ và tải lại trang.
- Phân trang phía server, không tải toàn bộ thư viện cùng lúc.

### 6.5. Trang chi tiết truyện

- Breadcrumb.
- Ảnh bìa.
- Tên truyện và tên thay thế.
- Tác giả.
- Thể loại.
- Trạng thái.
- Tổng số chương.
- Ngày cập nhật gần nhất.
- Nút “Đọc từ đầu”.
- Nút “Đọc tiếp” nếu trình duyệt đã lưu tiến độ, nếu chưa thì hiển thị “Đọc mới nhất”.
- Giới thiệu truyện.
- Danh sách chương.
- Sắp xếp chương cũ nhất/mới nhất.
- Tìm nhanh theo số hoặc tên chương.
- Truyện liên quan dựa trên thể loại.

Danh sách truyện hàng nghìn chương phải được phân trang hoặc tải từng nhóm, tránh render toàn bộ cùng lúc.

### 6.6. Trang đọc chương

- Breadcrumb gọn.
- Tên truyện.
- Tên chương.
- Số từ và thời gian đọc ước tính.
- Nội dung chương có chiều rộng tối ưu cho việc đọc.
- Nút chương trước, danh sách chương và chương sau ở đầu/cuối trang.
- Thanh cài đặt đọc có thể sticky trên mobile.
- Tùy chọn:
  - Cỡ chữ.
  - Font serif/sans-serif.
  - Giãn dòng.
  - Chiều rộng nội dung.
  - Nền trắng, giấy, xám hoặc tối.
- Tự lưu chương hiện tại và vị trí cuộn.
- Hỗ trợ phím mũi tên trái/phải trên desktop để đổi chương, nhưng không kích hoạt khi người dùng đang nhập liệu.

## 7. Responsive

Số cột card dự kiến:

| Kích thước | Số cột | Sidebar |
|---|---:|---|
| Mobile nhỏ | 2 | Chuyển thành drawer/bộ lọc |
| Mobile lớn | 2–3 | Chuyển thành drawer/bộ lọc |
| Tablet | 3–4 | Có thể ẩn hoặc thu gọn |
| Desktop | 5–6 | Hiển thị bên phải |

Trang đọc ưu tiên mobile-first, nút chuyển chương có vùng bấm lớn và nội dung không bị quảng cáo che khuất.

## 8. Cấu trúc dữ liệu dự kiến

### `books`

| Trường | Ý nghĩa |
|---|---|
| `id` | ID nội bộ |
| `slug` | Chuỗi dùng trong URL, duy nhất |
| `title` | Tên truyện |
| `alternative_titles` | Các tên khác để tìm kiếm |
| `author_id` | Tác giả |
| `description` | Giới thiệu đã làm sạch |
| `cover_path` | Khóa ảnh bìa trong storage |
| `status` | `ongoing`, `completed`, `paused` |
| `source_hash` | Hash file nguồn để chống trùng |
| `chapter_count` | Số chương đã đồng bộ |
| `published_at` | Ngày đưa lên website |
| `updated_at` | Ngày cập nhật gần nhất |

### `authors`

| Trường | Ý nghĩa |
|---|---|
| `id` | ID tác giả |
| `name` | Tên hiển thị |
| `slug` | URL tác giả |

### `categories`

| Trường | Ý nghĩa |
|---|---|
| `id` | ID thể loại |
| `name` | Tên thể loại |
| `slug` | URL thể loại |
| `description` | Nội dung giới thiệu SEO tùy chọn |

### `book_categories`

Bảng liên kết nhiều-nhiều giữa truyện và thể loại.

### `chapters`

| Trường | Ý nghĩa |
|---|---|
| `id` | ID chương |
| `book_id` | Truyện sở hữu chương |
| `chapter_number` | Thứ tự số, có thể rỗng với ngoại truyện |
| `position` | Thứ tự đọc bắt buộc, duy nhất trong truyện |
| `slug` | URL chương |
| `title` | Tiêu đề chương |
| `content_html` | Nội dung HTML đã sanitize |
| `word_count` | Số từ |
| `content_hash` | Phát hiện chương trùng/thay đổi |
| `published_at` | Thời điểm xuất bản |

### `source_files`

| Trường | Ý nghĩa |
|---|---|
| `id` | ID bản ghi nguồn |
| `book_id` | Truyện tương ứng |
| `original_name` | Tên file ban đầu |
| `format` | EPUB/TXT/DOCX/DOC |
| `file_hash` | Hash chống nhập lại |
| `storage_path` | Vị trí bản gốc nếu có lưu |
| `imported_at` | Thời gian nhập |

### `import_jobs` và `import_errors`

Lưu số file thành công, cảnh báo, lỗi và chi tiết file cần kiểm tra. Không dùng các bảng này để hiển thị cho người đọc.

## 9. Tìm kiếm

MVP tìm kiếm theo:

- Tên truyện.
- Tên thay thế.
- Tác giả.

Kết quả ưu tiên tên khớp chính xác, sau đó tên bắt đầu bằng từ khóa, rồi mới đến kết quả chứa từ khóa. Tìm kiếm không phân biệt hoa thường và nên xử lý tiếng Việt có/không dấu nếu PostgreSQL hỗ trợ extension cần thiết.

MVP **không tìm kiếm toàn văn trong nội dung hàng triệu chương**, vì chức năng này tốn tài nguyên và không cần thiết cho trải nghiệm ban đầu.

## 10. Thiết kế bộ nhập truyện

### 10.1. Cách chạy dự kiến

```bash
python importer.py scan "/duong-dan/thu-vien"
python importer.py import "/duong-dan/thu-vien"
```

- `scan`: chỉ phân tích và tạo báo cáo, không ghi database.
- `import`: nhập những file hợp lệ.

Các tùy chọn dự kiến:

```text
--recursive             quét thư mục con
--status completed      đặt trạng thái mặc định
--category "Tiên Hiệp" gắn thể loại mặc định
--keep-original         lưu file gốc vào storage
--update                cập nhật truyện đã tồn tại khi file thay đổi
--dry-run               không ghi dữ liệu
```

### 10.2. Quy trình cho mỗi file

1. Tính SHA-256 của file.
2. Kiểm tra file đã nhập hay chưa.
3. Xác định định dạng.
4. Đọc metadata: tiêu đề, tác giả, mô tả và bìa.
5. Nhận diện ranh giới chương.
6. Chuẩn hóa tiêu đề chương và thứ tự.
7. Làm sạch HTML, loại script/style và markup nguy hiểm.
8. Tính hash từng chương.
9. Kiểm tra dữ liệu và ghi theo transaction.
10. Xuất kết quả thành công/cảnh báo/lỗi.

Nếu một file lỗi, importer tiếp tục với các file khác và ghi lỗi vào báo cáo.

### 10.3. Chiến lược theo định dạng

#### EPUB

- Đọc metadata chuẩn EPUB.
- Ưu tiên thứ tự spine/navigation của EPUB.
- Giữ định dạng đoạn, nhấn mạnh và tiêu đề cơ bản.
- Trích xuất ảnh bìa nếu có.
- Bỏ CSS/script nhúng không cần thiết.

#### TXT

- Tự phát hiện UTF-8, UTF-16 và các encoding tiếng Việt phổ biến.
- Nhận diện chương bằng regex có cấu hình, ví dụ `Chương 1`, `Chương I`, `Chapter 1`, `Hồi 1`, `Phần 1`.
- Nếu không nhận diện được chương, tạo một chương duy nhất và ghi cảnh báo.

#### DOCX

- Dùng heading làm ranh giới chương khi có.
- Nếu không có heading, dùng quy tắc tương tự TXT.
- Giữ đoạn văn, tiêu đề, in đậm/in nghiêng cơ bản.

#### DOC

- Chuyển sang DOCX/TXT bằng LibreOffice headless trong thư mục tạm.
- Không sửa file gốc.
- Nếu máy chưa cài LibreOffice, ghi lỗi có hướng dẫn rõ ràng.

### 10.4. Metadata thiếu

- Thiếu tên truyện: lấy tên file đã làm sạch.
- Thiếu tác giả: dùng `Chưa rõ`.
- Thiếu bìa: giao diện tạo placeholder bằng CSS với tên truyện; không cần ảnh AI.
- Thiếu thể loại: gắn `Chưa phân loại`.
- Thiếu trạng thái: mặc định `completed` cho file offline hoàn chỉnh, nhưng importer cho phép thay đổi.

## 11. Quảng cáo

MVP chưa tải script quảng cáo. Giao diện chỉ chuẩn bị component `AdSlot` với các vị trí:

- `home-between-sections`: giữa Mới cập nhật và Truyện hoàn thành.
- `listing-inline`: sau một số hàng trong trang danh sách.
- `book-detail`: giữa giới thiệu và danh sách chương.
- `reader-top`: phía trên nội dung chương.
- `reader-bottom`: sau nội dung chương.

Nguyên tắc:

- Quảng cáo tắt mặc định bằng biến môi trường.
- Không đặt quảng cáo chen giữa từng đoạn văn.
- Không che nút chuyển chương.
- Khung quảng cáo dành sẵn kích thước để tránh layout nhảy khi tải.
- Có thể đổi nhà cung cấp quảng cáo mà không sửa layout các trang.

## 12. SEO

- URL truyện: `/truyen/{book-slug}`.
- URL chương: `/truyen/{book-slug}/{chapter-slug}`.
- URL thể loại: `/the-loai/{category-slug}`.
- Title và description riêng cho từng trang.
- Canonical URL.
- Open Graph cơ bản.
- Sitemap phân nhóm khi dữ liệu lớn.
- `robots.txt`.
- Structured data phù hợp cho trang sách và breadcrumb khi triển khai.
- Nội dung SEO trang chủ/thể loại lưu dưới dạng Markdown hoặc trong database, không hardcode vào component.

Không sao chép nội dung SEO từ website tham khảo.

## 13. Hiệu năng

- Render phía server cho trang danh sách, truyện và chương.
- Phân trang database và chỉ chọn các cột cần thiết.
- Index cho `slug`, `updated_at`, `status`, tác giả và tìm kiếm tên.
- Lazy-load ảnh bìa ngoài màn hình.
- Ảnh bìa được resize/nén khi import.
- Cache metadata và danh sách phổ biến; không cache sai nội dung chương mới.
- Không đưa file truyện vào bundle deploy của Next.js.
- Danh sách chương lớn được tải theo trang.

## 14. Bảo mật và độ bền dữ liệu

- Sanitize HTML nhập từ EPUB/DOCX trước khi lưu hoặc render.
- Không cho phép đường dẫn file thoát khỏi thư mục nguồn khi importer xử lý archive.
- Giới hạn kích thước file và tổng số chương hợp lý.
- Service-role key chỉ dùng ở importer/server, không gửi xuống browser.
- Database local không mở trực tiếp ra Internet.
- Có lệnh backup database và storage trước khi migrate.
- Không commit `.env`, database dump, file truyện hoặc secret vào Git.

## 15. Cấu trúc thư mục dự kiến

```text
web/
├── README.md
├── package.json
├── next.config.ts
├── app/
│   ├── page.tsx
│   ├── danh-sach/
│   ├── tim-kiem/
│   ├── the-loai/[slug]/
│   └── truyen/[bookSlug]/
│       ├── page.tsx
│       └── [chapterSlug]/page.tsx
├── components/
│   ├── layout/
│   ├── books/
│   ├── reader/
│   ├── search/
│   └── ads/
├── lib/
│   ├── db/
│   ├── storage/
│   ├── search/
│   └── validation/
├── importer/
│   ├── importer.py
│   ├── parsers/
│   ├── tests/
│   └── requirements.txt
├── supabase/
│   ├── config.toml
│   ├── migrations/
│   └── seed.sql
├── tests/
└── data/
    ├── incoming/        # không commit
    ├── storage/         # không commit nếu dùng driver local nhẹ
    └── import-reports/  # không commit
```

Cấu trúc thực tế có thể được tinh chỉnh khi scaffold dự án, nhưng ranh giới giữa website, importer và database migration phải được giữ rõ ràng.

## 16. Kiểm thử

### Website

- Unit test cho hàm tạo slug, định dạng dữ liệu và tìm kiếm.
- Component test cho card truyện và reader controls.
- End-to-end test cho các luồng:
  - Tìm truyện → mở chi tiết → đọc chương.
  - Lọc thể loại/trạng thái → đổi trang.
  - Đọc chương → chuyển chương → tải lại vẫn giữ tiến độ.
- Kiểm tra responsive trên các kích thước phổ biến.

### Importer

- Fixture EPUB/TXT/DOCX nhỏ, không dùng thư viện truyện thật trong Git.
- Test encoding TXT.
- Test nhận diện nhiều kiểu tiêu đề chương.
- Test EPUB không có bìa/metadata.
- Test chạy lại không tạo dữ liệu trùng.
- Test cập nhật file đã thay đổi.
- Test một file lỗi không làm dừng toàn bộ batch.

## 17. Các giai đoạn thực hiện

### Giai đoạn 1 — Khởi tạo local

- Scaffold Next.js/TypeScript/Tailwind.
- Thiết lập Supabase Local và migration đầu tiên.
- Tạo dữ liệu mẫu nhỏ.
- Tạo layout/header/footer/responsive cơ bản.

### Giai đoạn 2 — Chức năng đọc

- Trang chủ và card truyện.
- Danh sách, thể loại, tìm kiếm và bộ lọc.
- Chi tiết truyện và danh sách chương.
- Reader và lưu tiến độ local.

### Giai đoạn 3 — Importer

- Scan/report.
- EPUB và TXT trước.
- DOCX và DOC sau khi EPUB/TXT ổn định.
- Deduplicate, update và báo cáo lỗi.

### Giai đoạn 4 — Hoàn thiện

- SEO, sitemap và structured data.
- Tối ưu ảnh/cache/query.
- Ad slots tắt mặc định.
- Kiểm thử responsive và end-to-end.
- Backup/restore local.

### Giai đoạn 5 — Deploy

- Đẩy source code lên GitHub.
- Tạo Supabase Cloud.
- Áp dụng migration và chuyển dữ liệu.
- Deploy Next.js lên Vercel.
- Kiểm tra URL production, logs và sitemap.

## 18. Tiêu chí nghiệm thu MVP

MVP được coi là hoàn thành khi:

- Website chạy local bằng hướng dẫn trong README.
- Có thể nhập tự động một thư mục chứa nhiều EPUB/TXT/DOCX/DOC.
- Import lại cùng file không tạo truyện/chương trùng.
- Trang chủ, danh sách, thể loại, tìm kiếm, chi tiết và đọc chương hoạt động.
- Người dùng chuyển chương và lưu tiến độ không cần tài khoản.
- Website sử dụng tốt trên mobile và desktop.
- Một truyện có hàng nghìn chương không làm treo trang chi tiết.
- Ảnh bìa và nội dung được tải ngoài source bundle.
- Quảng cáo tắt mặc định nhưng có sẵn vị trí tích hợp.
- Database và file có quy trình backup/migrate.
- Dự án có thể deploy lên Vercel mà không đưa thư viện truyện vào GitHub.

## 19. Các quyết định cần review trước khi code

Các giá trị dưới đây là đề xuất mặc định. Cần xác nhận hoặc thay đổi trước khi bắt đầu scaffold:

1. **Tên website:** chưa chốt; dùng tên tạm “Website đọc truyện”.
2. **Màu chủ đạo:** xanh dương, giao diện sáng giống mật độ bố cục trang tham khảo.
3. **Database local:** Supabase Local qua Docker.
4. **Cloud mặc định:** Vercel + Supabase Free.
5. **Nội dung chương:** lưu PostgreSQL ở MVP.
6. **File gốc:** mặc định không upload lên cloud để tiết kiệm dung lượng; thư viện offline là bản sao gốc.
7. **Trạng thái file offline:** mặc định `completed`, có thể override khi import.
8. **Tìm kiếm:** tên truyện/tên khác/tác giả; chưa tìm trong toàn bộ nội dung chương.
9. **Rating:** không hiển thị ở MVP.
10. **Quảng cáo:** chỉ dành sẵn vị trí, tắt hoàn toàn cho tới khi được cấu hình.
11. **SEO article:** hỗ trợ Markdown nhưng chưa cần viết bài dài ở MVP.
12. **Thứ tự parser:** EPUB và TXT trước, DOCX và DOC sau.

Sau khi tài liệu này được duyệt, bước tiếp theo mới là scaffold mã nguồn và tạo môi trường local.

#### Domain page
https://vercel.com/tienhiep/tienhiep/settings/domains
