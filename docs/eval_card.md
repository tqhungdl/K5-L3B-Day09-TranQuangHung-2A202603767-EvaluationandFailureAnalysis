# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA:**
- **Phiên bản:** code (commit) … · eval set v1 (sha …) · metric_spec … · grader (commit) … · seeds 11/22/33/44/55
- **Eval set:** v1, 14 item × 5 seed, nguồn lab8_public; nhãn: labels_v1.json
- **Metric & ngưỡng:** (trích metric_spec.yaml)
- **Kết quả baseline vs PR:** bảng + paired CI
- **Judge:** tone_ok κ=…, P=…, R=…; helpful bị loại vì …
- **Trace case:** link `docs/trace_case.md`, bước sai đầu tiên, regression test
- **Gate owner:** ai xử lý khi gate exit 1
- **Phạm vi pilot:** …
- **Giới hạn / bằng chứng còn thiếu:** MockLLM, 14 item, judge replay; không đo trên người dùng thật
- **Khi nào tăng eval-set version:** …

## Eval v2 · Kiểm tra độ ổn định (M6)

- **A/A:** Chạy cùng shape `swarm` trên 28 item với hai bộ seed `11,22,33,44,55` và `66,77,88,99,110`. Cả hai đạt `pass_hat_5 = 0.8929` và `pass_rate = 0.9786` (Δ = 0 cho cả hai chỉ số).
- **Ngưỡng chặn:** Chọn `pass_hat_5 ≥ 0.80`, thấp hơn hai kết quả A/A 9,29 điểm phần trăm và cao hơn kết quả `0.5714` của `flaky_regression`. Với đúng năm seed, một item chỉ đóng góp vào `pass_hat_5` khi cả năm lần chạy đều đạt. Vì vậy, một lần lỗi đủ làm giảm chỉ số này dù ảnh hưởng lên `pass_rate` trung bình nhỏ hơn.
- **Giới hạn:** Hai lần chạy với MockLLM chỉ cho thấy độ lệch bằng 0 trên hai bộ seed đã thử. Khi dùng LLM thật, cần đo dải dao động trên nhiều lần A/A và đặt ngưỡng dưới dải dao động của phiên bản ổn định. Năm seed cho ít bằng chứng về lỗi hiếm, kể cả lỗi chỉ xuất hiện trên một số seed cụ thể.
