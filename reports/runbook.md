# Runbook: Region Chính Down

**Mục đích:** Sổ tay hướng dẫn người vận hành xử lý khi Region chính bị sập hoàn toàn lúc 3 giờ sáng.

## 1. Phát hiện & Xác nhận Outage
- **Lệnh cần gõ:** `python3 dr/health_checker.py --interval 5 --threshold 3` (hoặc check monitor alert tự động)
- **Signal xác nhận:** Màn hình hoặc Slack/Teams báo Alert `UNHEALTHY` liên tục. Hoặc gọi API `/readyz` trực tiếp bị timeout.
- **Người phụ trách:** L3 On-Call Engineer.

## 2. Failover Sang Region Phụ
- **Lệnh cần gõ:** `python3 dr/runbook.py --primary a --target b --backend fs`
- **Signal xác nhận:**
  - Script tự động xác nhận Region B kéo được snapshot DB/Model gần nhất.
  - DNS thay đổi trong `edge/active_region` thành `b`.
  - Không có 503 xuất hiện ở bước `verify_golden_signals`.
- **Người phụ trách:** L3 On-Call Engineer.

## 3. Rollback (Điều kiện & Lệnh)
- **Điều kiện Rollback:** Nếu Region B cũng sập hoặc tỷ lệ Error Rate > 50% trong 2 phút sau khi chuyển đổi.
- **Thẩm quyền:** L3 Incident Commander (IC).
- **Lệnh Rollback:** `python3 dr/runbook.py --primary b --target a` (Yêu cầu Region A phải online và đồng bộ lại State).
