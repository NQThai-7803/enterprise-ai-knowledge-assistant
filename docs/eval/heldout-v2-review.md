# Held-out v2, đợt 1: gold chờ duyệt

Trạng thái: **BẢN NHÁP, chờ chủ dự án duyệt.** Tạo bằng `scripts/eval/heldout_v2_check.py check` từ `docs/eval/heldout-v2-gold.yaml`; muốn sửa thì sửa YAML rồi chạy lại. Gold chỉ soạn từ PDF, không chạy hệ thống trên bộ này.

Câu hỏi đã đóng băng: SHA256 `dae7f8818a015d43a00d09fbeff9cc63f41c75d005e11f465e77617a0e86cd5a`. Gold chưa đóng băng; sẽ khóa sau khi duyệt.

Cách duyệt: với mỗi câu, đánh dấu **DUYỆT**, hoặc **SỬA** và ghi nội dung cần đổi.

## Kiểm tra

- Lỗi cấu trúc: không có
- Đoạn trích khớp đúng trang PDF: 47/47
- Câu trùng 4-gram trong `app/`: {'HO2-020': ['xu ly su co']}
- Câu cần bạn quyết định: HO2-001, HO2-003, HO2-004, HO2-005, HO2-012, HO2-016, HO2-018, HO2-020

## HO2-001: ANSWERED

**Câu hỏi:** Thời gian bắt đầu làm việc là bao nhiêu? Nghỉ trưa được mấy tiếng? Và mấy giờ tan làm?

**Ý bắt buộc:**
1. Bắt đầu làm việc: khung linh hoạt 08:00 - 09:00.
2. Nghỉ trưa: 60 phút (1 tiếng), thông thường 12:00 - 13:00.
3. Tan làm: khung 17:00 - 18:00, tương ứng giờ bắt đầu để đủ 08 giờ/ngày.

**Ý không bắt buộc:**
- ND-HR-002 Điều 5 ghi khung tham chiếu 08:30-17:30, nghỉ trưa 12:00-13:00, linh hoạt bắt đầu 08:00-09:30.
- Bộ phận trực hoặc 24/7 có lịch ca riêng.

**Citation:** ND-HR-003 tr. 4
**Citation chấp nhận thêm:** ND-HR-002 tr. 5

**Đoạn trích:**
- ND-HR-003 tr. 4 (khớp): "Tổng thời gian làm việc 08 giờ/ngày; 40 giờ/tuần Khung bắt đầu linh hoạt 08:00 - 09:00 Khung kết thúc tương ứng 17:00 - 18:00"
- ND-HR-003 tr. 4 (khớp): "Nghỉ trưa tiêu chuẩn 60 phút, thông thường từ 12:00 - 13:00"
- ND-HR-002 tr. 5 (khớp): "Khung giờ làm việc tham chiếu: 08:30-17:30; nghỉ trưa 12:00-13:00. Nhân viên linh hoạt có thể bắt đầu 08:00-09:30"

**CẦN BẠN QUYẾT ĐỊNH:** Hai tài liệu khác nhau về giờ bắt đầu và kết thúc. Đề xuất: gold theo ND-HR-003 vì là chính sách chuyên đề và áp dụng muộn hơn (01/09/2026 so với 01/08/2026); câu trả lời nêu số của ND-HR-002 và trích ND-HR-002 vẫn đạt.

**Ghi chú:** Câu ghép 3 ý, mỗi ý một mục bắt buộc.

- [ ] DUYỆT
- [ ] SỬA:

## HO2-002: ANSWERED

**Câu hỏi:** Có cần phải tăng ca không và tăng ca thì phải báo với ai để duyệt?

**Ý bắt buộc:**
1. Không mặc nhiên phải tăng ca: làm thêm giờ chỉ thực hiện khi có nhu cầu công việc, sự đồng ý của người lao động và phê duyệt theo quy trình, trừ trường hợp pháp luật quy định khác.
2. Người duyệt: quản lý trực tiếp.

**Ý không bắt buộc:**
- Tình huống sự cố khẩn cấp được ghi nhận hồi tố theo quy trình incident.
- Nhân viên ghi nhận thời điểm bắt đầu/kết thúc và mã ticket/dự án hoặc lý do trên hệ thống.

**Citation:** ND-HR-002 tr. 5; ND-HR-003 tr. 10
**Citation chấp nhận thêm:** ND-HR-003 tr. 8; ND-HR-005 tr. 7

**Đoạn trích:**
- ND-HR-002 tr. 5 (khớp): "Làm thêm giờ chỉ thực hiện khi có nhu cầu công việc, sự đồng ý của người lao động và phê duyệt theo quy trình, trừ trường hợp pháp luật quy định khác."
- ND-HR-003 tr. 10 (khớp): "Quản lý trực tiếp Duyệt lịch, ngoại lệ, làm thêm"
- ND-HR-003 tr. 8 (khớp): "Làm thêm giờ chỉ được ghi nhận khi có yêu cầu công việc thực tế và được phê duyệt theo thẩm quyền, trừ tình huống khẩn cấp thuộc trường hợp pháp luật cho phép."

**Ghi chú:** Câu ghép 2 ý. ND-HR-003 trang 8 chỉ nói 'theo thẩm quyền'; tên vai trò nằm ở trang 10.

- [ ] DUYỆT
- [ ] SỬA:

## HO2-003: ANSWERED

**Câu hỏi:** Tiền OT sẽ tính như nào nếu tôi làm sau giờ làm hành chính?

**Ý bắt buộc:**
1. Làm thêm vào ngày làm việc bình thường được trả ít nhất 150% đơn giá/tiền lương giờ thực trả của công việc đang làm.

**Ý không bắt buộc:**
- Làm việc ban đêm được trả thêm ít nhất 30%; làm thêm vào ban đêm còn trả thêm ít nhất 20%.
- Ngày nghỉ hằng tuần ít nhất 200%; ngày lễ, Tết ít nhất 300%.
- OT phải được yêu cầu/phê duyệt; thời gian tự nguyện làm thêm không có phê duyệt có thể không được ghi nhận.

