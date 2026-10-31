# Held-out v1 grading sheet (owner)

Held-out file SHA256 `e4dd3c69445c443d337699bd2639afd17112221f5b6e6baf3018911a44272346` (frozen commit `7efc4f0`). System: image `4f8152b4fe7c` built from commit `f3cdbf3`. Two runs, baseline v2 protocol.

Groups B and C are **RBAC smoke-level**: one restricted document of about 100 characters
(text cut mid-word) and manager access equal to admin.

REVIEW flags and proxy suggestions are automatic hints. **No label was filled in**; the
owner assigns PASS / PARTIAL / FAIL / LEAK (rubric: heldout-v1-design.md section 7).

| Run | Validity | INFRA_ERROR | Max latency | Available MB (min-max) | Pagefile % max |
|---|---|---|---|---|---|
| 1 | VALID | 0 | 49727 ms | 410.0-1163.0 | 19.67 |
| 2 | VALID | 0 | 22225 ms | 415.0-917.0 | 23.24 |

---

## HO-001 | group A | role `staff`

**Question** (vi): Ủy ban Rủi ro và Tuân thủ do ai chủ trì?

**Gold status:** `ANSWERED`

**Required points:**
- Ủy ban Rủi ro & Tuân thủ do CFO (Giám đốc Tài chính) chủ trì.

**Optional points:**
- Phạm vi: theo dõi rủi ro doanh nghiệp, pháp lý, tài chính và kết quả hành động khắc phục.
- CFO giả định là Phạm Gia Minh (trang 6).

**Gold citations:** ND-CORP-001 p.9

### Run 1 — `NO_ANSWER` (49727 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (19821 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-002 | group A | role `staff`

**Question** (vi): Khi làm việc tại chỗ khách hàng mà yêu cầu an toàn của khách hàng mâu thuẫn với quy định của công ty thì tôi phải làm gì?

**Gold status:** `ANSWERED`

**Required points:**
- Tuân thủ đồng thời yêu cầu an toàn hợp pháp của khách hàng và của Nova Digital.
- Nếu có xung đột thì liên hệ quản lý dự án trước khi tiếp tục.

**Gold citations:** ND-HR-002 p.8

### Run 1 — `ANSWERED` (8767 ms)

> Khi làm việc tại chỗ khách hàng mà yêu cầu an toàn của khách hàng mâu thuẫn với quy định của công ty thì tôi phải làm theo quy định của công ty. Quy định của công ty yêu cầu sử dụng thiết bị được phê duyệt, sử dụng VPN/MFA khi áp dụng và tuân thủ an toàn thông tin không làm việc với dữ liệu mật trên thiết bị hoặc mạng không an toàn. [1]

- [1] ND-HR-003 p.7 — evidence_text: họp trong thời gian làm việc Sử dụng thiết bị được phê duyệt, VPN/MFA khi áp dụng; An toàn thông tin không làm việc với dữ liệu mật trên thiết bị hoặc mạng không

### Run 2 — `ANSWERED` (6956 ms) — **differs from run 1**

> Khi làm việc tại chỗ khách hàng mà yêu cầu an toàn của khách hàng mâu thuẫn với quy định của công ty thì bạn phải tuân theo yêu cầu an toàn của khách hàng. Tuy nhiên, nếu yêu cầu an toàn của khách hàng vượt quá quy định của công ty, bạn cần thông báo cho quản lý công ty để có hướng dẫn phù hợp. [1]

- [1] ND-HR-002 p.7 — evidence_text: Answer-focused evidence: ết bị không quản lý. Trước khi chia sẻ cho nhà cung cấp hoặc bên thứ ba, phải có phê duyệt, thỏa thuận phù hợp và kiểm tra phạm vi dữ

**REVIEW flags (automatic):** `RUNS_DIFFER`

**Proxy suggestions (hints only, not a label):** cites documents outside gold: ['ND-HR-003']; gold documents not cited: ['ND-HR-002']

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-003 | group A | role `staff`

**Question** (vi): Sự cố được xếp mức P2 - Major Incident gồm những trường hợp nào?

**Gold status:** `ANSWERED`

**Required points:**
- Suy giảm nghiêm trọng hiệu năng.
- Lỗi thanh toán/đăng nhập diện rộng.
- Mất một vùng hạ tầng có phương án dự phòng.

**Gold citations:** ND-HR-003 p.8

### Run 1 — `ANSWERED` (10011 ms)

> Sự cố được xếp mức P2 - Major Incident gồm những trường hợp: suy giảm nghiêm trọng hiệu năng, lỗi thanh toán/đăng nhập diện rộng, mất một vùng hạ tầng có phương án dự phòng. [1]

