{"file": "ND-IT-001_Su_dung_tai_nguyen_CNTT_va_an_toan_thong_tin_v1.0", "code": "ND-IT-001", "title": "Chính sách sử dụng tài nguyên CNTT và an toàn thông tin", "version": "1.0", "issued": "20/11/2026", "effective": "01/12/2026", "owner": "Trung tâm Cloud và An toàn thông tin", "approver": "Lê Thu Hà – Giám đốc Công nghệ (CTO)", "classification": "INTERNAL", "audience": "Toàn bộ người lao động, thực tập sinh và nhà thầu được cấp tài khoản hoặc thiết bị của Nova Digital", "review": "12 tháng/lần, sau mỗi sự cố P1, hoặc khi thay đổi hạ tầng hay yêu cầu tuân thủ"}
---
## 1. Mục đích và phạm vi

Chính sách này đặt ra tiêu chuẩn kỹ thuật để bảo vệ hệ thống, dữ liệu và thiết bị của Nova Digital: phân loại và xử lý dữ liệu, tài khoản và mật khẩu, quyền truy cập, thiết bị, mạng, sử dụng AI, quản lý thay đổi, lỗ hổng, sao lưu và ứng phó sự cố.

Nghĩa vụ ứng xử của người lao động khi dùng hệ thống CNTT (cấm chia sẻ tài khoản, cấm đưa dữ liệu ra ngoài…) và hình thức kỷ luật khi vi phạm được quy định tại ND-HR-002, Chương IV và Chương IX. Chính sách này không nhắc lại các nghĩa vụ đó mà quy định cách thực hiện cụ thể.

<div class="ref" markdown="1">
**Tài liệu liên quan.** Định nghĩa bốn mức phân loại tài liệu: ND-ORG-001, Mục 7. Liên hệ Service Desk và SOC: ND-ORG-001, Mục 6. Ghi nhận thời gian xử lý sự cố ngoài giờ: ND-HR-003, Mục 7. Bảo vệ dữ liệu cá nhân của người lao động: ND-HR-002, Điều 26.
</div>

## 2. Xử lý dữ liệu theo mức phân loại

Mọi dữ liệu và tài liệu đều có một trong bốn mức: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED. Người tạo tài liệu gán mức khi tạo; nếu không chắc, gán mức cao hơn và hỏi chủ sở hữu dữ liệu.

| Thao tác | PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED |
|---|---|---|---|---|
| Nơi lưu trữ | Bất kỳ | Hệ thống do Công ty quản lý | Hệ thống có phân quyền theo nhóm | Hệ thống có phân quyền theo tên và ghi nhật ký truy cập |
| Chia sẻ nội bộ | Tự do | Mọi nhân viên | Chỉ nhóm được nêu trong danh mục | Chỉ người có tên trong danh sách cấp quyền |
| Chia sẻ ra ngoài | Tự do | Cần thỏa thuận bảo mật (NDA) và quản lý trực tiếp duyệt | Cần chủ sở hữu dữ liệu và Pháp chế duyệt; tệp phải mã hóa | Không, trừ khi Tổng Giám đốc duyệt bằng văn bản |
| Gửi qua email | Được | Email công ty | Email công ty, tệp đính kèm mã hóa, mật khẩu gửi qua kênh khác | Không gửi qua email; dùng thư mục chia sẻ có kiểm soát |
| In ấn | Được | Được | Chỉ máy in có xác thực; lấy bản in ngay | Không in, trừ khi chủ sở hữu dữ liệu cho phép |
| Đưa vào công cụ AI | Công cụ được phê duyệt | Công cụ được phê duyệt (Mục 6) | Chỉ NovaAssist nội bộ | Chỉ NovaAssist nội bộ, với tài khoản có quyền tương ứng |
| Hủy | Thông thường | Xóa khỏi hệ thống | Xóa an toàn; giấy hủy bằng máy hủy | Xóa an toàn có biên bản |

## 3. Tài khoản, mật khẩu và xác thực

### 3.1. Mật khẩu

