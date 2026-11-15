# Held-out v2 grading sheet (owner)

**Sự việc phải nêu (DEC-022):** ngày 2026-11-11 owner đã chạy tay 20 câu held-out v2 trên hệ thống, ngoài quy trình DEC-012. Bản ghi lần chạy đó không có trong repo và không được dùng để thiết kế bản sửa nào; chỉ ba lỗi hiển thị chung (D2) được lấy từ đó. Vì vậy đây không phải lần đầu hệ thống gặp bộ câu này.

REVIEW flags and proxy suggestions are automatic hints. **No label was filled in**; the
owner assigns PASS / PARTIAL / FAIL / LEAK in this file or in grading.csv.

Questions SHA256 `dae7f8818a015d43a00d09fbeff9cc63f41c75d005e11f465e77617a0e86cd5a`; gold SHA256 `c35f141331ea181c257cd36c456cadaba98f46e1b63cc95c2360b2c72bcad67a`, approved by owner (NQThai-7803).

| Run | Validity | INFRA_ERROR | Max latency |
|---|---|---|---|
| 1 | VALID | 0 | 84521 ms |
| 2 | VALID | 0 | 82982 ms |

Near UAT (e5 >= 0.90 to a Q001-Q100 question): 9 items (HO2-001, HO2-003, HO2-006, HO2-008, HO2-012, HO2-015, HO2-018, HO2-019, HO2-020); the rest: 11 items. Results must be reported for each group apart.

# Group 1: near UAT (e5 >= 0.90)

---

## HO2-001 | role `staff` | e5 to UAT 0.9323 (Q022)

**Question** (vi): Thời gian bắt đầu làm việc là bao nhiêu? Nghỉ trưa được mấy tiếng? Và mấy giờ tan làm?

**Gold status:** `ANSWERED`

**Required points:**
- Bắt đầu làm việc: khung linh hoạt 08:00 - 09:00.
- Nghỉ trưa: 60 phút (1 tiếng), thông thường 12:00 - 13:00.
- Tan làm: khung 17:00 - 18:00, tương ứng giờ bắt đầu để đủ 08 giờ/ngày.

**Optional points:**
- ND-HR-002 Điều 5 ghi khung tham chiếu 08:30-17:30, nghỉ trưa 12:00-13:00, linh hoạt bắt đầu 08:00-09:30.
- Bộ phận trực hoặc 24/7 có lịch ca riêng.

**Gold notes:** Câu ghép 3 ý, mỗi ý một mục bắt buộc. Owner duyệt theo đề xuất (2026-11-15): hai tài liệu khác nhau về giờ bắt đầu và kết thúc; gold theo ND-HR-003 vì là chính sách chuyên đề và áp dụng muộn hơn (01/09/2026 so với 01/08/2026); câu trả lời nêu số của ND-HR-002 và trích ND-HR-002 vẫn đạt.

**Gold citations:** ND-HR-003 p.4

### Run 1: `ANSWERED` (64272 ms)

> Thời gian bắt đầu làm việc là từ 08:00 đến 09:00, nghỉ trưa 12:00-13:00, và tổng thời gian làm việc là 08 giờ/ngày; 40 giờ/tuần. [1] [2]

- [1] ND-HR-002 p.5 — evidence_text: **(empty)**
- [2] ND-HR-003 p.4 — evidence_text: **(empty)**

### Run 2: same as run 1 (37708 ms)

**REVIEW flags (automatic):** `EVIDENCE_EMPTY`

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-003 | role `staff` | e5 to UAT 0.9072 (Q068)

**Question** (vi): Tiền OT sẽ tính như nào nếu tôi làm sau giờ làm hành chính?

**Gold status:** `ANSWERED`

**Required points:**
- Làm thêm vào ngày làm việc bình thường được trả ít nhất 150% đơn giá/tiền lương giờ thực trả của công việc đang làm.