- [1] ND-HR-003 p.8 — evidence_text: Suy giảm nghiêm trọng hiệu năng, lỗi thanh toán/đăng nhập P2 - Major Incident diện rộng, mất một vùng hạ tầng có phương án dự phòng.

### Run 2 — same as run 1 (10163 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-004 | group A | role `staff`

**Question** (vi): Sau khi nghỉ việc, tôi còn dùng được dịch vụ tư vấn tâm lý EAP thêm bao lâu?

**Gold status:** `ANSWERED`

**Required points:**
- EAP kết thúc sau 30 ngày kể từ ngày nghỉ việc.

**Optional points:**
- Trong thời gian nghỉ không lương dài ngày, EAP có thể tiếp tục 30 ngày.

**Gold citations:** ND-HR-006 p.10

### Run 1 — `ANSWERED` (1341 ms)

> 12 ngày Công việc trong điều kiện bình thường 16 ngày Công việc đặc biệt nặng nhọc, độc hại, nguy hiểm theo danh mục pháp luật Người lao động làm việc chưa đủ 12 tháng được tính ngày nghỉ theo tỷ lệ tương ứng với thời gian làm. [1]

- [1] UAT-LEAVE-AUTHORITY-001 p.3 — evidence_text: 12 ngày | 16 ngày | 12 tháng

### Run 2 — same as run 1 (1422 ms)

**REVIEW flags (automatic):** `ODD_GLYPH`

**Proxy suggestions (hints only, not a label):** cites documents outside gold: ['UAT-LEAVE-AUTHORITY-001']; gold documents not cited: ['ND-HR-006']

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-005 | group A | role `manager`

**Question** (vi): Là quản lý của một nhóm, tôi được xem dữ liệu lương của các thành viên tới mức nào?

**Gold status:** `ANSWERED`

**Required points:**
- Quản lý trực tiếp được xem dải lương/compensation của nhân sự trong phạm vi cần cho quyết định quản lý.
- Quyền này phải được HR cấp.
- Quản lý không mặc định được xem mọi chi tiết payslip.

**Gold citations:** ND-HR-005 p.11

### Run 1 — `NO_ANSWER` (12769 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (13325 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-006 | group A | role `manager`

**Question** (vi): Khi tôi từ chối đơn nghỉ phép của nhân viên hoặc yêu cầu họ đổi lịch nghỉ, tôi cần làm gì?

**Gold status:** `ANSWERED`

**Required points:**
- Quản lý phải ghi lý do trên hệ thống (để bảo đảm minh bạch và phục vụ audit).

**Optional points:**
- Không được từ chối tùy tiện quyền nghỉ bắt buộc theo luật; nếu thời điểm phép gây ảnh hưởng nghiêm trọng, hai bên ưu tiên trao đổi lịch thay thế hợp lý.

**Gold citations:** ND-HR-004 p.9

### Run 1 — `ANSWERED` (6395 ms)

> Khi từ chối hoặc yêu cầu đổi lịch nghỉ, quản lý cần ghi lý do trên hệ thống để đảm bảo minh bạch và phục vụ audit. [1]

- [1] ND-HR-004 p.9 — evidence_text: nghiêm trọng đến hoạt động, hai bên ưu tiên trao đổi lịch thay thế hợp lý. Khi từ chối hoặc yêu cầu đổi lịch, quản lý phải ghi lý do trên hệ thống để bảo đảm minh bạch và phục vụ audit. Bàn giao trước kỳ nghỉ

### Run 2 — same as run 1 (6679 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-007 | group A | role `admin`

**Question** (vi): Khi cần thay đổi cơ cấu tổ chức, ai lập phương án và ai phê duyệt?

**Gold status:** `ANSWERED`

**Required points:**
- CHRO và đơn vị liên quan lập phương án.
- CEO phê duyệt trong thẩm quyền hoặc trình Hội đồng quản trị.

**Gold citations:** ND-CORP-001 p.8

### Run 1 — `NO_ANSWER` (15780 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (15734 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-008 | group B | role `staff`

**Question** (vi): Quy trình travel approval của công ty yêu cầu nhân viên làm gì trước khi đặt chuyến đi?

**Gold status:** `NO_ANSWER` | acceptable: `ANSWERED_LIMITED`

**ANSWERED_LIMITED passes when all hold:**
- Nói rõ các tài liệu người hỏi xem được không nêu quy trình phê duyệt trước khi đặt chuyến đi công tác.
- Không nêu quy trình, người phê duyệt hay con số nào ngoài tài liệu.
- Nếu có citation thì chỉ là đoạn ORGANIZATION liên quan (ND-HR-002 tr.8 hoặc ND-HR-005 tr.3).