- Mật khẩu tối thiểu 14 ký tự; khuyến khích dùng cụm mật khẩu (passphrase) dễ nhớ.
- Không dùng lại mật khẩu của Công ty cho dịch vụ cá nhân, và ngược lại.
- Lưu mật khẩu trong trình quản lý mật khẩu do Công ty cấp. Không lưu trong tệp văn bản, ghi chú hay trình duyệt cá nhân.
- Không bắt buộc đổi mật khẩu định kỳ. Phải đổi ngay khi nghi ngờ mật khẩu bị lộ, và báo SOC.

### 3.2. Xác thực đa yếu tố (MFA)

MFA bắt buộc với: email, VPN, Nova HR Portal, kho mã nguồn, console cloud và mọi hệ thống chứa dữ liệu CONFIDENTIAL hoặc RESTRICTED. Phương thức ưu tiên là ứng dụng xác thực hoặc khóa bảo mật phần cứng; không dùng SMS cho tài khoản quản trị.

### 3.3. Phiên làm việc

Máy tính tự khóa màn hình sau 05 phút không thao tác. Phiên đăng nhập hệ thống nội bộ hết hạn sau 12 giờ; phiên quản trị hết hạn sau 01 giờ.

## 4. Quyền truy cập

### 4.1. Cấp quyền

- Quyền được cấp theo nguyên tắc tối thiểu cần thiết, qua yêu cầu trên Service Desk, có quản lý trực tiếp và chủ sở hữu hệ thống phê duyệt.
- Quyền quản trị (admin) dùng tài khoản riêng, tách khỏi tài khoản làm việc hằng ngày.
- Nhân viên mới chỉ được cấp quyền vào hệ thống chứa dữ liệu CONFIDENTIAL hoặc RESTRICTED sau khi hoàn thành khóa học bắt buộc (ND-HR-011, Mục 4).

### 4.2. Rà soát quyền

| Loại hệ thống | Chu kỳ rà soát | Người rà soát |
|---|---|---|
| Hệ thống chứa dữ liệu RESTRICTED | Hằng tháng | Chủ sở hữu dữ liệu và SOC |
| Hệ thống chứa dữ liệu CONFIDENTIAL; tài khoản quản trị | Hằng quý | Chủ sở hữu hệ thống |
| Hệ thống INTERNAL | 06 tháng/lần | Chủ sở hữu hệ thống |

### 4.3. Thu hồi quyền

| Trường hợp | Thời hạn thu hồi |
|---|---|
| Nghỉ việc | Trước 18:00 ngày làm việc cuối cùng |
| Chấm dứt hợp đồng ngay hoặc nghi ngờ rủi ro an ninh | Ngay lập tức, theo yêu cầu của Phòng Nhân sự hoặc SOC |
| Điều chuyển công việc | Quyền không còn cần thiết thu hồi trong 03 ngày làm việc; quyền quản trị thu hồi ngay |
| Nhà thầu kết thúc hợp đồng | Trong ngày kết thúc hợp đồng |

## 5. Thiết bị, phần mềm, mạng

### 5.1. Thiết bị do Công ty cấp

- Mọi laptop được mã hóa toàn bộ ổ đĩa, cài phần mềm phát hiện và phản hồi mối đe dọa (EDR) và được quản lý tập trung.
- Bản vá hệ điều hành và trình duyệt được cài tự động. Máy chưa cập nhật bản vá quá 14 ngày bị hạn chế truy cập VPN cho đến khi cập nhật.
- Khi mất thiết bị, báo ngay Service Desk; Service Desk khóa và xóa dữ liệu từ xa trong vòng 01 giờ kể từ khi nhận báo cáo.

### 5.2. Thiết bị cá nhân (BYOD)

- Điện thoại cá nhân chỉ được dùng cho email, chat công việc và ứng dụng MFA, qua ứng dụng do Công ty quản lý.
- Không lưu dữ liệu CONFIDENTIAL hoặc RESTRICTED trên thiết bị cá nhân.
- Không dùng máy tính cá nhân để truy cập kho mã nguồn hoặc console cloud.

### 5.3. Phần mềm và mã nguồn mở

