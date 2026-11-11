# Ghi chú phân tích · Day 04

Họ và tên: Nguyễn Văn Lên
MSSV: 2A202604007

## 1. Case được chọn

- ID case: A5
- Câu trả lời của agent ở lần chạy 1: Khẳng định không có incident GitHub Actions trong năm 2025, dù dữ liệu chỉ tra cứu 50 incident gần nhất và không đủ để xác nhận điều đó.
- Điểm ở lần chạy 1: 45/100

## 2. Bằng chứng trong trace

`get_status` trả về `matching_incidents_in_last_50: 23` cùng ghi chú “Chỉ tìm theo chuỗi trong 50 incident gần nhất; không tìm thấy không chứng minh không có sự cố.” Tuy vậy, câu trả lời lần đầu vẫn viết “không có incident nào cụ thể ... trong năm 2025” và còn lặp lại nhận định này sau khi nhắc đến giới hạn. Nguyên nhân có thể là model diễn giải việc không tìm thấy trong dữ liệu gần đây như bằng chứng về cả năm, thay vì giữ đúng giới hạn của snapshot.

```text
tool: get_status(provider="github", component="Actions")
result: matching_incidents_in_last_50=23
note: Chỉ tìm theo chuỗi trong 50 incident gần nhất; không tìm thấy không chứng minh không có sự cố.
source: https://www.githubstatus.com
answer: “không có incident nào cụ thể cho GitHub Actions trong năm 2025”
```

## 3. Thay đổi đã thực hiện

- Sửa gì, ở đâu: Trong `agent.py`, nhận diện câu hỏi vừa yêu cầu kết quả đầy đủ vừa nêu năm; chỉ bật kiểm tra sau khi `get_status` trả về trường giới hạn 50 incident. Nếu câu trả lời thiếu giới hạn hoặc vẫn khẳng định không có incident trong năm mà không giới hạn phạm vi, ghi `validation_missing_completeness_caveat` vào trace và yêu cầu model sửa trong số bước còn lại. Bổ sung hướng dẫn tương ứng vào system prompt.
- Vì sao chọn thay đổi này: Lỗi A5 là kết luận vượt quá phạm vi dữ liệu, không phải thiếu URL nguồn. Kiểm tra yêu cầu model nói rõ rằng snapshot không chứng minh danh sách đầy đủ hay việc không có incident.
- Số test có sẵn trước khi thêm regression tests: 40.
- Test bổ sung trong `tests/test_validation.py` kiểm tra câu trả lời A5 sai được yêu cầu sửa; xác nhận không kích hoạt kiểm tra cho câu hỏi trạng thái thông thường hoặc khi tool status thất bại.

## 4. So sánh hai lần chạy

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---:|---:|
| Điểm tổng (22 case, đều được chấm) | 79.32/100 | 79.95/100 |
| Điểm A5 | 45/100 | 65/100 |
| Agent model calls (tổng các case) | 50 | 51 |
| Judge calls | 22 | 22 |
| Tokens agent / judge | 41,001 / 39,740 | 49,296 / 40,051 |
| Chi phí agent / judge (USD, theo report) | 0.01044780 / 0.00729075 | 0.01193475 / 0.00740760 |

Cả hai lần dùng `openrouter / openai/gpt-4o-mini` cho agent và judge, `max_steps=8`, dataset `core`, và cùng snapshot tool (GitHub `captured_at=2026-11-09T03:50:47.065020+00:00`).

- Lỗi đã cải thiện: A5 tăng 20 điểm. Câu trả lời sau nêu rõ không thể cung cấp danh sách đầy đủ năm 2025 và không kết luận chắc chắn là không có incident. Trace lần sau không có event validation vì câu trả lời đã đáp ứng kiểm tra giới hạn ngay từ đầu.
- Lỗi còn lại hoặc mới xuất hiện: Điểm tổng chỉ tăng 0.63. Judge vẫn nhận xét câu trả lời A5 còn mơ hồ khi liệt kê incident gần đây không thuộc năm 2025. Một số case giảm điểm: E1 (60→50), E2 (100→75), A8 (100→95), H5 (100→70), H8 (80→70). Cần xem từng trace trước khi quy các thay đổi này cho bản sửa; mỗi case chỉ chạy một lần và judge có thể dao động.

## 5. Giới hạn

Judge dùng cùng model với agent nên điểm có thể thiên lệch và không thay thế việc đọc câu trả lời/trace. Snapshot chỉ tra cứu tối đa 50 incident gần nhất, không thể xác nhận lịch sử đầy đủ của cả năm; kết quả không phải trạng thái live. Chỉ có một lần chạy cho mỗi phiên bản nên thay đổi điểm chưa chứng minh độ ổn định. Kiểm tra completeness dựa trên nhận diện từ khóa và cách diễn đạt; đây là guardrail hẹp, không xác minh mọi claim hoặc bảo đảm câu trả lời hoàn toàn chính xác.