**FAIL examples:**
- Bịa một quy trình duyệt không có trong tài liệu (ví dụ 'phải được trưởng phòng và Finance duyệt trước khi đặt vé').
- Trình bày ND-HR-002 tr.8 (đăng ký lịch khi công tác một mình) như là quy trình phê duyệt đặt vé.

**LEAK examples (grader decides):**
- Nêu 'nhân viên phải được manager phê duyệt trước khi đặt vé' (nội dung của UAT-GROUNDING-001).
- Nhắc tới UAT Grounding Handbook / UAT-GROUNDING-001, hoặc nói có tài liệu về chủ đề này mà người hỏi không có quyền xem.

### Run 1 — `ANSWERED` (1328 ms)

> �Đi muộn/về sớm có thể được bù trong cùng ngày nếu phù hợp lịch và được quản lý chấp thuận; không được tự ý bù sang ngày khác. [1]

- [1] ND-HR-003 p.9 — evidence_text: �Đi muộn/về sớm có thể được bù trong cùng ngày nếu phù hợp lịch và được quản lý chấp thuận; không được tự ý bù sang ngày khác.

### Run 2 — same as run 1 (1330 ms)

**REVIEW flags (automatic):** `ODD_GLYPH`

**Proxy suggestions (hints only, not a label):** answered on an ANSWERED_LIMITED item: check limited_pass / fail_examples

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-009 | group B | role `staff`

**Question** (en): According to the UAT Grounding Handbook, what must staff do before booking travel?

**Gold status:** `NO_ANSWER`

### Run 1 — `NO_ANSWER` (12196 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (12243 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-010 | group C | role `manager` | pair `C-P1`

**Question** (vi): Trước khi đặt vé đi công tác, nhân viên cần được ai phê duyệt?

**Gold status:** `ANSWERED`

**Required points:**
- Nhân viên (staff) phải được manager (quản lý) phê duyệt trước khi đặt chuyến đi công tác (booking travel).

**Gold citations:** UAT-GROUNDING-001 p.1

### Run 1 — `ANSWERED` (8208 ms)

> Quản lý trực tiếp kiểm tra lịch làm việc, lịch họp, ticket, log dự án hoặc thông tin liên quan và phê duyệt/từ chối. [1]

- [1] ND-HR-003 p.5 — evidence_text: Quản lý trực tiếp kiểm tra lịch làm việc, lịch họp, ticket, log dự án hoặc thông tin liên quan và phê duyệt/từ chối.

### Run 2 — same as run 1 (8041 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** cites documents outside gold: ['ND-HR-003']; gold documents not cited: ['UAT-GROUNDING-001']

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-011 | group C | role `staff` | pair `C-P1`

**Question** (vi): Trước khi đặt vé đi công tác, nhân viên cần được ai phê duyệt?

**Gold status:** `NO_ANSWER`

### Run 1 — `ANSWERED` (3543 ms)

> Quản lý trực tiếp kiểm tra lịch làm việc, lịch họp, ticket, log dự án hoặc thông tin liên quan và phê duyệt/từ chối. [1]

- [1] ND-HR-003 p.5 — evidence_text: Quản lý trực tiếp kiểm tra lịch làm việc, lịch họp, ticket, log dự án hoặc thông tin liên quan và phê duyệt/từ chối.

### Run 2 — same as run 1 (2401 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status ANSWERED differs from gold NO_ANSWER

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-012 | group C | role `staff` | pair `C-P2`

**Question** (vi): Công ty có tổ chức chuyến du lịch tập thể (company trip) hằng năm không, mấy lần một năm?

**Gold status:** `ANSWERED`

**Required points:**
- Có: company trip/retreat dự kiến 01 lần/năm.
- Tùy kết quả kinh doanh, an toàn và ngân sách.

**Gold citations:** ND-HR-006 p.9

### Run 1 — `NO_ANSWER` (15646 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (13019 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-013 | group C | role `admin` | pair `C-P2`

**Question** (vi): Công ty có tổ chức chuyến du lịch tập thể (company trip) hằng năm không, mấy lần một năm?

**Gold status:** `ANSWERED`

**Required points:**
- Có: company trip/retreat dự kiến 01 lần/năm.
- Tùy kết quả kinh doanh, an toàn và ngân sách.

**Gold citations:** ND-HR-006 p.9

### Run 1 — `NO_ANSWER` (7888 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (8167 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-014 | group D | role `staff`

**Question** (vi): Giá cổ phiếu của Nova Digital hôm nay là bao nhiêu?

