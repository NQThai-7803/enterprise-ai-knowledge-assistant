# natural_dev_v1: gold chờ duyệt

Trạng thái: **BẢN NHÁP, chờ chủ dự án duyệt.** Tạo bằng `scripts/eval/natural_dev_check.py` từ `tests/acceptance/natural_dev_v1_gold.yaml`; muốn sửa thì sửa YAML rồi chạy lại.

Gold chỉ soạn từ PDF của corpus V2; chưa chạy hệ thống trên bộ này.

Câu hỏi đã đóng băng nguyên văn: SHA256 `c899d75a86baab36981ed8a424081885cdb7c102441311b97be10c509b19bc94`. Gold sẽ khóa sau khi duyệt.

Cách duyệt: với mỗi câu, đánh dấu **DUYỆT**, hoặc **SỬA** và ghi nội dung cần đổi.

## Kiểm tra

- Lỗi cấu trúc: không có
- Đoạn trích khớp đúng trang PDF: 47/47
- Câu trùng 4-gram trong `app/`: {'ND-003': ['gia tri cot loi']}
- Câu cần bạn quyết định: không có
- Câu gần một câu của bộ khác (bề mặt >= 0,60 hoặc e5 >= 0,90): ND-001, ND-003, ND-004, ND-005, ND-006, ND-008, ND-010, ND-011, ND-012, ND-013, ND-016

## ND-001: ANSWERED

**Câu hỏi:** Tổng thời gian nghỉ lễ là bao nhiêu ngày trong một năm?

**Ý bắt buộc:**
1. 11 ngày nghỉ lễ, Tết trong năm, hưởng nguyên lương.

**Ý không bắt buộc:**
- Gồm Tết Dương lịch 01, Tết Âm lịch 05, Chiến thắng 30/4 01, Quốc tế Lao động 01/5 01, Quốc khánh 02, Giỗ Tổ Hùng Vương 01 ngày.
- Người lao động nước ngoài được nghỉ thêm 01 ngày Tết cổ truyền và 01 ngày Quốc khánh của nước họ.
- Lịch nghỉ cụ thể do HR/doanh nghiệp thông báo hằng năm.

**Citation:** UAT-LEAVE-AUTHORITY-001 tr. 3
**Citation chấp nhận thêm:** ND-HR-004 tr. 5

**Đoạn trích:**
- UAT-LEAVE-AUTHORITY-001 tr. 3 (khớp): "Tổng số ngày nghỉ lễ, Tết theo lịch quốc gia là 11 ngày trong năm."
- ND-HR-004 tr. 5 (khớp): "Tết Dương lịch 01 ngày Tết Âm lịch 05 ngày Ngày Chiến thắng 30/4 01 ngày Ngày Quốc tế Lao động 01/5 01 ngày Quốc khánh 02 ngày Giỗ Tổ Hùng Vương 01 ngày"

**Ví dụ không đạt:**
- Một tổng khác 11 ngày.
- Cộng nghỉ hằng năm (12 ngày) vào nghỉ lễ.

**Gần câu của bộ khác:** uat: bề mặt 0.62 (Q068), e5 0.9061 (Q043); heldout_v1: bề mặt 0.538 (HO-029), e5 0.9302 (HO-029); heldout_v2: bề mặt 0.635 (HO2-017), e5 0.9537 (HO2-017)

**Ghi chú:** ND-HR-004 liệt kê từng dịp (cộng lại 11) nhưng không ghi tổng; UAT-LEAVE-AUTHORITY-001 ghi tổng 11 nhưng là tài liệu mẫu cần rà soát. Trích tài liệu nào cũng được.

- [ ] DUYỆT
- [ ] SỬA:

## ND-002: ANSWERED_LIMITED

**Câu hỏi:** Tôi là ứng viên được tuyển và hoàn thành mốc thử việc thì được thưởng thêm gì không?

**Ý bắt buộc:**
1. Đính chính: khoản thưởng gắn với việc ứng viên được tuyển và hoàn thành mốc thử việc là Employee Referral Bonus (thưởng giới thiệu, 3 - 15 triệu đồng), dành cho NGƯỜI GIỚI THIỆU ứng viên, không phải cho chính ứng viên.
2. Tài liệu không nêu khoản thưởng nào cho chính ứng viên khi hoàn thành thử việc.

**Tài liệu không nêu (phần của câu hỏi):**
- Khoản thưởng nào dành cho chính ứng viên/người mới khi qua thử việc.

**Citation:** ND-HR-005 tr. 9

**Đoạn trích:**
- ND-HR-005 tr. 9 (khớp): "Employee Referral Bonus 3 - 15 triệu đồng Ứng viên được tuyển và hoàn thành mốc thử việc/điều kiện chương trình."

**Điều kiện đạt:** Đính chính rằng Employee Referral Bonus là thưởng cho người giới thiệu khi ứng viên được tuyển hoàn thành thử việc, không phải thưởng cho ứng viên (có thể kèm mức 3 - 15 triệu đồng).

**Ví dụ không đạt:**
- Nói ứng viên (người được tuyển) nhận 3 - 15 triệu đồng khi qua thử việc.
- Nói không có khoản thưởng nào liên quan mà không nhắc Employee Referral Bonus.

**Ghi chú:** Owner 2026-11-17: ANSWERED_LIMITED; thưởng giới thiệu dành cho người giới thiệu, đạt khi đính chính, FAIL nếu nói ứng viên nhận 3 - 15 triệu. Trang 9 xếp khoản này trong mục 'Hiệu suất, dự án, sáng kiến, giới thiệu và thưởng đặc biệt'.

- [ ] DUYỆT
- [ ] SỬA:

## ND-003: ANSWERED

**Câu hỏi:** Năm giá trị cốt lõi của công ty Nova Digital là gì? Hãy liệt kê.

**Ý bắt buộc:**
1. Tin cậy.
2. Lấy khách hàng làm trung tâm.
3. Chất lượng kỹ thuật.
4. Hợp tác có trách nhiệm.
5. Học hỏi liên tục.

**Ý không bắt buộc:**
- Mô tả ngắn của từng giá trị như trong tài liệu.

**Citation:** ND-CORP-001 tr. 4

**Đoạn trích:**
- ND-CORP-001 tr. 4 (khớp): "Năm giá trị cốt lõi 01 TIN CẬY"
- ND-CORP-001 tr. 4 (khớp): "02 LẤY KHÁCH HÀNG LÀM TRUNG TÂM"
- ND-CORP-001 tr. 4 (khớp): "03 CHẤT LƯỢNG KỸ THUẬT"
- ND-CORP-001 tr. 4 (khớp): "04 HỢP TÁC CÓ TRÁCH NHIỆM"
- ND-CORP-001 tr. 4 (khớp): "05 HỌC HỎI LIÊN TỤC"

**Ví dụ không đạt:**
- Thiếu hoặc thay một giá trị bằng nội dung tầm nhìn, sứ mệnh hay nguyên tắc văn hóa.

**Gần câu của bộ khác:** heldout_v1: bề mặt 0.589 (HO-014), e5 0.9023 (HO-014)

- [ ] DUYỆT
- [ ] SỬA:

## ND-004: ANSWERED

**Câu hỏi:** Tôi kết hôn thì được nghỉ việc riêng mà vẫn hưởng lương mấy ngày?

**Ý bắt buộc:**
1. 03 ngày.

**Ý không bắt buộc:**
- Nghỉ việc riêng hưởng lương do kết hôn không trừ vào phép năm (tình huống mẫu).
- Phúc lợi kết hôn 2.000.000 đ là khoản tiền, không phải ngày nghỉ.

**Citation:** ND-HR-004 tr. 6
**Citation chấp nhận thêm:** UAT-LEAVE-AUTHORITY-001 tr. 4