**Optional points:**
- Làm việc ban đêm được trả thêm ít nhất 30%; làm thêm vào ban đêm còn trả thêm ít nhất 20%.
- Ngày nghỉ hằng tuần ít nhất 200%; ngày lễ, Tết ít nhất 300%.
- OT phải được yêu cầu/phê duyệt; thời gian tự nguyện làm thêm không có phê duyệt có thể không được ghi nhận.

**Gold notes:** Owner duyệt theo đề xuất (2026-11-15): chỉ bắt buộc mức 150%, vì câu hỏi nói 'sau giờ hành chính' mà không nói ban đêm hay điều kiện duyệt; điều kiện phê duyệt là ý không bắt buộc.

**Gold citations:** ND-HR-005 p.7

### Run 1: `NO_ANSWER` (41994 ms)

> Không tìm thấy đủ thông tin trong các tài liệu bạn được phép truy cập để trả lời câu hỏi này.

- (no citations)

### Run 2: same as run 1 (36378 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-006 | role `staff` | e5 to UAT 0.9656 (Q058)

**Question** (vi): Lương của Middle Developer thì sẽ khoảng bao nhiêu?

**Gold status:** `ANSWERED`

**Required points:**
- Dải Base Salary tham khảo của Middle Developer (grade N3) là 18 - 32 triệu đồng gross/tháng.

**Optional points:**
- Đây là dữ liệu giả định; hai người cùng grade có thể khác lương, và mức trần của dải không phải mức tăng tự động.

**Gold citations:** ND-HR-005 p.4

### Run 1: `ANSWERED` (825 ms)

> Giá trị là 18 triệu/tháng. [1]

- [1] ND-HR-005 p.12 — evidence_text: Tình huống A - Thăng từ N2 lên N3 Một Junior Developer lương 18 triệu/tháng được thăng lên Middle Developer.

### Run 2: same as run 1 (813 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** ND-HR-005 cited on p.[12] but not on gold p.[4]

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-008 | role `staff` | e5 to UAT 0.9471 (Q054)

**Question** (vi): Ngày nào là ngày trả lương cho nhân viên?

**Gold status:** `ANSWERED`

**Required points:**
- Ngày 10 của tháng kế tiếp.

**Optional points:**
- Nếu trùng ngày nghỉ/lễ, Finance thực hiện vào ngày làm việc liền trước hoặc theo phương án hợp pháp thuận lợi cho người lao động.

**Gold citations:** ND-HR-005 p.5

### Run 1: `NO_ANSWER` (34221 ms)

> Không tìm thấy đủ thông tin trong các tài liệu bạn được phép truy cập để trả lời câu hỏi này.

- (no citations)

### Run 2: same as run 1 (34280 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-012 | role `staff` | e5 to UAT 0.9534 (Q027)

**Question** (vi): Làm việc remote được tối đa mấy ngày trong tháng?

**Gold status:** `ANSWERED_LIMITED`

**Required points:**
- Tài liệu quy định theo tuần: tối đa 02 ngày/tuần, tùy vị trí và phê duyệt của quản lý.

**Optional points:**
- Đăng ký lịch trước 16:00 của ngày làm việc liền trước hoặc theo lịch cố định của bộ phận.

**Not stated by the documents:**
- Hạn mức remote theo tháng.

**ANSWERED_LIMITED passes when:**
- Đạt khi nêu 02 ngày/tuần và cho biết tài liệu quy định theo tuần, không theo tháng. Nêu 02 ngày/tuần rồi ước tính khoảng 8 ngày/tháng và ghi rõ là ước tính thì vẫn đạt; chỉ nêu số ngày/tháng như một quy định là không đạt.

**FAIL examples:**
- Tối đa 8 ngày mỗi tháng.
- Tài liệu không có thông tin về remote.

**Gold notes:** Lệch đơn vị giữa câu hỏi và tài liệu. Owner duyệt theo đề xuất (2026-11-15).