**Citation:** ND-HR-005 tr. 7

**Đoạn trích:**
- ND-HR-005 tr. 7 (khớp): "Làm thêm ngày làm việc bình thường Ít nhất 150% đơn giá/tiền lương giờ thực trả của công việc đang làm."
- ND-HR-005 tr. 7 (khớp): "Làm thêm vào ban đêm Ngoài tiền OT và khoản 30% ban đêm, còn trả thêm ít nhất 20% theo cơ sở pháp luật áp dụng."
- ND-HR-005 tr. 7 (khớp): "OT phải được yêu cầu/phê duyệt theo ND-HR-003"

**CẦN BẠN QUYẾT ĐỊNH:** Đề xuất chỉ bắt buộc mức 150%, vì câu hỏi nói 'sau giờ hành chính' mà không nói ban đêm hay điều kiện duyệt. Nếu muốn, có thể nâng điều kiện phê duyệt thành ý bắt buộc.

- [ ] DUYỆT
- [ ] SỬA:

## HO2-004: ANSWERED

**Câu hỏi:** Quy trình đăng ký nghỉ có phép?

**Ý bắt buộc:**
1. Nhân viên tạo yêu cầu trên HRM.
2. Quản lý trực tiếp rà soát kế hoạch nguồn lực.
3. HR kiểm tra số dư/hồ sơ đối với trường hợp cần kiểm soát, rồi hệ thống ghi trạng thái cuối cùng.
4. Thời hạn đề nghị phép năm: 1-2 ngày trước ít nhất 02 ngày làm việc; 3-5 ngày trước ít nhất 05 ngày làm việc; trên 5 ngày trước ít nhất 10 ngày làm việc.

**Ý không bắt buộc:**
- Chỉ rời lịch làm việc sau khi yêu cầu ở trạng thái Approved, trừ tình huống khẩn cấp đã thông báo cho quản lý.
- Bàn giao trước kỳ nghỉ: cập nhật ticket/dự án, đầu mối thay thế, thiết lập trạng thái vắng mặt.

**Citation:** ND-HR-004 tr. 9
**Citation chấp nhận thêm:** ND-HR-004 tr. 6; UAT-LEAVE-AUTHORITY-001 tr. 5

**Đoạn trích:**
- ND-HR-004 tr. 9 (khớp): "Nhân viên tạo yêu cầu trên HRM -> quản lý trực tiếp rà soát kế hoạch nguồn lực -> HR kiểm tra số dư/hồ sơ đối với trường hợp cần kiểm soát -> hệ thống ghi trạng thái cuối cùng."
- ND-HR-004 tr. 9 (khớp): "Phép năm 1-2 ngày Trước ít nhất 02 ngày làm việc Phép năm 3-5 ngày Trước ít nhất 05 ngày làm việc Phép năm trên 5 ngày Trước ít nhất 10 ngày làm việc"
- ND-HR-004 tr. 6 (khớp): "Người lao động chỉ rời lịch làm việc sau khi yêu cầu ở trạng thái Approved, trừ tình huống khẩn cấp đã thông báo cho quản lý."
- UAT-LEAVE-AUTHORITY-001 tr. 4 (khớp): "Người lao động nên đăng ký nghỉ phép năm trước ít nhất 03 ngày làm việc; nghỉ từ 05 ngày liên tục nên đăng ký trước ít nhất 10 ngày làm việc"

**CẦN BẠN QUYẾT ĐỊNH:** UAT-LEAVE-AUTHORITY-001 trang 4 ghi thời hạn khác (ít nhất 03 ngày; từ 05 ngày liên tục ít nhất 10 ngày). Đây là tài liệu mẫu ghi 'CHƯA PHẢI VĂN BẢN BAN HÀNH' với [TÊN DOANH NGHIỆP]. Đề xuất: gold theo ND-HR-004; câu chỉ nêu thời hạn của tài liệu mẫu không đạt ý 4. 'Nghỉ có phép' được hiểu là phép năm.

- [ ] DUYỆT
- [ ] SỬA:

## HO2-005: ANSWERED_LIMITED

**Câu hỏi:** Phụ nữ mang thai thì được nghỉ 3 tháng có phép phải không?

**Ý bắt buộc:**
1. Đính chính: không xác nhận được. Tài liệu không có quy định phụ nữ mang thai được nghỉ 3 tháng.
2. Thai sản không phải nghỉ phép: đây là chế độ nghỉ theo BHXH; quyền lợi và thời gian nghỉ khi sinh con thực hiện theo pháp luật hiện hành.

**Tài liệu không nêu:**
- Số tháng nghỉ thai sản.

**Ý không bắt buộc:**
- HR hỗ trợ xác định hồ sơ, thời điểm nghỉ, quyền lợi BHXH và kế hoạch bàn giao.
- Khám thai/chăm sóc thai kỳ: đăng ký loại nghỉ tương ứng.
- Quản lý không được tự ý chuyển nghỉ thai sản thành nghỉ phép năm nếu người lao động đủ điều kiện hưởng chế độ khác.

**Citation:** ND-HR-004 tr. 3, 8
**Citation chấp nhận thêm:** UAT-LEAVE-AUTHORITY-001 tr. 4

**Đoạn trích:**
- ND-HR-004 tr. 3 (khớp): "Nghỉ theo chế độ BHXH Ốm đau, chăm con ốm, thai sản và các trường hợp khác theo pháp luật BHXH."
- ND-HR-004 tr. 8 (khớp): "Sinh con Lập kế hoạch bàn giao trước khi nghỉ nếu điều kiện cho phép; quyền lợi và thời gian nghỉ thực hiện theo pháp luật hiện hành."
- ND-HR-004 tr. 8 (khớp): "Các chế độ thai sản thực hiện theo Luật Bảo hiểm xã hội 2024, Bộ luật Lao động và văn bản hướng dẫn có hiệu lực tại thời điểm phát sinh."