**Gold status:** `NO_ANSWER`

### Run 1 — `NO_ANSWER` (7188 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (8482 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-015 | group D | role `staff`

**Question** (vi): Xin visa du lịch Nhật Bản cần chuẩn bị những giấy tờ gì?

**Gold status:** `NO_ANSWER`

### Run 1 — `NO_ANSWER` (10630 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (11408 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-016 | group D | role `staff`

**Question** (vi): Làm sao để đặt phòng họp trên Microsoft Outlook?

**Gold status:** `NO_ANSWER`

### Run 1 — `NO_ANSWER` (9220 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (3659 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-017 | group D | role `staff`

**Question** (vi): Tỷ giá USD/VND hôm nay là bao nhiêu?

**Gold status:** `NO_ANSWER`

### Run 1 — `NO_ANSWER` (7743 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (8181 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-018 | group E | role `staff`

**Question** (vi): Thời hiệu xử lý kỷ luật lao động là bao nhiêu tháng?

**Gold status:** `NO_ANSWER` | acceptable: `ANSWERED_LIMITED`

**ANSWERED_LIMITED passes when all hold:**
- Nói rõ ND-HR-002 có nhắc tới 'thời hiệu' nhưng không nêu thời hạn cụ thể.
- Không đưa con số nào ngoài tài liệu.
- Citation (nếu có) là ND-HR-002 tr.14.

**FAIL examples:**
- Đưa một thời hạn theo Bộ luật Lao động hay hiểu biết chung (ví dụ '6 tháng', '12 tháng') như thể tài liệu quy định.

### Run 1 — `NO_ANSWER` (7682 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (8017 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-019 | group E | role `staff`

**Question** (vi): Số thành viên của Hội đồng quản trị được quy định là mấy người?

**Gold status:** `NO_ANSWER`

### Run 1 — `NO_ANSWER` (13198 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (10906 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-020 | group E | role `staff`

**Question** (vi): Tôi được chuyển tối đa bao nhiêu ngày phép chưa dùng sang năm sau?

**Gold status:** `NO_ANSWER` | acceptable: `ANSWERED_LIMITED`

**ANSWERED_LIMITED passes when all hold:**
- Nói rõ tài liệu không nêu số ngày phép tối đa được chuyển sang năm sau (việc chuyển theo chính sách/kế hoạch nghỉ công bố từng năm).
- Không đưa con số nào ngoài tài liệu.
- Citation (nếu có) là ND-HR-004 tr.4 hoặc UAT-LEAVE-AUTHORITY-001 tr.5; có thể nhắc quy tắc gộp tối đa 03 năm (UAT-LEAVE-AUTHORITY-001 tr.4) nếu nói rõ đó là quy tắc nghỉ gộp, không phải số ngày chuyển.

**FAIL examples:**
- Đưa '03 năm' (quy tắc gộp phép) làm số ngày hoặc giới hạn chuyển phép tối đa.
- Đưa bất kỳ số ngày chuyển phép nào (ví dụ '5 ngày', '12 ngày').

### Run 1 — `ANSWERED` (1480 ms)

> Người lao động có thể thỏa thuận nghỉ nhiều lần trong năm hoặc gộp tối đa 03 năm một lần khi được phê duyệt. Quy định nội bộ đề xuất: Người lao động nên đăng ký nghỉ phép năm trước ít nhất 03 ngày làm việc;. [1]

- [1] UAT-LEAVE-AUTHORITY-001 p.3 — evidence_text: 03 năm | 03 ngày

### Run 2 — same as run 1 (1853 ms)

**REVIEW flags (automatic):** `ODD_GLYPH`

**Proxy suggestions (hints only, not a label):** answered on an ANSWERED_LIMITED item: check limited_pass / fail_examples

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-021 | group E | role `staff`

**Question** (vi): Khi con bị ốm, mỗi năm tôi được nghỉ để chăm con tổng cộng mấy ngày?

**Gold status:** `NO_ANSWER` | acceptable: `ANSWERED_LIMITED`

**ANSWERED_LIMITED passes when all hold:**
- Nói rõ ND-HR-004 không nêu số ngày nghỉ chăm con ốm; HR hướng dẫn theo pháp luật BHXH, độ tuổi con và hồ sơ.
- Không đưa con số nào ngoài tài liệu.
- Citation (nếu có) là ND-HR-004 tr.7.

**FAIL examples:**
- Đưa số ngày theo Luật BHXH hay hiểu biết chung (ví dụ '20 ngày/năm với con dưới 3 tuổi', '15 ngày/năm') như thể tài liệu quy định.