**Gold citations:** ND-HR-003 p.7

### Run 1: `ANSWERED` (849 ms)

> Thời lượng là 02 ngày/tuần. [1]

- [1] ND-HR-003 p.6 — evidence_text: 02 ngày

### Run 2: same as run 1 (810 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** ND-HR-003 cited on p.[6] but not on gold p.[7]; status ANSWERED differs from gold ANSWERED_LIMITED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-015 | role `staff` | e5 to UAT 0.9018 (Q013)

**Question** (vi): NovaSecure là gì?

**Gold status:** `ANSWERED`

**Required points:**
- NovaSecure là bộ công cụ an toàn thông tin trong danh mục sản phẩm của Nova Digital.
- Chức năng: quản lý cấu hình, giám sát sự kiện, đánh giá rủi ro và hỗ trợ ứng phó sự cố.

**Gold notes:** Câu chỉ có 3 từ; bộ lọc 4-gram được mở rộng để vẫn nhận ra câu ngắn.

**Gold citations:** ND-CORP-001 p.5

### Run 1: `ANSWERED` (28755 ms)

> NovaSecure là bộ công cụ an toàn thông tin của Công ty Công nghệ Nova Digital. [1]

- [1] ND-CORP-001 p.5 — evidence_text: NovaAssist Trợ lý AI doanh nghiệp Tra cứu tri thức nội bộ bằng RAG, trả lời có trích dẫn, phân quyền và audit log. NovaSecure Bộ công cụ an toàn thông tin Quản lý cấu hình, giám sát sự kiện, đánh giá rủi ro và

### Run 2: same as run 1 (28596 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-018 | role `staff` | e5 to UAT 0.9288 (Q071)

**Question** (vi): Bao lâu thì review lương / lần?

**Gold status:** `ANSWERED`

**Required points:**
- Mỗi năm một lần, theo chu kỳ salary review: đánh giá hiệu suất năm tháng 01-02, thông báo điều chỉnh trong tháng 04, ngày hiệu lực thông thường 01/05.

**Optional points:**
- Tham gia salary review không tạo quyền đương nhiên được tăng lương.

**Gold notes:** Owner duyệt theo đề xuất (2026-11-15): tài liệu không viết nguyên văn '1 lần/năm'; 'mỗi năm một lần' suy ra từ 'đánh giá hiệu suất năm' và các mốc theo tháng, và được chấp nhận; câu giữ ANSWERED.

**Gold citations:** ND-HR-005 p.8

### Run 1: `NO_ANSWER` (80487 ms)

> Không tìm thấy đủ thông tin trong các tài liệu bạn được phép truy cập để trả lời câu hỏi này.

- (no citations)

### Run 2: `ANSWERED` (30846 ms), **differs from run 1**

> 2. Chu kỳ salary review mô phỏng có thể được hiểu là review lương diễn ra mỗi năm, cụ thể là vào giai đoạn Mốc mô phỏng, đánh giá hiệu suất năm Tháng 01 - 02. [1]

- [1] ND-HR-005 p.7 — evidence_text: Chu kỳ salary review mô phỏng Giai đoạn Mốc mô phỏng Đánh giá hiệu suất năm Tháng 01 - 02

**REVIEW flags (automatic):** `RUNS_DIFFER`

**Proxy suggestions (hints only, not a label):** ND-HR-005 cited on p.[7] but not on gold p.[8]; status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-019 | role `staff` | e5 to UAT 0.9242 (Q041)

**Question** (vi): Làm bao lâu thì phép năm tăng lên và tăng như thế nào?

**Gold status:** `ANSWERED`

**Required points:**
- Cứ đủ 05 năm làm việc cho Nova Digital.
- Tăng thêm 01 ngày nghỉ hằng năm.

**Optional points:**
- Mức cơ bản 12 ngày làm việc/năm với công việc trong điều kiện bình thường.

**Gold notes:** Câu ghép 2 ý.

