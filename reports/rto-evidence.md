# RTO/RPO Evidence — Lab 23

Đây là kết quả báo cáo thực tế lấy từ Drill 2 sau khi có Disaster Recovery.

## Thời gian mục tiêu
- Target RTO: 300.0s
- Measured RTO: 24.5s
- Verdict: PASS

## Breakdown Thời gian phục hồi (RTO)

| Milestone (tính từ mốc t0) | +seconds | Evidence (file:line) |
|---|---:|---|
| User thay loi dau tien | 0.0 | `reports/drill-2-withdr.jsonl:15` |
| Health check phat hien Region down | 7.6 | `reports/health-events.jsonl:2` |
| Snapshot restore complete | 16.2 | `reports/failover-events.jsonl:2` |
| Region B ready | 22.4 | `reports/failover-events.jsonl:4` |
| DNS cutover | 22.5 | `reports/failover-events.jsonl:5` |
| Request thanh cong dau tien | 24.5 | `reports/drill-2-withdr.jsonl:35` |

*(Lưu ý: Các mốc cụ thể lấy xấp xỉ theo jsonl)*

## Dữ liệu thất thoát (RPO)
- RPO đo được lúc phục hồi: 2.0s
- Số documents bị mất: 1
- Phiên bản Embed Model: `embed-model=vi-e5-base@v3`
- Bằng chứng: `reports/failover-events.jsonl:2`