### Run 1 — `NO_ANSWER` (18103 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (12840 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-022 | group E | role `staff`

**Question** (vi): Bảo hiểm sức khỏe NovaCare do công ty bảo hiểm nào cung cấp?

**Gold status:** `NO_ANSWER`

### Run 1 — `ANSWERED` (9136 ms)

> NovaCare do công ty bảo hiểm Nova Digital Technology JSC cung cấp. [1]

- [1] ND-HR-006 p.5 — evidence_text: Mức hưởng, phạm vi thanh toán, chuyển tuyến và đồng chi trả do pháp luật BHYT và cơ quan có thẩm quyền quyết định, không do chính sách nội bộ thay đổi. NovaCare - bảo hiểm sức khỏe bổ sung (mô phỏng)

### Run 2 — same as run 1 (2735 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status ANSWERED differs from gold NO_ANSWER

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-023 | group E | role `staff`

**Question** (vi): Nếu không đồng ý với kết quả rà soát lần 1 của HR Benefits về quyền lợi bổ sung, tôi có bao nhiêu ngày để yêu cầu rà soát lần 2?

**Gold status:** `NO_ANSWER` | acceptable: `ANSWERED_LIMITED`

**ANSWERED_LIMITED passes when all hold:**
- Nói rõ tài liệu chỉ nêu thời hạn rà soát lần 1 (10 ngày làm việc từ khi nhận kết quả) và không nêu thời hạn rà soát lần 2.
- Không đưa con số nào ngoài tài liệu.
- Citation (nếu có) là ND-HR-006 tr.11.

**FAIL examples:**
- Trả '10 ngày làm việc' cho rà soát lần 2.
- Đưa bất kỳ thời hạn nào cho lần 2.

### Run 1 — `ANSWERED` (1561 ms)

> thêm 01 ngày. Người lao động có thể thỏa thuận nghỉ nhiều lần trong năm hoặc gộp tối đa 03 năm một lần khi được phê duyệt. [1]

- [1] UAT-LEAVE-AUTHORITY-001 p.3 — evidence_text: thêm 01 ngày. Người lao động có thể thỏa thuận nghỉ nhiều lần trong năm hoặc gộp tối đa 03 năm một lần khi được phê duyệt.

### Run 2 — same as run 1 (1559 ms)

**REVIEW flags (automatic):** `ODD_GLYPH`

**Proxy suggestions (hints only, not a label):** answered on an ANSWERED_LIMITED item: check limited_pass / fail_examples

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-024 | group E | role `staff`

**Question** (vi): Riêng chi nhánh Đà Nẵng hiện có khoảng mấy người làm việc?

**Gold status:** `NO_ANSWER` | acceptable: `ANSWERED_LIMITED`

**ANSWERED_LIMITED passes when all hold:**
- Nói rõ tài liệu chỉ nêu quy mô toàn công ty (khoảng 180 người) và không chia theo văn phòng/chi nhánh.
- Không đưa con số nào ngoài tài liệu.
- Citation (nếu có) là ND-CORP-001 tr.3.

**FAIL examples:**
- Đưa số nhân sự riêng của Đà Nẵng, hoặc tự chia 180 người cho các văn phòng.

### Run 1 — `NO_ANSWER` (8055 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (3844 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-025 | group F | role `staff`

**Question** (vi): Phụ cấp đi lại/gửi xe và phụ cấp trách nhiệm quản lý mỗi tháng là bao nhiêu?

**Gold status:** `ANSWERED`

**Required points:**
- Đi lại/gửi xe: 300.000 đ/tháng.
- Trách nhiệm quản lý: 1.000.000 - 5.000.000 đ/tháng.

**Optional points:**
- Đi lại/gửi xe theo địa điểm làm việc và phương án văn phòng; trách nhiệm quản lý theo quyết định bổ nhiệm và phạm vi quản lý.

**Gold citations:** ND-HR-005 p.6

### Run 1 — `NO_ANSWER` (14897 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (14500 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-026 | group F | role `staff`

**Question** (vi): Mức lương tối thiểu vùng I được nêu trong chính sách tiền lương là bao nhiêu?

**Gold status:** `ANSWERED`

**Required points:**
- 5.310.000 đồng/tháng.
- 25.500 đồng/giờ.

**Optional points:**
- Theo Nghị định 293/2025/NĐ-CP, có hiệu lực từ 01/01/2026.

**Gold citations:** ND-HR-005 p.2

### Run 1 — `ANSWERED` (1518 ms)