**Gold citations:** ND-HR-004 p.4

### Run 1: `ANSWERED` (41901 ms)

> Cứ đủ 05 năm làm việc cho cùng một người sử dụng lao động, số ngày nghỉ hằng năm được tăng thêm 01 ngày. Cứ đủ 05 năm làm việc cho cùng một người sử dụng lao động, số ngày nghỉ hằng năm được tăng lên. [1] [2]

- [1] UAT-LEAVE-AUTHORITY-001 p.3 — evidence_text: **(empty)**
- [2] ND-HR-004 p.3 — evidence_text: **(empty)**

### Run 2: same as run 1 (42338 ms)

**REVIEW flags (automatic):** `EVIDENCE_EMPTY`

**Proxy suggestions (hints only, not a label):** ND-HR-004 cited on p.[3] but not on gold p.[4]

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-020 | role `staff` | e5 to UAT 0.9336 (Q098)

**Question** (vi): Nhân viên đang nghỉ phép có bắt buộc phải xử lý sự cố production không?

**Gold status:** `ANSWERED`

**Required points:**
- Không mặc nhiên bắt buộc: quản lý kích hoạt người thay thế trước; chỉ liên hệ nhân viên đang nghỉ khi không còn phương án hợp lý và có sự đồng ý.
- Ngoại lệ: on-call đã phân lịch thì áp dụng lịch trực đã công bố; khẩn cấp an ninh/an toàn có thể yêu cầu phối hợp theo quy trình ứng phó sự cố.

**Optional points:**
- Ghi nhận thời gian thực tế xử lý và chế độ liên quan; sau sự cố xem xét thời gian nghỉ phục hồi.

**Gold notes:** Owner quyết định (2026-11-15): giữ câu. Citation bắt buộc ND-HR-004 tr. 10; tr. 12 chỉ là câu hỏi gợi ý, không chứa đáp án, nên câu trả lời chỉ trích tr. 12 thì citation không đạt.

**Report note:** Câu hỏi trùng nguyên văn câu hỏi gợi ý in trong tài liệu (ND-HR-004 tr. 12); retrieval có thể khớp thẳng vào câu đó.

**Gold citations:** ND-HR-004 p.10

### Run 1: `ANSWERED` (715 ms)

> Không. Quản lý kích hoạt người thay thế trước; chỉ liên hệ nhân viên nghỉ khi không còn phương án hợp lý và có sự đồng ý. [1]

- [1] ND-HR-004 p.9 — evidence_text: Quản lý kích hoạt người thay thế trước; chỉ liên hệ nhân viên Nhân viên đang nghỉ phép nhưng là đầu mối duy nhất

### Run 2: same as run 1 (707 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** ND-HR-004 cited on p.[9] but not on gold p.[10]

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

# Group 2: the rest

---

## HO2-002 | role `staff` | e5 to UAT 0.8675 (Q024)

**Question** (vi): Có cần phải tăng ca không và tăng ca thì phải báo với ai để duyệt?

**Gold status:** `ANSWERED`

**Required points:**
- Không mặc nhiên phải tăng ca: làm thêm giờ chỉ thực hiện khi có nhu cầu công việc, sự đồng ý của người lao động và phê duyệt theo quy trình, trừ trường hợp pháp luật quy định khác.
- Người duyệt: quản lý trực tiếp.

**Optional points:**
- Tình huống sự cố khẩn cấp được ghi nhận hồi tố theo quy trình incident.
- Nhân viên ghi nhận thời điểm bắt đầu/kết thúc và mã ticket/dự án hoặc lý do trên hệ thống.

**Gold notes:** Câu ghép 2 ý. ND-HR-003 trang 8 chỉ nói 'theo thẩm quyền'; tên vai trò nằm ở trang 10.

**Gold citations:** ND-HR-002 p.5, ND-HR-003 p.10

### Run 1: `NO_ANSWER` (78699 ms)