**Đoạn trích:**
- ND-HR-004 tr. 6 (khớp): "Kết hôn 03 ngày Con đẻ hoặc con nuôi kết hôn 01 ngày"
- UAT-LEAVE-AUTHORITY-001 tr. 4 (khớp): "Kết hôn 03 ngày Con kết hôn 01 ngày"

**Ví dụ không đạt:**
- 01 ngày (mức khi con kết hôn).

**Gần câu của bộ khác:** uat: bề mặt 0.589 (Q043), e5 0.9348 (Q043); heldout_v1: bề mặt 0.6 (HO-021), e5 0.88 (HO-029)

- [ ] DUYỆT
- [ ] SỬA:

## ND-005: ANSWERED

**Câu hỏi:** Tôi lần đầu lỡ quên chấm công thì có bị phạt gì không?

**Ý bắt buộc:**
1. Quên chấm công / vi phạm quy trình lần đầu, không gây hậu quả thuộc nhóm nhẹ: nhắc nhở, hướng dẫn, bổ sung hồ sơ; chỉ xem xét kỷ luật nếu có căn cứ và tái diễn.
2. Công ty không phạt tiền hoặc cắt lương thay cho xử lý kỷ luật.

**Tài liệu không nói:**
- Không có mức phạt cụ thể nào cho lần quên đầu tiên.

**Ý không bắt buộc:**
- Tạo yêu cầu điều chỉnh chấm công trên HRM kèm bằng chứng, nên trong 03 ngày làm việc.
- Dữ liệu chấm công bất thường phải được xác minh trước khi kết luận vi phạm.

**Citation:** ND-HR-002 tr. 15
**Citation chấp nhận thêm:** ND-HR-003 tr. 6, 9; ND-HR-002 tr. 12; ND-HR-005 tr. 10

**Đoạn trích:**
- ND-HR-002 tr. 15 (khớp): "Nhẹ Quên chấm công; vi phạm quy trình lần đầu, không gây hậu quả Nhắc nhở, hướng dẫn, bổ sung hồ sơ; xem xét kỷ luật nếu có căn cứ và tái diễn"
- ND-HR-003 tr. 9 (khớp): "Không áp dụng phạt tiền hoặc cắt lương thay cho xử lý kỷ luật lao động trái quy định pháp luật."

**Ví dụ không đạt:**
- Bị phạt tiền hoặc trừ lương.
- Tự động bị khiển trách.

**Gần câu của bộ khác:** uat: bề mặt 0.618 (Q038), e5 0.9044 (Q038)

- [ ] DUYỆT
- [ ] SỬA:

## ND-006: ANSWERED

**Câu hỏi:** Nhân viên được phép nói về lương của chính mình cho người khác không?

**Ý bắt buộc:**
1. Được: chính sách không cấm người lao động sử dụng, trao đổi hoặc cung cấp thông tin lương của chính mình khi thực hiện quyền hợp pháp.

**Ý không bắt buộc:**
- Không được truy cập, sao chép hoặc phát tán dữ liệu lương của người khác khi không có nhiệm vụ/phê duyệt.
- Quyền của người lao động với thông tin lương của chính mình không bị hạn chế.

**Citation:** ND-HR-005 tr. 11
**Citation chấp nhận thêm:** ND-HR-005 tr. 3

**Đoạn trích:**
- ND-HR-005 tr. 11 (khớp): "Chính sách không cấm người lao động sử dụng, trao đổi hoặc cung cấp thông tin lương của chính mình khi thực hiện quyền hợp pháp."
- ND-HR-005 tr. 3 (khớp): "quyền của người lao động đối với thông tin lương của chính mình không bị hạn chế."

**Ví dụ không đạt:**
- Không được, lương là thông tin bảo mật.

**Gần câu của bộ khác:** uat: bề mặt 0.569 (Q073), e5 0.9308 (Q073)

- [ ] DUYỆT
- [ ] SỬA:

## ND-007: ANSWERED

**Câu hỏi:** Tôi chia sẻ tài khoản của tôi cho đồng nghiệp để làm hộ phần cần thiết thì có bị kỷ luật không?

**Ý bắt buộc:**
1. Nội quy cấm chia sẻ: mỗi người dùng tài khoản cá nhân; cấm chia sẻ mật khẩu, mã OTP, khóa API, khóa SSH hoặc token.
2. Chia sẻ tài khoản thuộc nhóm nặng: khoanh vùng rủi ro, thu hồi quyền; xem xét hình thức kỷ luật phù hợp sau quy trình.

**Tài liệu không nói:**
- Lý do làm hộ phần việc cần thiết không phải ngoại lệ được nêu.
- Hình thức kỷ luật cụ thể sẽ áp dụng.

**Ý không bắt buộc:**
- Không hành vi nào tự động dẫn đến một hình thức kỷ luật khi chưa xác minh và đủ thủ tục.
- Các hình thức kỷ luật: khiển trách; kéo dài thời hạn nâng lương không quá 06 tháng; cách chức; sa thải theo điều kiện pháp luật.

**Citation:** ND-HR-002 tr. 7, 15
**Citation chấp nhận thêm:** ND-HR-002 tr. 12

**Đoạn trích:**
- ND-HR-002 tr. 7 (khớp): "Mỗi người sử dụng tài khoản cá nhân; cấm chia sẻ mật khẩu, mã OTP, khóa API, khóa SSH hoặc token truy cập."
- ND-HR-002 tr. 15 (khớp): "Nặng Chia sẻ tài khoản; gửi dữ liệu công việc sang email cá nhân; bỏ qua kiểm soát thay đổi Khoanh vùng rủi ro, thu hồi quyền; xem xét hình thức kỷ luật phù hợp sau quy trình"

**Ví dụ không đạt:**
- Được phép nếu chỉ để làm hộ.
- Chắc chắn bị sa thải.

- [ ] DUYỆT
- [ ] SỬA:

## ND-008: ANSWERED_LIMITED

**Câu hỏi:** Công ty Nova Digital có bao nhiêu khối và giám đốc của từng khối là ai?

**Ý bắt buộc:**
1. Ba khối trong sơ đồ cơ cấu: Khối Sản phẩm & Công nghệ, Khối Kinh doanh & Khách hàng, Khối Vận hành Doanh nghiệp.
2. Tài liệu không ghi giám đốc của từng khối; chỉ liệt kê Ban điều hành và phạm vi phụ trách: CEO Nguyễn Anh Khoa, CTO Lê Thu Hà, COO Võ Ngọc Linh, CFO Phạm Gia Minh, CHRO Trương Thanh An.

**Tài liệu không nêu (phần của câu hỏi):**
- Người đứng đầu từng khối.

**Citation:** ND-CORP-001 tr. 6
**Citation chấp nhận thêm:** ND-CORP-001 tr. 7, 8

**Đoạn trích:**
- ND-CORP-001 tr. 6 (khớp): "KHỐI SẢN PHẨM & CÔNG NGHỆ KHỐI KINH DOANH & KHÁCH HÀNG KHỐI VẬN HÀNH DOANH NGHIỆP"
- ND-CORP-001 tr. 6 (khớp): "Tổng Giám đốc (CEO) Nguyễn Anh Khoa - chịu trách nhiệm kết quả kinh doanh và điều hành chung"
- ND-CORP-001 tr. 6 (khớp): "Giám đốc Vận hành (COO) Võ Ngọc Linh - phụ trách triển khai, dịch vụ khách hàng và vận hành nội bộ"

**Điều kiện đạt:** Nêu đúng 3 khối và nói rõ tài liệu không ghi giám đốc từng khối; có thể kèm Ban điều hành và phạm vi phụ trách.

**Ví dụ không đạt:**
- Tự gán một giám đốc cho từng khối, ví dụ giám đốc Khối Kinh doanh & Khách hàng là COO.
- Một số khối khác 3 mà không giải thích.

**Gần câu của bộ khác:** uat: bề mặt 0.582 (Q009), e5 0.9426 (Q002); heldout_v1: bề mặt 0.489 (HO-014), e5 0.916 (HO-014)