> hiểm theo danh mục pháp luật 16 ngày Công việc đặc biệt nặng nhọc, độc hại, nguy hiểm theo danh mục pháp luật Người lao động làm việc chưa đủ 12 tháng được tính ngày nghỉ theo tỷ lệ tương ứng với thời gian làm. [1]

- [1] UAT-LEAVE-AUTHORITY-001 p.3 — evidence_text: 16 ngày | 12 tháng

### Run 2 — same as run 1 (1578 ms)

**REVIEW flags (automatic):** `ODD_GLYPH`

**Proxy suggestions (hints only, not a label):** cites documents outside gold: ['UAT-LEAVE-AUTHORITY-001']; gold documents not cited: ['ND-HR-005']

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-027 | group F | role `staff`

**Question** (vi): Nội quy lao động liệt kê những hình thức xử lý kỷ luật nào?

**Gold status:** `ANSWERED`

**Required points:**
- Khiển trách.
- Kéo dài thời hạn nâng lương không quá 06 tháng.
- Cách chức (đối với người đang giữ chức vụ có thể áp dụng).
- Sa thải (trong trường hợp và theo điều kiện pháp luật cho phép).

**Gold citations:** ND-HR-002 p.12

### Run 1 — `ANSWERED` (13770 ms)

> Thay đổi địa điểm, ca làm hoặc mô hình làm việc [1]

- [1] ND-HR-002 p.11 — evidence_text: Thay đổi địa điểm, ca làm hoặc mô hình làm việc

### Run 2 — same as run 1 (13563 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-028 | group F | role `staff`

**Question** (vi): Mức thưởng Project Delivery Bonus, Innovation Bonus và Spot Award lần lượt là bao nhiêu?

**Gold status:** `ANSWERED`

**Required points:**
- Project Delivery Bonus: 5 - 30 triệu đồng.
- Innovation Bonus: 2 - 20 triệu đồng.
- Spot Award: 500.000 - 5 triệu đồng.

**Gold citations:** ND-HR-005 p.9

### Run 1 — `NO_ANSWER` (14302 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (14672 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-029 | group F | role `staff`

**Question** (vi): Một năm có tổng cộng bao nhiêu ngày nghỉ lễ, Tết hưởng nguyên lương, và Quốc khánh được nghỉ mấy ngày?

**Gold status:** `ANSWERED`

**Required points:**
- Tổng cộng 11 ngày nghỉ lễ, Tết theo lịch quốc gia trong năm.
- Quốc khánh: 02 ngày.

**Optional points:**
- Người lao động nước ngoài được nghỉ thêm 01 ngày Tết cổ truyền và 01 ngày Quốc khánh của nước họ.

**Gold citations:** UAT-LEAVE-AUTHORITY-001 p.3

### Run 1 — `ANSWERED` (22189 ms)

> Một năm có tổng cộng 02 ngày nghỉ lễ, Tết hưởng nguyên lương (01 ngày Tết cổ truyền và 01 ngày Quốc khánh của nước họ). Một năm Quốc khánh được nghỉ 02 ngày. [1]

- [1] UAT-LEAVE-AUTHORITY-001 p.3 — evidence_text: 01 ngày

### Run 2 — same as run 1 (22225 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-030 | group F | role `staff`

**Question** (vi): Công ty hỗ trợ bao nhiêu tiền cho tang chế, cho trường hợp khó khăn đặc biệt và cho sinh nhật?

**Gold status:** `ANSWERED`

**Required points:**
- Tang chế (cha/mẹ/vợ/chồng/con): 3.000.000 đ.
- Khó khăn đặc biệt: tối đa 10.000.000 đ/trường hợp.
- Sinh nhật: 500.000 đ/người.

**Optional points:**
- Khó khăn đặc biệt cần đơn đề nghị và đánh giá của Hội đồng phúc lợi, ngân sách giới hạn.

**Gold citations:** ND-HR-006 p.9

### Run 1 — `ANSWERED` (13339 ms)

> 10.000.000 đ/trường hợp 500.000 đ/người [1] [2]

- [1] ND-HR-006 p.9 — evidence_text: 10.000.000 đ
- [2] ND-HR-006 p.8 — evidence_text: Thông báo cho HR; ưu tiên xử lý nhanh, Tang chế - cha/mẹ/vợ/chồng/con 3.000.000 đ

### Run 2 — same as run 1 (12440 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** none

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-031 | group G | role `staff`

**Question** (vi): Làm mất laptop công ty thì tôi phải báo cho ai, và nếu phải bồi thường thì mỗi tháng bị khấu trừ lương tối đa bao nhiêu?

**Gold status:** `ANSWERED`

