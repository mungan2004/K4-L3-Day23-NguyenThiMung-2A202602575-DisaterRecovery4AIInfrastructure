# Postmortem: Region A Outage

## 1. Tóm tắt sự cố
- **Nguyên nhân giả lập:** Region A bị cô lập mạng (Network partition / AZ failure) thông qua script chaos.
- **RTO đạt được:** 24.5s
- **RPO đạt được:** 2.0s (mất 1 document)

## 2. Timeline sự kiện
- t0 (0s): Sự cố xảy ra tại Region A.
- t+0.0s: Request của người dùng bắt đầu lỗi.
- t+7.6s: Hệ thống Health Check phát hiện sập sau 2 lần check liên tiếp không phản hồi.
- t+16.2s: Quá trình Failover bắt đầu, Snapshot của DB và Model Weights được phục hồi tại Region B.
- t+22.4s: GPU Pool tại Region B warm-up xong, Endpoint `/readyz` trả về 200.
- t+22.5s: DNS được chuyển hướng (Cutover) sang Region B.
- t+24.5s: Request của người dùng tiếp tục thành công bình thường.

## 3. Câu hỏi phản hồi
**Câu 1: interval=5s, threshold=3 -> sớm nhất bạn có thể phát hiện outage là bao nhiêu giây? Con số đó nằm TRONG hay NGOÀI RTO của bạn?**
> Phát hiện sớm nhất mất 15 giây. Con số này nằm TRONG RTO. Nếu muốn RTO 5 phút, interval có thể để tới 60s (với threshold 3-4 lần). 

**Câu 2: RTO của bạn bị chiếm dụng nhiều nhất bởi phần nào?**
> Health Check (mất 7.6s với thiết lập test interval=2, threshold=2) và GPU warm-up (mất khoảng ~6s).

**Câu 3: Làm thế nào để thu hẹp thời gian warm-up? Có đáng đánh đổi chi phí không?**
> Chuyển sang mô hình Active-Active (Region B cũng luôn full capacity). Điều này sẽ rút ngắn thời gian warm-up xuống 0s, nhưng sẽ tốn gấp đôi chi phí GPU (idle cost).