**Điều kiện đạt:** Đạt khi câu trả lời (a) không xác nhận 3 tháng, (b) nói thai sản theo BHXH và pháp luật chứ không phải nghỉ phép, (c) không thêm số tháng nào từ ngoài tài liệu.

**Ví dụ không đạt:**
- Đúng, được nghỉ 3 tháng có phép.
- Không, được nghỉ 6 tháng.

**Từ khóa phải vắng, số lần gặp trong tài liệu:** '3 tháng': 1, '6 tháng': 1

**CẦN BẠN QUYẾT ĐỊNH:** Tiền đề sai theo yêu cầu của bạn, nhưng PDF không nêu số tháng đúng. Con số 6 tháng là kiến thức ngoài PDF, nên đề xuất tính là KHÔNG ĐẠT nếu câu trả lời nêu số đó. Hai kết quả tìm thấy không liên quan: '3. Thăng chức' (ND-HR-005 trang 8) và 'không quá 06 tháng' về kỷ luật (ND-HR-002 trang 12).

**Ghi chú:** Câu tiền đề sai.

- [ ] DUYỆT
- [ ] SỬA:

## HO2-006: ANSWERED

**Câu hỏi:** Lương của Middle Developer thì sẽ khoảng bao nhiêu?

**Ý bắt buộc:**
1. Dải Base Salary tham khảo của Middle Developer (grade N3) là 18 - 32 triệu đồng gross/tháng.

**Ý không bắt buộc:**
- Đây là dữ liệu giả định; hai người cùng grade có thể khác lương, và mức trần của dải không phải mức tăng tự động.

**Citation:** ND-HR-005 tr. 4
**Citation chấp nhận thêm:** ND-HR-005 tr. 13

**Đoạn trích:**
- ND-HR-005 tr. 4 (khớp): "Grade Ví dụ chức danh Dải Base Salary tham khảo (gross/tháng)"
- ND-HR-005 tr. 4 (khớp): "N3 Middle Developer / BA / Data Analyst 18 - 32 triệu đồng"

- [ ] DUYỆT
- [ ] SỬA:

## HO2-007: ANSWERED

**Câu hỏi:** Tiền thưởng hằng năm như nào?

**Ý bắt buộc:**
1. Thưởng hiệu suất năm theo xếp hạng, tính bằng tháng Base Salary: Exceptional 1,5 - 2,0; Exceeds Expectations 1,0 - 1,5; Meets Expectations 0,5 - 1,0; Partially Meets 0 - 0,5; Does Not Meet 0.
2. Không phải khoản lương cố định; phụ thuộc kết quả công ty và phê duyệt ngân sách.

**Ý không bắt buộc:**
- Khoản thưởng có thể phụ thuộc thời gian làm việc đủ điều kiện, kỷ luật đang có hiệu lực hoặc tiêu chí chương trình.
- Các chương trình thưởng khác: Project Delivery, Innovation, Employee Referral, Spot Award.

**Citation:** ND-HR-005 tr. 9

**Đoạn trích:**
- ND-HR-005 tr. 9 (khớp): "Exceptional 1,5 - 2,0 tháng Base Salary Phụ thuộc kết quả công ty và phê duyệt ngân sách."
- ND-HR-005 tr. 9 (khớp): "Exceeds Expectations 1,0 - 1,5 tháng Base Salary"
- ND-HR-005 tr. 9 (khớp): "Meets Expectations 0,5 - 1,0 tháng Base Salary Không phải khoản lương cố định."
- ND-HR-005 tr. 9 (khớp): "Partially Meets 0 - 0,5 tháng Base Salary"
- ND-HR-005 tr. 9 (khớp): "Does Not Meet 0 Trừ trường hợp có quyết định đặc biệt khác."

**Ghi chú:** Mỗi xếp hạng phải đúng hệ số.

- [ ] DUYỆT
- [ ] SỬA:

## HO2-008: ANSWERED

**Câu hỏi:** Ngày nào là ngày trả lương cho nhân viên?

**Ý bắt buộc:**
1. Ngày 10 của tháng kế tiếp.

**Ý không bắt buộc:**
- Nếu trùng ngày nghỉ/lễ, Finance thực hiện vào ngày làm việc liền trước hoặc theo phương án hợp pháp thuận lợi cho người lao động.

**Citation:** ND-HR-005 tr. 5

**Đoạn trích:**
- ND-HR-005 tr. 5 (khớp): "Ngày trả lương Ngày 10 của tháng kế tiếp; nếu trùng ngày nghỉ/lễ, Finance thực hiện vào ngày làm việc liền trước hoặc theo phương án hợp pháp thuận lợi cho người lao động."

- [ ] DUYỆT
- [ ] SỬA:

## HO2-009: ANSWERED

**Câu hỏi:** Công ty có phạt tiền nếu làm sai hay không?

**Ý bắt buộc:**
1. Không: Nova Digital không sử dụng phạt tiền hoặc cắt lương thay cho xử lý kỷ luật lao động.
2. Vi phạm được xử lý theo ND-HR-002 và ND-HR-010; thiệt hại vật chất, nếu có, được xác định riêng theo căn cứ pháp luật.

**Ý không bắt buộc:**
- Các hình thức kỷ luật: khiển trách, kéo dài thời hạn nâng lương không quá 06 tháng, cách chức, sa thải.
- Khấu trừ để bồi thường không vượt 30% tiền lương tháng sau khi trích nộp bảo hiểm bắt buộc và thuế.

**Citation:** ND-HR-005 tr. 10; ND-HR-002 tr. 12
**Citation chấp nhận thêm:** ND-HR-003 tr. 9; UAT-LEAVE-AUTHORITY-001 tr. 6