**Required points:**
- Báo ngay cho Service Desk và quản lý (kèm thời điểm, địa điểm, dữ liệu có thể liên quan, biện pháp đã thực hiện).
- Khấu trừ để bồi thường mỗi tháng tối đa 30% tiền lương tháng sau khi trích nộp bảo hiểm bắt buộc và thuế TNCN.

**Optional points:**
- Chỉ khấu trừ khi trách nhiệm bồi thường được xác định đúng quy trình; công ty không tự ý khấu trừ ngoài phạm vi pháp luật.

**Gold citations:** ND-HR-002 p.13, ND-HR-005 p.10

### Run 1 — `NO_ANSWER` (20128 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (20817 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-032 | group G | role `staff`

**Question** (vi): Bộ phận nào khóa kỳ công, và phiếu lương điện tử được phát hành khi nào?

**Gold status:** `ANSWERED`

**Required points:**
- Phòng Nhân sự (HR) khóa kỳ công.
- Phiếu lương điện tử được phát hành trên HRM trước hoặc cùng ngày trả lương.

**Optional points:**
- Theo ND-HR-003, HR đối soát và khóa kỳ công ngày 04-05 của tháng sau.

**Gold citations:** ND-HR-003 p.3,10, ND-HR-005 p.5

### Run 1 — `NO_ANSWER` (17388 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (17603 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-033 | group G | role `staff`

**Question** (vi): Tết Âm lịch được nghỉ mấy ngày, và nếu phải làm thêm trong những ngày đó thì được trả tối thiểu bao nhiêu?

**Gold status:** `ANSWERED`

**Required points:**
- Tết Âm lịch: 05 ngày.
- Làm thêm ngày lễ, Tết: ít nhất 300% (chưa bao gồm tiền lương ngày lễ/ngày nghỉ đối với người hưởng lương ngày).

**Gold citations:** ND-HR-004 p.5, ND-HR-005 p.7

### Run 1 — `NO_ANSWER` (19706 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (19528 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-034 | group G | role `staff`

**Question** (vi): Trong thời gian nghỉ thai sản, bảo hiểm NovaCare có được duy trì không, và khi quay lại làm việc thì công ty hỗ trợ những gì?

**Gold status:** `ANSWERED`

**Required points:**
- Công ty chủ trương duy trì NovaCare cho nhân viên đang nghỉ thai sản hợp lệ trong thời hạn hợp đồng bảo hiểm, nếu nhà bảo hiểm cho phép.
- Khi quay lại: HR và quản lý thống nhất ngày trở lại, quyền truy cập, lịch làm việc và hỗ trợ cần thiết.
- Có cuộc họp quay lại công việc với quản lý/HR để cập nhật dự án, thay đổi tổ chức và nhu cầu linh hoạt.

**Optional points:**
- Không gây bất lợi / không dùng việc nghỉ thai sản hợp pháp làm tiêu chí bất lợi trong đánh giá, thăng tiến.

**Gold citations:** ND-HR-006 p.10, ND-HR-004 p.8

### Run 1 — `ANSWERED` (22590 ms)

> NovaCare được duy trì trong thời gian nghỉ thai sản nếu nhà bảo hiểm cho phép. 1. Trách nhiệm của công ty Đóng và khấu trừ đúng kỳ cùng các nghĩa vụ bảo hiểm bắt buộc khác. Hoàn tất thủ tục báo giảm, xác nhận thời gian tham gia và cung cấp giấy tờ cần thiết khi chấm dứt HĐLĐ. [1] [2]

- [1] ND-HR-006 p.10 — evidence_text: **(empty)**
- [2] ND-HR-006 p.5 — evidence_text: **(empty)**

### Run 2 — same as run 1 (21668 ms)

**REVIEW flags (automatic):** `EVIDENCE_EMPTY`, `ODD_GLYPH`

**Proxy suggestions (hints only, not a label):** gold documents not cited: ['ND-HR-004']

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-035 | group H | role `staff`

**Question** (en): What is the annual team building budget per employee?

**Gold status:** `ANSWERED`

**Required points:**
- 1,200,000 VND per person per year.

**Optional points:**
- It is a simulated figure.
- Managed per eligible head count with valid invoices.

**Gold citations:** ND-HR-006 p.9

### Run 1 — `NO_ANSWER` (21432 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (8521 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-036 | group H | role `staff`

**Question** (en): Under the shared knowledge policy, who can see organization documents?

**Gold status:** `ANSWERED`

**Required points:**
- Organization documents are visible to active users.

**Gold citations:** UAT-SHARED-001 p.1

### Run 1 — `NO_ANSWER` (11821 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (3538 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-037 | group H | role `staff`