**Ghi chú:** Owner 2026-11-17: ANSWERED_LIMITED; nêu 3 khối theo sơ đồ trang 6 và nói rõ tài liệu không quy định giám đốc riêng cho từng khối; FAIL nếu tự gán giám đốc cho từng khối. Trang 7-8 cũng gọi một số đơn vị là 'Khối'; số khối theo trang 6.

- [ ] DUYỆT
- [ ] SỬA:

## ND-009: ANSWERED

**Câu hỏi:** Tôi dùng công cụ AI để làm việc thì có bị kỷ luật không?

**Ý bắt buộc:**
1. Được dùng công cụ AI được Công ty phê duyệt cho mục đích công việc.
2. Không nhập dữ liệu mật, dữ liệu cá nhân, mã nguồn độc quyền, khóa truy cập, hợp đồng hoặc thông tin khách hàng vào dịch vụ AI công cộng chưa được đánh giá; nội dung AI tạo phải được người kiểm tra trước khi dùng.
3. Dùng phần mềm chưa duyệt thuộc nhóm trung bình: xác minh, coaching/đào tạo; có thể xem xét khiển trách tùy lỗi và tình tiết.

**Tài liệu không nói:**
- Dùng công cụ AI đã được phê duyệt đúng quy tắc thì bị kỷ luật.
- Một điều khoản kỷ luật riêng cho việc dùng AI.

**Citation:** ND-HR-002 tr. 7
**Citation chấp nhận thêm:** ND-HR-002 tr. 15

**Đoạn trích:**
- ND-HR-002 tr. 7 (khớp): "Chỉ sử dụng công cụ AI được Công ty phê duyệt cho mục đích công việc."
- ND-HR-002 tr. 7 (khớp): "Không nhập dữ liệu mật, dữ liệu cá nhân, mã nguồn độc quyền, khóa truy cập, hợp đồng hoặc thông tin khách hàng vào dịch vụ AI công cộng chưa được đánh giá."
- ND-HR-002 tr. 15 (khớp): "Trung bình Đi muộn lặp lại; dùng phần mềm chưa duyệt; không hoàn tất bàn giao Xác minh, coaching/đào tạo; có thể xem xét khiển trách tùy lỗi và tình tiết"

**Ví dụ không đạt:**
- Dùng AI là bị kỷ luật.
- Được dùng mọi công cụ AI tùy ý.

- [ ] DUYỆT
- [ ] SỬA:

## ND-010: ANSWERED

**Câu hỏi:** Tôi là nhân viên thì có thể xin tạm ứng lương trước được không?

**Ý bắt buộc:**
1. Có thể đề nghị tạm ứng trong trường hợp khó khăn hoặc tình huống được pháp luật/chính sách cho phép.
2. Mức và lịch hoàn ứng do HR/Finance xác nhận bằng văn bản hoặc trên HRM.

**Tài liệu không nói:**
- Mức tạm ứng tối đa và thời hạn xét duyệt.

**Ý không bắt buộc:**
- Không thu lãi nội bộ với khoản tạm ứng lương thông thường.

**Citation:** ND-HR-005 tr. 10

**Đoạn trích:**
- ND-HR-005 tr. 10 (khớp): "Người lao động có thể đề nghị tạm ứng trong trường hợp khó khăn hoặc tình huống được pháp luật/chính sách cho phép."
- ND-HR-005 tr. 10 (khớp): "Mức và lịch hoàn ứng được HR/Finance xác nhận bằng văn bản hoặc trên HRM."

**Ví dụ không đạt:**
- Không được tạm ứng.
- Một mức tạm ứng tối đa không có trong tài liệu.

**Gần câu của bộ khác:** uat: bề mặt 0.622 (Q046), e5 0.8876 (Q046)

- [ ] DUYỆT
- [ ] SỬA:

## ND-011: ANSWERED

**Câu hỏi:** Ví dụ tôi muốn tố giác nội bộ công ty thì liên lạc qua mail nào?

**Ý bắt buộc:**
1. compliance@novadigital.example (đầu mối Tuân thủ và tố giác nội bộ).

**Ý không bắt buộc:**
- Kênh phản ánh theo nội quy: quản lý, HR Business Partner, Ethics Officer hoặc ethics@novadigital.example.

**Citation:** ND-CORP-001 tr. 9
**Citation chấp nhận thêm:** ND-HR-002 tr. 9, 15

**Đoạn trích:**
- ND-CORP-001 tr. 9 (khớp): "Tuân thủ và tố giác nội bộ compliance@novadigital.example"
- ND-HR-002 tr. 9 (khớp): "Người lao động có thể phản ánh với quản lý, HR Business Partner, Ethics Officer hoặc kênh ethics@novadigital.example."
- ND-HR-002 tr. 15 (khớp): "Đạo đức và phản ánh ethics@novadigital.example"

**Ví dụ không đạt:**
- Một địa chỉ email khác không được chỉ định cho tố giác (hr@, people@, ethics@, ...) mà không có compliance@.

**Gần câu của bộ khác:** heldout_v2: bề mặt 0.63 (HO2-014), e5 0.8773 (HO2-014)

**Ghi chú:** Owner 2026-11-17: nếu tài liệu chỉ định ethics@ là kênh tố giác thì chỉ nêu ethics@ = PASS; nếu tài liệu liệt kê nhiều kênh dành riêng cho tố giác thì thiếu kênh = PARTIAL; email sai mục đích = FAIL. Theo PDF chỉ compliance@ được chỉ định cho tố giác, nên: nêu compliance@ = PASS (kèm ethics@ cũng được); chỉ nêu ethics@ hoặc email khác = FAIL.

- [ ] DUYỆT
- [ ] SỬA:

## ND-012: ANSWERED

**Câu hỏi:** Nếu trường hợp khẩn cấp thì tôi xin nghỉ không lương có được không?

**Ý bắt buộc:**
1. Ngoài trường hợp luật định, người lao động có thể đề nghị nghỉ không hưởng lương nhưng phải được công ty chấp thuận.
2. Khi khẩn cấp: không bắt buộc báo trước theo thời hạn (đề nghị từ 05 ngày liên tục thường gửi trước 10 ngày làm việc), có thể rời lịch làm việc trước khi yêu cầu được duyệt nếu đã thông báo cho quản lý; hoàn thiện HRM và hồ sơ sau.

**Tài liệu không nói:**
- Nghỉ không lương khẩn cấp được tự động chấp thuận.
- Thế nào là khẩn cấp.

**Ý không bắt buộc:**
- Theo chính sách nghỉ mẫu: báo qua điện thoại/kênh khẩn cấp trong 02 giờ kể từ giờ bắt đầu ca; nghỉ không lương có thể ảnh hưởng lương, phụ cấp, chuyên cần, bảo hiểm.

**Citation:** ND-HR-004 tr. 6
**Citation chấp nhận thêm:** ND-HR-004 tr. 9; UAT-LEAVE-AUTHORITY-001 tr. 4, 5

**Đoạn trích:**
- ND-HR-004 tr. 6 (khớp): "Ngoài các trường hợp luật định, người lao động có thể đề nghị nghỉ không hưởng lương và phải được công ty chấp thuận trước."
- ND-HR-004 tr. 6 (khớp): "Đề nghị từ 05 ngày làm việc liên tục trở lên nên gửi trước ít nhất 10 ngày làm việc, trừ trường hợp khẩn cấp."
- ND-HR-004 tr. 6 (khớp): "Người lao động chỉ rời lịch làm việc sau khi yêu cầu ở trạng thái Approved, trừ tình huống khẩn cấp đã thông báo cho quản lý."

**Ví dụ không đạt:**
- Được nghỉ ngay, không cần ai chấp thuận.
- Không được nghỉ không lương.

**Gần câu của bộ khác:** uat: bề mặt 0.541 (Q046), e5 0.9102 (Q046)