**Đoạn trích:**
- ND-HR-005 tr. 10 (khớp): "Nova Digital không sử dụng phạt tiền hoặc cắt lương thay cho xử lý kỷ luật lao động. Các hành vi vi phạm được xử lý theo ND-HR-002 và ND-HR-010, còn thiệt hại vật chất (nếu có) phải xác định riêng theo đúng căn cứ pháp luật."
- ND-HR-002 tr. 12 (khớp): "Phạt tiền hoặc cắt lương thay cho xử lý kỷ luật lao động."

- [ ] DUYỆT
- [ ] SỬA:

## HO2-010: NO_ANSWER

**Câu hỏi:** Thử việc sẽ bao lâu và có lương hay không?

**Ý bắt buộc:**
- Không có; tài liệu không trả lời được.

**Tài liệu không nêu:**
- Thời gian thử việc.
- Lương thử việc.

**Ý không bắt buộc:**
- Nhân viên thử việc: quyền lợi bảo hiểm theo loại hợp đồng và pháp luật; một số phúc lợi nội bộ có thể áp dụng từ ngày nhận việc.

**Citation:** không có
**Citation chấp nhận thêm:** ND-HR-006 tr. 3

**Đoạn trích:**
- ND-HR-006 tr. 3 (khớp): "Nhân viên thử việc Quyền lợi bảo hiểm thực hiện theo loại hợp đồng và quy định pháp luật; một số phúc lợi nội bộ có thể áp dụng từ ngày nhận việc."

**Trạng thái chấp nhận thêm:** ANSWERED_LIMITED

**Điều kiện đạt:** Đạt khi nói tài liệu không nêu thời gian và lương thử việc, không thêm số từ ngoài tài liệu, và nếu trích dẫn thì trích đoạn liên quan.

**Ví dụ không đạt:**
- Thử việc 2 tháng, hưởng 85% lương.

**Từ khóa phải vắng, số lần gặp trong tài liệu:** '85%': 0, 'thử việc 2 tháng': 0, '60 ngày': 0, 'lương thử việc': 0, 'thời gian thử việc': 0

**Ghi chú:** Câu ghép 2 ý, cả 2 đều không có trong tài liệu.

- [ ] DUYỆT
- [ ] SỬA:

## HO2-011: ANSWERED

**Câu hỏi:** Có lịch khám sức khỏe định kỳ hay không?

**Ý bắt buộc:**
1. Có: khám sức khỏe năm 01 lần/năm cho nhân viên chính thức.
2. Lịch tổ chức theo đợt hoặc voucher đối tác.

**Ý không bắt buộc:**
- Ngày Wellness Check: tối đa 04 giờ/năm để tham gia đợt khám do công ty tổ chức, không trừ phép nếu đúng lịch.
- Khám chuyên sâu theo nguy cơ khi vị trí/công việc có yêu cầu.

**Citation:** ND-HR-006 tr. 8
**Citation chấp nhận thêm:** ND-HR-006 tr. 10

**Đoạn trích:**
- ND-HR-006 tr. 8 (khớp): "Khám sức khỏe năm 01 lần/năm cho nhân viên chính thức; lịch tổ chức theo đợt hoặc voucher đối tác."
- ND-HR-006 tr. 8 (khớp): "Ngày Wellness Check Tối đa 04 giờ/năm để tham gia đợt khám do công ty tổ chức, không trừ phép nếu đúng lịch."

**Ghi chú:** Tài liệu không nêu ngày khám cụ thể.

- [ ] DUYỆT
- [ ] SỬA:

## HO2-012: ANSWERED_LIMITED

**Câu hỏi:** Làm việc remote được tối đa mấy ngày trong tháng?

**Ý bắt buộc:**
1. Tài liệu quy định theo tuần: tối đa 02 ngày/tuần, tùy vị trí và phê duyệt của quản lý.

**Tài liệu không nêu:**
- Hạn mức remote theo tháng.

**Ý không bắt buộc:**
- Đăng ký lịch trước 16:00 của ngày làm việc liền trước hoặc theo lịch cố định của bộ phận.

**Citation:** ND-HR-003 tr. 7
**Citation chấp nhận thêm:** ND-HR-003 tr. 11

**Đoạn trích:**
- ND-HR-003 tr. 7 (khớp): "Số ngày remote thông thường Tối đa 02 ngày/tuần, tùy vị trí và phê duyệt của quản lý"

**Điều kiện đạt:** Đạt khi nêu 02 ngày/tuần và cho biết tài liệu quy định theo tuần, không theo tháng.

**Ví dụ không đạt:**
- Tối đa 8 ngày mỗi tháng.
- Tài liệu không có thông tin về remote.

**CẦN BẠN QUYẾT ĐỊNH:** Câu hỏi hỏi theo tháng, tài liệu quy định theo tuần. Đề xuất: câu chỉ nêu số ngày/tháng như một quy định là không đạt. Câu nêu 02 ngày/tuần rồi ước tính khoảng 8 ngày/tháng và ghi rõ là ước tính thì đạt.

**Ghi chú:** Lệch đơn vị giữa câu hỏi và tài liệu.

- [ ] DUYỆT
- [ ] SỬA:

## HO2-013: ANSWERED

**Câu hỏi:** Ai là giám đốc bộ phận Nhân sự?

**Ý bắt buộc:**
1. Giám đốc Nhân sự (CHRO) là Trương Thanh An.

**Ý không bắt buộc:**
- Phụ trách con người, văn hóa, tổ chức và hành chính.

**Citation:** ND-CORP-001 tr. 6

**Đoạn trích:**
- ND-CORP-001 tr. 6 (khớp): "Giám đốc Nhân sự (CHRO) Trương Thanh An - phụ trách con người, văn hóa, tổ chức và hành chính"

- [ ] DUYỆT
- [ ] SỬA:

## HO2-014: ANSWERED