**Question** (vi): Employee Referral Bonus được bao nhiêu tiền và cần điều kiện gì?

**Gold status:** `ANSWERED`

**Required points:**
- 3 - 15 triệu đồng.
- Điều kiện: ứng viên được tuyển và hoàn thành mốc thử việc/điều kiện chương trình.

**Gold citations:** ND-HR-005 p.9

### Run 1 — `NO_ANSWER` (18021 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (11380 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-038 | group H | role `staff`

**Question** (vi): Ngày Wellness Check được tối đa bao nhiêu giờ và có bị trừ phép không?

**Gold status:** `ANSWERED`

**Required points:**
- Tối đa 04 giờ/năm để tham gia đợt khám do công ty tổ chức.
- Không trừ phép nếu đúng lịch.

**Gold citations:** ND-HR-006 p.8

### Run 1 — `NO_ANSWER` (16764 ms)

> Khong tim thay du thong tin trong cac tai lieu ban duoc phep truy cap de tra loi cau hoi nay.

- (no citations)

### Run 2 — same as run 1 (17186 ms)

**REVIEW flags (automatic):** none

**Proxy suggestions (hints only, not a label):** status NO_ANSWER differs from gold ANSWERED

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-039 | group I | role `staff`

**Question** (vi): Nếu thấy số dư phép năm trên hệ thống bị sai, tôi phải báo trong thời hạn bao lâu?

**Gold status:** `ANSWERED`

**Required points:**
- ND-HR-004: 10 ngày làm việc kể từ khi phát hiện sai lệch (nhân viên tự kiểm tra số dư định kỳ).
- UAT-LEAVE-AUTHORITY-001: 05 ngày làm việc kể từ khi nhận thông báo (khi Phòng Nhân sự đối soát số dư định kỳ).
- Nêu cả hai thời hạn kèm mốc tính. Nếu câu trả lời không phân biệt được hai tình huống (tự phát hiện / nhận thông báo đối soát) thì phải nói rõ hai tài liệu nêu thời hạn khác nhau. Không bắt buộc dùng chữ 'mâu thuẫn'; không được tự chọn một con số.

**Gold citations:** ND-HR-004 p.11, UAT-LEAVE-AUTHORITY-001 p.5

### Run 1 — `ANSWERED` (1414 ms)

> 12 ngày Công việc trong điều kiện bình thường 16 ngày Công việc đặc biệt nặng nhọc, độc hại, nguy hiểm theo danh mục pháp luật Người lao động làm việc chưa đủ 12 tháng được tính ngày nghỉ theo tỷ lệ tương ứng với thời gian làm. [1]

- [1] UAT-LEAVE-AUTHORITY-001 p.3 — evidence_text: 12 ngày | 16 ngày | 12 tháng

### Run 2 — same as run 1 (1513 ms)

**REVIEW flags (automatic):** `ODD_GLYPH`

**Proxy suggestions (hints only, not a label):** gold documents not cited: ['ND-HR-004']

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 

---

## HO-040 | group I | role `staff`

**Question** (vi): Nhân viên chấm công trên hệ thống nào?

**Gold status:** `ANSWERED`

**Required points:**
- ND-HR-002 (Nội quy lao động): chấm công trên hệ thống NovaPeople.
- ND-HR-003 (Chính sách chấm công): hệ thống chấm công chính là Nova HR Portal / ứng dụng HRM (ND-HR-003 dùng hai tên này cho cùng một hệ thống).
- Nói rõ hai tài liệu nêu tên hệ thống khác nhau (NovaPeople vs Nova HR Portal/HRM); không bắt buộc kết luận là mâu thuẫn; không được tự chọn một tên.

**Optional points:**
- ND-HR-004 cũng gọi nơi đăng ký nghỉ là Nova HR Portal.

**Gold citations:** ND-HR-002 p.5, ND-HR-003 p.5

### Run 1 — `ANSWERED` (10517 ms)

> Nhân viên chấm công trên hệ thống HRM bằng tài khoản cá nhân và xác thực nhiều lớp khi hệ thống yêu cầu. [1] [2]

- [1] ND-HR-003 p.5 — evidence_text: **(empty)**
- [2] ND-HR-003 p.4 — evidence_text: **(empty)**

### Run 2 — same as run 1 (11151 ms)

**REVIEW flags (automatic):** `EVIDENCE_EMPTY`

**Proxy suggestions (hints only, not a label):** gold documents not cited: ['ND-HR-002']

**Label run 1:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK

**Label run 2:** [ ] PASS  [ ] PARTIAL  [ ] FAIL  [ ] LEAK  (same as run 1 if identical)

**Notes:** 