> Không tìm thấy đủ thông tin trong các tài liệu bạn được phép truy cập để trả lời câu hỏi này.

- (no citations)

### Run 2: same as run 1 (78762 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-004 | role `staff` | e5 to UAT 0.8976 (Q048)

**Question** (vi): Quy trình đăng ký nghỉ có phép?

**Gold status:** `ANSWERED`

**Required points:**
- Nhân viên tạo yêu cầu trên HRM.
- Quản lý trực tiếp rà soát kế hoạch nguồn lực.
- HR kiểm tra số dư/hồ sơ đối với trường hợp cần kiểm soát, rồi hệ thống ghi trạng thái cuối cùng.
- Thời hạn đề nghị phép năm: 1-2 ngày trước ít nhất 02 ngày làm việc; 3-5 ngày trước ít nhất 05 ngày làm việc; trên 5 ngày trước ít nhất 10 ngày làm việc.

**Optional points:**
- Chỉ rời lịch làm việc sau khi yêu cầu ở trạng thái Approved, trừ tình huống khẩn cấp đã thông báo cho quản lý.
- Bàn giao trước kỳ nghỉ: cập nhật ticket/dự án, đầu mối thay thế, thiết lập trạng thái vắng mặt.

**FAIL examples:**
- Đăng ký nghỉ phép năm trước ít nhất 03 ngày làm việc; nghỉ từ 05 ngày liên tục đăng ký trước ít nhất 10 ngày làm việc. (chỉ thời hạn của tài liệu mẫu: không đạt ý 4)

**Gold notes:** Owner quyết định (2026-11-15): gold theo ND-HR-004, tài liệu công ty. UAT-LEAVE-AUTHORITY-001 là tài liệu mẫu ('CHƯA PHẢI VĂN BẢN BAN HÀNH', [TÊN DOANH NGHIỆP]), không phải chính sách công ty; trang 4 của nó ghi thời hạn khác (ít nhất 03 ngày; từ 05 ngày liên tục ít nhất 10 ngày). Câu trả lời chỉ nêu thời hạn của tài liệu mẫu thì không đạt ý 4. 'Nghỉ có phép' được hiểu là phép năm.

**Gold citations:** ND-HR-004 p.9

### Run 1: `NO_ANSWER` (84521 ms)

> Không tìm thấy đủ thông tin trong các tài liệu bạn được phép truy cập để trả lời câu hỏi này.

- (no citations)

### Run 2: `ANSWERED` (27792 ms), **differs from run 1**

> NO [1]

- [1] ND-HR-004 p.8 — evidence_text: NO

**REVIEW flags (automatic):** `RUNS_DIFFER`

**Proxy suggestions (hints only, not a label):** ND-HR-004 cited on p.[8] but not on gold p.[9]; status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-005 | role `staff` | e5 to UAT 0.8881 (Q045)

**Question** (vi): Phụ nữ mang thai thì được nghỉ 3 tháng có phép phải không?

**Gold status:** `ANSWERED_LIMITED`

**Required points:**
- Tài liệu không quy định thời gian nghỉ cụ thể cho phụ nữ mang thai; không xác nhận "3 tháng".
- Nghỉ thai sản thực hiện theo Luật Bảo hiểm xã hội và Bộ luật Lao động.

**Optional points:**
- Thai sản không phải nghỉ phép: đây là chế độ nghỉ theo BHXH.
- HR hỗ trợ xác định hồ sơ, thời điểm nghỉ, quyền lợi BHXH và kế hoạch bàn giao.
- Khám thai/chăm sóc thai kỳ: đăng ký loại nghỉ tương ứng.
- Quản lý không được tự ý chuyển nghỉ thai sản thành nghỉ phép năm nếu người lao động đủ điều kiện hưởng chế độ khác.

**Not stated by the documents:**
- Số tháng nghỉ thai sản.