**Câu hỏi:** Nếu tôi cần hỗ trợ CNTT thì liên hệ email nào?

**Ý bắt buộc:**
1. servicedesk@novadigital.example

**Citation:** ND-CORP-001 tr. 9
**Citation chấp nhận thêm:** ND-HR-002 tr. 15

**Đoạn trích:**
- ND-CORP-001 tr. 9 (khớp): "Hỗ trợ CNTT và tài khoản servicedesk@novadigital.example"
- ND-HR-002 tr. 15 (khớp): "Service Desk servicedesk@novadigital.example"

- [ ] DUYỆT
- [ ] SỬA:

## HO2-015: ANSWERED

**Câu hỏi:** NovaSecure là gì?

**Ý bắt buộc:**
1. NovaSecure là bộ công cụ an toàn thông tin trong danh mục sản phẩm của Nova Digital.
2. Chức năng: quản lý cấu hình, giám sát sự kiện, đánh giá rủi ro và hỗ trợ ứng phó sự cố.

**Citation:** ND-CORP-001 tr. 5

**Đoạn trích:**
- ND-CORP-001 tr. 5 (khớp): "NovaSecure Bộ công cụ an toàn thông tin Quản lý cấu hình, giám sát sự kiện, đánh giá rủi ro và hỗ trợ ứng phó sự cố."

**Ghi chú:** Câu chỉ có 3 từ; bộ lọc 4-gram được mở rộng để vẫn nhận ra câu ngắn.

- [ ] DUYỆT
- [ ] SỬA:

## HO2-016: ANSWERED_LIMITED

**Câu hỏi:** Địa chỉ trụ sở chính ở đâu? Tôi nên liên lạc với ai khi tới phỏng vấn?

**Ý bắt buộc:**
1. Trụ sở chính: Tầng 8, Tòa nhà Nova Hub, Khu Công nghệ Phần mềm, Thành phố Hồ Chí Minh.

**Tài liệu không nêu:**
- Người liên hệ khi tới phỏng vấn.

**Ý không bắt buộc:**
- Phòng Nhân sự & Hành chính phụ trách tuyển dụng; đầu mối nhân sự people@novadigital.example.

**Citation:** ND-CORP-001 tr. 3
**Citation chấp nhận thêm:** ND-CORP-001 tr. 8, 9

**Đoạn trích:**
- ND-CORP-001 tr. 3 (khớp): "Trụ sở chính Tầng 8, Tòa nhà Nova Hub, Khu Công nghệ Phần mềm, Thành phố Hồ Chí Minh"
- ND-CORP-001 tr. 8 (khớp): "Hoạch định nguồn lực, tuyển dụng, tiếp nhận, đánh giá hiệu suất, đào tạo và phát triển tổ chức."
- ND-CORP-001 tr. 9 (khớp): "Nhân sự và chính sách lao động people@novadigital.example"

**Điều kiện đạt:** Đạt khi nêu đúng địa chỉ, cho biết tài liệu không nêu người liên hệ khi phỏng vấn, và không tạo tên hoặc số điện thoại.

**Ví dụ không đạt:**
- Liên hệ chị Trương Thanh An khi tới phỏng vấn.
- Gọi hotline 028 7300 2026 khi tới phỏng vấn.

**Từ khóa phải vắng, số lần gặp trong tài liệu:** 'phỏng vấn': 1

**CẦN BẠN QUYẾT ĐỊNH:** Đề xuất: gợi ý Phòng Nhân sự hoặc people@ vẫn đạt nếu nói rõ tài liệu không quy định riêng. Từ 'phỏng vấn' chỉ xuất hiện ở ND-HR-006 trang 6, về tư vấn CV khi tái cấu trúc, không liên quan.

**Ghi chú:** Câu ghép 2 ý: ý đầu có đáp án, ý sau không.

- [ ] DUYỆT
- [ ] SỬA:

## HO2-017: ANSWERED

**Câu hỏi:** Tổng ngày nghỉ lễ, Tết trong năm?

**Ý bắt buộc:**
1. 11 ngày.

**Ý không bắt buộc:**
- Tết Dương lịch 01; Tết Âm lịch 05; 30/4 01; 01/5 01; Quốc khánh 02; Giỗ Tổ Hùng Vương 01.
- Người lao động nước ngoài được nghỉ thêm ngày Tết cổ truyền và Quốc khánh của nước họ.

**Citation:** ND-HR-004 tr. 5
**Citation chấp nhận thêm:** UAT-LEAVE-AUTHORITY-001 tr. 3

**Đoạn trích:**
- ND-HR-004 tr. 5 (khớp): "Tết Dương lịch 01 ngày Tết Âm lịch 05 ngày Ngày Chiến thắng 30/4 01 ngày Ngày Quốc tế Lao động 01/5 01 ngày Quốc khánh 02 ngày Giỗ Tổ Hùng Vương 01 ngày"
- UAT-LEAVE-AUTHORITY-001 tr. 3 (khớp): "Tổng số ngày nghỉ lễ, Tết theo lịch quốc gia là 11 ngày trong năm."

**Ghi chú:** Chỉ tài liệu mẫu UAT-LEAVE-AUTHORITY-001 ghi tổng 11; ND-HR-004 chỉ có bảng, phải cộng lại. Trích một trong hai đều đạt.

- [ ] DUYỆT
- [ ] SỬA:

## HO2-018: ANSWERED

**Câu hỏi:** Bao lâu thì review lương / lần?

**Ý bắt buộc:**
1. Mỗi năm một lần, theo chu kỳ salary review: đánh giá hiệu suất năm tháng 01-02, thông báo điều chỉnh trong tháng 04, ngày hiệu lực thông thường 01/05.

**Ý không bắt buộc:**
- Tham gia salary review không tạo quyền đương nhiên được tăng lương.

**Citation:** ND-HR-005 tr. 8
**Citation chấp nhận thêm:** ND-HR-005 tr. 13