- [ ] DUYỆT
- [ ] SỬA:

## ND-013: ANSWERED

**Câu hỏi:** Ví dụ trong trường hợp tôi sinh con thì có hỗ trợ phần tiền nào không?

**Ý bắt buộc:**
1. Có: phúc lợi 2.000.000 đ/lần khi sinh con hoặc nhận con nuôi hợp pháp.

**Ý không bắt buộc:**
- Đề nghị qua HRM > Welfare Request, mục tiêu 03 ngày làm việc.
- Chế độ thai sản do BHXH chi theo pháp luật, không phải khoản công ty chi.

**Citation:** ND-HR-006 tr. 9
**Citation chấp nhận thêm:** ND-HR-006 tr. 11; ND-HR-004 tr. 8

**Đoạn trích:**
- ND-HR-006 tr. 9 (khớp): "Sinh con / nhận con nuôi hợp pháp 2.000.000 đ/lần"

**Ví dụ không đạt:**
- 3.000.000 đ (mức tang chế).
- Không có hỗ trợ nào.

**Gần câu của bộ khác:** uat: bề mặt 0.538 (Q087), e5 0.9329 (Q087)

- [ ] DUYỆT
- [ ] SỬA:

## ND-014: ANSWERED_LIMITED

**Câu hỏi:** Công ty tổ chức team building mấy lần trong năm?

**Ý bắt buộc:**
1. Tài liệu không ghi số lần tổ chức team building trong năm.
2. Tài liệu ghi company trip/retreat dự kiến 01 lần/năm (tùy kết quả kinh doanh, an toàn, ngân sách) và ngân sách team building 1.200.000 đ/người/năm.

**Tài liệu không nêu (phần của câu hỏi):**
- Số lần team building trong năm.

**Citation:** ND-HR-006 tr. 9

**Đoạn trích:**
- ND-HR-006 tr. 9 (khớp): "Company trip/retreat dự kiến 01 lần/năm tùy kết quả kinh doanh, an toàn và ngân sách."
- ND-HR-006 tr. 9 (khớp): "Team building budget mô phỏng: 1.200.000 đ/người/năm, quản lý theo đầu người đủ điều kiện và hóa đơn hợp lệ."

**Điều kiện đạt:** Nói tài liệu không ghi số lần team building; có thể kèm company trip/retreat dự kiến 01 lần/năm và ngân sách 1.200.000 đ/người/năm.

**Ví dụ không đạt:**
- Khẳng định team building 01 lần/năm (lấy từ company trip: sai chủ thể).
- Một số lần không có trong tài liệu.

**Ghi chú:** Owner 2026-11-17: ANSWERED_LIMITED; tài liệu không nêu số lần team building (chỉ có ngân sách/người/năm); trả '01 lần/năm' lấy từ company trip = FAIL (sai chủ thể).

- [ ] DUYỆT
- [ ] SỬA:

## ND-015: ANSWERED

**Câu hỏi:** Quy trình khiếu nại của Payroll Query là như nào? Giải thích chi tiết.

**Ý bắt buộc:**
1. Gửi yêu cầu: nhân viên tạo ticket HRM, nêu kỳ lương, khoản sai lệch và tài liệu hỗ trợ.
2. Xác minh: HR/Finance đối chiếu HRM, chấm công, HĐLĐ, quyết định lương, OT và dữ liệu ngân hàng.
3. Phản hồi: mục tiêu phản hồi sơ bộ trong 03 ngày làm việc, trừ vụ việc phức tạp.
4. Điều chỉnh: khoản thiếu thanh toán bổ sung sớm nhất hợp lý; khoản trả thừa xử lý minh bạch, ưu tiên thỏa thuận lộ trình hoàn trả.
5. Escalation: nếu chưa thống nhất, yêu cầu HR Head/Finance Head rà soát và dùng quy trình khiếu nại ND-HR-010.

**Ý không bắt buộc:**
- Sai lệch được gửi qua HRM Payroll Query trong vòng 05 ngày làm việc.
- Không quản lý nào được trả đũa người hỏi về payslip một cách thiện chí.

**Citation:** ND-HR-005 tr. 12
**Citation chấp nhận thêm:** ND-HR-005 tr. 5, 13

**Đoạn trích:**
- ND-HR-005 tr. 12 (khớp): "1. Gửi yêu cầu Nhân viên tạo ticket HRM, nêu kỳ lương, khoản sai lệch và tài liệu hỗ trợ."
- ND-HR-005 tr. 12 (khớp): "2. Xác minh HR/Finance đối chiếu HRM, chấm công, HĐLĐ, quyết định lương, OT và dữ liệu ngân hàng."
- ND-HR-005 tr. 12 (khớp): "3. Phản hồi Mục tiêu phản hồi sơ bộ trong 03 ngày làm việc, trừ vụ việc phức tạp."
- ND-HR-005 tr. 12 (khớp): "5. Escalation Nếu chưa thống nhất, nhân viên có thể yêu cầu HR Head/Finance Head rà soát và sử dụng quy trình khiếu nại ND- HR-010."
- ND-HR-005 tr. 5 (khớp): "Sai lệch được gửi qua HRM Payroll Query trong vòng 05 ngày làm việc"

**Ví dụ không đạt:**
- Thời hạn phản hồi khác 03 ngày làm việc.
- Bỏ bước xác minh hoặc escalation.

- [ ] DUYỆT
- [ ] SỬA:

## ND-016: ANSWERED

**Câu hỏi:** Thưởng hiệu suất exceptional là bao nhiêu?

**Ý bắt buộc:**
1. 1,5 - 2,0 tháng Base Salary.

**Ý không bắt buộc:**
- Phụ thuộc kết quả công ty và phê duyệt ngân sách.

**Citation:** ND-HR-005 tr. 9

**Đoạn trích:**
- ND-HR-005 tr. 9 (khớp): "Exceptional 1,5 - 2,0 tháng Base Salary Phụ thuộc kết quả công ty và phê duyệt ngân sách."

**Ví dụ không đạt:**
- 1,0 - 1,5 tháng (mức Exceeds Expectations).

**Gần câu của bộ khác:** heldout_v1: bề mặt 0.609 (HO-018), e5 0.8226 (HO-028)

- [ ] DUYỆT
- [ ] SỬA:

## ND-017: ANSWERED

**Câu hỏi:** Vai trò của HR Benefits thì gồm những trách nhiệm gì?

**Ý bắt buộc:**
1. Đăng ký/điều chỉnh (bảo hiểm, phúc lợi).
2. Hướng dẫn hồ sơ.
3. Quản lý nhà bảo hiểm.
4. Tiếp nhận ticket.
5. Bảo mật dữ liệu.

**Ý không bắt buộc:**
- Tiếp nhận báo sai lệch thông tin BHXH/BHYT.
- Rà soát lần 1 khiếu nại quyết định quyền lợi bổ sung trong 10 ngày làm việc.
- Hỗ trợ NovaCare claim (HR hỗ trợ trong 02 ngày).

**Citation:** ND-HR-006 tr. 13
**Citation chấp nhận thêm:** ND-HR-006 tr. 4, 5, 11, 12

**Đoạn trích:**
- ND-HR-006 tr. 13 (khớp): "HR Benefits Đăng ký/điều chỉnh, hướng dẫn hồ sơ, quản lý nhà bảo hiểm, tiếp nhận ticket, bảo mật dữ liệu."

**Ví dụ không đạt:**
- Trách nhiệm của Payroll/Finance (khấu trừ, đóng bảo hiểm, thanh toán) gán cho HR Benefits.

- [ ] DUYỆT
- [ ] SỬA:

## ND-018: ANSWERED

**Câu hỏi:** Đánh giá hiệu suất làm việc vào tháng mấy trong năm?

**Ý bắt buộc:**
1. Tháng 01 - 02 (đánh giá hiệu suất năm trong chu kỳ salary review mô phỏng).