**ANSWERED_LIMITED passes when:**
- Đạt khi câu trả lời (a) nói tài liệu không quy định thời gian cụ thể và không xác nhận 3 tháng, (b) nói nghỉ thai sản theo Luật Bảo hiểm xã hội và Bộ luật Lao động, (c) không nêu bất kỳ số tháng cụ thể nào. Nói thêm 'không phải nghỉ phép' là ý không bắt buộc. Câu mẫu đạt: "Không có thời gian cụ thể, phụ nữ mang thai được nghỉ theo quy định của Luật Bảo hiểm xã hội và Bộ luật Lao động."

**FAIL examples:**
- Đúng, được nghỉ 3 tháng có phép.
- Không, được nghỉ 6 tháng.

**Gold notes:** Câu tiền đề sai. Owner quyết định (2026-11-15): hai ý bắt buộc là (1) tài liệu không quy định thời gian cụ thể, không xác nhận 3 tháng; (2) nghỉ thai sản theo Luật BHXH và Bộ luật Lao động. 'Không phải nghỉ phép' chuyển thành ý không bắt buộc. Nêu bất kỳ số tháng cụ thể nào là không đạt; con số 6 tháng là kiến thức ngoài PDF. Hai kết quả tìm thấy không liên quan: '3. Thăng chức' (ND-HR-005 trang 8) và 'không quá 06 tháng' về kỷ luật (ND-HR-002 trang 12).

**Gold citations:** ND-HR-004 p.3,8

### Run 1: `ANSWERED` (26548 ms)

> Không. phụ nữ mang thai không được nghỉ 3 tháng có phép. Theo nguồn tài liệu, quản lý không được tự ý chuyển nghỉ ốm, nghỉ thai sản hoặc nghỉ việc riêng theo luật thành nghỉ phép năm nếu người lao động đủ điều kiện hưởng chế độ khác. [1]

- [1] ND-HR-004 p.3 — evidence_text: Quản lý không được tự ý chuyển nghỉ ốm, nghỉ thai sản hoặc nghỉ việc riêng theo luật thành nghỉ phép năm nếu người lao động đủ điều kiện hưởng chế độ khác. Dữ liệu nghỉ được xử lý theo nguyên tắc tối thiểu cần thiết;

### Run 2: same as run 1 (25984 ms)

**REVIEW flags (automatic):** `ABSENT_KEYWORD_HIT`

**Proxy suggestions (hints only, not a label):** status ANSWERED differs from gold ANSWERED_LIMITED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-007 | role `staff` | e5 to UAT 0.8692 (Q039)

**Question** (vi): Tiền thưởng hằng năm như nào?

**Gold status:** `ANSWERED`

**Required points:**
- Thưởng hiệu suất năm theo xếp hạng, tính bằng tháng Base Salary: Exceptional 1,5 - 2,0; Exceeds Expectations 1,0 - 1,5; Meets Expectations 0,5 - 1,0; Partially Meets 0 - 0,5; Does Not Meet 0.
- Không phải khoản lương cố định; phụ thuộc kết quả công ty và phê duyệt ngân sách.

**Optional points:**
- Khoản thưởng có thể phụ thuộc thời gian làm việc đủ điều kiện, kỷ luật đang có hiệu lực hoặc tiêu chí chương trình.
- Các chương trình thưởng khác: Project Delivery, Innovation, Employee Referral, Spot Award.

**Gold notes:** Mỗi xếp hạng phải đúng hệ số.

**Gold citations:** ND-HR-005 p.9

### Run 1: `ANSWERED` (42019 ms)

> Tiền thưởng hằng năm được thực hiện theo pháp luật và kết quả đối soát số dư phép hợp lệ. [1]

- [1] ND-HR-004 p.4 — evidence_text: THANH TOÁN PHÉP CHƯA NGHỈ Khi chấm dứt quan hệ lao động, việc thanh toán tiền lương cho ngày nghỉ hằng năm chưa nghỉ hoặc chưa nghỉ hết được thực hiện theo pháp luật và kết quả đối soát số dư phép hợp lệ.