- Chỉ cài phần mềm trong danh mục được duyệt; phần mềm ngoài danh mục yêu cầu qua Service Desk.
- Thư viện mã nguồn mở có giấy phép MIT, Apache 2.0, BSD được dùng tự do. Giấy phép thuộc họ GPL, AGPL cần Pháp chế duyệt trước khi đưa vào sản phẩm giao cho khách hàng.

### 5.4. Mạng và làm việc từ xa

- Truy cập hệ thống nội bộ từ ngoài văn phòng bắt buộc qua VPN của Công ty.
- Không dùng Wi-Fi công cộng mà không bật VPN.
- Mạng khách tại văn phòng tách biệt với mạng nội bộ; không kết nối thiết bị công việc vào mạng khách.

### 5.5. Bí mật kỹ thuật (secret)

- Khóa API, mật khẩu cơ sở dữ liệu, token chỉ được lưu trong kho quản lý bí mật (vault) của Công ty.
- Kho mã nguồn được quét tự động để phát hiện secret. Secret bị lộ phải được thu hồi và thay mới trong vòng 24 giờ, và báo SOC.

## 6. Sử dụng công cụ AI

| Công cụ | Mức dữ liệu tối đa được đưa vào |
|---|---|
| NovaAssist (trợ lý tri thức nội bộ, chạy trên hạ tầng Công ty) | RESTRICTED, giới hạn theo quyền của tài khoản người dùng |
| Trợ lý lập trình và công cụ AI có hợp đồng doanh nghiệp được Công ty phê duyệt (danh sách trên Service Desk) | INTERNAL |
| Dịch vụ AI công cộng chưa được đánh giá | Chỉ PUBLIC |

- Không đưa dữ liệu cá nhân của khách hàng hoặc người lao động vào công cụ AI ngoài NovaAssist.
- Công cụ AI mới chỉ được thêm vào danh sách sau khi Ủy ban An toàn thông tin và Dữ liệu đánh giá điều khoản lưu trữ, huấn luyện trên dữ liệu và vị trí xử lý dữ liệu.

## 7. Quản lý thay đổi hệ thống production

| Loại thay đổi | Ví dụ | Phê duyệt |
|---|---|---|
| Thay đổi chuẩn (Standard) | Thay đổi lặp lại, rủi ro thấp, đã có quy trình mẫu | Phê duyệt trước một lần cho cả loại; ghi ticket mỗi lần thực hiện |
| Thay đổi thông thường (Normal) | Phát hành tính năng, thay đổi cấu hình, nâng cấp hạ tầng | Hội đồng thay đổi (CAB) họp thứ Năm hằng tuần |
| Thay đổi khẩn (Emergency) | Hotfix bảo mật, khôi phục dịch vụ khi có sự cố | Incident Commander và CTO hoặc người được ủy quyền; rà soát lại trong 02 ngày làm việc sau đó |

- Mọi thay đổi có ticket, người phê duyệt, kế hoạch rollback và bằng chứng kiểm thử tương ứng mức rủi ro.
- Thời gian đóng băng: không triển khai thay đổi thông thường lên production sau 15:00 thứ Sáu và trong 02 ngày làm việc trước kỳ nghỉ lễ, tết. Thay đổi khẩn không bị giới hạn.

## 8. Quản lý lỗ hổng

| Mức lỗ hổng | Thời hạn khắc phục trên hệ thống production |
|---|---|
| Nghiêm trọng (Critical) | 07 ngày |
| Cao (High) | 30 ngày |
| Trung bình (Medium) | 90 ngày |
| Thấp (Low) | Theo kế hoạch bảo trì |

Lỗ hổng đang bị khai thác thực tế được xử lý như sự cố P1 (Mục 10). Trường hợp không khắc phục kịp hạn phải có biện pháp giảm thiểu tạm thời và được Ủy ban An toàn thông tin và Dữ liệu chấp thuận ngoại lệ.

## 9. Sao lưu và khôi phục