**Ý không bắt buộc:**
- Calibration tháng 03; phê duyệt ngân sách tăng lương tháng 03 - 04; thông báo trong tháng 04; hiệu lực thường 01/05.

**Citation:** ND-HR-005 tr. 8

**Đoạn trích:**
- ND-HR-005 tr. 8 (khớp): "Đánh giá hiệu suất năm Tháng 01 - 02"

**Ví dụ không đạt:**
- Tháng 03 hoặc 04 (calibration, thông báo).

- [ ] DUYỆT
- [ ] SỬA:

## ND-019: ANSWERED

**Câu hỏi:** Trong trường hợp tôi là người lao động bị ốm nặng thì cần làm gì?

**Ý bắt buộc:**
1. Thông báo cho quản lý càng sớm càng tốt, ưu tiên trước giờ làm; khi cấp cứu có thể nhờ người thân thông báo.
2. Đăng ký Sick Leave / BHXH trên HRM (khi khẩn cấp có thể hoàn thiện sau) và nộp chứng từ khi pháp luật hoặc cơ quan BHXH yêu cầu.

**Tài liệu không nói:**
- Định nghĩa ốm nặng, hay quy trình riêng cho ốm nặng ngoài nghỉ ốm và ốm dài ngày.

**Ý không bắt buộc:**
- Nghỉ ốm theo chế độ BHXH không đồng nghĩa nghỉ hưởng nguyên lương do công ty; mức hưởng theo pháp luật BHXH.
- Không bị yêu cầu họp hay xử lý công việc thường xuyên khi đang nghỉ ốm.
- Chẩn đoán chi tiết chỉ cung cấp cho HR/BHXH khi cần.
- Ốm dài ngày: quyền lợi bắt buộc theo pháp luật; các allowance phụ thuộc ngày làm việc có thể tạm dừng, HR thông báo rõ.
- Theo chính sách nghỉ mẫu: thông báo cả quản lý trực tiếp và Phòng Nhân sự; cấp cứu hoặc điều trị nội trú thì thân nhân có thể báo thay.

**Citation:** ND-HR-004 tr. 7
**Citation chấp nhận thêm:** ND-HR-004 tr. 9; UAT-LEAVE-AUTHORITY-001 tr. 4; ND-HR-006 tr. 10; ND-HR-003 tr. 9

**Đoạn trích:**
- ND-HR-004 tr. 7 (khớp): "Thông báo cho quản lý càng sớm càng tốt, ưu tiên trước giờ bắt đầu làm việc; trong trường hợp cấp cứu có thể nhờ người thân thông báo."
- ND-HR-004 tr. 7 (khớp): "Đăng ký loại nghỉ Sick Leave / BHXH trên HRM và cung cấp chứng từ khi pháp luật hoặc cơ quan BHXH yêu cầu."
- UAT-LEAVE-AUTHORITY-001 tr. 4 (khớp): "Trường hợp cấp cứu hoặc điều trị nội trú, thân nhân có thể thay người lao động thông báo ban đầu."

**Ví dụ không đạt:**
- Phải đi làm hoặc họp khi đang ốm.
- Nghỉ ốm luôn được công ty trả nguyên lương.

- [ ] DUYỆT
- [ ] SỬA:

## ND-020: ANSWERED

**Câu hỏi:** Tôi quên check-in nhưng có bằng chứng hợp lệ thực tế về việc đi làm thì tôi phải báo cáo ai?

**Ý bắt buộc:**
1. Tạo yêu cầu điều chỉnh chấm công trên HRM, nêu ngày, thời gian cần sửa, lý do và bằng chứng; nên gửi trong 03 ngày làm việc.
2. Quản lý trực tiếp kiểm tra và phê duyệt/từ chối.
3. HR kiểm tra tính nhất quán, xử lý ngoại lệ và khóa dữ liệu khi kết thúc kỳ công.

**Ý không bắt buộc:**
- Bằng chứng có thể là log hệ thống, lịch họp, ticket, biên bản công tác hoặc xác nhận của quản lý.
- Sau khi khóa kỳ công (ngày 04-05 tháng sau), điều chỉnh muộn cần yêu cầu đặc biệt có phê duyệt của HR và quản lý có thẩm quyền.

**Citation:** ND-HR-003 tr. 6
**Citation chấp nhận thêm:** ND-HR-003 tr. 10, 11

**Đoạn trích:**
- ND-HR-003 tr. 6 (khớp): "Quên check-in hoặc check-out nhưng có bằng chứng hợp lý về việc làm việc thực tế."
- ND-HR-003 tr. 6 (khớp): "1. Nhân viên tạo yêu cầu điều chỉnh trên HRM, nêu ngày, thời gian cần sửa, lý do và bằng chứng liên quan."
- ND-HR-003 tr. 6 (khớp): "3. Quản lý trực tiếp kiểm tra lịch làm việc, lịch họp, ticket, log dự án hoặc thông tin liên quan và phê duyệt/từ chối."

**Ví dụ không đạt:**
- Chỉ cần báo đồng nghiệp hoặc không cần làm gì.
- Gửi email cho Service Desk thay cho yêu cầu trên HRM.

- [ ] DUYỆT
- [ ] SỬA:

## Kiểm trùng, chỉ báo số liệu

Số lớn nhất của mỗi câu so với từng bộ, kèm id gần nhất. Không loại câu nào theo số này.