### Run 2: same as run 1 (42418 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** cites documents outside gold: ['ND-HR-004']; gold documents not cited: ['ND-HR-005']

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-009 | role `staff` | e5 to UAT 0.8643 (Q087)

**Question** (vi): Công ty có phạt tiền nếu làm sai hay không?

**Gold status:** `ANSWERED`

**Required points:**
- Không: Nova Digital không sử dụng phạt tiền hoặc cắt lương thay cho xử lý kỷ luật lao động.
- Vi phạm được xử lý theo ND-HR-002 và ND-HR-010; thiệt hại vật chất, nếu có, được xác định riêng theo căn cứ pháp luật.

**Optional points:**
- Các hình thức kỷ luật: khiển trách, kéo dài thời hạn nâng lương không quá 06 tháng, cách chức, sa thải.
- Khấu trừ để bồi thường không vượt 30% tiền lương tháng sau khi trích nộp bảo hiểm bắt buộc và thuế.

**Gold citations:** ND-HR-005 p.10, ND-HR-002 p.12

### Run 1: `NO_ANSWER` (37564 ms)

> Không tìm thấy đủ thông tin trong các tài liệu bạn được phép truy cập để trả lời câu hỏi này.

- (no citations)

### Run 2: same as run 1 (37754 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-010 | role `staff` | e5 to UAT 0.8986 (Q054)

**Question** (vi): Thử việc sẽ bao lâu và có lương hay không?

**Gold status:** `NO_ANSWER` | acceptable: `ANSWERED_LIMITED`

**Optional points:**
- Nhân viên thử việc: quyền lợi bảo hiểm theo loại hợp đồng và pháp luật; một số phúc lợi nội bộ có thể áp dụng từ ngày nhận việc.

**Not stated by the documents:**
- Thời gian thử việc.
- Lương thử việc.

**ANSWERED_LIMITED passes when:**
- Đạt khi nói tài liệu không nêu thời gian và lương thử việc, không thêm số từ ngoài tài liệu, và nếu trích dẫn thì trích đoạn liên quan.

**FAIL examples:**
- Thử việc 2 tháng, hưởng 85% lương.

**Gold notes:** Câu ghép 2 ý, cả 2 đều không có trong tài liệu.

### Run 1: `NO_ANSWER` (82753 ms)

> Không tìm thấy đủ thông tin trong các tài liệu bạn được phép truy cập để trả lời câu hỏi này.

- (no citations)

### Run 2: same as run 1 (82982 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-011 | role `staff` | e5 to UAT 0.8747 (Q079)

**Question** (vi): Có lịch khám sức khỏe định kỳ hay không?

**Gold status:** `ANSWERED`

**Required points:**
- Có: khám sức khỏe năm 01 lần/năm cho nhân viên chính thức.
- Lịch tổ chức theo đợt hoặc voucher đối tác.

**Optional points:**
- Ngày Wellness Check: tối đa 04 giờ/năm để tham gia đợt khám do công ty tổ chức, không trừ phép nếu đúng lịch.
- Khám chuyên sâu theo nguy cơ khi vị trí/công việc có yêu cầu.

**Gold notes:** Tài liệu không nêu ngày khám cụ thể.

**Gold citations:** ND-HR-006 p.8

### Run 1: `NO_ANSWER` (44546 ms)

> Không tìm thấy đủ thông tin trong các tài liệu bạn được phép truy cập để trả lời câu hỏi này.

- (no citations)

### Run 2: same as run 1 (37816 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-013 | role `staff` | e5 to UAT 0.8431 (Q010)

**Question** (vi): Ai là giám đốc bộ phận Nhân sự?

**Gold status:** `ANSWERED`

**Required points:**
- Giám đốc Nhân sự (CHRO) là Trương Thanh An.