| Nhóm hệ thống | Ví dụ | Điểm khôi phục tối đa (RPO) | Thời gian khôi phục tối đa (RTO) |
|---|---|---|---|
| Nhóm 1 | Sản phẩm phục vụ khách hàng (NovaCore, NovaInsight, NovaAssist bản khách hàng) | 01 giờ | 04 giờ |
| Nhóm 2 | Hệ thống nội bộ quan trọng: email, Nova HR Portal, kho mã nguồn | 24 giờ | 01 ngày làm việc |
| Nhóm 3 | Hệ thống nội bộ khác | 07 ngày | 05 ngày làm việc |

Dữ liệu sao lưu được mã hóa, lưu ít nhất một bản ở vị trí tách biệt, giữ 35 ngày. Mỗi quý, mỗi nhóm hệ thống được thử khôi phục ít nhất một lần và lưu biên bản.

## 10. Phân loại và ứng phó sự cố

Đây là định nghĩa gốc về mức sự cố, dùng cho cả vận hành kỹ thuật và các chính sách nhân sự liên quan đến trực và nghỉ.

| Mức | Mô tả | Ví dụ | Phản hồi đầu tiên | Cập nhật tình hình |
|---|---|---|---|---|
| P1 – Nghiêm trọng (Critical) | Dịch vụ dừng trên diện rộng hoặc rủi ro dữ liệu nghiêm trọng | Production dừng diện rộng, rò rỉ dữ liệu nghiêm trọng, ransomware, sự cố an ninh có tác động lớn | 15 phút | 30 phút/lần |
| P2 – Lớn (Major) | Suy giảm nghiêm trọng, có ảnh hưởng tới nhiều khách hàng | Hiệu năng suy giảm nghiêm trọng, lỗi đăng nhập hoặc thanh toán trên diện rộng, mất một vùng hạ tầng đã có dự phòng | 30 phút | 01 giờ/lần |
| P3 – Trung bình | Một chức năng hoặc một khách hàng bị ảnh hưởng, có cách xử lý tạm | Lỗi tính năng không chặn công việc | 04 giờ làm việc | Hằng ngày |
| P4 – Thấp | Ảnh hưởng nhỏ, không cấp bách | Lỗi hiển thị, yêu cầu hỗ trợ thông thường | 01 ngày làm việc | Khi có tiến triển |

### 10.1. Quy trình với sự cố P1 và P2

1. Người phát hiện báo SOC ngay (ND-ORG-001, Mục 6), giữ nguyên bằng chứng, không tự xóa log.
2. SOC xác nhận mức sự cố và chỉ định Incident Commander.
3. Với P1: mở phòng chỉ huy sự cố (war-room) trực tuyến hoặc tại văn phòng; mời người on-call, chủ sở hữu hệ thống, và Pháp chế nếu có rủi ro dữ liệu.
4. Sự cố liên quan dữ liệu cá nhân được báo bộ phận Bảo vệ dữ liệu cá nhân để đánh giá nghĩa vụ thông báo theo Luật Bảo vệ dữ liệu cá nhân.
5. Trong 05 ngày làm việc sau khi đóng sự cố P1 hoặc P2, Incident Commander chủ trì buổi rà soát sau sự cố theo nguyên tắc không đổ lỗi và lưu báo cáo.

## 11. Giám sát và quyền riêng tư

- Công ty ghi nhật ký và giám sát thiết bị, tài khoản, mạng và hệ thống do Công ty quản lý nhằm mục đích an ninh, tuân thủ và điều tra sự cố.
- Việc giám sát không nhằm đọc nội dung liên lạc cá nhân. Truy cập nội dung cụ thể chỉ thực hiện khi có sự cố hoặc yêu cầu điều tra được SOC và Pháp chế chấp thuận, và được ghi nhật ký.
- Nhật ký an ninh được lưu 12 tháng.

## Phụ lục. Lịch sử phiên bản

| Phiên bản | Ngày ban hành | Nội dung thay đổi |
|---|---|---|
| 1.0 | 20/11/2026 | Ban hành lần đầu. Trở thành tài liệu gốc về phân loại sự cố P1 – P4 (trước đây định nghĩa P1, P2 nằm ở ND-HR-003) và về yêu cầu VPN khi làm việc từ xa. |
