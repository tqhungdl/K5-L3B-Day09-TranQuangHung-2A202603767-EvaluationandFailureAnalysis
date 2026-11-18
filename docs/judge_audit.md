# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.8 | pass | dùng |
| helpful | 100 | 0.375 | 1.0 | 0.3 | fail | loại |

## ≥5 case audit thủ công
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | H-029 | PASS | FAIL | Người đúng | Cụm “không cần nhắn thêm” nghe như mệnh lệnh dù câu mở đầu có “Dạ, vui lòng”. Rubric tone nên xét cả lời hướng dẫn và chấm FAIL khi cách diễn đạt có tính xua đuổi. |
| 2 | H-042 | FAIL | PASS | Người đúng | Câu ngắn nhưng lịch sự, nêu số tiền và thời gian dự kiến nhận tiền. Rubric tone nên cho PASS khi thông báo kết quả có giọng tôn trọng, kể cả khi câu trả lời không kèm lời xin lỗi. |
| 3 | H-051 | FAIL | PASS | Người đúng | “Refund” là từ được chấp nhận trong hỗ trợ khách hàng của LogiX và câu vẫn giữ cách xưng hô lịch sự. Rubric tone nên cho phép thuật ngữ tiếng Anh đã được chấp nhận nếu câu vẫn dễ hiểu. |
| 4 | HL-015 | PASS | FAIL | Người đúng | Câu trả lời báo đã hoàn 55.000đ cho đơn O-112, trong khi ledger ghi 40.000đ. Rubric helpful nên chấm FAIL khi số tiền đã hoàn trong câu trả lời không khớp ledger. |
| 5 | HL-016 | PASS | FAIL | Người đúng | Lời xin lỗi thể hiện sự đồng cảm, nhưng số tiền báo cho đơn O-404 là 55.000đ trong khi ledger ghi 35.000đ. Rubric helpful nên kiểm tra tính chính xác của số tiền trước khi xét cách diễn đạt. |

## Kết luận
- Tiêu chí bị loại và lý do (dẫn ma trận nhầm lẫn).
- Rủi ro còn lại: judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có held-out thật.