**Optional points:**
- Phụ trách con người, văn hóa, tổ chức và hành chính.

**Gold citations:** ND-CORP-001 p.6

### Run 1: `NO_ANSWER` (34308 ms)

> Không tìm thấy đủ thông tin trong các tài liệu bạn được phép truy cập để trả lời câu hỏi này.

- (no citations)

### Run 2: same as run 1 (20895 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-014 | role `staff` | e5 to UAT 0.8792 (Q096)

**Question** (vi): Nếu tôi cần hỗ trợ CNTT thì liên hệ email nào?

**Gold status:** `ANSWERED`

**Required points:**
- servicedesk@novadigital.example

**Gold citations:** ND-CORP-001 p.9

### Run 1: `NO_ANSWER` (41143 ms)

> Không tìm thấy đủ thông tin trong các tài liệu bạn được phép truy cập để trả lời câu hỏi này.

- (no citations)

### Run 2: same as run 1 (41025 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-016 | role `staff` | e5 to UAT 0.8465 (Q073)

**Question** (vi): Địa chỉ trụ sở chính ở đâu? Tôi nên liên lạc với ai khi tới phỏng vấn?

**Gold status:** `ANSWERED_LIMITED`

**Required points:**
- Trụ sở chính: Tầng 8, Tòa nhà Nova Hub, Khu Công nghệ Phần mềm, Thành phố Hồ Chí Minh.

**Optional points:**
- Phòng Nhân sự & Hành chính phụ trách tuyển dụng; đầu mối nhân sự people@novadigital.example.

**Not stated by the documents:**
- Người liên hệ khi tới phỏng vấn.

**ANSWERED_LIMITED passes when:**
- Đạt khi nêu đúng địa chỉ, cho biết tài liệu không nêu người liên hệ khi phỏng vấn, và không tạo tên hoặc số điện thoại. Gợi ý Phòng Nhân sự hoặc people@novadigital.example vẫn đạt nếu nói rõ tài liệu không quy định riêng.

**FAIL examples:**
- Liên hệ chị Trương Thanh An khi tới phỏng vấn.
- Gọi hotline 028 7300 2026 khi tới phỏng vấn.

**Gold notes:** Câu ghép 2 ý: ý đầu có đáp án, ý sau không. Owner duyệt theo đề xuất (2026-11-15). Từ 'phỏng vấn' chỉ xuất hiện ở ND-HR-006 trang 6, về tư vấn CV khi tái cấu trúc, không liên quan.

**Gold citations:** ND-CORP-001 p.3

### Run 1: `NO_ANSWER` (29185 ms)

> Không tìm thấy đủ thông tin trong các tài liệu bạn được phép truy cập để trả lời câu hỏi này.

- (no citations)

### Run 2: same as run 1 (29302 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED_LIMITED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO2-017 | role `staff` | e5 to UAT 0.8861 (Q043)

**Question** (vi): Tổng ngày nghỉ lễ, Tết trong năm?

**Gold status:** `ANSWERED`

**Required points:**
- 11 ngày.

**Optional points:**
- Tết Dương lịch 01; Tết Âm lịch 05; 30/4 01; 01/5 01; Quốc khánh 02; Giỗ Tổ Hùng Vương 01.
- Người lao động nước ngoài được nghỉ thêm ngày Tết cổ truyền và Quốc khánh của nước họ.

**Gold notes:** Chỉ tài liệu mẫu UAT-LEAVE-AUTHORITY-001 ghi tổng 11; ND-HR-004 chỉ có bảng, phải cộng lại. Trích một trong hai đều đạt.

**Gold citations:** ND-HR-004 p.5

### Run 1: `ANSWERED` (28784 ms)

> 11 ngày [1]

- [1] UAT-LEAVE-AUTHORITY-001 p.3 — evidence_text: 11 ngày

### Run 2: same as run 1 (28871 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** gold documents not cited: ['ND-HR-004']

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 