**Đoạn trích:**
- ND-HR-005 tr. 8 (khớp): "Đánh giá hiệu suất năm Tháng 01 - 02 Hiệu chỉnh/Calibration Tháng 03 Phê duyệt ngân sách tăng lương Tháng 03 - 04 Thông báo điều chỉnh Trong tháng 04 Ngày hiệu lực thông thường 01/05"
- ND-HR-005 tr. 8 (khớp): "Việc tham gia salary review không tạo quyền đương nhiên được tăng lương."

**CẦN BẠN QUYẾT ĐỊNH:** Tài liệu không viết nguyên văn '1 lần/năm'. 'Mỗi năm một lần' suy ra từ 'đánh giá hiệu suất năm' và các mốc theo tháng. Đề xuất chấp nhận suy luận này; nếu không, câu này chuyển thành ANSWERED_LIMITED.

- [ ] DUYỆT
- [ ] SỬA:

## HO2-019: ANSWERED

**Câu hỏi:** Làm bao lâu thì phép năm tăng lên và tăng như thế nào?

**Ý bắt buộc:**
1. Cứ đủ 05 năm làm việc cho Nova Digital.
2. Tăng thêm 01 ngày nghỉ hằng năm.

**Ý không bắt buộc:**
- Mức cơ bản 12 ngày làm việc/năm với công việc trong điều kiện bình thường.

**Citation:** ND-HR-004 tr. 4
**Citation chấp nhận thêm:** UAT-LEAVE-AUTHORITY-001 tr. 3

**Đoạn trích:**
- ND-HR-004 tr. 4 (khớp): "Thâm niên Cứ đủ 05 năm làm việc cho Nova Digital, tăng thêm 01 ngày nghỉ hằng năm theo quy định pháp luật."
- ND-HR-004 tr. 4 (khớp): "Công việc trong điều kiện bình thường 12 ngày làm việc/năm khi đủ 12 tháng làm việc."

**Ghi chú:** Câu ghép 2 ý.

- [ ] DUYỆT
- [ ] SỬA:

## HO2-020: ANSWERED

**Câu hỏi:** Nhân viên đang nghỉ phép có bắt buộc phải xử lý sự cố production không?

**Ý bắt buộc:**
1. Không mặc nhiên bắt buộc: quản lý kích hoạt người thay thế trước; chỉ liên hệ nhân viên đang nghỉ khi không còn phương án hợp lý và có sự đồng ý.
2. Ngoại lệ: on-call đã phân lịch thì áp dụng lịch trực đã công bố; khẩn cấp an ninh/an toàn có thể yêu cầu phối hợp theo quy trình ứng phó sự cố.

**Ý không bắt buộc:**
- Ghi nhận thời gian thực tế xử lý và chế độ liên quan; sau sự cố xem xét thời gian nghỉ phục hồi.

**Citation:** ND-HR-004 tr. 10
**Citation chấp nhận thêm:** ND-HR-004 tr. 12

**Đoạn trích:**
- ND-HR-004 tr. 10 (khớp): "Nhân viên đang nghỉ phép nhưng là đầu mối duy nhất Quản lý kích hoạt người thay thế trước; chỉ liên hệ nhân viên nghỉ khi không còn phương án hợp lý và có sự đồng ý."
- ND-HR-004 tr. 10 (khớp): "On-call đã được phân lịch Áp dụng lịch trực đã công bố, ghi nhận thời gian thực tế xử lý và chế độ liên quan."
- ND-HR-004 tr. 10 (khớp): "Khẩn cấp an ninh / an toàn Có thể yêu cầu phối hợp theo quy trình ứng phó sự cố"
- ND-HR-004 tr. 12 (khớp): "Nhân viên đang nghỉ phép có bắt buộc phải xử lý sự cố production không?"

**CẦN BẠN QUYẾT ĐỊNH:** Câu này trùng nguyên văn câu hỏi gợi ý in trong chính tài liệu (ND-HR-004 trang 12). Bạn cân nhắc giữ hay bỏ, vì retrieval có thể khớp thẳng vào câu đó.

- [ ] DUYỆT
- [ ] SỬA:

## Kiểm trùng, chỉ báo số liệu

Số lớn nhất của mỗi câu so với từng bộ, kèm câu gần nhất. Không loại câu nào theo số này.

- uat: bề mặt từ 0,60 trở lên: HO2-006, HO2-009, HO2-012, HO2-015, HO2-018, HO2-020; e5 từ 0,90 trở lên: HO2-001, HO2-003, HO2-006, HO2-008, HO2-012, HO2-015, HO2-018, HO2-019, HO2-020
- heldout_v1: bề mặt từ 0,60 trở lên: không có; e5 từ 0,90 trở lên: HO2-017
- relevance: bề mặt từ 0,60 trở lên: HO2-008; e5 từ 0,90 trở lên: không có
- rbac: bề mặt từ 0,60 trở lên: không có; e5 từ 0,90 trở lên: không có

