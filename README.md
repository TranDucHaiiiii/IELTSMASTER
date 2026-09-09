# 🎯 IELTS Master Hub - Nền Tảng Luyện Thi IELTS 4 Kỹ Năng Bằng Python

Một ứng dụng web học và luyện thi IELTS toàn diện, hiện đại được phát triển bằng **Python (Flask)** kết hợp cơ sở dữ liệu **SQLite** và giao diện chuẩn kỳ thi máy tính (**IELTS on Computer**).

---

## 🌟 Các Tính Năng Nổi Bật

### 1. 📖 IELTS Reading Simulation (Mô phỏng thi đọc máy tính)
- Giao diện **2 cột chia đôi màn hình** (Split-screen) giống hệt phòng thi IDP/British Council:
  - Cột trái: Bài đọc dài phân theo Passage.
  - Cột phải: Danh sách câu hỏi làm trực tiếp (True/False/Not Given, Multiple Choice, Điền từ).
- Đồng hồ đếm ngược 60 phút.
- Tự động chấm điểm và quy đổi sang **IELTS Band Score (0.0 - 9.0)**.
- Bảng giải thích chi tiết đáp án kèm dẫn chứng trích từ bài đọc.

### 2. 🎧 IELTS Listening Simulation (Luyện nghe tương tác)
- Trình phát audio thông minh với điều chỉnh tốc độ (1.0x chuẩn thi, 1.15x nâng cao, 0.9x dễ nghe).
- Hỗ trợ xem Audio Transcript và dẫn chứng giải thích.
- Chấm điểm ngay lập tức và tính Band điểm.

### 3. ✍️ IELTS Writing Lab (Phòng luyện viết & Chấm điểm tự động)
- Hỗ trợ cả **Task 1** (Biểu đồ, thư) và **Task 2** (Nghị luận xã hội).
- Trình soạn thảo văn bản có **đếm từ tự động theo thời gian thực**.
- Bộ đếm thời gian 20 phút / 40 phút.
- **Hệ thống phân tích tiêu chí chuẩn IELTS**:
  1. *Task Achievement / Response*
  2. *Coherence & Cohesion* (phân tích từ nối, cấu trúc đoạn)
  3. *Lexical Resource* (phát hiện từ vựng học thuật C1-C2)
  4. *Grammatical Range & Accuracy*
- Thư viện bài mẫu chuẩn **Band 8.5+** kèm phân tích từ vựng đắt giá.

### 4. 🗣️ IELTS Speaking Room (Luyện nói với Microphone)
- Đủ 3 Part: Phỏng vấn nhanh, Cue Card và Thảo luận chuyên sâu.
- **Tích hợp sẵn bộ thu âm Microphone (Web MediaRecorder)**: Người học bấm nút Mic để nói, sau đó nghe lại giọng của mình ngay trên web để tự sửa phát âm và độ lưu loát.
- Đồng hồ đếm ngược 1 phút chuẩn bị Cue Card & 2 phút nói.
- Bài nói mẫu Band 8.5+ kèm phát âm giọng bản ngữ (Web SpeechSynthesis).

### 5. 📚 3D Flashcards Từ Vựng Học Thuật (Vocabulary Booster)
- Kho từ vựng học thuật Academic Word List (AWL) theo chủ đề (Môi trường, Công nghệ, Giáo dục, Kinh tế, Xã hội,...).
- Thẻ Flashcard hiệu ứng lật 3D mượt mà (hỗ trợ phím tắt `Space`, `←`, `→`).
- Nút bấm nghe phát âm chuẩn Anh - Anh / Anh - Mỹ.
- Đánh dấu từ đã nhớ (Mastered) để theo dõi tiến độ.

### 6. 🧮 Official IELTS Band Score Calculator
- Công cụ quy đổi điểm Listening & Reading (số câu đúng / 40 ➔ Band 0 - 9).
- Hỗ trợ cả hình thức **Academic** và **General Training**.
- Tính điểm **Overall Band** chính xác theo quy tắc làm tròn chính thức của IDP / British Council.

---

## 📁 Cấu Trúc Dự Án

```text
d:\Python\ielts_app\
│
├── app.py                     # Máy chủ Flask & REST API
├── database.py                # Quản lý SQLite Database
├── requirements.txt           # Danh sách thư viện Python
├── run.bat                    # File chạy nhanh ứng dụng bằng 1 cú click
├── test_app.py                # Bộ unit tests kiểm thử tự động
│
├── data/                      # Ngân hàng dữ liệu học tập
│   ├── reading_tests.json     # Đề thi đọc, passage, câu hỏi, đáp án, giải thích
│   ├── listening_tests.json   # Đề thi nghe, transcript, câu hỏi, giải thích
│   ├── writing_prompts.json   # Đề Writing Task 1 & 2, bài mẫu Band 8.5+
│   ├── speaking_topics.json   # Đề thi Speaking Part 1, 2, 3, bài mẫu, collocations
│   └── vocabulary.json        # Từ vựng Academic Band 7.5+, phiên âm IPA, ví dụ
│
├── static/
│   ├── css/
│   │   └── style.css          # Design system Dark/Light, Glassmorphism
│   └── js/
│       ├── main.js            # Theme toggle, SpeechSynthesis, Toast
│       ├── test_engine.js     # Bộ máy thi Reading/Listening & chấm điểm
│       ├── recorder.js        # Ghi âm giọng nói Microphone & Speaking timers
│       └── flashcards.js      # Logic lật thẻ 3D & quản lý tiến độ từ vựng
│
└── templates/
    ├── base.html              # Layout chung & thanh điều hướng
    ├── index.html             # Trang chủ & Dashboard tổng quan
    ├── reading.html           # Giao diện thi Reading 2 cột
    ├── listening.html         # Giao diện thi Listening
    ├── writing.html           # Phòng luyện viết Writing Lab
    ├── speaking.html          # Phòng luyện nói Speaking Room
    ├── vocabulary.html        # Bộ Flashcards từ vựng 3D
    ├── calculator.html        # Bộ tính điểm IELTS Band Score
    └── history.html           # Xem lại lịch sử thi & bài viết
```

---

## 🚀 Hướng Dẫn Khởi Động

### Cách 1: Click chuột (Đơn giản nhất)
Nhấp đúp chuột vào file **`run.bat`** trong thư mục `d:\Python\ielts_app\`.

### Cách 2: Bằng dòng lệnh terminal
Mở terminal tại thư mục dự án và chạy:
```powershell
cd d:\Python
.\.venv\Scripts\python ielts_app\app.py
```

Mở trình duyệt web và truy cập vào địa chỉ:
👉 **`http://127.0.0.1:5000`**