| id | bộ | 3-gram ký tự | difflib | 4-gram từ | e5 cosine |
|---|---|---:|---:|---:|---:|
| ND-001 | uat | 0.344 (Q068) | 0.62 (Q067) | 0.0 (Q001) | 0.9061 (Q043) |
| ND-001 | heldout_v1 | 0.313 (HO-029) | 0.538 (HO-020) | 0.0 (HO-001) | 0.9302 (HO-029) |
| ND-001 | heldout_v2 | 0.356 (HO2-017) | 0.635 (HO2-017) | 0.0 (HO2-001) | 0.9537 (HO2-017) |
| ND-001 | relevance | 0.319 (REL-203) | 0.569 (REL-204) | 0.0 (REL-101) | 0.8632 (REL-206) |
| ND-001 | rbac | 0.291 (RBD-13) | 0.531 (RBD-14) | 0.0 (RBD-01) | 0.8364 (RBD-11) |
| ND-001 | false_refusal | 0.272 (FR-N01) | 0.53 (FR-N05) | 0.0 (FR-N01) | 0.8585 (FR-N03) |
| ND-001 | false_refusal_v2 | 0.235 (FR2-F05) | 0.523 (FR2-F01) | 0.0 (FR2-L01) | 0.8351 (FR2-C04) |
| ND-001 | compound | 0.286 (CP1-P02) | 0.493 (CP1-P05) | 0.0 (CP1-P01) | 0.8533 (CP1-A03) |
| ND-002 | uat | 0.314 (Q096) | 0.543 (Q086) | 0.0 (Q001) | 0.8657 (Q096) |
| ND-002 | heldout_v1 | 0.245 (HO-004) | 0.498 (HO-034) | 0.0 (HO-001) | 0.8535 (HO-028) |
| ND-002 | heldout_v2 | 0.217 (HO2-012) | 0.486 (HO2-005) | 0.0 (HO2-001) | 0.8687 (HO2-010) |
| ND-002 | relevance | 0.253 (REL-101) | 0.474 (REL-101) | 0.0 (REL-101) | 0.8386 (REL-306) |
| ND-002 | rbac | 0.165 (RBD-09) | 0.409 (RBD-14) | 0.0 (RBD-01) | 0.8157 (RBD-05) |
| ND-002 | false_refusal | 0.258 (FR-N10) | 0.503 (FR-N10) | 0.0 (FR-N01) | 0.8453 (FR-N05) |
| ND-002 | false_refusal_v2 | 0.275 (FR2-C03) | 0.395 (FR2-E04) | 0.0 (FR2-L01) | 0.8368 (FR2-C03) |
| ND-002 | compound | 0.248 (CP1-P05) | 0.484 (CP1-P02) | 0.0 (CP1-P01) | 0.8193 (CP1-P01) |
| ND-003 | uat | 0.282 (Q004) | 0.523 (Q004) | 0.0 (Q001) | 0.8951 (Q009) |
| ND-003 | heldout_v1 | 0.301 (HO-014) | 0.589 (HO-014) | 0.0 (HO-001) | 0.9023 (HO-014) |
| ND-003 | heldout_v2 | 0.149 (HO2-009) | 0.431 (HO2-008) | 0.0 (HO2-001) | 0.8558 (HO2-015) |
| ND-003 | relevance | 0.153 (REL-103) | 0.408 (REL-207) | 0.0 (REL-101) | 0.8256 (REL-402) |
| ND-003 | rbac | 0.149 (RBD-09) | 0.442 (RBD-03) | 0.0 (RBD-01) | 0.8189 (RBD-02) |
| ND-003 | false_refusal | 0.147 (FR-A02) | 0.47 (FR-A02) | 0.0 (FR-N01) | 0.822 (FR-N06) |
| ND-003 | false_refusal_v2 | 0.156 (FR2-L01) | 0.425 (FR2-F06) | 0.0 (FR2-L01) | 0.8154 (FR2-F04) |
| ND-003 | compound | 0.093 (CP1-P06) | 0.354 (CP1-R01) | 0.0 (CP1-P01) | 0.8091 (CP1-P01) |
| ND-004 | uat | 0.355 (Q043) | 0.589 (Q043) | 0.0 (Q001) | 0.9348 (Q043) |
| ND-004 | heldout_v1 | 0.282 (HO-021) | 0.6 (HO-021) | 0.0 (HO-001) | 0.88 (HO-029) |
| ND-004 | heldout_v2 | 0.287 (HO2-012) | 0.552 (HO2-010) | 0.0 (HO2-001) | 0.8756 (HO2-010) |
| ND-004 | relevance | 0.221 (REL-205) | 0.473 (REL-206) | 0.0 (REL-101) | 0.8544 (REL-206) |
| ND-004 | rbac | 0.156 (RBD-16) | 0.426 (RBD-01) | 0.0 (RBD-01) | 0.8249 (RBD-11) |
| ND-004 | false_refusal | 0.211 (FR-N08) | 0.532 (FR-N08) | 0.0 (FR-N01) | 0.8753 (FR-N01) |
| ND-004 | false_refusal_v2 | 0.21 (FR2-C03) | 0.446 (FR2-F01) | 0.0 (FR2-L01) | 0.8422 (FR2-C03) |
| ND-004 | compound | 0.198 (CP1-P02) | 0.489 (CP1-A02) | 0.0 (CP1-P01) | 0.8357 (CP1-A03) |
| ND-005 | uat | 0.351 (Q038) | 0.618 (Q038) | 0.056 (Q024) | 0.9044 (Q038) |
| ND-005 | heldout_v1 | 0.222 (HO-002) | 0.533 (HO-040) | 0.0 (HO-001) | 0.8708 (HO-040) |
| ND-005 | heldout_v2 | 0.23 (HO2-009) | 0.473 (HO2-008) | 0.0 (HO2-001) | 0.8491 (HO2-009) |
| ND-005 | relevance | 0.22 (REL-101) | 0.467 (REL-401) | 0.0 (REL-101) | 0.8471 (REL-103) |
| ND-005 | rbac | 0.189 (RBD-01) | 0.481 (RBD-03) | 0.0 (RBD-01) | 0.8406 (RBD-18) |
| ND-005 | false_refusal | 0.2 (FR-N10) | 0.458 (FR-A06) | 0.0 (FR-N01) | 0.8434 (FR-A01) |
| ND-005 | false_refusal_v2 | 0.229 (FR2-L01) | 0.491 (FR2-L01) | 0.0 (FR2-L01) | 0.8453 (FR2-C03) |
| ND-005 | compound | 0.137 (CP1-P06) | 0.357 (CP1-P03) | 0.0 (CP1-P01) | 0.8392 (CP1-P02) |
| ND-006 | uat | 0.357 (Q073) | 0.569 (Q073) | 0.0 (Q001) | 0.9308 (Q073) |
| ND-006 | heldout_v1 | 0.242 (HO-010) | 0.523 (HO-005) | 0.0 (HO-001) | 0.8699 (HO-005) |
| ND-006 | heldout_v2 | 0.269 (HO2-008) | 0.495 (HO2-010) | 0.0 (HO2-001) | 0.8802 (HO2-008) |
| ND-006 | relevance | 0.198 (REL-303) | 0.426 (REL-303) | 0.0 (REL-101) | 0.8196 (REL-306) |
| ND-006 | rbac | 0.209 (RBD-09) | 0.409 (RBD-02) | 0.0 (RBD-01) | 0.817 (RBD-18) |
| ND-006 | false_refusal | 0.311 (FR-N09) | 0.438 (FR-N08) | 0.0 (FR-N01) | 0.8822 (FR-N09) |
| ND-006 | false_refusal_v2 | 0.2 (FR2-C04) | 0.464 (FR2-F01) | 0.0 (FR2-L01) | 0.844 (FR2-C03) |
| ND-006 | compound | 0.2 (CP1-P04) | 0.414 (CP1-P04) | 0.0 (CP1-P01) | 0.8275 (CP1-R03) |
| ND-007 | uat | 0.358 (Q073) | 0.539 (Q089) | 0.0 (Q001) | 0.8944 (Q089) |
| ND-007 | heldout_v1 | 0.242 (HO-006) | 0.462 (HO-030) | 0.0 (HO-001) | 0.8744 (HO-002) |
| ND-007 | heldout_v2 | 0.208 (HO2-002) | 0.427 (HO2-020) | 0.0 (HO2-001) | 0.8517 (HO2-014) |
| ND-007 | relevance | 0.235 (REL-101) | 0.405 (REL-201) | 0.0 (REL-101) | 0.8362 (REL-106) |
| ND-007 | rbac | 0.188 (RBD-01) | 0.386 (RBD-03) | 0.0 (RBD-01) | 0.8363 (RBD-01) |
| ND-007 | false_refusal | 0.204 (FR-N06) | 0.453 (FR-N09) | 0.0 (FR-N01) | 0.854 (FR-A06) |
| ND-007 | false_refusal_v2 | 0.186 (FR2-F04) | 0.463 (FR2-F04) | 0.0 (FR2-L01) | 0.8273 (FR2-C01) |
| ND-007 | compound | 0.152 (CP1-A03) | 0.442 (CP1-A03) | 0.0 (CP1-P01) | 0.8147 (CP1-A03) |
| ND-008 | uat | 0.333 (Q009) | 0.582 (Q099) | 0.0 (Q001) | 0.9426 (Q002) |
| ND-008 | heldout_v1 | 0.366 (HO-014) | 0.489 (HO-020) | 0.0 (HO-001) | 0.916 (HO-014) |
| ND-008 | heldout_v2 | 0.192 (HO2-013) | 0.458 (HO2-001) | 0.0 (HO2-001) | 0.8503 (HO2-015) |
| ND-008 | relevance | 0.221 (REL-201) | 0.528 (REL-201) | 0.0 (REL-101) | 0.8244 (REL-406) |
| ND-008 | rbac | 0.222 (RBD-08) | 0.467 (RBD-09) | 0.0 (RBD-01) | 0.8052 (RBD-02) |
| ND-008 | false_refusal | 0.218 (FR-N06) | 0.544 (FR-N06) | 0.0 (FR-N01) | 0.8293 (FR-N06) |
| ND-008 | false_refusal_v2 | 0.202 (FR2-C02) | 0.493 (FR2-C05) | 0.0 (FR2-L01) | 0.8054 (FR2-F02) |
| ND-008 | compound | 0.196 (CP1-R01) | 0.493 (CP1-R01) | 0.0 (CP1-P01) | 0.8116 (CP1-P01) |
| ND-009 | uat | 0.247 (Q094) | 0.509 (Q092) | 0.0 (Q001) | 0.8864 (Q094) |
| ND-009 | heldout_v1 | 0.224 (HO-034) | 0.44 (HO-008) | 0.0 (HO-001) | 0.8728 (HO-027) |
| ND-009 | heldout_v2 | 0.217 (HO2-002) | 0.476 (HO2-006) | 0.0 (HO2-001) | 0.8512 (HO2-020) |
| ND-009 | relevance | 0.239 (REL-103) | 0.472 (REL-104) | 0.0 (REL-101) | 0.8518 (REL-302) |
| ND-009 | rbac | 0.165 (RBD-01) | 0.476 (RBD-09) | 0.0 (RBD-01) | 0.8472 (RBD-04) |
| ND-009 | false_refusal | 0.214 (FR-N03) | 0.504 (FR-N10) | 0.0 (FR-N01) | 0.8344 (FR-N09) |
| ND-009 | false_refusal_v2 | 0.142 (FR2-C01) | 0.482 (FR2-L01) | 0.0 (FR2-L01) | 0.8198 (FR2-C01) |
| ND-009 | compound | 0.152 (CP1-R01) | 0.481 (CP1-P02) | 0.0 (CP1-P01) | 0.8206 (CP1-R01) |
| ND-010 | uat | 0.361 (Q046) | 0.622 (Q038) | 0.032 (Q096) | 0.8876 (Q046) |
| ND-010 | heldout_v1 | 0.318 (HO-010) | 0.525 (HO-040) | 0.0 (HO-001) | 0.869 (HO-006) |
| ND-010 | heldout_v2 | 0.24 (HO2-008) | 0.47 (HO2-020) | 0.0 (HO2-001) | 0.8653 (HO2-010) |
| ND-010 | relevance | 0.288 (REL-103) | 0.451 (REL-303) | 0.0 (REL-101) | 0.8659 (REL-303) |
| ND-010 | rbac | 0.189 (RBD-08) | 0.472 (RBD-14) | 0.0 (RBD-01) | 0.8187 (RBD-18) |
| ND-010 | false_refusal | 0.258 (FR-A01) | 0.477 (FR-N10) | 0.0 (FR-N01) | 0.8787 (FR-N02) |
| ND-010 | false_refusal_v2 | 0.21 (FR2-C03) | 0.471 (FR2-L02) | 0.0 (FR2-L01) | 0.8303 (FR2-L03) |
| ND-010 | compound | 0.224 (CP1-R01) | 0.477 (CP1-R01) | 0.0 (CP1-P01) | 0.8167 (CP1-A01) |
| ND-011 | uat | 0.207 (Q087) | 0.496 (Q073) | 0.0 (Q001) | 0.8656 (Q097) |
| ND-011 | heldout_v1 | 0.274 (HO-005) | 0.481 (HO-032) | 0.0 (HO-001) | 0.8683 (HO-002) |
| ND-011 | heldout_v2 | 0.233 (HO2-014) | 0.63 (HO2-014) | 0.0 (HO2-001) | 0.8773 (HO2-014) |
| ND-011 | relevance | 0.179 (REL-105) | 0.467 (REL-403) | 0.0 (REL-101) | 0.8346 (REL-405) |
| ND-011 | rbac | 0.168 (RBD-03) | 0.433 (RBD-05) | 0.0 (RBD-01) | 0.8422 (RBD-03) |
| ND-011 | false_refusal | 0.214 (FR-A10) | 0.544 (FR-N07) | 0.0 (FR-N01) | 0.8385 (FR-N02) |
| ND-011 | false_refusal_v2 | 0.244 (FR2-L01) | 0.481 (FR2-L05) | 0.0 (FR2-L01) | 0.8482 (FR2-F04) |
| ND-011 | compound | 0.189 (CP1-P02) | 0.482 (CP1-P02) | 0.0 (CP1-P01) | 0.8239 (CP1-A03) |
| ND-012 | uat | 0.383 (Q046) | 0.541 (Q046) | 0.091 (Q046) | 0.9102 (Q046) |
| ND-012 | heldout_v1 | 0.224 (HO-026) | 0.497 (HO-029) | 0.0 (HO-001) | 0.8695 (HO-006) |
| ND-012 | heldout_v2 | 0.259 (HO2-005) | 0.414 (HO2-014) | 0.0 (HO2-001) | 0.8542 (HO2-010) |
| ND-012 | relevance | 0.224 (REL-103) | 0.411 (REL-305) | 0.0 (REL-101) | 0.8457 (REL-206) |
| ND-012 | rbac | 0.179 (RBD-02) | 0.477 (RBD-02) | 0.0 (RBD-01) | 0.8577 (RBD-02) |
| ND-012 | false_refusal | 0.232 (FR-N05) | 0.531 (FR-A01) | 0.0 (FR-N01) | 0.8514 (FR-N01) |
| ND-012 | false_refusal_v2 | 0.168 (FR2-F06) | 0.443 (FR2-C04) | 0.0 (FR2-L01) | 0.8345 (FR2-L01) |
| ND-012 | compound | 0.202 (CP1-A03) | 0.377 (CP1-P05) | 0.0 (CP1-P01) | 0.8124 (CP1-A01) |
| ND-013 | uat | 0.324 (Q087) | 0.538 (Q063) | 0.0 (Q001) | 0.9329 (Q087) |
| ND-013 | heldout_v1 | 0.311 (HO-030) | 0.449 (HO-038) | 0.0 (HO-001) | 0.8863 (HO-030) |
| ND-013 | heldout_v2 | 0.235 (HO2-014) | 0.476 (HO2-005) | 0.0 (HO2-001) | 0.8703 (HO2-014) |
| ND-013 | relevance | 0.198 (REL-101) | 0.452 (REL-103) | 0.0 (REL-101) | 0.8301 (REL-207) |
| ND-013 | rbac | 0.207 (RBD-05) | 0.432 (RBD-16) | 0.0 (RBD-01) | 0.8206 (RBD-02) |
| ND-013 | false_refusal | 0.253 (FR-A10) | 0.526 (FR-A10) | 0.0 (FR-N01) | 0.8579 (FR-N09) |
| ND-013 | false_refusal_v2 | 0.207 (FR2-L01) | 0.441 (FR2-C03) | 0.0 (FR2-L01) | 0.8283 (FR2-F04) |
| ND-013 | compound | 0.235 (CP1-A03) | 0.448 (CP1-A03) | 0.0 (CP1-P01) | 0.8189 (CP1-P03) |
| ND-014 | uat | 0.259 (Q054) | 0.545 (Q012) | 0.0 (Q001) | 0.8735 (Q008) |
| ND-014 | heldout_v1 | 0.319 (HO-012) | 0.561 (HO-012) | 0.0 (HO-001) | 0.882 (HO-012) |
| ND-014 | heldout_v2 | 0.2 (HO2-017) | 0.562 (HO2-009) | 0.0 (HO2-001) | 0.8313 (HO2-012) |
| ND-014 | relevance | 0.159 (REL-105) | 0.5 (REL-105) | 0.0 (REL-101) | 0.827 (REL-201) |
| ND-014 | rbac | 0.171 (RBD-15) | 0.495 (RBD-10) | 0.0 (RBD-01) | 0.8197 (RBD-11) |
| ND-014 | false_refusal | 0.169 (FR-N08) | 0.542 (FR-N08) | 0.0 (FR-N01) | 0.8458 (FR-N04) |
| ND-014 | false_refusal_v2 | 0.185 (FR2-C06) | 0.558 (FR2-F01) | 0.0 (FR2-L01) | 0.8529 (FR2-F05) |
| ND-014 | compound | 0.125 (CP1-A03) | 0.492 (CP1-R02) | 0.0 (CP1-P01) | 0.8235 (CP1-A03) |
| ND-015 | uat | 0.165 (Q024) | 0.415 (Q046) | 0.0 (Q001) | 0.8615 (Q024) |
| ND-015 | heldout_v1 | 0.184 (HO-008) | 0.442 (HO-008) | 0.0 (HO-001) | 0.8695 (HO-027) |
| ND-015 | heldout_v2 | 0.172 (HO2-003) | 0.388 (HO2-004) | 0.0 (HO2-001) | 0.8635 (HO2-004) |
| ND-015 | relevance | 0.165 (REL-101) | 0.357 (REL-403) | 0.0 (REL-101) | 0.8667 (REL-201) |
| ND-015 | rbac | 0.175 (RBD-13) | 0.397 (RBD-01) | 0.0 (RBD-01) | 0.8177 (RBD-18) |
| ND-015 | false_refusal | 0.15 (FR-N07) | 0.403 (FR-N03) | 0.0 (FR-N01) | 0.8436 (FR-A07) |
| ND-015 | false_refusal_v2 | 0.144 (FR2-F06) | 0.404 (FR2-L05) | 0.0 (FR2-L01) | 0.8321 (FR2-C01) |
| ND-015 | compound | 0.132 (CP1-P02) | 0.372 (CP1-A01) | 0.0 (CP1-P01) | 0.8347 (CP1-P06) |
| ND-016 | uat | 0.254 (Q016) | 0.551 (Q061) | 0.0 (Q001) | 0.8355 (Q072) |
| ND-016 | heldout_v1 | 0.292 (HO-018) | 0.609 (HO-018) | 0.0 (HO-001) | 0.8226 (HO-028) |
| ND-016 | heldout_v2 | 0.179 (HO2-007) | 0.462 (HO2-006) | 0.0 (HO2-001) | 0.818 (HO2-007) |
| ND-016 | relevance | 0.213 (REL-207) | 0.519 (REL-207) | 0.0 (REL-101) | 0.8192 (REL-203) |
| ND-016 | rbac | 0.219 (RBD-13) | 0.457 (RBD-02) | 0.0 (RBD-01) | 0.8339 (RBD-18) |
| ND-016 | false_refusal | 0.14 (FR-N05) | 0.436 (FR-N08) | 0.0 (FR-N01) | 0.8152 (FR-N02) |
| ND-016 | false_refusal_v2 | 0.159 (FR2-F04) | 0.541 (FR2-F04) | 0.0 (FR2-L01) | 0.832 (FR2-C06) |
| ND-016 | compound | 0.195 (CP1-P02) | 0.468 (CP1-P01) | 0.0 (CP1-P01) | 0.8139 (CP1-R01) |
| ND-017 | uat | 0.156 (Q087) | 0.478 (Q016) | 0.0 (Q001) | 0.8601 (Q026) |
| ND-017 | heldout_v1 | 0.172 (HO-025) | 0.478 (HO-003) | 0.0 (HO-001) | 0.873 (HO-023) |
| ND-017 | heldout_v2 | 0.11 (HO2-006) | 0.45 (HO2-016) | 0.0 (HO2-001) | 0.8359 (HO2-007) |
| ND-017 | relevance | 0.141 (REL-103) | 0.457 (REL-303) | 0.0 (REL-101) | 0.8244 (REL-204) |
| ND-017 | rbac | 0.125 (RBD-08) | 0.431 (RBD-09) | 0.0 (RBD-01) | 0.8253 (RBD-02) |
| ND-017 | false_refusal | 0.134 (FR-N06) | 0.456 (FR-A01) | 0.0 (FR-N01) | 0.8529 (FR-N09) |
| ND-017 | false_refusal_v2 | 0.111 (FR2-F05) | 0.475 (FR2-F04) | 0.0 (FR2-L01) | 0.8093 (FR2-C04) |
| ND-017 | compound | 0.137 (CP1-P02) | 0.413 (CP1-P02) | 0.0 (CP1-P01) | 0.8302 (CP1-R03) |
| ND-018 | uat | 0.219 (Q018) | 0.471 (Q092) | 0.0 (Q001) | 0.8771 (Q071) |
| ND-018 | heldout_v1 | 0.253 (HO-024) | 0.451 (HO-018) | 0.0 (HO-001) | 0.8865 (HO-018) |
| ND-018 | heldout_v2 | 0.293 (HO2-012) | 0.537 (HO2-001) | 0.0 (HO2-001) | 0.8864 (HO2-012) |
| ND-018 | relevance | 0.217 (REL-105) | 0.5 (REL-105) | 0.0 (REL-101) | 0.8388 (REL-207) |
| ND-018 | rbac | 0.22 (RBD-13) | 0.547 (RBD-14) | 0.0 (RBD-01) | 0.8519 (RBD-11) |
| ND-018 | false_refusal | 0.19 (FR-N03) | 0.475 (FR-N03) | 0.0 (FR-N01) | 0.8502 (FR-N03) |
| ND-018 | false_refusal_v2 | 0.178 (FR2-F05) | 0.481 (FR2-F01) | 0.0 (FR2-L01) | 0.8621 (FR2-F05) |
| ND-018 | compound | 0.211 (CP1-A03) | 0.46 (CP1-A02) | 0.0 (CP1-P01) | 0.8514 (CP1-A03) |
| ND-019 | uat | 0.297 (Q051) | 0.504 (Q046) | 0.0 (Q001) | 0.8826 (Q051) |
| ND-019 | heldout_v1 | 0.212 (HO-006) | 0.465 (HO-020) | 0.0 (HO-001) | 0.886 (HO-002) |
| ND-019 | heldout_v2 | 0.193 (HO2-014) | 0.462 (HO2-008) | 0.0 (HO2-001) | 0.8618 (HO2-003) |
| ND-019 | relevance | 0.227 (REL-103) | 0.455 (REL-103) | 0.0 (REL-101) | 0.8355 (REL-101) |
| ND-019 | rbac | 0.2 (RBD-16) | 0.486 (RBD-17) | 0.0 (RBD-01) | 0.8334 (RBD-01) |
| ND-019 | false_refusal | 0.247 (FR-N05) | 0.476 (FR-A01) | 0.0 (FR-N01) | 0.8684 (FR-A01) |
| ND-019 | false_refusal_v2 | 0.21 (FR2-L04) | 0.457 (FR2-L05) | 0.0 (FR2-L01) | 0.8382 (FR2-L01) |
| ND-019 | compound | 0.204 (CP1-A03) | 0.394 (CP1-R01) | 0.0 (CP1-P01) | 0.8199 (CP1-P02) |
| ND-020 | uat | 0.221 (Q038) | 0.463 (Q023) | 0.0 (Q001) | 0.8867 (Q038) |
| ND-020 | heldout_v1 | 0.223 (HO-002) | 0.409 (HO-039) | 0.024 (HO-031) | 0.8872 (HO-031) |
| ND-020 | heldout_v2 | 0.206 (HO2-002) | 0.397 (HO2-002) | 0.0 (HO2-001) | 0.8654 (HO2-002) |
| ND-020 | relevance | 0.146 (REL-201) | 0.37 (REL-403) | 0.0 (REL-101) | 0.8358 (REL-201) |
| ND-020 | rbac | 0.175 (RBD-01) | 0.435 (RBD-06) | 0.0 (RBD-01) | 0.8458 (RBD-05) |
| ND-020 | false_refusal | 0.246 (FR-N03) | 0.44 (FR-A10) | 0.0 (FR-N01) | 0.8708 (FR-N03) |
| ND-020 | false_refusal_v2 | 0.209 (FR2-C02) | 0.46 (FR2-F04) | 0.0 (FR2-L01) | 0.8401 (FR2-L01) |
| ND-020 | compound | 0.184 (CP1-P06) | 0.42 (CP1-R03) | 0.0 (CP1-P01) | 0.85 (CP1-P06) |