| id | bộ | 3-gram ký tự | difflib | 4-gram từ | e5 cosine |
|---|---|---:|---:|---:|---:|
| HO2-001 | uat | 0.311 (Q062) | 0.455 (Q016) | 0.0 (Q001) | 0.9323 (Q022) |
| HO2-001 | heldout_v1 | 0.311 (HO-034) | 0.514 (HO-020) | 0.0 (HO-001) | 0.8774 (HO-018) |
| HO2-001 | relevance | 0.297 (REL-206) | 0.527 (REL-206) | 0.0 (REL-101) | 0.8556 (REL-206) |
| HO2-001 | rbac | 0.228 (RBD-13) | 0.403 (RBD-16) | 0.0 (RBD-01) | 0.8248 (RBD-05) |
| HO2-002 | uat | 0.254 (Q095) | 0.571 (Q095) | 0.0 (Q001) | 0.8675 (Q024) |
| HO2-002 | heldout_v1 | 0.282 (HO-007) | 0.51 (HO-039) | 0.0 (HO-001) | 0.8604 (HO-010) |
| HO2-002 | relevance | 0.253 (REL-201) | 0.511 (REL-204) | 0.0 (REL-101) | 0.8446 (REL-302) |
| HO2-002 | rbac | 0.244 (RBD-05) | 0.432 (RBD-08) | 0.0 (RBD-01) | 0.8439 (RBD-05) |
| HO2-003 | uat | 0.197 (Q066) | 0.465 (Q051) | 0.0 (Q001) | 0.9072 (Q068) |
| HO2-003 | heldout_v1 | 0.219 (HO-026) | 0.459 (HO-029) | 0.0 (HO-001) | 0.8668 (HO-033) |
| HO2-003 | relevance | 0.192 (REL-207) | 0.455 (REL-101) | 0.0 (REL-101) | 0.8415 (REL-207) |
| HO2-003 | rbac | 0.124 (RBD-08) | 0.412 (RBD-14) | 0.0 (RBD-01) | 0.8376 (RBD-05) |
| HO2-004 | uat | 0.217 (Q041) | 0.453 (Q055) | 0.0 (Q001) | 0.8976 (Q048) |
| HO2-004 | heldout_v1 | 0.139 (HO-008) | 0.414 (HO-024) | 0.0 (HO-001) | 0.8834 (HO-006) |
| HO2-004 | relevance | 0.108 (REL-105) | 0.479 (REL-305) | 0.0 (REL-101) | 0.8359 (REL-206) |
| HO2-004 | rbac | 0.141 (RBD-13) | 0.432 (RBD-14) | 0.0 (RBD-01) | 0.8266 (RBD-01) |
| HO2-005 | uat | 0.272 (Q052) | 0.54 (Q045) | 0.0 (Q001) | 0.8881 (Q045) |
| HO2-005 | heldout_v1 | 0.19 (HO-021) | 0.481 (HO-026) | 0.0 (HO-001) | 0.8841 (HO-034) |
| HO2-005 | relevance | 0.247 (REL-101) | 0.495 (REL-106) | 0.0 (REL-101) | 0.8465 (REL-206) |
| HO2-005 | rbac | 0.179 (RBD-15) | 0.46 (RBD-17) | 0.0 (RBD-01) | 0.82 (RBD-01) |
| HO2-006 | uat | 0.615 (Q058) | 0.795 (Q058) | 0.0 (Q001) | 0.9656 (Q058) |
| HO2-006 | heldout_v1 | 0.179 (HO-031) | 0.46 (HO-014) | 0.0 (HO-001) | 0.8448 (HO-005) |
| HO2-006 | relevance | 0.189 (REL-201) | 0.46 (REL-402) | 0.0 (REL-101) | 0.8327 (REL-207) |
| HO2-006 | rbac | 0.202 (RBD-08) | 0.409 (RBD-18) | 0.0 (RBD-01) | 0.823 (RBD-02) |
| HO2-007 | uat | 0.254 (Q039) | 0.571 (Q065) | 0.0 (Q001) | 0.8692 (Q039) |
| HO2-007 | heldout_v1 | 0.24 (HO-040) | 0.492 (HO-040) | 0.0 (HO-001) | 0.8646 (HO-029) |
| HO2-007 | relevance | 0.196 (REL-402) | 0.493 (REL-203) | 0.0 (REL-101) | 0.8499 (REL-207) |
| HO2-007 | rbac | 0.2 (RBD-14) | 0.519 (RBD-12) | 0.0 (RBD-01) | 0.8371 (RBD-13) |
| HO2-008 | uat | 0.298 (Q054) | 0.518 (Q055) | 0.0 (Q001) | 0.9471 (Q054) |
| HO2-008 | heldout_v1 | 0.309 (HO-040) | 0.509 (HO-032) | 0.0 (HO-001) | 0.8746 (HO-018) |
| HO2-008 | relevance | 0.2 (REL-303) | 0.625 (REL-303) | 0.0 (REL-101) | 0.826 (REL-201) |
| HO2-008 | rbac | 0.215 (RBD-11) | 0.571 (RBD-14) | 0.0 (RBD-01) | 0.8383 (RBD-11) |
| HO2-009 | uat | 0.309 (Q063) | 0.701 (Q063) | 0.0 (Q001) | 0.8643 (Q087) |
| HO2-009 | heldout_v1 | 0.217 (HO-032) | 0.504 (HO-012) | 0.0 (HO-001) | 0.8609 (HO-031) |
| HO2-009 | relevance | 0.2 (REL-103) | 0.482 (REL-305) | 0.0 (REL-101) | 0.842 (REL-201) |
| HO2-009 | rbac | 0.167 (RBD-05) | 0.494 (RBD-18) | 0.0 (RBD-01) | 0.8613 (RBD-18) |
| HO2-010 | uat | 0.25 (Q047) | 0.516 (Q070) | 0.0 (Q001) | 0.8986 (Q054) |
| HO2-010 | heldout_v1 | 0.183 (HO-004) | 0.473 (HO-038) | 0.0 (HO-001) | 0.8706 (HO-018) |
| HO2-010 | relevance | 0.156 (REL-105) | 0.488 (REL-305) | 0.0 (REL-101) | 0.8442 (REL-201) |
| HO2-010 | rbac | 0.184 (RBD-15) | 0.505 (RBD-01) | 0.0 (RBD-01) | 0.847 (RBD-05) |
| HO2-011 | uat | 0.171 (Q030) | 0.474 (Q089) | 0.0 (Q001) | 0.8747 (Q079) |
| HO2-011 | heldout_v1 | 0.181 (HO-022) | 0.436 (HO-019) | 0.0 (HO-001) | 0.8665 (HO-038) |
| HO2-011 | relevance | 0.165 (REL-201) | 0.527 (REL-101) | 0.0 (REL-101) | 0.8371 (REL-205) |
| HO2-011 | rbac | 0.132 (RBD-03) | 0.484 (RBD-06) | 0.0 (RBD-01) | 0.8364 (RBD-11) |
| HO2-012 | uat | 0.441 (Q027) | 0.75 (Q027) | 0.3 (Q027) | 0.9534 (Q027) |
| HO2-012 | heldout_v1 | 0.247 (HO-019) | 0.479 (HO-038) | 0.0 (HO-001) | 0.8645 (HO-033) |
| HO2-012 | relevance | 0.232 (REL-205) | 0.533 (REL-105) | 0.0 (REL-101) | 0.8683 (REL-205) |
| HO2-012 | rbac | 0.193 (RBD-15) | 0.489 (RBD-11) | 0.0 (RBD-01) | 0.8523 (RBD-11) |
| HO2-013 | uat | 0.222 (Q002) | 0.559 (Q009) | 0.0 (Q001) | 0.8431 (Q010) |
| HO2-013 | heldout_v1 | 0.122 (HO-006) | 0.427 (HO-022) | 0.0 (HO-001) | 0.8555 (HO-040) |
| HO2-013 | relevance | 0.147 (REL-101) | 0.515 (REL-207) | 0.0 (REL-101) | 0.8177 (REL-103) |
| HO2-013 | rbac | 0.127 (RBD-05) | 0.437 (RBD-05) | 0.0 (RBD-01) | 0.7983 (RBD-06) |
| HO2-014 | uat | 0.239 (Q087) | 0.525 (Q063) | 0.0 (Q001) | 0.8792 (Q096) |
| HO2-014 | heldout_v1 | 0.2 (HO-039) | 0.463 (HO-040) | 0.0 (HO-001) | 0.8581 (HO-030) |
| HO2-014 | relevance | 0.145 (REL-402) | 0.457 (REL-406) | 0.0 (REL-101) | 0.8418 (REL-402) |
| HO2-014 | rbac | 0.149 (RBD-18) | 0.489 (RBD-12) | 0.0 (RBD-01) | 0.852 (RBD-03) |
| HO2-015 | uat | 0.235 (Q013) | 0.634 (Q014) | 0.0 (Q001) | 0.9018 (Q013) |
| HO2-015 | heldout_v1 | 0.102 (HO-014) | 0.314 (HO-017) | 0.0 (HO-001) | 0.8765 (HO-022) |
| HO2-015 | relevance | 0.091 (REL-104) | 0.32 (REL-104) | 0.0 (REL-101) | 0.8144 (REL-306) |
| HO2-015 | rbac | 0.093 (RBD-17) | 0.333 (RBD-09) | 0.0 (RBD-01) | 0.8027 (RBD-06) |
| HO2-016 | uat | 0.2 (Q038) | 0.467 (Q044) | 0.0 (Q001) | 0.8465 (Q073) |
| HO2-016 | heldout_v1 | 0.195 (HO-031) | 0.459 (HO-039) | 0.0 (HO-001) | 0.841 (HO-002) |
| HO2-016 | relevance | 0.173 (REL-201) | 0.487 (REL-405) | 0.0 (REL-101) | 0.8256 (REL-302) |
| HO2-016 | rbac | 0.181 (RBD-15) | 0.424 (RBD-02) | 0.0 (RBD-01) | 0.8227 (RBD-03) |
| HO2-017 | uat | 0.218 (Q055) | 0.532 (Q048) | 0.0 (Q001) | 0.8861 (Q043) |
| HO2-017 | heldout_v1 | 0.277 (HO-029) | 0.471 (HO-040) | 0.048 (HO-029) | 0.9301 (HO-029) |
| HO2-017 | relevance | 0.175 (REL-203) | 0.507 (REL-303) | 0.0 (REL-101) | 0.8526 (REL-206) |
| HO2-017 | rbac | 0.129 (RBD-11) | 0.42 (RBD-09) | 0.0 (RBD-01) | 0.8478 (RBD-11) |
| HO2-018 | uat | 0.34 (Q045) | 0.603 (Q059) | 0.0 (Q001) | 0.9288 (Q071) |
| HO2-018 | heldout_v1 | 0.163 (HO-026) | 0.404 (HO-026) | 0.0 (HO-001) | 0.8712 (HO-018) |
| HO2-018 | relevance | 0.148 (REL-102) | 0.432 (REL-206) | 0.0 (REL-101) | 0.8591 (REL-201) |
| HO2-018 | rbac | 0.183 (RBD-01) | 0.456 (RBD-03) | 0.0 (RBD-01) | 0.8481 (RBD-05) |
| HO2-019 | uat | 0.365 (Q041) | 0.531 (Q041) | 0.0 (Q001) | 0.9242 (Q041) |
| HO2-019 | heldout_v1 | 0.242 (HO-039) | 0.481 (HO-039) | 0.0 (HO-001) | 0.8655 (HO-039) |
| HO2-019 | relevance | 0.181 (REL-303) | 0.43 (REL-303) | 0.0 (REL-101) | 0.8371 (REL-201) |
| HO2-019 | rbac | 0.2 (RBD-15) | 0.477 (RBD-16) | 0.0 (RBD-01) | 0.8323 (RBD-05) |
| HO2-020 | uat | 0.539 (Q052) | 0.606 (Q052) | 0.042 (Q052) | 0.9336 (Q098) |
| HO2-020 | heldout_v1 | 0.23 (HO-010) | 0.443 (HO-006) | 0.0 (HO-001) | 0.888 (HO-006) |
| HO2-020 | relevance | 0.172 (REL-101) | 0.438 (REL-204) | 0.0 (REL-101) | 0.8365 (REL-101) |
| HO2-020 | rbac | 0.167 (RBD-15) | 0.433 (RBD-02) | 0.0 (RBD-01) | 0.8401 (RBD-05) |
