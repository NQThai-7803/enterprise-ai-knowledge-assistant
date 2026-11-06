# Rà soát so khớp trên text tiếng Việt đã bỏ dấu

Chỉ báo cáo, không sửa. Sinh bởi `scripts/diagnostics/diacritics_audit.py`.

- **Số cue:** 2682, trong đó 2265 có từ có thể va chạm, và 859 cue chỉ gồm một từ có thể va chạm (rủi ro cao nhất).
- **Cue** là chuỗi trong file có bỏ dấu, chỉ gồm ký tự không dấu và có ít nhất một từ tiếng Việt đã biết. Chuỗi không phải để so khớp vẫn có thể lọt vào danh sách.
- **Va chạm** lấy từ văn bản tiếng Việt trong repo, phần đầu các chunk UAT đã trace và bảng `COMMON_FORMS`. Không có va chạm nghĩa là "chưa thấy", không phải "không thể".
- **Nhiễu:** vài cue là từ tiếng Anh trùng chữ, như `the`, `day`, `no`. Danh sách chưa được lọc tay, nên cần đọc code tại từng vị trí trước khi kết luận.

## Đã xác nhận gây lỗi

- `dong` trong `_asks_for_amount`: "đồng ý" bị hiểu là tiền (HO-023, REL-201, REL-204). Đã có cách sửa sau `RAG_ANSWER_UNIT_GUARD_ENABLED`.
- `neu `: khớp "nêu" như "nếu" trong route `legacy` (HO-026). `strict` so khớp cả từ có dấu.
- `chua du`: khớp một phần "chưa dùng" trong route `legacy` (HO-020). `strict` so khớp cả từ.

## Nơi bỏ dấu

- `app/chat/context_builder.py:1121`
- `app/chat/context_builder.py:1284`
- `app/chat/follow_up_resolver.py:538`
- `app/chat/follow_up_resolver.py:539`
- `app/chat/prompt_builder.py:394`
- `app/chat/prompt_builder.py:505`
- `app/chat/prompt_builder.py:506`
- `app/citations/evidence.py:236`
- `app/retrieval/question_analysis.py:293`
- `app/retrieval/question_analysis.py:294`
- `app/retrieval/structured.py:725`
- `app/retrieval/structured.py:948`
- `app/services/claim_evidence_validation_service.py:2517`
- `app/services/grounded_answer_service.py:3354`
- `app/services/grounded_answer_service.py:4138`

## Rủi ro cao: cue chỉ có một từ

| Từ | Có thể là | Số chỗ | Vị trí |
|---|---|---:|---|
| `ngay` | ngay, ngày, ngây | 41 | `app/chat/context_builder.py:691`, `app/chat/prompt_builder.py:53`, `app/retrieval/keyword_repository.py:37`, `app/retrieval/question_analysis.py:490`, `app/retrieval/reranker.py:84`, `app/retrieval/reranker.py:649`, `app/retrieval/structured.py:27`, `app/retrieval/structured.py:28`, `app/retrieval/structured.py:29`, `app/retrieval/structured.py:100`, `app/retrieval/structured.py:372`, `app/retrieval/structured.py:764`, `app/services/claim_evidence_validation_service.py:480`, `app/services/claim_evidence_validation_service.py:1105`, `app/services/claim_evidence_validation_service.py:1932`, `app/services/claim_evidence_validation_service.py:3420`, `app/services/claim_evidence_validation_service.py:3568`, `app/services/grounded_answer_service.py:236`, `app/services/grounded_answer_service.py:276`, `app/services/grounded_answer_service.py:4495`, `app/services/grounded_answer_service.py:10501`, `app/services/grounded_answer_service.py:10502`, `app/services/grounded_answer_service.py:10503`, `app/services/grounded_answer_service.py:10530`, `app/services/grounded_answer_service.py:10563`, `app/services/grounded_answer_service.py:3780`, `app/services/grounded_answer_service.py:10562`, `app/services/grounded_answer_service.py:3781`, `app/services/grounded_answer_service.py:5132`, `app/services/grounded_answer_service.py:10284`, `app/services/grounded_answer_service.py:4710`, `app/services/grounded_answer_service.py:4711`, `app/services/grounded_answer_service.py:7749`, `app/services/grounded_answer_service.py:8700`, `app/services/grounded_answer_service.py:10075`, `app/services/grounded_answer_service.py:6669`, `app/services/grounded_answer_service.py:6670`, `app/services/grounded_answer_service.py:9548`, `app/services/grounded_answer_service.py:10318`, `app/services/grounded_answer_service.py:10319`, `app/services/grounded_answer_service.py:3560` |
| `duoc` | dược, được | 34 | `app/chat/context_builder.py:45`, `app/chat/prompt_builder.py:29`, `app/retrieval/evidence_quality.py:64`, `app/retrieval/keyword_repository.py:30`, `app/retrieval/question_analysis.py:86`, `app/retrieval/reranker.py:64`, `app/retrieval/reranker.py:646`, `app/retrieval/structured.py:147`, `app/retrieval/structured.py:536`, `app/services/claim_evidence_validation_service.py:96`, `app/services/claim_evidence_validation_service.py:474`, `app/services/claim_evidence_validation_service.py:522`, `app/services/claim_evidence_validation_service.py:1799`, `app/services/claim_evidence_validation_service.py:1739`, `app/services/claim_evidence_validation_service.py:2977`, `app/services/claim_evidence_validation_service.py:3008`, `app/services/claim_evidence_validation_service.py:3894`, `app/services/claim_evidence_validation_service.py:1881`, `app/services/grounded_answer_service.py:223`, `app/services/grounded_answer_service.py:531`, `app/services/grounded_answer_service.py:3589`, `app/services/grounded_answer_service.py:8787`, `app/services/grounded_answer_service.py:5586`, `app/services/grounded_answer_service.py:8722`, `app/services/grounded_answer_service.py:8728`, `app/services/grounded_answer_service.py:4235`, `app/services/grounded_answer_service.py:4927`, `app/services/grounded_answer_service.py:4955`, `app/services/grounded_answer_service.py:6647`, `app/services/grounded_answer_service.py:8678`, `app/services/grounded_answer_service.py:9109`, `app/services/grounded_answer_service.py:9589`, `app/services/grounded_answer_service.py:10182`, `app/services/grounded_answer_service.py:10726` |
| `tuan` | tuân, tuấn, tuần | 28 | `app/chat/prompt_builder.py:55`, `app/retrieval/keyword_repository.py:45`, `app/retrieval/question_analysis.py:490`, `app/retrieval/reranker.py:650`, `app/retrieval/structured.py:101`, `app/retrieval/structured.py:764`, `app/services/claim_evidence_validation_service.py:482`, `app/services/claim_evidence_validation_service.py:1108`, `app/services/claim_evidence_validation_service.py:3421`, `app/services/claim_evidence_validation_service.py:3568`, `app/services/grounded_answer_service.py:284`, `app/services/grounded_answer_service.py:417`, `app/services/grounded_answer_service.py:4496`, `app/services/grounded_answer_service.py:10504`, `app/services/grounded_answer_service.py:10505`, `app/services/grounded_answer_service.py:10506`, `app/services/grounded_answer_service.py:10532`, `app/services/grounded_answer_service.py:10565`, `app/services/grounded_answer_service.py:3782`, `app/services/grounded_answer_service.py:10564`, `app/services/grounded_answer_service.py:3783`, `app/services/grounded_answer_service.py:4712`, `app/services/grounded_answer_service.py:4713`, `app/services/grounded_answer_service.py:6669`, `app/services/grounded_answer_service.py:6670`, `app/services/grounded_answer_service.py:10318`, `app/services/grounded_answer_service.py:10319`, `app/services/grounded_answer_service.py:10357` |
| `nam` | nam, năm, nấm, nắm, nằm | 26 | `app/chat/context_builder.py:1140`, `app/chat/prompt_builder.py:52`, `app/retrieval/authority.py:17`, `app/retrieval/keyword_repository.py:36`, `app/retrieval/question_analysis.py:490`, `app/retrieval/reranker.py:652`, `app/retrieval/structured.py:33`, `app/retrieval/structured.py:34`, `app/retrieval/structured.py:35`, `app/retrieval/structured.py:103`, `app/retrieval/structured.py:374`, `app/retrieval/structured.py:764`, `app/services/claim_evidence_validation_service.py:484`, `app/services/claim_evidence_validation_service.py:1106`, `app/services/grounded_answer_service.py:10568`, `app/services/grounded_answer_service.py:234`, `app/services/grounded_answer_service.py:275`, `app/services/grounded_answer_service.py:4500`, `app/services/grounded_answer_service.py:10510`, `app/services/grounded_answer_service.py:10511`, `app/services/grounded_answer_service.py:10512`, `app/services/grounded_answer_service.py:10536`, `app/services/grounded_answer_service.py:3786`, `app/services/grounded_answer_service.py:3787`, `app/services/grounded_answer_service.py:4716`, `app/services/grounded_answer_service.py:4717` |
| `thang` | thang, tháng, thăng, thắng, thẳng | 26 | `app/chat/prompt_builder.py:56`, `app/retrieval/keyword_repository.py:42`, `app/retrieval/question_analysis.py:490`, `app/retrieval/reranker.py:651`, `app/retrieval/structured.py:30`, `app/retrieval/structured.py:31`, `app/retrieval/structured.py:32`, `app/retrieval/structured.py:102`, `app/retrieval/structured.py:373`, `app/retrieval/structured.py:764`, `app/services/claim_evidence_validation_service.py:483`, `app/services/claim_evidence_validation_service.py:1107`, `app/services/grounded_answer_service.py:247`, `app/services/grounded_answer_service.py:281`, `app/services/grounded_answer_service.py:4497`, `app/services/grounded_answer_service.py:10507`, `app/services/grounded_answer_service.py:10508`, `app/services/grounded_answer_service.py:10509`, `app/services/grounded_answer_service.py:10534`, `app/services/grounded_answer_service.py:10567`, `app/services/grounded_answer_service.py:3784`, `app/services/grounded_answer_service.py:10566`, `app/services/grounded_answer_service.py:3785`, `app/services/grounded_answer_service.py:3088`, `app/services/grounded_answer_service.py:4714`, `app/services/grounded_answer_service.py:4715` |
| `co` | có, cô, cơ, cố, cổ, cờ, cỡ | 25 | `app/chat/follow_up_resolver.py:436`, `app/chat/follow_up_resolver.py:437`, `app/retrieval/question_analysis.py:326`, `app/retrieval/structured.py:146`, `app/services/claim_evidence_validation_service.py:95`, `app/services/claim_evidence_validation_service.py:520`, `app/services/claim_evidence_validation_service.py:1795`, `app/services/claim_evidence_validation_service.py:686`, `app/services/claim_evidence_validation_service.py:3016`, `app/services/claim_evidence_validation_service.py:3026`, `app/services/claim_evidence_validation_service.py:684`, `app/services/claim_evidence_validation_service.py:1882`, `app/services/grounded_answer_service.py:521`, `app/services/grounded_answer_service.py:260`, `app/services/grounded_answer_service.py:437`, `app/services/grounded_answer_service.py:7196`, `app/services/grounded_answer_service.py:7204`, `app/services/grounded_answer_service.py:8728`, `app/services/grounded_answer_service.py:4235`, `app/services/grounded_answer_service.py:4927`, `app/services/grounded_answer_service.py:6647`, `app/services/grounded_answer_service.py:8678`, `app/services/grounded_answer_service.py:9108`, `app/services/grounded_answer_service.py:10181`, `app/services/grounded_answer_service.py:10725` |
| `dong` | dong, dòng, đóng, đông, đống, đồng, động | 25 | `app/retrieval/question_analysis.py:524`, `app/retrieval/question_analysis.py:541`, `app/retrieval/question_analysis.py:542`, `app/retrieval/reranker.py:152`, `app/retrieval/reranker.py:202`, `app/retrieval/structured.py:104`, `app/retrieval/structured.py:62`, `app/retrieval/structured.py:766`, `app/services/claim_evidence_validation_service.py:266`, `app/services/claim_evidence_validation_service.py:432`, `app/services/claim_evidence_validation_service.py:487`, `app/services/claim_evidence_validation_service.py:517`, `app/services/claim_evidence_validation_service.py:1099`, `app/services/grounded_answer_service.py:222`, `app/services/grounded_answer_service.py:264`, `app/services/grounded_answer_service.py:387`, `app/services/grounded_answer_service.py:4358`, `app/services/grounded_answer_service.py:6697`, `app/services/grounded_answer_service.py:4360`, `app/services/grounded_answer_service.py:5231`, `app/services/grounded_answer_service.py:7918`, `app/services/grounded_answer_service.py:4720`, `app/services/grounded_answer_service.py:10028`, `app/services/grounded_answer_service.py:10032`, `app/services/grounded_answer_service.py:4721` |
| `gio` | gió, giỗ, giờ | 25 | `app/chat/prompt_builder.py:54`, `app/retrieval/keyword_repository.py:31`, `app/retrieval/question_analysis.py:89`, `app/retrieval/question_analysis.py:490`, `app/retrieval/reranker.py:85`, `app/retrieval/reranker.py:653`, `app/retrieval/structured.py:99`, `app/retrieval/structured.py:762`, `app/retrieval/structured.py:764`, `app/services/claim_evidence_validation_service.py:26`, `app/services/claim_evidence_validation_service.py:481`, `app/services/claim_evidence_validation_service.py:1104`, `app/services/grounded_answer_service.py:269`, `app/services/grounded_answer_service.py:10497`, `app/services/grounded_answer_service.py:10498`, `app/services/grounded_answer_service.py:10499`, `app/services/grounded_answer_service.py:10500`, `app/services/grounded_answer_service.py:10561`, `app/services/grounded_answer_service.py:3778`, `app/services/grounded_answer_service.py:10560`, `app/services/grounded_answer_service.py:3779`, `app/services/grounded_answer_service.py:4708`, `app/services/grounded_answer_service.py:4709`, `app/services/grounded_answer_service.py:8149`, `app/services/grounded_answer_service.py:6087` |
| `bao` | bao, báo, bão, bảo | 22 | `app/chat/context_builder.py:45`, `app/chat/prompt_builder.py:46`, `app/citations/evidence.py:55`, `app/retrieval/keyword_repository.py:26`, `app/retrieval/keyword_repository.py:53`, `app/retrieval/reranker.py:62`, `app/retrieval/reranker.py:138`, `app/retrieval/reranker.py:194`, `app/retrieval/reranker.py:647`, `app/retrieval/structured.py:60`, `app/retrieval/structured.py:183`, `app/retrieval/structured.py:534`, `app/services/claim_evidence_validation_service.py:407`, `app/services/claim_evidence_validation_service.py:470`, `app/services/claim_evidence_validation_service.py:534`, `app/services/grounded_answer_service.py:219`, `app/services/grounded_answer_service.py:377`, `app/services/grounded_answer_service.py:531`, `app/services/grounded_answer_service.py:8960`, `app/services/grounded_answer_service.py:10462`, `app/services/grounded_answer_service.py:6297`, `app/services/grounded_answer_service.py:9105` |
| `nhan` | nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn | 20 | `app/chat/prompt_builder.py:24`, `app/retrieval/keyword_repository.py:39`, `app/retrieval/reranker.py:69`, `app/retrieval/reranker.py:644`, `app/services/claim_evidence_validation_service.py:190`, `app/services/claim_evidence_validation_service.py:262`, `app/services/claim_evidence_validation_service.py:428`, `app/services/claim_evidence_validation_service.py:513`, `app/services/claim_evidence_validation_service.py:1804`, `app/services/claim_evidence_validation_service.py:1095`, `app/services/grounded_answer_service.py:278`, `app/services/grounded_answer_service.py:3581`, `app/services/grounded_answer_service.py:10445`, `app/services/grounded_answer_service.py:4958`, `app/services/grounded_answer_service.py:9112`, `app/services/grounded_answer_service.py:9343`, `app/services/grounded_answer_service.py:10184`, `app/services/grounded_answer_service.py:10728`, `app/services/grounded_answer_service.py:4718`, `app/services/grounded_answer_service.py:4719` |
| `cua` | của, cửa | 18 | `app/chat/context_builder.py:45`, `app/chat/context_builder.py:663`, `app/chat/context_builder.py:1056`, `app/chat/prompt_builder.py:33`, `app/retrieval/reranker.py:65`, `app/retrieval/structured.py:153`, `app/retrieval/structured.py:537`, `app/services/claim_evidence_validation_service.py:102`, `app/services/claim_evidence_validation_service.py:183`, `app/services/claim_evidence_validation_service.py:310`, `app/services/claim_evidence_validation_service.py:528`, `app/services/grounded_answer_service.py:531`, `app/services/grounded_answer_service.py:5607`, `app/services/grounded_answer_service.py:4235`, `app/services/grounded_answer_service.py:4954`, `app/services/grounded_answer_service.py:6647`, `app/services/grounded_answer_service.py:10177`, `app/services/grounded_answer_service.py:10721` |
| `day` | đây, đầy | 18 | `app/chat/prompt_builder.py:66`, `app/retrieval/structured.py:28`, `app/retrieval/structured.py:764`, `app/services/claim_evidence_validation_service.py:1102`, `app/services/claim_evidence_validation_service.py:1933`, `app/services/claim_evidence_validation_service.py:3568`, `app/services/grounded_answer_service.py:261`, `app/services/grounded_answer_service.py:4501`, `app/services/grounded_answer_service.py:10502`, `app/services/grounded_answer_service.py:10531`, `app/services/grounded_answer_service.py:3780`, `app/services/grounded_answer_service.py:10562`, `app/services/grounded_answer_service.py:3781`, `app/services/grounded_answer_service.py:4710`, `app/services/grounded_answer_service.py:4711`, `app/services/grounded_answer_service.py:8701`, `app/services/grounded_answer_service.py:10075`, `app/services/grounded_answer_service.py:9548` |
| `luong` | luồng, lương, lường, lượng | 17 | `app/retrieval/keyword_repository.py:34`, `app/retrieval/question_analysis.py:527`, `app/retrieval/question_analysis.py:558`, `app/retrieval/reranker.py:594`, `app/retrieval/structured.py:66`, `app/retrieval/structured.py:680`, `app/retrieval/structured.py:504`, `app/services/claim_evidence_validation_service.py:438`, `app/services/claim_evidence_validation_service.py:3659`, `app/services/grounded_answer_service.py:228`, `app/services/grounded_answer_service.py:10071`, `app/services/grounded_answer_service.py:10120`, `app/services/grounded_answer_service.py:9872`, `app/services/grounded_answer_service.py:6507`, `app/services/grounded_answer_service.py:5279`, `app/services/grounded_answer_service.py:6675`, `app/services/grounded_answer_service.py:1934` |
| `vien` | viên, viền, viễn, viện | 17 | `app/chat/prompt_builder.py:25`, `app/retrieval/keyword_repository.py:46`, `app/retrieval/reranker.py:70`, `app/retrieval/reranker.py:645`, `app/services/claim_evidence_validation_service.py:263`, `app/services/claim_evidence_validation_service.py:429`, `app/services/claim_evidence_validation_service.py:514`, `app/services/claim_evidence_validation_service.py:1813`, `app/services/claim_evidence_validation_service.py:1096`, `app/services/grounded_answer_service.py:285`, `app/services/grounded_answer_service.py:3582`, `app/services/grounded_answer_service.py:10446`, `app/services/grounded_answer_service.py:4962`, `app/services/grounded_answer_service.py:9115`, `app/services/grounded_answer_service.py:9347`, `app/services/grounded_answer_service.py:10185`, `app/services/grounded_answer_service.py:10729` |
| `cong` | cong, công, cổng, cộng | 15 | `app/chat/prompt_builder.py:27`, `app/retrieval/reranker.py:146`, `app/services/claim_evidence_validation_service.py:180`, `app/services/claim_evidence_validation_service.py:518`, `app/services/claim_evidence_validation_service.py:1796`, `app/services/claim_evidence_validation_service.py:1879`, `app/services/claim_evidence_validation_service.py:3222`, `app/services/grounded_answer_service.py:292`, `app/services/grounded_answer_service.py:432`, `app/services/grounded_answer_service.py:6377`, `app/services/grounded_answer_service.py:8728`, `app/services/grounded_answer_service.py:4927`, `app/services/grounded_answer_service.py:4953`, `app/services/grounded_answer_service.py:8678`, `app/services/grounded_answer_service.py:9830` |
| `the` | thẻ, thế, thể | 14 | `app/citations/evidence.py:45`, `app/retrieval/reranker.py:89`, `app/retrieval/structured.py:117`, `app/retrieval/structured.py:158`, `app/retrieval/structured.py:943`, `app/retrieval/structured.py:944`, `app/services/claim_evidence_validation_service.py:382`, `app/services/claim_evidence_validation_service.py:544`, `app/services/claim_evidence_validation_service.py:1809`, `app/services/claim_evidence_validation_service.py:2827`, `app/services/claim_evidence_validation_service.py:1895`, `app/services/grounded_answer_service.py:9000`, `app/services/grounded_answer_service.py:10459`, `app/services/grounded_answer_service.py:8722` |
| `moi` | môi, mọi, mỏi, mối, mỗi, mới, mời | 13 | `app/chat/context_builder.py:46`, `app/chat/prompt_builder.py:51`, `app/retrieval/reranker.py:78`, `app/services/claim_evidence_validation_service.py:33`, `app/services/claim_evidence_validation_service.py:495`, `app/services/claim_evidence_validation_service.py:1089`, `app/services/grounded_answer_service.py:231`, `app/services/grounded_answer_service.py:274`, `app/services/grounded_answer_service.py:3721`, `app/services/grounded_answer_service.py:4235`, `app/services/grounded_answer_service.py:6647`, `app/services/grounded_answer_service.py:10183`, `app/services/grounded_answer_service.py:10727` |
| `tro` | trò, trỏ, trở, trợ | 13 | `app/retrieval/structured.py:174`, `app/services/claim_evidence_validation_service.py:200`, `app/services/claim_evidence_validation_service.py:398`, `app/services/claim_evidence_validation_service.py:493`, `app/services/claim_evidence_validation_service.py:1811`, `app/services/claim_evidence_validation_service.py:1884`, `app/services/grounded_answer_service.py:251`, `app/services/grounded_answer_service.py:283`, `app/services/grounded_answer_service.py:4499`, `app/services/grounded_answer_service.py:8728`, `app/services/grounded_answer_service.py:4927`, `app/services/grounded_answer_service.py:4961`, `app/services/grounded_answer_service.py:8678` |
| `chinh` | chính, chỉnh | 12 | `app/retrieval/keyword_repository.py:28`, `app/retrieval/reranker.py:67`, `app/retrieval/structured.py:539`, `app/services/claim_evidence_validation_service.py:261`, `app/services/claim_evidence_validation_service.py:439`, `app/services/grounded_answer_service.py:5599`, `app/services/grounded_answer_service.py:4235`, `app/services/grounded_answer_service.py:6647`, `app/services/grounded_answer_service.py:9107`, `app/services/grounded_answer_service.py:9342`, `app/services/grounded_answer_service.py:10179`, `app/services/grounded_answer_service.py:10723` |
| `tien` | tiên, tiến, tiền, tiện | 12 | `app/retrieval/question_analysis.py:526`, `app/retrieval/structured.py:75`, `app/services/claim_evidence_validation_service.py:489`, `app/services/claim_evidence_validation_service.py:1810`, `app/services/claim_evidence_validation_service.py:1885`, `app/services/grounded_answer_service.py:248`, `app/services/grounded_answer_service.py:282`, `app/services/grounded_answer_service.py:4498`, `app/services/grounded_answer_service.py:8728`, `app/services/grounded_answer_service.py:4927`, `app/services/grounded_answer_service.py:4960`, `app/services/grounded_answer_service.py:8678` |
| `dai` | dài, dải, đại | 11 | `app/retrieval/question_analysis.py:559`, `app/retrieval/structured.py:61`, `app/retrieval/structured.py:683`, `app/retrieval/structured.py:508`, `app/retrieval/structured.py:713`, `app/services/grounded_answer_service.py:221`, `app/services/grounded_answer_service.py:5536`, `app/services/grounded_answer_service.py:9875`, `app/services/grounded_answer_service.py:4309`, `app/services/grounded_answer_service.py:4327`, `app/services/grounded_answer_service.py:1934` |
| `ho` | họ, hồ, hỗ, hộ, hợ | 11 | `app/chat/follow_up_resolver.py:43`, `app/chat/follow_up_resolver.py:504`, `app/retrieval/reranker.py:156`, `app/services/claim_evidence_validation_service.py:492`, `app/services/claim_evidence_validation_service.py:1801`, `app/services/claim_evidence_validation_service.py:1883`, `app/services/grounded_answer_service.py:227`, `app/services/grounded_answer_service.py:391`, `app/services/grounded_answer_service.py:8728`, `app/services/grounded_answer_service.py:4927`, `app/services/grounded_answer_service.py:8678` |
| `la` | là, lá, lã | 11 | `app/retrieval/evidence_quality.py:61`, `app/retrieval/structured.py:151`, `app/services/claim_evidence_validation_service.py:100`, `app/services/claim_evidence_validation_service.py:188`, `app/services/claim_evidence_validation_service.py:525`, `app/services/claim_evidence_validation_service.py:2922`, `app/services/grounded_answer_service.py:8790`, `app/services/grounded_answer_service.py:5838`, `app/services/grounded_answer_service.py:5590`, `app/services/grounded_answer_service.py:3024`, `app/services/grounded_answer_service.py:3032` |
| `sach` | sách, sạch | 11 | `app/retrieval/keyword_repository.py:41`, `app/retrieval/reranker.py:68`, `app/retrieval/structured.py:540`, `app/services/claim_evidence_validation_service.py:278`, `app/services/grounded_answer_service.py:5600`, `app/services/grounded_answer_service.py:4235`, `app/services/grounded_answer_service.py:6647`, `app/services/grounded_answer_service.py:9113`, `app/services/grounded_answer_service.py:9345`, `app/services/grounded_answer_service.py:10180`, `app/services/grounded_answer_service.py:10724` |
| `lam` | lam, làm, lâm, lạm, lắm | 10 | `app/services/claim_evidence_validation_service.py:409`, `app/services/claim_evidence_validation_service.py:494`, `app/services/claim_evidence_validation_service.py:536`, `app/services/claim_evidence_validation_service.py:2820`, `app/services/claim_evidence_validation_service.py:3462`, `app/services/grounded_answer_service.py:10453`, `app/services/grounded_answer_service.py:10736`, `app/services/grounded_answer_service.py:5046`, `app/services/grounded_answer_service.py:10352`, `app/services/grounded_answer_service.py:3239` |
| `muc` | múc, mục, mức, mực | 10 | `app/chat/prompt_builder.py:48`, `app/retrieval/keyword_repository.py:35`, `app/retrieval/reranker.py:82`, `app/retrieval/structured.py:86`, `app/retrieval/structured.py:67`, `app/services/claim_evidence_validation_service.py:437`, `app/services/claim_evidence_validation_service.py:476`, `app/services/grounded_answer_service.py:233`, `app/services/grounded_answer_service.py:4545`, `app/services/grounded_answer_service.py:9878` |
| `nhieu` | nhiêu, nhiếu, nhiều, nhiễu, nhiệu | 10 | `app/chat/context_builder.py:45`, `app/chat/prompt_builder.py:47`, `app/retrieval/reranker.py:63`, `app/retrieval/reranker.py:648`, `app/retrieval/structured.py:69`, `app/retrieval/structured.py:535`, `app/services/claim_evidence_validation_service.py:471`, `app/services/grounded_answer_service.py:237`, `app/services/grounded_answer_service.py:531`, `app/services/grounded_answer_service.py:10463` |
| `no` | nó, nợ | 10 | `app/chat/follow_up_resolver.py:42`, `app/chat/follow_up_resolver.py:503`, `app/services/claim_evidence_validation_service.py:82`, `app/services/claim_evidence_validation_service.py:107`, `app/services/claim_evidence_validation_service.py:689`, `app/services/claim_evidence_validation_service.py:3016`, `app/services/claim_evidence_validation_service.py:3026`, `app/services/grounded_answer_service.py:521`, `app/services/grounded_answer_service.py:3889`, `app/services/grounded_answer_service.py:7199` |
| `toi` | tôi, tỏi, tối, tội, tới | 10 | `app/chat/prompt_builder.py:49`, `app/retrieval/question_analysis.py:145`, `app/retrieval/reranker.py:79`, `app/services/claim_evidence_validation_service.py:228`, `app/services/claim_evidence_validation_service.py:259`, `app/services/claim_evidence_validation_service.py:477`, `app/services/grounded_answer_service.py:249`, `app/services/grounded_answer_service.py:461`, `app/services/grounded_answer_service.py:6667`, `app/services/grounded_answer_service.py:10314` |
| `cap` | cấp, cập, cặp | 9 | `app/retrieval/keyword_repository.py:27`, `app/retrieval/reranker.py:141`, `app/retrieval/reranker.py:196`, `app/services/claim_evidence_validation_service.py:323`, `app/services/claim_evidence_validation_service.py:491`, `app/services/claim_evidence_validation_service.py:1794`, `app/services/claim_evidence_validation_service.py:1887`, `app/services/grounded_answer_service.py:220`, `app/services/grounded_answer_service.py:379` |
| `cho` | cho, chó, chỗ, chờ, chở, chợ | 9 | `app/chat/prompt_builder.py:34`, `app/retrieval/keyword_repository.py:60`, `app/retrieval/structured.py:154`, `app/services/claim_evidence_validation_service.py:103`, `app/services/claim_evidence_validation_service.py:311`, `app/services/claim_evidence_validation_service.py:529`, `app/services/claim_evidence_validation_service.py:1894`, `app/services/grounded_answer_service.py:8968`, `app/services/grounded_answer_service.py:8722` |
| `truc` | trúc, trực | 9 | `app/retrieval/question_analysis.py:499`, `app/retrieval/reranker.py:185`, `app/retrieval/reranker.py:225`, `app/services/claim_evidence_validation_service.py:2599`, `app/services/grounded_answer_service.py:416`, `app/services/grounded_answer_service.py:6073`, `app/services/grounded_answer_service.py:9316`, `app/services/grounded_answer_service.py:6100`, `app/services/grounded_answer_service.py:7692` |
| `do` | do, dò, dở, đo, đó, đỏ, đồ, đổ, độ | 8 | `app/retrieval/question_analysis.py:326`, `app/retrieval/structured.py:192`, `app/services/claim_evidence_validation_service.py:110`, `app/services/claim_evidence_validation_service.py:301`, `app/services/claim_evidence_validation_service.py:419`, `app/services/grounded_answer_service.py:518`, `app/services/grounded_answer_service.py:9014`, `app/services/grounded_answer_service.py:7230` |
| `dung` | dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng | 8 | `app/retrieval/structured.py:150`, `app/services/claim_evidence_validation_service.py:99`, `app/services/claim_evidence_validation_service.py:317`, `app/services/claim_evidence_validation_service.py:434`, `app/services/claim_evidence_validation_service.py:1893`, `app/services/grounded_answer_service.py:521`, `app/services/grounded_answer_service.py:265`, `app/services/grounded_answer_service.py:8722` |
| `trong` | trọng, trống | 8 | `app/retrieval/keyword_repository.py:92`, `app/services/claim_evidence_validation_service.py:90`, `app/services/claim_evidence_validation_service.py:2977`, `app/services/claim_evidence_validation_service.py:3008`, `app/services/grounded_answer_service.py:8974`, `app/services/grounded_answer_service.py:10468`, `app/services/grounded_answer_service.py:10186`, `app/services/grounded_answer_service.py:10730` |
| `lan` | lan, lân, lãn, lần, lẫn, lặn | 7 | `app/retrieval/structured.py:22`, `app/retrieval/structured.py:23`, `app/retrieval/structured.py:24`, `app/retrieval/structured.py:25`, `app/retrieval/structured.py:26`, `app/retrieval/structured.py:368`, `app/services/grounded_answer_service.py:229` |
| `neu` | nêu, nếu, nệu | 7 | `app/chat/context_builder.py:660`, `app/chat/follow_up_resolver.py:69`, `app/retrieval/question_analysis.py:646`, `app/services/claim_evidence_validation_service.py:1929`, `app/services/grounded_answer_service.py:9073`, `app/services/grounded_answer_service.py:5591`, `app/services/grounded_answer_service.py:8697` |
| `nghi` | nghi, nghĩ, nghỉ, nghị | 7 | `app/retrieval/keyword_repository.py:38`, `app/retrieval/question_analysis.py:491`, `app/services/grounded_answer_service.py:10071`, `app/services/grounded_answer_service.py:5105`, `app/services/grounded_answer_service.py:10304`, `app/services/grounded_answer_service.py:7744`, `app/services/grounded_answer_service.py:10357` |
| `phu` | phù, phụ | 7 | `app/chat/context_builder.py:1060`, `app/retrieval/keyword_repository.py:40`, `app/services/claim_evidence_validation_service.py:193`, `app/services/claim_evidence_validation_service.py:490`, `app/services/claim_evidence_validation_service.py:1886`, `app/services/grounded_answer_service.py:239`, `app/services/grounded_answer_service.py:454` |
| `thi` | thi, thì, thí, thị | 7 | `app/retrieval/structured.py:77`, `app/retrieval/structured.py:156`, `app/services/claim_evidence_validation_service.py:105`, `app/services/claim_evidence_validation_service.py:507`, `app/services/claim_evidence_validation_service.py:524`, `app/services/grounded_answer_service.py:292`, `app/services/grounded_answer_service.py:5592` |
| `ban` | ban, bàn, bán, bạn, bản, bận | 6 | `app/retrieval/reranker.py:137`, `app/retrieval/reranker.py:230`, `app/services/claim_evidence_validation_service.py:175`, `app/services/grounded_answer_service.py:423`, `app/services/grounded_answer_service.py:428`, `app/services/grounded_answer_service.py:10352` |
| `bo` | bỏ, bố, bổ, bộ | 6 | `app/retrieval/reranker.py:230`, `app/retrieval/structured.py:172`, `app/services/claim_evidence_validation_service.py:176`, `app/services/claim_evidence_validation_service.py:396`, `app/services/grounded_answer_service.py:423`, `app/services/grounded_answer_service.py:429` |
| `giam` | giám, giảm | 6 | `app/chat/context_builder.py:54`, `app/retrieval/reranker.py:154`, `app/services/claim_evidence_validation_service.py:187`, `app/services/grounded_answer_service.py:389`, `app/services/grounded_answer_service.py:443`, `app/services/grounded_answer_service.py:9123` |
| `to` | tố, tổ, tờ | 6 | `app/chat/context_builder.py:670`, `app/services/claim_evidence_validation_service.py:444`, `app/services/grounded_answer_service.py:466`, `app/services/grounded_answer_service.py:9004`, `app/services/grounded_answer_service.py:9439`, `app/services/grounded_answer_service.py:9446` |
| `bat` | bất, bật, bắt | 5 | `app/citations/evidence.py:51`, `app/retrieval/structured.py:164`, `app/services/claim_evidence_validation_service.py:388`, `app/services/grounded_answer_service.py:10735`, `app/services/grounded_answer_service.py:10783` |
| `can` | cân, căn, cần, cận | 5 | `app/retrieval/question_analysis.py:326`, `app/services/claim_evidence_validation_service.py:112`, `app/services/claim_evidence_validation_service.py:303`, `app/services/grounded_answer_service.py:9026`, `app/services/grounded_answer_service.py:7232` |
| `dau` | dấu, dầu, đau, đâu, đầu | 5 | `app/chat/context_builder.py:480`, `app/services/grounded_answer_service.py:6171`, `app/services/grounded_answer_service.py:10735`, `app/services/grounded_answer_service.py:10783`, `app/services/grounded_answer_service.py:9548` |
| `du` | du, dù, dư, dụ, dữ, dự, đu, đủ | 5 | `app/retrieval/leave_relations.py:54`, `app/retrieval/reranker.py:153`, `app/retrieval/reranker.py:203`, `app/services/claim_evidence_validation_service.py:275`, `app/services/grounded_answer_service.py:388` |
| `hoi` | hỏi, hồi, hội | 5 | `app/retrieval/reranker.py:157`, `app/retrieval/reranker.py:205`, `app/retrieval/reranker.py:230`, `app/services/grounded_answer_service.py:392`, `app/services/grounded_answer_service.py:423` |
| `khoi` | khôi, khỏi, khối, khởi | 5 | `app/retrieval/reranker.py:162`, `app/retrieval/reranker.py:230`, `app/services/grounded_answer_service.py:423`, `app/services/grounded_answer_service.py:449`, `app/services/grounded_answer_service.py:10456` |
| `mat` | mát, mất, mật, mắt, mặt | 5 | `app/retrieval/reranker.py:165`, `app/retrieval/reranker.py:212`, `app/services/claim_evidence_validation_service.py:2709`, `app/services/grounded_answer_service.py:400`, `app/services/grounded_answer_service.py:5101` |
| `phan` | phan, phán, phân, phản, phần, phận | 5 | `app/chat/prompt_builder.py:57`, `app/services/claim_evidence_validation_service.py:191`, `app/services/claim_evidence_validation_service.py:485`, `app/services/grounded_answer_service.py:238`, `app/services/grounded_answer_service.py:10438` |
| `phong` | phong, phòng, phóng, phỏng | 5 | `app/retrieval/reranker.py:172`, `app/retrieval/reranker.py:230`, `app/services/claim_evidence_validation_service.py:192`, `app/services/grounded_answer_service.py:423`, `app/services/grounded_answer_service.py:457` |
| `sau` | sau, sáu, sâu | 5 | `app/chat/context_builder.py:977`, `app/chat/follow_up_resolver.py:68`, `app/services/grounded_answer_service.py:8941`, `app/services/grounded_answer_service.py:9072`, `app/services/grounded_answer_service.py:3764` |
| `tham` | thâm, thẩm | 5 | `app/retrieval/keyword_repository.py:43`, `app/retrieval/structured.py:73`, `app/services/claim_evidence_validation_service.py:3897`, `app/services/grounded_answer_service.py:246`, `app/services/grounded_answer_service.py:9594` |
| `thuong` | thương, thường, thưởng | 5 | `app/chat/context_builder.py:713`, `app/chat/context_builder.py:691`, `app/services/claim_evidence_validation_service.py:506`, `app/services/grounded_answer_service.py:8053`, `app/services/grounded_answer_service.py:8372` |
| `van` | văn, vấn, vẫn, vận | 5 | `app/retrieval/reranker.py:187`, `app/retrieval/reranker.py:230`, `app/services/claim_evidence_validation_service.py:435`, `app/services/grounded_answer_service.py:423`, `app/services/grounded_answer_service.py:468` |
| `an` | án, ăn, ản, ấn | 4 | `app/retrieval/reranker.py:135`, `app/retrieval/reranker.py:192`, `app/services/grounded_answer_service.py:375`, `app/services/grounded_answer_service.py:9002` |
| `cam` | cảm, cấm | 4 | `app/services/claim_evidence_validation_service.py:294`, `app/services/grounded_answer_service.py:6265`, `app/services/grounded_answer_service.py:6270`, `app/services/grounded_answer_service.py:6275` |
| `dua` | dựa, đũa, đưa | 4 | `app/services/claim_evidence_validation_service.py:3714`, `app/services/claim_evidence_validation_service.py:3730`, `app/services/grounded_answer_service.py:7860`, `app/services/grounded_answer_service.py:6330` |
| `hang` | hàng, hãng, hạng, hằng | 4 | `app/retrieval/reranker.py:155`, `app/retrieval/reranker.py:204`, `app/services/grounded_answer_service.py:390`, `app/services/grounded_answer_service.py:10357` |
| `may` | may, mày, máy, mây, mấy | 4 | `app/retrieval/question_analysis.py:218`, `app/services/claim_evidence_validation_service.py:63`, `app/services/claim_evidence_validation_service.py:302`, `app/services/claim_evidence_validation_service.py:472` |
| `noi` | nói, nơi, nối, nội | 4 | `app/retrieval/reranker.py:167`, `app/services/claim_evidence_validation_service.py:433`, `app/services/grounded_answer_service.py:401`, `app/services/grounded_answer_service.py:5601` |
| `tang` | tang, tăng, tảng, tầng, tặng | 4 | `app/chat/context_builder.py:52`, `app/retrieval/leave_relations.py:50`, `app/retrieval/structured.py:176`, `app/services/claim_evidence_validation_service.py:400` |
| `thong` | thông, thống | 4 | `app/retrieval/reranker.py:182`, `app/retrieval/reranker.py:222`, `app/services/claim_evidence_validation_service.py:272`, `app/services/grounded_answer_service.py:412` |
| `tin` | tin, tín | 4 | `app/retrieval/reranker.py:183`, `app/retrieval/reranker.py:223`, `app/services/claim_evidence_validation_service.py:273`, `app/services/grounded_answer_service.py:413` |
| `toan` | toàn, toán | 4 | `app/retrieval/reranker.py:184`, `app/retrieval/reranker.py:224`, `app/services/grounded_answer_service.py:414`, `app/services/grounded_answer_service.py:6697` |
| `tram` | trám, trăm, trạm | 4 | `app/chat/prompt_builder.py:58`, `app/services/claim_evidence_validation_service.py:486`, `app/services/grounded_answer_service.py:250`, `app/services/grounded_answer_service.py:10439` |
| `tu` | tu, tư, tủ, tứ, từ, tử, tự | 4 | `app/services/claim_evidence_validation_service.py:443`, `app/services/grounded_answer_service.py:418`, `app/services/grounded_answer_service.py:4310`, `app/services/grounded_answer_service.py:9878` |
| `ve` | vé, vẻ, vẽ, về, vệ | 4 | `app/retrieval/structured.py:152`, `app/services/claim_evidence_validation_service.py:101`, `app/services/claim_evidence_validation_service.py:312`, `app/services/claim_evidence_validation_service.py:530` |
| `buoc` | buộc, bước | 3 | `app/citations/evidence.py:52`, `app/retrieval/structured.py:165`, `app/services/claim_evidence_validation_service.py:389` |
| `cao` | cáo, cạo | 3 | `app/retrieval/reranker.py:140`, `app/retrieval/reranker.py:195`, `app/services/grounded_answer_service.py:378` |
| `cau` | câu, cấu, cầu | 3 | `app/chat/prompt_builder.py:36`, `app/services/claim_evidence_validation_service.py:298`, `app/services/claim_evidence_validation_service.py:533` |
| `con` | con, còn, cơn, cồn | 3 | `app/chat/follow_up_resolver.py:12`, `app/chat/follow_up_resolver.py:56`, `app/chat/follow_up_resolver.py:380` |
| `da` | dá, đa, đà, đã | 3 | `app/chat/prompt_builder.py:50`, `app/retrieval/reranker.py:80`, `app/services/claim_evidence_validation_service.py:479` |
| `de` | dễ, đe, đè, đẻ, đề, để | 3 | `app/chat/context_builder.py:664`, `app/services/grounded_answer_service.py:9439`, `app/services/grounded_answer_service.py:9446` |
| `hop` | họp, hợp | 3 | `app/retrieval/reranker.py:158`, `app/retrieval/reranker.py:206`, `app/services/grounded_answer_service.py:393` |
| `kiem` | kiếm, kiểm | 3 | `app/retrieval/reranker.py:161`, `app/retrieval/reranker.py:209`, `app/services/grounded_answer_service.py:397` |
| `kien` | kiến, kiện | 3 | `app/retrieval/reranker.py:159`, `app/retrieval/reranker.py:207`, `app/services/grounded_answer_service.py:395` |
| `nghe` | nghề, nghệ | 3 | `app/retrieval/reranker.py:166`, `app/services/claim_evidence_validation_service.py:189`, `app/services/grounded_answer_service.py:451` |
| `tai` | tai, tài, tái, tại, tải | 3 | `app/services/claim_evidence_validation_service.py:195`, `app/services/grounded_answer_service.py:245`, `app/services/grounded_answer_service.py:3239` |
| `thuoc` | thuộc, thước | 3 | `app/retrieval/structured.py:74`, `app/services/grounded_answer_service.py:252`, `app/services/grounded_answer_service.py:10455` |
| `yeu` | yêu, yếu | 3 | `app/chat/prompt_builder.py:35`, `app/services/claim_evidence_validation_service.py:297`, `app/services/claim_evidence_validation_service.py:532` |
| `bang` | bang, băng, bảng, bằng | 2 | `app/retrieval/structured.py:713`, `app/services/grounded_answer_service.py:5531` |
| `biet` | biết, biệt | 2 | `app/services/grounded_answer_service.py:4530`, `app/services/grounded_answer_service.py:4531` |
| `ca` | cá, cã, cả, cầ | 2 | `app/services/claim_evidence_validation_service.py:1091`, `app/services/grounded_answer_service.py:259` |
| `chuyen` | chuyên, chuyến, chuyển, chuyện | 2 | `app/services/claim_evidence_validation_service.py:442`, `app/services/grounded_answer_service.py:436` |
| `cot` | cốt, cột | 2 | `app/services/grounded_answer_service.py:10739`, `app/services/grounded_answer_service.py:10790` |
| `cung` | cùng, cũng | 2 | `app/services/claim_evidence_validation_service.py:322`, `app/services/grounded_answer_service.py:10458` |
| `dam` | đám, đảm | 2 | `app/services/claim_evidence_validation_service.py:408`, `app/services/claim_evidence_validation_service.py:535` |
| `doc` | đọc, đốc, độc | 2 | `app/services/claim_evidence_validation_service.py:185`, `app/services/grounded_answer_service.py:440` |
| `han` | hàn, hán, hân, hạn, hẳn | 2 | `app/retrieval/keyword_repository.py:32`, `app/services/claim_evidence_validation_service.py:295` |
| `he` | hề, hệ | 2 | `app/chat/follow_up_resolver.py:44`, `app/chat/follow_up_resolver.py:505` |
| `hon` | hôn, hơn | 2 | `app/services/grounded_answer_service.py:10311`, `app/services/grounded_answer_service.py:10309` |
| `huong` | huống, hướng, hưởng | 2 | `app/services/grounded_answer_service.py:10071`, `app/services/grounded_answer_service.py:10306` |
| `khoan` | khoán, khoản | 2 | `app/services/claim_evidence_validation_service.py:1802`, `app/services/grounded_answer_service.py:4957` |
| `loi` | lõi, lối, lỗi, lội, lời, lợi | 2 | `app/services/grounded_answer_service.py:10739`, `app/services/grounded_answer_service.py:10790` |
| `nha` | nhà, nhá, nhã | 2 | `app/services/claim_evidence_validation_service.py:3116`, `app/services/grounded_answer_service.py:10074` |
| `quan` | quan, quán, quân, quản, quần, quận | 2 | `app/services/claim_evidence_validation_service.py:436`, `app/services/claim_evidence_validation_service.py:2826` |
| `quy` | quy, quý, quỳ, quỹ | 2 | `app/services/grounded_answer_service.py:3590`, `app/services/grounded_answer_service.py:5602` |
| `ra` | rà, rã | 2 | `app/chat/context_builder.py:715`, `app/retrieval/keyword_repository.py:87` |
| `su` | sư, sứ, sử, sự | 2 | `app/services/claim_evidence_validation_service.py:194`, `app/services/claim_evidence_validation_service.py:316` |
| `tat` | tất, tật, tắt | 2 | `app/services/claim_evidence_validation_service.py:1090`, `app/services/grounded_answer_service.py:280` |
| `thieu` | thiếu, thiểu, thiệu | 2 | `app/services/claim_evidence_validation_service.py:478`, `app/services/grounded_answer_service.py:465` |
| `thuc` | thúc, thục, thức, thực | 2 | `app/services/grounded_answer_service.py:10738`, `app/services/grounded_answer_service.py:10786` |
| `tra` | trá, trã, trả | 2 | `app/retrieval/question_analysis.py:447`, `app/services/grounded_answer_service.py:6507` |
| `trung` | trùng, trưng | 2 | `app/retrieval/reranker.py:230`, `app/services/grounded_answer_service.py:423` |
| `truong` | trương, trường, trưởng | 2 | `app/services/grounded_answer_service.py:464`, `app/services/grounded_answer_service.py:6446` |
| `va` | và, vá, vã | 2 | `app/chat/context_builder.py:661`, `app/services/grounded_answer_service.py:5608` |
| `voi` | vôi, vội, với | 2 | `app/retrieval/structured.py:79`, `app/services/grounded_answer_service.py:10457` |
| `bi` | bí, bị | 1 | `app/services/grounded_answer_service.py:305` |
| `chu` | chú, chủ, chứ, chữ | 1 | `app/retrieval/structured.py:814` |
| `cuoi` | cuối, cưới | 1 | `app/services/grounded_answer_service.py:5093` |
| `dem` | đêm, đếm | 1 | `app/services/grounded_answer_service.py:10352` |
| `dien` | diễn, diện, điền, điện | 1 | `app/chat/context_builder.py:714` |
| `dinh` | dính, đinh, đình, đính, đỉnh, định | 1 | `app/services/grounded_answer_service.py:3591` |
| `doi` | dõi, dồi, đòi, đôi, đối, đổi, đội, đời, đợi | 1 | `app/services/claim_evidence_validation_service.py:319` |
| `don` | dọn, dồn, đón, đơn | 1 | `app/services/claim_evidence_validation_service.py:186` |
| `gop` | góp, gộp | 1 | `app/retrieval/leave_relations.py:18` |
| `ha` | hà, há, hã, hạ, hả | 1 | `app/services/grounded_answer_service.py:7742` |
| `hien` | hiển, hiện | 1 | `app/services/grounded_answer_service.py:226` |
| `ke` | kê, kế, kể, kệ | 1 | `app/services/grounded_answer_service.py:394` |
| `lap` | lập, lắp, lặp | 1 | `app/services/grounded_answer_service.py:6463` |
| `nhap` | nháp, nhập | 1 | `app/services/grounded_answer_service.py:7860` |
| `nhat` | nhất, nhật | 1 | `app/retrieval/structured.py:814` |
| `phat` | phát, phạt | 1 | `app/services/claim_evidence_validation_service.py:324` |
| `san` | sản, sẵn | 1 | `app/services/grounded_answer_service.py:458` |
| `se` | sẻ, sẽ | 1 | `app/services/claim_evidence_validation_service.py:321` |
| `tan` | tan, tán, tân, tăn, tấn, tần, tận | 1 | `app/services/claim_evidence_validation_service.py:325` |
| `than` | thần, thắn | 1 | `app/services/grounded_answer_service.py:8998` |
| `thu` | thu, thú, thư, thủ, thứ, thử | 1 | `app/services/grounded_answer_service.py:411` |
| `tinh` | tình, tính, tỉnh | 1 | `app/services/grounded_answer_service.py:6697` |
| `trang` | trạng, trắng | 1 | `app/services/grounded_answer_service.py:3154` |
| `vi` | vì, ví, vị | 1 | `app/services/claim_evidence_validation_service.py:202` |

## Toàn bộ cue theo file

### `app/chat/context_builder.py` (112)

| Dòng | Cue | Từ có thể va chạm |
|---:|---|---|
| 45 | `bao` | bao: bao, báo, bão, bảo |
| 45 | `nhieu` | nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 45 | `cua` | cua: của, cửa |
| 45 | `duoc` | duoc: dược, được |
| 46 | `moi` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời |
| 46 | `tat ca` | tat: tất, tật, tắt; ca: cá, cã, cả, cầ |
| 46 | `deu` | - |
| 48 | `thay doi` | doi: dõi, dồi, đòi, đôi, đối, đổi, đội, đời, đợi |
| 52 | `tang` | tang: tang, tăng, tảng, tầng, tặng |
| 53 | `them` | - |
| 54 | `giam` | giam: giám, giảm |
| 56 | `dieu chinh` | chinh: chính, chỉnh |
| 150 | `max_tokens must be greater than zero.` | than: thần, thắn |
| 377 | `cham cong` | cham: chăm, chạm, chấm, chậm; cong: cong, công, cổng, cộng |
| 382 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 382 | `tu xa` | tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 386 | `lam viec tu xa` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 389 | `nghia vu cham cong` | nghia: nghiá, nghĩa; cham: chăm, chạm, chấm, chậm; cong: cong, công, cổng, cộng |
| 396 | `nhu khi lam tai van phong` | lam: lam, làm, lâm, lạm, lắm; tai: tai, tài, tái, tại, tải; van: văn, vấn, vẫn, vận; phong: phong, phòng, phóng, phỏng |
| 400 | `lam viec tu xa` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 407 | `quen` | - |
| 408 | `cham cong` | cham: chăm, chạm, chấm, chậm; cong: cong, công, cổng, cộng |
| 413 | `quen` | - |
| 413 | `cham cong` | cham: chăm, chạm, chấm, chậm; cong: cong, công, cổng, cộng |
| 417 | `yeu cau` | yeu: yêu, yếu; cau: câu, cấu, cầu |
| 418 | `gui` | - |
| 419 | `\b\d+\s+(?:ngay\|working days?\|business days?)\b` | ngay: ngay, ngày, ngây |
| 457 | `linh vuc hoat dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 467 | `nhan su` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; su: sư, sứ, sử, sự |
| 467 | `nhan vien` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; vien: viên, viền, viễn, viện |
| 471 | `quy mo nhan su` | quy: quy, quý, quỳ, quỹ; mo: mô, mơ, mỏ, mổ, mộ, mở; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; su: sư, sứ, sử, sự |
| 479 | `van phong` | van: văn, vấn, vẫn, vận; phong: phong, phòng, phóng, phỏng |
| 480 | `o dau` | dau: dấu, dầu, đau, đâu, đầu |
| 480 | `tai dau` | tai: tai, tài, tái, tại, tải; dau: dấu, dầu, đau, đâu, đầu |
| 485 | `^(?:van phong\|offices?)\s+((?:thanh pho\|tinh\|city\|province\|dia chi\|address)\b.+)` | van: văn, vấn, vẫn, vận; phong: phong, phòng, phóng, phỏng; pho: phó, phố; tinh: tình, tính, tỉnh; dia: đĩa, địa; chi: chi, chí, chỉ, chị |
| 660 | ` neu` | neu: nêu, nếu, nệu |
| 661 | ` va` | va: và, vá, vã |
| 662 | ` hoac` | - |
| 663 | ` cua` | cua: của, cửa |
| 664 | ` de` | de: dễ, đe, đè, đẻ, đề, để |
| 670 | ` to` | to: tố, tổ, tờ |
| 691 | `ngay` | ngay: ngay, ngày, ngây |
| 691 | `nao` | - |
| 691 | `thuong` | thuong: thương, thường, thưởng |
| 713 | `thuong` | thuong: thương, thường, thưởng |
| 714 | `dien` | dien: diễn, diện, điền, điện |
| 715 | `ra` | ra: rà, rã |
| 716 | `khoang` | - |
| 717 | `thoi` | - |
| 718 | `gian` | - |
| 719 | `nao` | - |
| 756 | `danh gia` | danh: dành, đánh; gia: gia, già, giá, giã, giả |
| 758 | `phe duyet` | - |
| 760 | `thong bao` | thong: thông, thống; bao: bao, báo, bão, bảo |
| 762 | `hieu luc` | hieu: hiểu, hiệu; luc: lúc, lục, lực |
| 776 | `ngay thuong` | ngay: ngay, ngày, ngây; thuong: thương, thường, thưởng |
| 776 | `ngay lam viec binh thuong` | ngay: ngay, ngày, ngây; lam: lam, làm, lâm, lạm, lắm; thuong: thương, thường, thưởng |
| 777 | `ngay nghi hang tuan` | ngay: ngay, ngày, ngây; nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; tuan: tuân, tuấn, tuần |
| 777 | `chu nhat` | chu: chú, chủ, chứ, chữ; nhat: nhất, nhật |
| 778 | `ngay le` | ngay: ngay, ngày, ngây; le: le, lê, lẻ, lẽ, lễ, lệ |
| 778 | `ngay nghi co huong luong` | ngay: ngay, ngày, ngây; nghi: nghi, nghĩ, nghỉ, nghị; co: có, cô, cơ, cố, cổ, cờ, cỡ; huong: huống, hướng, hưởng; luong: luồng, lương, lường, lượng |
| 778 | `tet` | - |
| 779 | `lam them vao ban dem` | lam: lam, làm, lâm, lạm, lắm; ban: ban, bàn, bán, bạn, bản, bận; dem: đêm, đếm |
| 780 | `lam viec ban dem` | lam: lam, làm, lâm, lạm, lắm; ban: ban, bàn, bán, bạn, bản, bận; dem: đêm, đếm |
| 784 | `duoc tra them` | duoc: dược, được; tra: trá, trã, trả |
| 785 | `ngoai tien ot` | ngoai: ngoài, ngoại; tien: tiên, tiến, tiền, tiện |
| 807 | `lam them` | lam: lam, làm, lâm, lạm, lắm |
| 931 | `bao nhieu` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 936 | `tat ca` | tat: tất, tật, tắt; ca: cá, cã, cả, cầ |
| 936 | `deu` | - |
| 942 | `\bmoi\s+(?!ngay\b\|tuan\b\|thang\b\|nam\b\|lan\b\|ky\b\|day\b\|week\b\|month\b\|year\b)\w+` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời; ngay: ngay, ngày, ngây; tuan: tuân, tuấn, tuần; thang: thang, tháng, thăng, thắng, thẳng; nam: nam, năm, nấm, nắm, nằm; lan: lan, lân, lãn, lần, lẫn, lặn; ky: ký, kỳ, kỵ, kỷ, kỹ; day: đây, đầy |
| 968 | `bao lau` | bao: bao, báo, bão, bảo |
| 969 | `chua du` | chua: chưa, chứa, chữa; du: du, dù, dư, dụ, dữ, dự, đu, đủ |
| 970 | `it nhat` | nhat: nhất, nhật |
| 971 | `khong qua` | qua: quá, quả |
| 972 | `toi da` | toi: tôi, tỏi, tối, tội, tới; da: dá, đa, đà, đã |
| 973 | `toi thieu` | toi: tôi, tỏi, tối, tội, tới; thieu: thiếu, thiểu, thiệu |
| 974 | `truoc bao` | bao: bao, báo, bão, bảo |
| 975 | `trong vong` | trong: trọng, trống; vong: vòng, vọng |
| 976 | `ke tu` | ke: kê, kế, kể, kệ; tu: tu, tư, tủ, tứ, từ, tử, tự |
| 977 | `sau ` | sau: sau, sáu, sâu |
| 984 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 985 | `lam viec tu xa` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 1000 | ` la ai` | la: là, lá, lã |
| 1001 | ` ai` | - |
| 1002 | ` ten gi` | - |
| 1003 | ` ten` | - |
| 1004 | ` what is the name` | the: thẻ, thế, thể |
| 1007 | ` hay xac nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 1008 | ` vui long xac nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 1011 | ` confirm that` | that: thất, thật |
| 1012 | ` dung khong` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 1013 | ` phai khong` | - |
| 1014 | `co phai` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 1015 | ` khong` | - |
| 1016 | ` khong?` | - |
| 1056 | `cua` | cua: của, cửa |
| 1058 | `gi` | - |
| 1059 | `nguoi` | - |
| 1060 | `phu` | phu: phù, phụ |
| 1061 | `ten` | - |
| 1062 | `trach` | - |
| 1140 | `phep` | - |
| 1140 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 1142 | `dieu kien` | kien: kiến, kiện |
| 1143 | `doi tuong` | doi: dõi, dồi, đòi, đôi, đối, đổi, đội, đời, đợi; tuong: tương, tưởng, tượng |
| 1144 | `chua thanh nien` | chua: chưa, chứa, chữa |
| 1145 | `khuyet tat` | tat: tất, tật, tắt |
| 1146 | `nang nhoc` | nang: nâng, năng, nẵng, nặng |
| 1147 | `doc hai` | doc: đọc, đốc, độc; hai: hai, hài, hại, hải |
| 1148 | `nguy hiem` | - |
| 1149 | `dac biet` | biet: biết, biệt |

### `app/chat/follow_up_resolver.py` (68)

| Dòng | Cue | Từ có thể va chạm |
|---:|---|---|
| 12 | `con ` | con: con, còn, cơn, cồn |
| 13 | `the con ` | the: thẻ, thế, thể; con: con, còn, cơn, cồn |
| 14 | `vay con ` | con: con, còn, cơn, cồn |
| 15 | `vay ` | - |
| 16 | `neu vay ` | neu: nêu, nếu, nệu |
| 17 | `truong hop do ` | truong: trương, trường, trưởng; hop: họp, hợp; do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 18 | `truong hop nay ` | truong: trương, trường, trưởng; hop: họp, hợp |
| 19 | `nguoi do ` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 20 | `nguoi nay ` | - |
| 26 | `does it ` | - |
| 27 | `is it ` | - |
| 29 | `do they ` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 33 | `thi sao` | thi: thi, thì, thí, thị |
| 34 | `truong hop nay` | truong: trương, trường, trưởng; hop: họp, hợp |
| 35 | `truong hop do` | truong: trương, trường, trưởng; hop: họp, hợp; do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 36 | `nguoi nay` | - |
| 37 | `nguoi do` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 38 | `nhu vay` | - |
| 39 | `cai do` | cai: cài, cái, cải; do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 40 | `che do do` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 41 | `che do nay` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 42 | ` no ` | no: nó, nợ |
| 43 | ` ho ` | ho: họ, hồ, hỗ, hộ, hợ |
| 44 | ` he ` | he: hề, hệ |
| 49 | ` them ` | - |
| 50 | ` it ` | - |
| 54 | `the con ` | the: thẻ, thế, thể; con: con, còn, cơn, cồn |
| 55 | `vay con ` | con: con, còn, cơn, cồn |
| 56 | `con ` | con: con, còn, cơn, cồn |
| 63 | ` thi nhu the nao` | thi: thi, thì, thí, thị; the: thẻ, thế, thể |
| 64 | ` thi sao` | thi: thi, thì, thí, thị |
| 68 | `sau ` | sau: sau, sáu, sâu |
| 69 | `neu ` | neu: nêu, nếu, nệu |
| 71 | `trong truong hop ` | trong: trọng, trống; truong: trương, trường, trưởng; hop: họp, hợp |
| 81 | ` la ai` | la: là, lá, lã |
| 82 | ` la gi` | la: là, lá, lã |
| 83 | ` duoc quy dinh nhu the nao` | duoc: dược, được; quy: quy, quý, quỳ, quỹ; dinh: dính, đinh, đình, đính, đỉnh, định; the: thẻ, thế, thể |
| 85 | ` bao nhieu` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 204 | `che do ` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 329 | `\s+-\s+(?=(?:sau\|neu\|khi\|trong truong hop\|after\|if\|when\|for)\b)` | sau: sau, sáu, sâu; neu: nêu, nếu, nệu; trong: trọng, trống; truong: trương, trường, trưởng; hop: họp, hợp |
| 336 | `\s+(?:sau\|neu\|khi\|trong truong hop\|after\|if\|when\|for)\b.*\bthay doi nhu the nao$` | sau: sau, sáu, sâu; neu: nêu, nếu, nệu; trong: trọng, trống; truong: trương, trường, trưởng; hop: họp, hợp; doi: dõi, dồi, đòi, đôi, đối, đổi, đội, đời, đợi; the: thẻ, thế, thể |
| 361 | `bao nhieu` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 362 | `la ai` | la: là, lá, lã |
| 363 | `la gi` | la: là, lá, lã |
| 364 | `nhu the nao` | the: thẻ, thế, thể |
| 380 | `con ` | con: con, còn, cơn, cồn |
| 380 | `the con ` | the: thẻ, thế, thể; con: con, còn, cơn, cồn |
| 380 | `vay con ` | con: con, còn, cơn, cồn |
| 380 | `vay ` | - |
| 398 | `han muc` | han: hàn, hán, hân, hạn, hẳn; muc: múc, mục, mức, mực |
| 399 | `phu cap` | phu: phù, phụ; cap: cấp, cập, cặp |
| 400 | `tro cap` | tro: trò, trỏ, trở, trợ; cap: cấp, cập, cặp |
| 401 | `muc ho tro` | muc: múc, mục, mức, mực; ho: họ, hồ, hỗ, hộ, hợ; tro: trò, trỏ, trở, trợ |
| 402 | `so ngay` | so: so, sơ, số, sổ, sở, sợ; ngay: ngay, ngày, ngây |
| 403 | `thoi luong` | luong: luồng, lương, lường, lượng |
| 404 | `ty le` | le: le, lê, lẻ, lẽ, lễ, lệ |
| 436 | ` co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 437 | ` co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 497 | `che do nay` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 498 | `che do do` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 499 | `nguoi nay` | - |
| 500 | `nguoi do` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 501 | `that person` | that: thất, thật |
| 503 | `no` | no: nó, nợ |
| 504 | `ho` | ho: họ, hồ, hỗ, hộ, hợ |
| 505 | `he` | he: hề, hệ |
| 510 | `them` | - |
| 511 | `it` | - |

### `app/chat/prompt_builder.py` (43)

| Dòng | Cue | Từ có thể va chạm |
|---:|---|---|
| 24 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 25 | `vien` | vien: viên, viền, viễn, viện |
| 26 | `nguoi` | - |
| 27 | `cong` | cong: cong, công, cổng, cộng |
| 28 | `ty` | - |
| 29 | `duoc` | duoc: dược, được |
| 30 | `khong` | - |
| 31 | `phai` | - |
| 33 | `cua` | cua: của, cửa |
| 34 | `cho` | cho: cho, chó, chỗ, chờ, chở, chợ |
| 35 | `yeu` | yeu: yêu, yếu |
| 36 | `cau` | cau: câu, cấu, cầu |
| 46 | `bao` | bao: bao, báo, bão, bảo |
| 47 | `nhieu` | nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 48 | `muc` | muc: múc, mục, mức, mực |
| 49 | `toi` | toi: tôi, tỏi, tối, tội, tới |
| 50 | `da` | da: dá, đa, đà, đã |
| 51 | `moi` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời |
| 52 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 53 | `ngay` | ngay: ngay, ngày, ngây |
| 54 | `gio` | gio: gió, giỗ, giờ |
| 55 | `tuan` | tuan: tuân, tuấn, tuần |
| 56 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 57 | `phan` | phan: phan, phán, phân, phản, phần, phận |
| 58 | `tram` | tram: trám, trăm, trạm |
| 66 | `day` | day: đây, đầy |
| 419 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 419 | `lam viec tu xa` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 430 | `ket noi an toan` | noi: nói, nơi, nối, nội; an: án, ăn, ản, ấn; toan: toàn, toán |
| 431 | `xac thuc nhieu lop` | thuc: thúc, thục, thức, thực; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu; lop: lốp, lớp |
| 432 | `thiet bi duoc phe duyet` | thiet: thiết, thiệt; bi: bí, bị; duoc: dược, được |
| 433 | `thiet bi duoc quan ly` | thiet: thiết, thiệt; bi: bí, bị; duoc: dược, được; quan: quan, quán, quân, quản, quần, quận |
| 434 | `khong de nguoi khong co tham quyen` | de: dễ, đe, đè, đẻ, đề, để; co: có, cô, cơ, cố, cổ, cờ, cỡ; tham: thâm, thẩm |
| 435 | `khong lam viec voi du lieu mat` | lam: lam, làm, lâm, lạm, lắm; voi: vôi, vội, với; du: du, dù, dư, dụ, dữ, dự, đu, đủ; mat: mát, mất, mật, mắt, mặt |
| 480 | `bao mat` | bao: bao, báo, bão, bảo; mat: mát, mất, mật, mắt, mặt |
| 482 | `yeu cau` | yeu: yêu, yếu; cau: câu, cấu, cầu |
| 482 | `bao dam` | bao: bao, báo, bão, bảo; dam: đám, đảm |
| 482 | `can tuan thu` | can: cân, căn, cần, cận; tuan: tuân, tuấn, tuần; thu: thu, thú, thư, thủ, thứ, thử |
| 482 | `tuan thu` | tuan: tuân, tuấn, tuần; thu: thu, thú, thư, thủ, thứ, thử |
| 485 | `an toan` | an: án, ăn, ản, ấn; toan: toàn, toán |
| 486 | `bao dam` | bao: bao, báo, bão, bảo; dam: đám, đảm |
| 486 | `dam bao` | dam: đám, đảm; bao: bao, báo, bão, bảo |
| 486 | `gi` | - |

### `app/citations/evidence.py` (16)

| Dòng | Cue | Từ có thể va chạm |
|---:|---|---|
| 15 | `thay the` | the: thẻ, thế, thể |
| 23 | `bat buoc` | bat: bất, bật, bắt; buoc: buộc, bước |
| 24 | `theo luat` | - |
| 31 | `bo sung` | bo: bỏ, bố, bổ, bộ |
| 32 | `bo tro` | bo: bỏ, bố, bổ, bộ; tro: trò, trỏ, trở, trợ |
| 33 | `them` | - |
| 34 | `tang cuong` | tang: tang, tăng, tảng, tầng, tặng |
| 43 | `khong` | - |
| 44 | `thay` | - |
| 45 | `the` | the: thẻ, thế, thể |
| 51 | `bat` | bat: bất, bật, bắt |
| 52 | `buoc` | buoc: buộc, bước |
| 55 | `bao` | bao: bao, báo, bão, bảo |
| 56 | `hiem` | - |
| 57 | `suc` | - |
| 58 | `khoe` | - |

### `app/retrieval/authority.py` (5)

| Dòng | Cue | Từ có thể va chạm |
|---:|---|---|
| 9 | `lich su` | su: sư, sứ, sử, sự |
| 10 | `phien ban cu` | ban: ban, bàn, bán, bạn, bản, bận; cu: cù, cũ, cụ, cứ |
| 11 | `version cu` | cu: cù, cũ, cụ, cứ |
| 16 | `truoc day` | day: đây, đầy |
| 17 | `nam ` | nam: nam, năm, nấm, nắm, nằm |

### `app/retrieval/evidence_quality.py` (31)

| Dòng | Cue | Từ có thể va chạm |
|---:|---|---|
| 16 | `cau hoi goi y` | cau: câu, cấu, cầu; hoi: hỏi, hồi, hội; goi: gói, gọi, gợi |
| 17 | `cau hoi kiem thu` | cau: câu, cấu, cầu; hoi: hỏi, hồi, hội; kiem: kiếm, kiểm; thu: thu, thú, thư, thủ, thứ, thử |
| 18 | `cau hoi tham khao` | cau: câu, cấu, cầu; hoi: hỏi, hồi, hội; tham: thâm, thẩm |
| 19 | `cau hoi mau` | cau: câu, cấu, cầu; hoi: hỏi, hồi, hội; mau: mâu, mẫu |
| 20 | `tinh huong mau` | tinh: tình, tính, tỉnh; huong: huống, hướng, hưởng; mau: mâu, mẫu |
| 21 | `ky vong cau tra loi` | ky: ký, kỳ, kỵ, kỷ, kỹ; vong: vòng, vọng; cau: câu, cấu, cầu; tra: trá, trã, trả; loi: lõi, lối, lỗi, lội, lời, lợi |
| 22 | `cau tra loi ai` | cau: câu, cấu, cầu; tra: trá, trã, trả; loi: lõi, lối, lỗi, lội, lời, lợi |
| 26 | `expected ai answer` | - |
| 30 | `kiem thu rag` | kiem: kiếm, kiểm; thu: thu, thú, thư, thủ, thứ, thử |
| 32 | `no-answer test` | no: nó, nợ |
| 36 | `cau hoi kiem thu` | cau: câu, cấu, cầu; hoi: hỏi, hồi, hội; kiem: kiếm, kiểm; thu: thu, thú, thư, thủ, thứ, thử |
| 37 | `ky vong cau tra loi` | ky: ký, kỳ, kỵ, kỷ, kỹ; vong: vòng, vọng; cau: câu, cấu, cầu; tra: trá, trã, trả; loi: lõi, lối, lỗi, lội, lời, lợi |
| 38 | `cau tra loi ai` | cau: câu, cấu, cầu; tra: trá, trã, trả; loi: lõi, lối, lỗi, lội, lời, lợi |
| 40 | `expected ai answer` | - |
| 41 | `kiem thu rag` | kiem: kiếm, kiểm; thu: thu, thú, thư, thủ, thứ, thử |
| 43 | `no-answer test` | no: nó, nợ |
| 47 | `muc luc` | muc: múc, mục, mức, mực; luc: lúc, lục, lực |
| 48 | `danh muc tai lieu` | danh: dành, đánh; muc: múc, mục, mức, mực; tai: tai, tài, tái, tại, tải |
| 49 | `tai lieu lien quan` | tai: tai, tài, tái, tại, tải; lien: liên, liền; quan: quan, quán, quân, quản, quần, quận |
| 50 | `lich su phien ban` | su: sư, sứ, sử, sự; ban: ban, bàn, bán, bạn, bản, bận |
| 51 | `kiem soat tai lieu` | kiem: kiếm, kiểm; tai: tai, tài, tái, tại, tải |
| 59 | `tra loi:` | tra: trá, trã, trả; loi: lõi, lối, lỗi, lội, lời, lợi |
| 60 | `dap an:` | an: án, ăn, ản, ấn |
| 61 | `la ` | la: là, lá, lã |
| 64 | `duoc ` | duoc: dược, được |
| 65 | `khong duoc ` | duoc: dược, được |
| 66 | `khong co ` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 67 | `khong quy dinh` | quy: quy, quý, quỳ, quỹ; dinh: dính, đinh, đình, đính, đỉnh, định |
| 70 | `(?<!\d)\d+(?:[.,]\d+)?\s*(?:%\|dong\|trieu\|ngay\|gio\|tuan\|thang\|nam\|days?\|hours?\|weeks?\|months?\|years?)\b` | dong: dong, dòng, đóng, đông, đống, đồng, động; ngay: ngay, ngày, ngây; gio: gió, giỗ, giờ; tuan: tuân, tuấn, tuần; thang: thang, tháng, thăng, thắng, thẳng; nam: nam, năm, nấm, nắm, nằm |
| 73 | `\bcau hoi kiem\s+(?:\d+\s+)?thu rag\b` | cau: câu, cấu, cầu; hoi: hỏi, hồi, hội; kiem: kiếm, kiểm; thu: thu, thú, thư, thủ, thứ, thử |
| 74 | `\bky vong\s+cau tra loi\b` | ky: ký, kỳ, kỵ, kỷ, kỹ; vong: vòng, vọng; cau: câu, cấu, cầu; tra: trá, trã, trả; loi: lõi, lối, lỗi, lội, lời, lợi |

### `app/retrieval/keyword_repository.py` (26)

| Dòng | Cue | Từ có thể va chạm |
|---:|---|---|
| 26 | `bao` | bao: bao, báo, bão, bảo |
| 27 | `cap` | cap: cấp, cập, cặp |
| 28 | `chinh` | chinh: chính, chỉnh |
| 29 | `dieu` | - |
| 30 | `duoc` | duoc: dược, được |
| 31 | `gio` | gio: gió, giỗ, giờ |
| 32 | `han` | han: hàn, hán, hân, hạn, hẳn |
| 33 | `khong` | - |
| 34 | `luong` | luong: luồng, lương, lường, lượng |
| 35 | `muc` | muc: múc, mục, mức, mực |
| 36 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 37 | `ngay` | ngay: ngay, ngày, ngây |
| 38 | `nghi` | nghi: nghi, nghĩ, nghỉ, nghị |
| 39 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 40 | `phu` | phu: phù, phụ |
| 41 | `sach` | sach: sách, sạch |
| 42 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 43 | `tham` | tham: thâm, thẩm |
| 44 | `trua` | - |
| 45 | `tuan` | tuan: tuân, tuấn, tuần |
| 46 | `vien` | vien: viên, viền, viễn, viện |
| 51 | `ai` | - |
| 53 | `bao` | bao: bao, báo, bão, bảo |
| 60 | `cho` | cho: cho, chó, chỗ, chờ, chở, chợ |
| 87 | `ra` | ra: rà, rã |
| 92 | `trong` | trong: trọng, trống |

### `app/retrieval/leave_relations.py` (31)

| Dòng | Cue | Từ có thể va chạm |
|---:|---|---|
| 8 | `phep` | - |
| 8 | `nghi hang nam` | nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; nam: nam, năm, nấm, nắm, nằm |
| 9 | `nghi hang nam` | nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; nam: nam, năm, nấm, nắm, nằm |
| 9 | `phep nam` | nam: nam, năm, nấm, nắm, nằm |
| 10 | `dieu kien binh thuong` | kien: kiến, kiện; thuong: thương, thường, thưởng |
| 12 | `chua thanh nien` | chua: chưa, chứa, chữa |
| 13 | `khuyet tat` | tat: tất, tật, tắt |
| 14 | `nang nhoc` | nang: nâng, năng, nẵng, nặng |
| 15 | `doc hai` | doc: đọc, đốc, độc; hai: hai, hài, hại, hải |
| 16 | `nguy hiem` | - |
| 18 | `tang them` | tang: tang, tăng, tảng, tầng, tặng |
| 18 | `tham nien` | tham: thâm, thẩm |
| 18 | `dang ky` | dang: dang, dạng, đang, đáng, đăng, đằng, đẳng; ky: ký, kỳ, kỵ, kỷ, kỹ |
| 18 | `truoc it nhat` | nhat: nhất, nhật |
| 18 | `gop` | gop: góp, gộp |
| 45 | `binh thuong` | thuong: thương, thường, thưởng |
| 46 | `bao nhieu` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 46 | `may ngay` | may: may, mày, máy, mây, mấy; ngay: ngay, ngày, ngây |
| 50 | `them` | - |
| 50 | `tang` | tang: tang, tăng, tảng, tầng, tặng |
| 54 | `tham nien` | tham: thâm, thẩm |
| 54 | `du` | du: du, dù, dư, dụ, dữ, dự, đu, đủ |
| 54 | `quy tac` | quy: quy, quý, quỳ, quỹ; tac: tác, tắc |
| 83 | `\b(?:ngay(?:\s+lam\s+viec)?\|days?)\s*/\s*(?:nam\|year)\b` | ngay: ngay, ngày, ngây; lam: lam, làm, lâm, lạm, lắm; nam: nam, năm, nấm, nắm, nằm |
| 109 | `cu du` | cu: cù, cũ, cụ, cứ; du: du, dù, dư, dụ, dữ, dự, đu, đủ |
| 109 | `tham nien` | tham: thâm, thẩm |
| 109 | `nghi hang nam` | nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; nam: nam, năm, nấm, nắm, nằm |
| 110 | `khong luong` | luong: luồng, lương, lường, lượng |
| 110 | `om dau` | dau: dấu, dầu, đau, đâu, đầu |
| 110 | `thai san` | thai: thái, thải; san: sản, sẵn |
| 124 | `cu du` | cu: cù, cũ, cụ, cứ; du: du, dù, dư, dụ, dữ, dự, đu, đủ |

### `app/retrieval/question_analysis.py` (177)

| Dòng | Cue | Từ có thể va chạm |
|---:|---|---|
| 83 | `bao nhieu` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 84 | `khong` | - |
| 85 | `khong` | - |
| 86 | `duoc` | duoc: dược, được |
| 87 | `cong ty` | cong: cong, công, cổng, cộng |
| 88 | `nhan vien` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; vien: viên, viền, viễn, viện |
| 89 | `tieng` | - |
| 89 | `gio` | gio: gió, giỗ, giờ |
| 123 | `su co` | su: sư, sứ, sử, sự; co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 126 | `ma nguon` | ma: ma, mà, má, mã, mạ, mả |
| 127 | `kho ma nguon` | ma: ma, mà, má, mã, mạ, mả |
| 128 | `ho tro` | ho: họ, hồ, hỗ, hộ, hợ; tro: trò, trỏ, trở, trợ |
| 128 | `tro cap` | tro: trò, trỏ, trở, trợ; cap: cấp, cập, cặp |
| 128 | `phuc loi` | phuc: phúc, phục, phức; loi: lõi, lối, lỗi, lội, lời, lợi |
| 131 | `\bco con\b` | co: có, cô, cơ, cố, cổ, cờ, cỡ; con: con, còn, cơn, cồn |
| 131 | `sinh con` | con: con, còn, cơn, cồn |
| 135 | `nghi phep` | nghi: nghi, nghĩ, nghỉ, nghị |
| 136 | `on call` | - |
| 137 | `on-call` | - |
| 140 | `phu cap` | phu: phù, phụ; cap: cấp, cập, cặp |
| 141 | `tro cap` | tro: trò, trỏ, trở, trợ; cap: cấp, cập, cặp |
| 142 | `bao hiem` | bao: bao, báo, bão, bảo |
| 145 | `\btoi\b` | toi: tôi, tỏi, tối, tội, tới |
| 145 | `nhan vien` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; vien: viên, viền, viễn, viện |
| 146 | `\bma phai\b` | ma: ma, mà, má, mã, mạ, mả |
| 146 | `nhung phai` | nhung: nhưng, những |
| 148 | `\bcan tuan thu bao mat (?:nao\|gi)\b` | can: cân, căn, cần, cận; tuan: tuân, tuấn, tuần; thu: thu, thú, thư, thủ, thứ, thử; bao: bao, báo, bão, bảo; mat: mát, mất, mật, mắt, mặt |
| 149 | `yeu cau bao mat gi` | yeu: yêu, yếu; cau: câu, cấu, cầu; bao: bao, báo, bão, bảo; mat: mát, mất, mật, mắt, mặt |
| 153 | `\bphai (?:bao dam\|dam bao) an toan gi\b` | bao: bao, báo, bão, bảo; dam: đám, đảm; an: án, ăn, ản, ấn; toan: toàn, toán |
| 154 | `yeu cau bao mat gi` | yeu: yêu, yếu; cau: câu, cấu, cầu; bao: bao, báo, bão, bảo; mat: mát, mất, mật, mắt, mặt |
| 158 | ` cham cong dieu chinh` | cham: chăm, chạm, chấm, chậm; cong: cong, công, cổng, cộng; chinh: chính, chỉnh |
| 159 | `nam vien` | nam: nam, năm, nấm, nắm, nằm; vien: viên, viền, viễn, viện |
| 160 | `\bnam vien\b` | nam: nam, năm, nấm, nắm, nằm; vien: viên, viền, viễn, viện |
| 160 | `noi tru` | noi: nói, nơi, nối, nội; tru: trú, trừ, trữ |
| 161 | `yeu cau bao mat gi` | yeu: yêu, yếu; cau: câu, cấu, cầu; bao: bao, báo, bão, bảo; mat: mát, mất, mật, mắt, mặt |
| 162 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 162 | `lam viec tu xa` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 164 | `lam viec tu xa yeu cau bao mat` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ; yeu: yêu, yếu; cau: câu, cấu, cầu; bao: bao, báo, bão, bảo; mat: mát, mất, mật, mắt, mặt |
| 173 | `bao nhieu` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 180 | `phan tram` | phan: phan, phán, phân, phản, phần, phận; tram: trám, trăm, trạm |
| 196 | `bat dau` | bat: bất, bật, bắt; dau: dấu, dầu, đau, đâu, đầu |
| 196 | `ket thuc` | thuc: thúc, thục, thức, thực |
| 217 | `bao nhieu` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 218 | ` may` | may: may, mày, máy, mây, mấy |
| 219 | `grade nao` | - |
| 219 | `so nao` | so: so, sơ, số, sổ, sở, sợ |
| 219 | `muc nao` | muc: múc, mục, mức, mực |
| 223 | ` muc nao` | muc: múc, mục, mức, mực |
| 224 | ` toi thieu` | toi: tôi, tỏi, tối, tội, tới; thieu: thiếu, thiểu, thiệu |
| 307 | `cong ty` | cong: cong, công, cổng, cộng |
| 307 | `doanh nghiep` | - |
| 312 | `mang gi` | mang: mạng, mảng |
| 313 | `linh vuc` | - |
| 314 | `hoat dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 317 | `what does the company do` | the: thẻ, thế, thể; do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 326 | `co ` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 326 | `co phai ` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 326 | `do ` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 326 | `can ` | can: cân, căn, cần, cận |
| 330 | `hay xac nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 331 | `vui long xac nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 334 | `confirm that` | that: thất, thật |
| 337 | ` dung khong` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 338 | ` phai khong` | - |
| 339 | ` khong` | - |
| 340 | ` khong?` | - |
| 341 | ` khong.` | - |
| 351 | `\bpublic\s+ai\b` | - |
| 352 | `\bcong\s+cu\s+ai\b` | cong: cong, công, cổng, cộng; cu: cù, cũ, cụ, cứ |
| 353 | `\bdich\s+vu\s+ai\b` | dich: dịch, đích, địch |
| 354 | `\bai\s+tao\b` | - |
| 355 | `\bket\s+qua\s+ai\b` | qua: quá, quả |
| 359 | ` la ai` | la: là, lá, lã |
| 359 | `ai la ` | la: là, lá, lã |
| 369 | ` duyet ` | - |
| 370 | ` phe duyet ` | - |
| 371 | ` xac nhan ` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 377 | ` ten gi` | - |
| 377 | ` ten la gi` | la: là, lá, lã |
| 381 | ` la ai` | la: là, lá, lã |
| 382 | ` ai` | - |
| 383 | ` ai ` | - |
| 386 | ` ten gi` | - |
| 387 | ` ten la gi` | la: là, lá, lã |
| 397 | `\b(?:bo phan\|phong ban\|don vi\|nhom) nao\b` | bo: bỏ, bố, bổ, bộ; phan: phan, phán, phân, phản, phần, phận; phong: phong, phòng, phóng, phỏng; ban: ban, bàn, bán, bạn, bản, bận; don: dọn, dồn, đón, đơn; vi: vì, ví, vị |
| 406 | ` nam nao` | nam: nam, năm, nấm, nắm, nằm |
| 407 | ` nam may` | nam: nam, năm, nấm, nắm, nằm; may: may, mày, máy, mây, mấy |
| 408 | ` thanh lap ` | lap: lập, lắp, lặp |
| 416 | `\bty\s+le\b` | le: le, lê, lẻ, lẽ, lễ, lệ |
| 418 | `\b(?:ot\s+bao nhieu\|bao nhieu\s+ot)\b` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 423 | ` muc ot ` | muc: múc, mục, mức, mực |
| 424 | ` ty le ot ` | le: le, lê, lẻ, lẽ, lễ, lệ |
| 425 | ` muc overtime ` | muc: múc, mục, mức, mực |
| 431 | `bao nhieu` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 433 | `cong them` | cong: cong, công, cổng, cộng |
| 433 | `tra them` | tra: trá, trã, trả |
| 434 | `lam them` | lam: lam, làm, lâm, lạm, lắm |
| 434 | `ban dem` | ban: ban, bàn, bán, bạn, bản, bận; dem: đêm, đếm |
| 437 | `toi thieu` | toi: tôi, tỏi, tối, tội, tới; thieu: thiếu, thiểu, thiệu |
| 437 | `it nhat` | nhat: nhất, nhật |
| 443 | `lam them` | lam: lam, làm, lâm, lạm, lắm |
| 445 | `ban dem` | ban: ban, bàn, bán, bạn, bản, bận; dem: đêm, đếm |
| 447 | `tra` | tra: trá, trã, trả |
| 456 | ` ngay nao` | ngay: ngay, ngày, ngây |
| 457 | ` ngay may` | ngay: ngay, ngày, ngây; may: may, mày, máy, mây, mấy |
| 458 | ` vao ngay nao` | ngay: ngay, ngày, ngây |
| 465 | ` may gio` | may: may, mày, máy, mây, mấy; gio: gió, giỗ, giờ |
| 465 | ` gio nao` | gio: gió, giỗ, giờ |
| 471 | `\btu\s+may\s+gio\s+(?:toi\|den)\s+may\s+gio\b` | tu: tu, tư, tủ, tứ, từ, tử, tự; may: may, mày, máy, mây, mấy; gio: gió, giỗ, giờ; toi: tôi, tỏi, tối, tội, tới |
| 472 | ` khoang nao` | - |
| 473 | ` khung gio` | gio: gió, giỗ, giờ |
| 474 | ` khung bat dau` | bat: bất, bật, bắt; dau: dấu, dầu, đau, đâu, đầu |
| 475 | ` khung ket thuc` | thuc: thúc, thục, thức, thực |
| 476 | ` gio cot loi` | gio: gió, giỗ, giờ; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 487 | ` bao nhieu` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 490 | ` ngay` | ngay: ngay, ngày, ngây |
| 490 | ` gio` | gio: gió, giỗ, giờ |
| 490 | ` tuan` | tuan: tuân, tuấn, tuần |
| 490 | ` thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 490 | ` nam` | nam: nam, năm, nấm, nắm, nằm |
| 491 | ` nghi` | nghi: nghi, nghĩ, nghỉ, nghị |
| 491 | ` huong luong` | huong: huống, hướng, hưởng; luong: luồng, lương, lường, lượng |
| 495 | `nam vien` | nam: nam, năm, nấm, nắm, nằm; vien: viên, viền, viễn, viện |
| 499 | ` truc` | truc: trúc, trực |
| 504 | ` phu cap ` | phu: phù, phụ; cap: cấp, cập, cặp |
| 506 | ` tro cap ` | tro: trò, trỏ, trở, trợ; cap: cấp, cập, cặp |
| 510 | ` han muc ` | han: hàn, hán, hân, hạn, hẳn; muc: múc, mục, mức, mực |
| 513 | ` bao hiem ` | bao: bao, báo, bão, bảo |
| 516 | ` nha khoa ` | nha: nhà, nhá, nhã |
| 517 | ` ngoai tru ` | ngoai: ngoài, ngoại; tru: trú, trừ, trữ |
| 518 | ` noi tru ` | noi: nói, nơi, nối, nội; tru: trú, trừ, trữ |
| 524 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 525 | `trieu` | - |
| 526 | `tien` | tien: tiên, tiến, tiền, tiện |
| 527 | `luong` | luong: luồng, lương, lường, lượng |
| 528 | `phu cap` | phu: phù, phụ; cap: cấp, cập, cặp |
| 529 | `tro cap` | tro: trò, trỏ, trở, trợ; cap: cấp, cập, cặp |
| 530 | `ho tro` | ho: họ, hồ, hỗ, hộ, hợ; tro: trò, trỏ, trở, trợ |
| 531 | `chi tra` | chi: chi, chí, chỉ, chị; tra: trá, trã, trả |
| 532 | `han muc` | han: hàn, hán, hân, hạn, hẳn; muc: múc, mục, mức, mực |
| 533 | `noi tru` | noi: nói, nơi, nối, nội; tru: trú, trừ, trữ |
| 534 | `ngoai tru` | ngoai: ngoài, ngoại; tru: trú, trừ, trữ |
| 541 | `dong y` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 542 | `\bdong y\b` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 556 | `nghi khong luong` | nghi: nghi, nghĩ, nghỉ, nghị; luong: luồng, lương, lường, lượng |
| 558 | `luong` | luong: luồng, lương, lường, lượng |
| 559 | `dai` | dai: dài, dải, đại |
| 559 | `khoang` | - |
| 575 | `khoang thoi gian` | - |
| 576 | `giai doan` | doan: đoán, đoạn |
| 577 | `chu ky` | chu: chú, chủ, chứ, chữ; ky: ký, kỳ, kỵ, kỷ, kỹ |
| 579 | `thang nao` | thang: thang, tháng, thăng, thắng, thẳng |
| 591 | `danh gia` | danh: dành, đánh; gia: gia, già, giá, giã, giả |
| 593 | `phe duyet ngan sach` | ngan: ngân, ngăn, ngắn; sach: sách, sạch |
| 595 | `hieu luc` | hieu: hiểu, hiệu; luc: lúc, lục, lực |
| 606 | ` nhan su ` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; su: sư, sứ, sử, sự |
| 607 | ` nhan vien ` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; vien: viên, viền, viễn, viện |
| 608 | ` nguoi lao dong ` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 614 | ` bao nhieu` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 621 | `\bso\s+(?:ngay\|gio\|tuan\|thang\|nam)\b` | so: so, sơ, số, sổ, sở, sợ; ngay: ngay, ngày, ngây; gio: gió, giỗ, giờ; tuan: tuân, tuấn, tuần; thang: thang, tháng, thăng, thắng, thẳng; nam: nam, năm, nấm, nắm, nằm |
| 622 | `\bmay\s+(?:ngay\|gio\|tieng\|tuan\|thang\|nam)\b` | may: may, mày, máy, mây, mấy; ngay: ngay, ngày, ngây; gio: gió, giỗ, giờ; tuan: tuân, tuấn, tuần; thang: thang, tháng, thăng, thắng, thẳng; nam: nam, năm, nấm, nắm, nằm |
| 625 | ` bao lau` | bao: bao, báo, bão, bảo |
| 626 | ` trong bao lau` | trong: trọng, trống; bao: bao, báo, bão, bảo |
| 646 | `neu ` | neu: nêu, nếu, nệu |
| 646 | `trong truong hop ` | trong: trọng, trống; truong: trương, trường, trưởng; hop: họp, hợp |
| 648 | ` khi nao` | - |
| 649 | `duoc huong` | duoc: dược, được; huong: huống, hướng, hưởng |
| 649 | `tham gia` | tham: thâm, thẩm; gia: gia, già, giá, giã, giả |
| 651 | ` theo chinh sach` | chinh: chính, chỉnh; sach: sách, sạch |
| 659 | ` dung de` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng; de: dễ, đe, đè, đẻ, đề, để |
| 660 | ` lam gi` | lam: lam, làm, lâm, lạm, lắm |
| 668 | ` la gi` | la: là, lá, lã |
| 672 | ` nhung gi` | nhung: nhưng, những |
| 672 | ` liet ke` | ke: kê, kế, kể, kệ |
| 677 | `tai sao` | tai: tai, tài, tái, tại, tải |
| 677 | `vi sao` | vi: vì, ví, vị |
| 678 | ` giai thich` | - |

### `app/retrieval/reranker.py` (128)

| Dòng | Cue | Từ có thể va chạm |
|---:|---|---|
| 44 | `(?<!\d)(?:[01]?\d\|2[0-3])(?:[:h][0-5]\d)?\s*(?:-\|\u2013\|\u2014\|den\|to)\s*(?:[01]?\d\|2[0-3])(?:[:h][0-5]\d)?` | to: tố, tổ, tờ |
| 49 | `(?<!\d)(?:[01]?\d\|2[0-3])[:h][0-5]\d\s*(?:-\|den\|to)\s*(?:[01]?\d\|2[0-3])[:h][0-5]\d` | to: tố, tổ, tờ |
| 62 | `bao` | bao: bao, báo, bão, bảo |
| 63 | `nhieu` | nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 64 | `duoc` | duoc: dược, được |
| 65 | `cua` | cua: của, cửa |
| 67 | `chinh` | chinh: chính, chỉnh |
| 68 | `sach` | sach: sách, sạch |
| 69 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 70 | `vien` | vien: viên, viền, viễn, viện |
| 71 | `nguoi` | - |
| 78 | `moi` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời |
| 79 | `toi` | toi: tôi, tỏi, tối, tội, tới |
| 80 | `da` | da: dá, đa, đà, đã |
| 81 | `vao` | - |
| 82 | `muc` | muc: múc, mục, mức, mực |
| 83 | `nao` | - |
| 84 | `ngay` | ngay: ngay, ngày, ngây |
| 85 | `gio` | gio: gió, giỗ, giờ |
| 89 | `the` | the: thẻ, thế, thể |
| 94 | `khong` | - |
| 95 | `khong duoc` | duoc: dược, được |
| 96 | `khong phai` | - |
| 97 | `khong can` | can: cân, căn, cần, cận |
| 98 | `khong tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 99 | `duoc phep` | duoc: dược, được |
| 100 | `phai` | - |
| 101 | `bat buoc` | bat: bất, bật, bắt; buoc: buộc, bước |
| 102 | `yeu cau` | yeu: yêu, yếu; cau: câu, cấu, cầu |
| 124 | `giam doc` | giam: giám, giảm; doc: đọc, đốc, độc |
| 125 | `truong phong` | truong: trương, trường, trưởng; phong: phong, phòng, phóng, phỏng |
| 126 | `nguoi phe duyet` | - |
| 133 | `ai` | - |
| 135 | `an` | an: án, ăn, ản, ấn |
| 137 | `ban` | ban: ban, bàn, bán, bạn, bản, bận |
| 138 | `bao` | bao: bao, báo, bão, bảo |
| 140 | `cao` | cao: cáo, cạo |
| 141 | `cap` | cap: cấp, cập, cặp |
| 142 | `che` | - |
| 146 | `cong` | cong: cong, công, cổng, cộng |
| 152 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 153 | `du` | du: du, dù, dư, dụ, dữ, dự, đu, đủ |
| 154 | `giam` | giam: giám, giảm |
| 155 | `hang` | hang: hàng, hãng, hạng, hằng |
| 156 | `ho` | ho: họ, hồ, hỗ, hộ, hợ |
| 157 | `hoi` | hoi: hỏi, hồi, hội |
| 158 | `hop` | hop: họp, hợp |
| 159 | `kien` | kien: kiến, kiện |
| 160 | `khach` | - |
| 161 | `kiem` | kiem: kiếm, kiểm |
| 162 | `khoi` | khoi: khôi, khỏi, khối, khởi |
| 164 | `lieu` | - |
| 165 | `mat` | mat: mát, mất, mật, mắt, mặt |
| 166 | `nghe` | nghe: nghề, nghệ |
| 167 | `noi` | noi: nói, nơi, nối, nội |
| 171 | `phap` | - |
| 172 | `phong` | phong: phong, phòng, phóng, phỏng |
| 176 | `quyen` | - |
| 177 | `rieng` | - |
| 180 | `soc` | - |
| 182 | `thong` | thong: thông, thống |
| 183 | `tin` | tin: tin, tín |
| 184 | `toan` | toan: toàn, toán |
| 185 | `truc` | truc: trúc, trực |
| 186 | `uy` | - |
| 187 | `van` | van: văn, vấn, vẫn, vận |
| 192 | `an` | an: án, ăn, ản, ấn |
| 194 | `bao` | bao: bao, báo, bão, bảo |
| 195 | `cao` | cao: cáo, cạo |
| 196 | `cap` | cap: cấp, cập, cặp |
| 197 | `che` | - |
| 202 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 203 | `du` | du: du, dù, dư, dụ, dữ, dự, đu, đủ |
| 204 | `hang` | hang: hàng, hãng, hạng, hằng |
| 205 | `hoi` | hoi: hỏi, hồi, hội |
| 206 | `hop` | hop: họp, hợp |
| 207 | `kien` | kien: kiến, kiện |
| 208 | `khach` | - |
| 209 | `kiem` | kiem: kiếm, kiểm |
| 211 | `lieu` | - |
| 212 | `mat` | mat: mát, mất, mật, mắt, mặt |
| 213 | `phap` | - |
| 217 | `quyen` | - |
| 218 | `rieng` | - |
| 221 | `soc` | - |
| 222 | `thong` | thong: thông, thống |
| 223 | `tin` | tin: tin, tín |
| 224 | `toan` | toan: toàn, toán |
| 225 | `truc` | truc: trúc, trực |
| 226 | `uy` | - |
| 230 | `ban` | ban: ban, bàn, bán, bạn, bản, bận |
| 230 | `bo` | bo: bỏ, bố, bổ, bộ |
| 230 | `hoi` | hoi: hỏi, hồi, hội |
| 230 | `khoi` | khoi: khôi, khỏi, khối, khởi |
| 230 | `phong` | phong: phong, phòng, phóng, phỏng |
| 230 | `trung` | trung: trùng, trưng |
| 230 | `uy` | - |
| 230 | `van` | van: văn, vấn, vẫn, vận |
| 247 | `%s: ranking with lexical alignment, not the cross-encoder (%s).` | the: thẻ, thế, thể |
| 265 | `top_k must be greater than zero.` | than: thần, thắn |
| 292 | `batch_size must be greater than zero.` | than: thần, thắn |
| 295 | `max_length must be greater than zero.` | than: thần, thắn |
| 298 | `timeout_seconds must be greater than zero.` | than: thần, thắn |
| 340 | `top_k must be greater than zero.` | than: thần, thắn |
| 422 | `reranker returned an unexpected score count.` | an: án, ăn, ản, ấn |
| 592 | `tra luong` | tra: trá, trã, trả; luong: luồng, lương, lường, lượng |
| 592 | `ngay tra luong` | ngay: ngay, ngày, ngây; tra: trá, trã, trả; luong: luồng, lương, lường, lượng |
| 594 | `luong` | luong: luồng, lương, lường, lượng |
| 597 | ` nhan su` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; su: sư, sứ, sử, sự |
| 597 | ` nhan vien` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; vien: viên, viền, viễn, viện |
| 597 | ` nguoi` | - |
| 613 | `gio cot loi` | gio: gió, giỗ, giờ; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 615 | `gia tri cot loi` | gia: gia, già, giá, giã, giả; tri: trì, trí, trị; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 625 | `tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 627 | `khong tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 644 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 645 | `vien` | vien: viên, viền, viễn, viện |
| 646 | `duoc` | duoc: dược, được |
| 647 | `bao` | bao: bao, báo, bão, bảo |
| 648 | `nhieu` | nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 649 | `ngay` | ngay: ngay, ngày, ngây |
| 650 | `tuan` | tuan: tuân, tuấn, tuần |
| 651 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 652 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 653 | `gio` | gio: gió, giỗ, giờ |
| 675 | `\s*(?:gio\|ngay\|tuan\|thang\|nam\|%)` | gio: gió, giỗ, giờ; ngay: ngay, ngày, ngây; tuan: tuân, tuấn, tuần; thang: thang, tháng, thăng, thắng, thẳng; nam: nam, năm, nấm, nắm, nằm |
| 685 | `cau hoi goi y` | cau: câu, cấu, cầu; hoi: hỏi, hồi, hội; goi: gói, gọi, gợi |
| 685 | `kiem thu rag` | kiem: kiếm, kiểm; thu: thu, thú, thư, thủ, thứ, thử |

### `app/retrieval/structured.py` (202)

| Dòng | Cue | Từ có thể va chạm |
|---:|---|---|
| 14 | `(?<!\d)\d+(?:[.,]\d+)?\s*(?:nguoi\|nhan\s+su\|nhan\s+vien\|employees?\|people)\b` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; su: sư, sứ, sử, sự; vien: viên, viền, viễn, viện |
| 22 | `lan` | lan: lan, lân, lãn, lần, lẫn, lặn |
| 23 | `lan` | lan: lan, lân, lãn, lần, lẫn, lặn |
| 24 | `lan` | lan: lan, lân, lãn, lần, lẫn, lặn |
| 25 | `lan` | lan: lan, lân, lãn, lần, lẫn, lặn |
| 26 | `lan` | lan: lan, lân, lãn, lần, lẫn, lặn |
| 27 | `ngay` | ngay: ngay, ngày, ngây |
| 28 | `day` | day: đây, đầy |
| 28 | `ngay` | ngay: ngay, ngày, ngây |
| 29 | `ngay` | ngay: ngay, ngày, ngây |
| 30 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 31 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 32 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 33 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 34 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 35 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 38 | `(?:\s+(?:dong\|vnd\|d))?\s*(?:/\s*\|per\s+\|moi\s+)(lan\|visits?\|occurrences?\|ngay\|days?\|thang\|months?\|nam\|years?)\b` | dong: dong, dòng, đóng, đông, đống, đồng, động; moi: môi, mọi, mỏi, mối, mỗi, mới, mời; lan: lan, lân, lãn, lần, lẫn, lặn; ngay: ngay, ngày, ngây; thang: thang, tháng, thăng, thắng, thẳng; nam: nam, năm, nấm, nắm, nằm |
| 42 | `(?<!\d)(?:[01]?\d\|2[0-3])(?:[:h][0-5]\d)?\s*(?:-\|\u2013\|\u2014\|den\|to)\s*(?:[01]?\d\|2[0-3])(?:[:h][0-5]\d)?` | to: tố, tổ, tờ |
| 53 | `(?<!\d)\d+(?:[.,]\d+)?\s*(?:-\|\u2013\|\u2014)\s*\d+(?:[.,]\d+)?\s*(?:trieu\|dong\|vnd\|d\|\u20ab)\b` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 60 | `bao` | bao: bao, báo, bão, bảo |
| 61 | `dai` | dai: dài, dải, đại |
| 62 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 65 | `khoang` | - |
| 66 | `luong` | luong: luồng, lương, lường, lượng |
| 67 | `muc` | muc: múc, mục, mức, mực |
| 68 | `nao` | - |
| 69 | `nhieu` | nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 73 | `tham` | tham: thâm, thẩm |
| 74 | `thuoc` | thuoc: thuộc, thước |
| 75 | `tien` | tien: tiên, tiến, tiền, tiện |
| 76 | `trieu` | - |
| 77 | `thi` | thi: thi, thì, thí, thị |
| 78 | `vay` | - |
| 79 | `voi` | voi: vôi, vội, với |
| 80 | `nhe` | - |
| 84 | `noi dung` | noi: nói, nơi, nối, nội; dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 85 | `hang muc` | hang: hàng, hãng, hạng, hằng; muc: múc, mục, mức, mực |
| 86 | `muc` | muc: múc, mục, mức, mực |
| 87 | `loai` | - |
| 88 | `doi tuong` | doi: dõi, dồi, đòi, đôi, đối, đổi, đội, đời, đợi; tuong: tương, tưởng, tượng |
| 89 | `dieu kien` | kien: kiến, kiện |
| 90 | `quy dinh` | quy: quy, quý, quỳ, quỹ; dinh: dính, đinh, đình, đính, đỉnh, định |
| 91 | `chinh sach` | chinh: chính, chỉnh; sach: sách, sạch |
| 99 | `gio` | gio: gió, giỗ, giờ |
| 100 | `ngay` | ngay: ngay, ngày, ngây |
| 101 | `tuan` | tuan: tuân, tuấn, tuần |
| 102 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 103 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 104 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 105 | `trieu` | - |
| 116 | `thay` | - |
| 117 | `the` | the: thẻ, thế, thể |
| 126 | `bat buoc` | bat: bất, bật, bắt; buoc: buộc, bước |
| 127 | `theo luat` | - |
| 134 | `bo sung` | bo: bỏ, bố, bổ, bộ |
| 135 | `bo tro` | bo: bỏ, bố, bổ, bộ; tro: trò, trỏ, trở, trợ |
| 136 | `them` | - |
| 137 | `tang cuong` | tang: tang, tăng, tảng, tầng, tặng |
| 146 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 147 | `duoc` | duoc: dược, được |
| 148 | `khong` | - |
| 149 | `phai` | - |
| 150 | `dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 151 | `la` | la: là, lá, lã |
| 152 | `ve` | ve: vé, vẻ, vẽ, về, vệ |
| 153 | `cua` | cua: của, cửa |
| 154 | `cho` | cho: cho, chó, chỗ, chờ, chở, chợ |
| 156 | `thi` | thi: thi, thì, thí, thị |
| 157 | `thay` | - |
| 158 | `the` | the: thẻ, thế, thể |
| 164 | `bat` | bat: bất, bật, bắt |
| 165 | `buoc` | buoc: buộc, bước |
| 167 | `luat` | - |
| 172 | `bo` | bo: bỏ, bố, bổ, bộ |
| 174 | `tro` | tro: trò, trỏ, trở, trợ |
| 175 | `them` | - |
| 176 | `tang` | tang: tang, tăng, tảng, tầng, tặng |
| 177 | `cuong` | - |
| 183 | `bao` | bao: bao, báo, bão, bảo |
| 184 | `hiem` | - |
| 185 | `suc` | - |
| 186 | `khoe` | - |
| 191 | `che` | - |
| 192 | `do` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 193 | `loai` | - |
| 194 | `hinh` | - |
| 316 | `vi du chi phi hop le` | vi: vì, ví, vị; du: du, dù, dư, dụ, dữ, dự, đu, đủ; chi: chi, chí, chỉ, chị; phi: phi, phí; hop: họp, hợp; le: le, lê, lẻ, lẽ, lễ, lệ |
| 364 | `\bbao\s+lau\s+(?:duoc\s+)?(?:moi\|mot)\s+lan\b` | bao: bao, báo, bão, bảo; duoc: dược, được; moi: môi, mọi, mỏi, mối, mỗi, mới, mời; lan: lan, lân, lãn, lần, lẫn, lặn |
| 368 | `lan` | lan: lan, lân, lãn, lần, lẫn, lặn |
| 369 | `\b(?:moi\|mot\|tung)\s+lan\b` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời; lan: lan, lân, lãn, lần, lẫn, lặn |
| 372 | `ngay` | ngay: ngay, ngày, ngây |
| 372 | `\b(?:moi\|mot\|hang)\s+ngay\b` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời; hang: hàng, hãng, hạng, hằng; ngay: ngay, ngày, ngây |
| 372 | `\bper\s+day\b` | day: đây, đầy |
| 373 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 373 | `\b(?:moi\|mot\|hang)\s+thang\b` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời; hang: hàng, hãng, hạng, hằng; thang: thang, tháng, thăng, thắng, thẳng |
| 374 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 374 | `\b(?:moi\|mot\|hang)\s+nam\b` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời; hang: hàng, hãng, hạng, hằng; nam: nam, năm, nấm, nắm, nằm |
| 465 | `toi da` | toi: tôi, tỏi, tối, tội, tới; da: dá, đa, đà, đã |
| 465 | `muc toi da` | muc: múc, mục, mức, mực; toi: tôi, tỏi, tối, tội, tới; da: dá, đa, đà, đã |
| 465 | `up to` | to: tố, tổ, tờ |
| 504 | `luong` | luong: luồng, lương, lường, lượng |
| 508 | `dai` | dai: dài, dải, đại |
| 508 | `khoang` | - |
| 534 | `bao` | bao: bao, báo, bão, bảo |
| 535 | `nhieu` | nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 536 | `duoc` | duoc: dược, được |
| 537 | `cua` | cua: của, cửa |
| 539 | `chinh` | chinh: chính, chỉnh |
| 540 | `sach` | sach: sách, sạch |
| 623 | `bao ai` | bao: bao, báo, bão, bảo |
| 623 | `bao cho ai` | bao: bao, báo, bão, bảo; cho: cho, chó, chỗ, chờ, chở, chợ |
| 623 | `report to whom` | to: tố, tổ, tờ |
| 623 | `who to report` | to: tố, tổ, tờ |
| 626 | `tai khoan bi lo` | tai: tai, tài, tái, tại, tải; khoan: khoán, khoản; bi: bí, bị; lo: lỗ, lộ |
| 627 | `lo tai khoan` | lo: lỗ, lộ; tai: tai, tài, tái, tại, tải; khoan: khoán, khoản |
| 628 | `lo thong tin xac thuc` | lo: lỗ, lộ; thong: thông, thống; tin: tin, tín; thuc: thúc, thục, thức, thực |
| 629 | `dang nhap bat thuong` | dang: dang, dạng, đang, đáng, đăng, đằng, đẳng; nhap: nháp, nhập; bat: bất, bật, bắt; thuong: thương, thường, thưởng |
| 637 | `bao ngay` | bao: bao, báo, bão, bảo; ngay: ngay, ngày, ngây |
| 637 | `bao cho` | bao: bao, báo, bão, bảo; cho: cho, chó, chỗ, chờ, chở, chợ |
| 637 | `report to` | to: tố, tổ, tờ |
| 645 | `thong tin xac thuc` | thong: thông, thống; tin: tin, tín; thuc: thúc, thục, thức, thực |
| 646 | `dang nhap bat thuong` | dang: dang, dạng, đang, đáng, đăng, đằng, đẳng; nhap: nháp, nhập; bat: bất, bật, bắt; thuong: thương, thường, thưởng |
| 647 | `tai khoan` | tai: tai, tài, tái, tại, tải; khoan: khoán, khoản |
| 680 | `luong` | luong: luồng, lương, lường, lượng |
| 683 | `dai` | dai: dài, dải, đại |
| 683 | `khoang` | - |
| 713 | `dai` | dai: dài, dải, đại |
| 713 | `gross/thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 713 | `bang` | bang: bang, băng, bảng, bằng |
| 737 | `khong quy dinh` | quy: quy, quý, quỳ, quỹ; dinh: dính, đinh, đình, đính, đỉnh, định |
| 738 | `khong xac dinh` | dinh: dính, đinh, đình, đính, đỉnh, định |
| 739 | `khong neu` | neu: nêu, nếu, nệu |
| 740 | `khong co ty le co dinh` | co: có, cô, cơ, cố, cổ, cờ, cỡ; le: le, lê, lẻ, lẽ, lễ, lệ; dinh: dính, đinh, đình, đính, đỉnh, định |
| 741 | `khong co dinh ty le` | co: có, cô, cơ, cố, cổ, cờ, cỡ; dinh: dính, đinh, đình, đính, đỉnh, định; le: le, lê, lẻ, lẽ, lễ, lệ |
| 742 | `khong co dinh` | co: có, cô, cơ, cố, cổ, cờ, cỡ; dinh: dính, đinh, đình, đính, đỉnh, định |
| 743 | `khong an dinh` | an: án, ăn, ản, ấn; dinh: dính, đinh, đình, đính, đỉnh, định |
| 744 | `khong duoc neu ro` | duoc: dược, được; neu: nêu, nếu, nệu; ro: rò, rõ |
| 749 | `no fixed` | no: nó, nợ |
| 750 | `ty le cu the duoc cap nhat theo` | le: le, lê, lẻ, lẽ, lễ, lệ; cu: cù, cũ, cụ, cứ; the: thẻ, thế, thể; duoc: dược, được; cap: cấp, cập, cặp; nhat: nhất, nhật |
| 751 | `muc cu the duoc cap nhat theo` | muc: múc, mục, mức, mực; cu: cù, cũ, cụ, cứ; the: thẻ, thế, thể; duoc: dược, được; cap: cấp, cập, cặp; nhat: nhất, nhật |
| 753 | `specific rate is updated according to` | to: tố, tổ, tờ |
| 760 | `phan tram` | phan: phan, phán, phân, phản, phần, phận; tram: trám, trăm, trạm |
| 762 | `gio` | gio: gió, giỗ, giờ |
| 764 | `gio` | gio: gió, giỗ, giờ |
| 764 | `ngay` | ngay: ngay, ngày, ngây |
| 764 | `tuan` | tuan: tuân, tuấn, tuần |
| 764 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 764 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 764 | `day` | day: đây, đầy |
| 766 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 766 | `trieu` | - |
| 768 | `nhan su` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; su: sư, sứ, sử, sự |
| 768 | `nhan vien` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; vien: viên, viền, viễn, viện |
| 768 | `nguoi` | - |
| 792 | `ket noi an toan` | noi: nói, nơi, nối, nội; an: án, ăn, ản, ấn; toan: toàn, toán |
| 793 | `xac thuc nhieu lop` | thuc: thúc, thục, thức, thực; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu; lop: lốp, lớp |
| 794 | `thiet bi duoc phe duyet` | thiet: thiết, thiệt; bi: bí, bị; duoc: dược, được |
| 795 | `thiet bi duoc quan ly` | thiet: thiết, thiệt; bi: bí, bị; duoc: dược, được; quan: quan, quán, quân, quản, quần, quận |
| 796 | `khong de nguoi khong co tham quyen` | de: dễ, đe, đè, đẻ, đề, để; co: có, cô, cơ, cố, cổ, cờ, cỡ; tham: thâm, thẩm |
| 809 | `thoi gian` | - |
| 809 | `thoi` | - |
| 809 | `gian` | - |
| 811 | `ghi nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 814 | `chu` | chu: chú, chủ, chứ, chữ |
| 814 | `nhat` | nhat: nhất, nhật |
| 816 | `ngay nghi hang tuan` | ngay: ngay, ngày, ngây; nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; tuan: tuân, tuấn, tuần |
| 818 | `ngay le` | ngay: ngay, ngày, ngây; le: le, lê, lẻ, lẽ, lễ, lệ |
| 818 | `tet` | - |
| 822 | `lam viec ban dem` | lam: lam, làm, lâm, lạm, lắm; ban: ban, bàn, bán, bạn, bản, bận; dem: đêm, đếm |
| 824 | `lam them vao ban dem` | lam: lam, làm, lâm, lạm, lắm; ban: ban, bàn, bán, bạn, bản, bận; dem: đêm, đếm |
| 854 | `bao mat` | bao: bao, báo, bão, bảo; mat: mát, mất, mật, mắt, mặt |
| 856 | `yeu cau` | yeu: yêu, yếu; cau: câu, cấu, cầu |
| 856 | `bao dam` | bao: bao, báo, bão, bảo; dam: đám, đảm |
| 856 | `can tuan thu` | can: cân, căn, cần, cận; tuan: tuân, tuấn, tuần; thu: thu, thú, thư, thủ, thứ, thử |
| 856 | `tuan thu` | tuan: tuân, tuấn, tuần; thu: thu, thú, thư, thủ, thứ, thử |
| 859 | `an toan` | an: án, ăn, ản, ấn; toan: toàn, toán |
| 860 | `bao dam` | bao: bao, báo, bão, bảo; dam: đám, đảm |
| 860 | `dam bao` | dam: đám, đảm; bao: bao, báo, bão, bảo |
| 860 | `gi` | - |
| 872 | `lam viec ban dem` | lam: lam, làm, lâm, lạm, lắm; ban: ban, bàn, bán, bạn, bản, bận; dem: đêm, đếm |
| 873 | `lam them` | lam: lam, làm, lâm, lạm, lắm |
| 887 | `lam viec ban dem` | lam: lam, làm, lâm, lạm, lắm; ban: ban, bàn, bán, bạn, bản, bận; dem: đêm, đếm |
| 892 | `lam them` | lam: lam, làm, lâm, lạm, lắm |
| 893 | `ngay nghi hang tuan` | ngay: ngay, ngày, ngây; nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; tuan: tuân, tuấn, tuần |
| 894 | `ngay le` | ngay: ngay, ngày, ngây; le: le, lê, lẻ, lẽ, lễ, lệ |
| 943 | `thay` | - |
| 943 | `the` | the: thẻ, thế, thể |
| 944 | `thay` | - |
| 944 | `the` | the: thẻ, thế, thể |
| 982 | `quyen loi` | loi: lõi, lối, lỗi, lội, lời, lợi |
| 983 | `tu ngay` | tu: tu, tư, tủ, tứ, từ, tử, tự; ngay: ngay, ngày, ngây |
| 984 | `sau thu viec` | sau: sau, sáu, sâu; thu: thu, thú, thư, thủ, thứ, thử |
| 985 | `dieu kien` | kien: kiến, kiện |
| 986 | `han muc` | han: hàn, hán, hân, hạn, hẳn; muc: múc, mục, mức, mực |
| 987 | `tinh huong` | tinh: tình, tính, tỉnh; huong: huống, hướng, hưởng |
| 988 | `muc toi thieu` | muc: múc, mục, mức, mực; toi: tôi, tỏi, tối, tội, tới; thieu: thiếu, thiểu, thiệu |
| 992 | `from first day` | day: đây, đầy |
| 1033 | `phai` | - |
| 1034 | `bat buoc` | bat: bất, bật, bắt; buoc: buộc, bước |
| 1035 | `khong duoc` | duoc: dược, được |
| 1036 | `khong tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 1037 | `duoc phep` | duoc: dược, được |

### `app/retrieval/subclaims.py` (5)

| Dòng | Cue | Từ có thể va chạm |
|---:|---|---|
| 73 | `khi nao` | - |
| 73 | `muc ot` | muc: múc, mục, mức, mực |
| 73 | `muc overtime` | muc: múc, mục, mức, mực |
| 89 | `\b(?:bao\s+nhieu\|how\s+much)\b` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 97 | `\b(?:va\|and)\b` | va: và, vá, vã |

### `app/services/claim_evidence_validation_service.py` (570)

| Dòng | Cue | Từ có thể va chạm |
|---:|---|---|
| 26 | `(?<!\d)(?:[01]?\d\|2[0-3])\s*(?::\|h\|gio)\s*[0-5]\d(?!\d)` | gio: gió, giỗ, giờ |
| 33 | `moi` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời |
| 34 | `tat ca` | tat: tất, tật, tắt; ca: cá, cã, cả, cầ |
| 35 | `deu` | - |
| 41 | `phai` | - |
| 42 | `bat buoc` | bat: bất, bật, bắt; buoc: buộc, bước |
| 43 | `yeu cau` | yeu: yêu, yếu; cau: câu, cấu, cầu |
| 44 | `can gui` | can: cân, căn, cần, cận |
| 45 | `can thuc hien` | can: cân, căn, cần, cận; thuc: thúc, thục, thức, thực; hien: hiển, hiện |
| 48 | `needs to` | to: tố, tổ, tờ |
| 49 | `has to` | to: tố, tổ, tờ |
| 52 | `khong phai` | - |
| 53 | `khong can` | can: cân, căn, cần, cận |
| 54 | `khong bat buoc` | bat: bất, bật, bắt; buoc: buộc, bước |
| 55 | `khong yeu cau` | yeu: yêu, yếu; cau: câu, cấu, cầu |
| 57 | `do not need` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 58 | `not need to` | to: tố, tổ, tờ |
| 63 | `duoc phep` | duoc: dược, được |
| 63 | `co the` | co: có, cô, cơ, cố, cổ, cờ, cỡ; the: thẻ, thế, thể |
| 63 | `may ` | may: may, mày, máy, mây, mấy |
| 65 | `khong duoc` | duoc: dược, được |
| 66 | `khong the` | the: thẻ, thế, thể |
| 67 | `khong co the` | co: có, cô, cơ, cố, cổ, cờ, cỡ; the: thẻ, thế, thể |
| 69 | `may not` | may: may, mày, máy, mây, mấy |
| 71 | `can not` | can: cân, căn, cần, cận |
| 78 | `tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 80 | `khong` | - |
| 82 | `no ` | no: nó, nợ |
| 84 | `do not` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 86 | `can not` | can: cân, căn, cần, cận |
| 87 | `may not` | may: may, mày, máy, mây, mấy |
| 88 | `khong tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 90 | `trong vong` | trong: trọng, trống; vong: vòng, vọng |
| 90 | `trong` | trong: trọng, trống |
| 91 | `khong trong vong` | trong: trọng, trống; vong: vòng, vọng |
| 91 | `khong trong` | trong: trọng, trống |
| 95 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 96 | `duoc` | duoc: dược, được |
| 97 | `khong` | - |
| 98 | `phai` | - |
| 99 | `dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 100 | `la` | la: là, lá, lã |
| 101 | `ve` | ve: vé, vẻ, vẽ, về, vệ |
| 102 | `cua` | cua: của, cửa |
| 103 | `cho` | cho: cho, chó, chỗ, chờ, chở, chợ |
| 105 | `thi` | thi: thi, thì, thí, thị |
| 107 | `no` | no: nó, nợ |
| 110 | `do` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 112 | `can` | can: cân, căn, cần, cận |
| 117 | `khong cam` | cam: cảm, cấm |
| 118 | `khong bi han che` | bi: bí, bị; han: hàn, hán, hân, hạn, hẳn |
| 119 | `khong bi gioi han` | bi: bí, bị; han: hàn, hán, hân, hạn, hẳn |
| 121 | `do not prohibit` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 123 | `do not restrict` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 130 | `khong thay the` | the: thẻ, thế, thể |
| 132 | `do not replace` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 137 | `khong ` | - |
| 140 | `do not ` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 142 | `can not ` | can: cân, căn, cần, cận |
| 143 | `may not ` | may: may, mày, máy, mây, mấy |
| 147 | `khong chi` | chi: chi, chí, chỉ, chị |
| 148 | `khong nhung` | nhung: nhưng, những |
| 153 | `co quyen` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 154 | `duoc quyen` | duoc: dược, được |
| 159 | `chinh minh` | chinh: chính, chỉnh |
| 160 | `cua minh` | cua: của, cửa |
| 161 | `chinh toi` | chinh: chính, chỉnh; toi: tôi, tỏi, tối, tội, tới |
| 162 | `cua chinh toi` | cua: của, cửa; chinh: chính, chỉnh; toi: tôi, tỏi, tối, tội, tới |
| 163 | `chinh ban` | chinh: chính, chỉnh; ban: ban, bàn, bán, bạn, bản, bận |
| 164 | `cua chinh ban` | cua: của, cửa; chinh: chính, chỉnh; ban: ban, bàn, bán, bạn, bản, bận |
| 165 | `ban than` | ban: ban, bàn, bán, bạn, bản, bận; than: thần, thắn |
| 174 | `ai` | - |
| 175 | `ban` | ban: ban, bàn, bán, bạn, bản, bận |
| 176 | `bo` | bo: bỏ, bố, bổ, bộ |
| 180 | `cong` | cong: cong, công, cổng, cộng |
| 183 | `cua` | cua: của, cửa |
| 185 | `doc` | doc: đọc, đốc, độc |
| 186 | `don` | don: dọn, dồn, đón, đơn |
| 187 | `giam` | giam: giám, giảm |
| 188 | `la` | la: là, lá, lã |
| 189 | `nghe` | nghe: nghề, nghệ |
| 190 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 191 | `phan` | phan: phan, phán, phân, phản, phần, phận |
| 192 | `phong` | phong: phong, phòng, phóng, phỏng |
| 193 | `phu` | phu: phù, phụ |
| 194 | `su` | su: sư, sứ, sử, sự |
| 195 | `tai` | tai: tai, tài, tái, tại, tải |
| 198 | `tong` | - |
| 199 | `trach` | - |
| 200 | `tro` | tro: trò, trỏ, trở, trợ |
| 201 | `vai` | - |
| 202 | `vi` | vi: vì, ví, vị |
| 207 | `nguoi khac` | khac: khác, khắc |
| 208 | `cua nguoi khac` | cua: của, cửa; khac: khác, khắc |
| 209 | `nhan vien khac` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; vien: viên, viền, viễn, viện; khac: khác, khắc |
| 210 | `cua nhan vien khac` | cua: của, cửa; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; vien: viên, viền, viễn, viện; khac: khác, khắc |
| 211 | `nguoi lao dong khac` | dong: dong, dòng, đóng, đông, đống, đồng, động; khac: khác, khắc |
| 212 | `cua nguoi lao dong khac` | cua: của, cửa; dong: dong, dòng, đóng, đông, đống, đồng, động; khac: khác, khắc |
| 213 | `dong nghiep khac` | dong: dong, dòng, đóng, đông, đống, đồng, động; khac: khác, khắc |
| 227 | `nhan vien` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; vien: viên, viền, viễn, viện |
| 227 | `nguoi lao dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 228 | `toi` | toi: tôi, tỏi, tối, tội, tới |
| 228 | `minh` | - |
| 228 | ` my ` | - |
| 228 | ` me ` | - |
| 236 | `trao doi` | doi: dõi, dồi, đòi, đôi, đối, đổi, đội, đời, đợi |
| 237 | `chia se` | se: sẻ, sẽ |
| 238 | `cung cap` | cung: cùng, cũng; cap: cấp, cập, cặp |
| 239 | `phat tan` | phat: phát, phạt; tan: tan, tán, tân, tăn, tấn, tần, tận |
| 250 | `su dung` | su: sư, sứ, sử, sự; dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 251 | `yeu cau` | yeu: yêu, yếu; cau: câu, cấu, cầu |
| 252 | `truy cap` | cap: cấp, cập, cặp |
| 253 | `sao chep` | - |
| 254 | `luu tru` | tru: trú, trừ, trữ |
| 259 | `toi` | toi: tôi, tỏi, tối, tội, tới |
| 260 | `minh` | - |
| 261 | `chinh` | chinh: chính, chỉnh |
| 262 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 263 | `vien` | vien: viên, viền, viễn, viện |
| 264 | `nguoi` | - |
| 266 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 272 | `thong` | thong: thông, thống |
| 273 | `tin` | tin: tin, tín |
| 275 | `du` | du: du, dù, dư, dụ, dữ, dự, đu, đủ |
| 276 | `lieu` | - |
| 278 | `sach` | sach: sách, sạch |
| 294 | `cam` | cam: cảm, cấm |
| 295 | `han` | han: hàn, hán, hân, hạn, hẳn |
| 296 | `che` | - |
| 297 | `yeu` | yeu: yêu, yếu |
| 298 | `cau` | cau: câu, cấu, cầu |
| 301 | `do` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 302 | `may` | may: may, mày, máy, mây, mấy |
| 303 | `can` | can: cân, căn, cần, cận |
| 310 | `cua` | cua: của, cửa |
| 311 | `cho` | cho: cho, chó, chỗ, chờ, chở, chợ |
| 312 | `ve` | ve: vé, vẻ, vẽ, về, vệ |
| 316 | `su` | su: sư, sứ, sử, sự |
| 317 | `dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 319 | `doi` | doi: dõi, dồi, đòi, đôi, đối, đổi, đội, đời, đợi |
| 321 | `se` | se: sẻ, sẽ |
| 322 | `cung` | cung: cùng, cũng |
| 323 | `cap` | cap: cấp, cập, cặp |
| 324 | `phat` | phat: phát, phạt |
| 325 | `tan` | tan: tan, tán, tân, tăn, tấn, tần, tận |
| 328 | `chep` | - |
| 329 | `luu` | - |
| 344 | `hoac` | - |
| 350 | `thay the` | the: thẻ, thế, thể |
| 359 | `bat buoc` | bat: bất, bật, bắt; buoc: buộc, bước |
| 360 | `theo luat` | - |
| 368 | `bo sung` | bo: bỏ, bố, bổ, bộ |
| 369 | `bo tro` | bo: bỏ, bố, bổ, bộ; tro: trò, trỏ, trở, trợ |
| 370 | `them` | - |
| 371 | `tang cuong` | tang: tang, tăng, tảng, tầng, tặng |
| 381 | `thay` | - |
| 382 | `the` | the: thẻ, thế, thể |
| 388 | `bat` | bat: bất, bật, bắt |
| 389 | `buoc` | buoc: buộc, bước |
| 391 | `luat` | - |
| 396 | `bo` | bo: bỏ, bố, bổ, bộ |
| 398 | `tro` | tro: trò, trỏ, trở, trợ |
| 399 | `them` | - |
| 400 | `tang` | tang: tang, tăng, tảng, tầng, tặng |
| 401 | `cuong` | - |
| 407 | `bao` | bao: bao, báo, bão, bảo |
| 408 | `dam` | dam: đám, đảm |
| 409 | `lam` | lam: lam, làm, lâm, lạm, lắm |
| 410 | `viec` | - |
| 411 | `hiem` | - |
| 412 | `suc` | - |
| 413 | `khoe` | - |
| 418 | `che` | - |
| 419 | `do` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 420 | `loai` | - |
| 421 | `hinh` | - |
| 428 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 429 | `vien` | vien: viên, viền, viễn, viện |
| 430 | `nguoi` | - |
| 432 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 433 | `noi` | noi: nói, nơi, nối, nội |
| 434 | `dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 435 | `van` | van: văn, vấn, vẫn, vận |
| 436 | `quan` | quan: quan, quán, quân, quản, quần, quận |
| 437 | `muc` | muc: múc, mục, mức, mực |
| 438 | `luong` | luong: luồng, lương, lường, lượng |
| 439 | `chinh` | chinh: chính, chỉnh |
| 440 | `minh` | - |
| 441 | `gui` | - |
| 442 | `chuyen` | chuyen: chuyên, chuyến, chuyển, chuyện |
| 443 | `tu` | tu: tu, tư, tủ, tứ, từ, tử, tự |
| 444 | `to` | to: tố, tổ, tờ |
| 455 | `kho ma nguon` | ma: ma, mà, má, mã, mạ, mả |
| 455 | `kho ca nhan` | ca: cá, cã, cả, cầ; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 456 | `email ca nhan` | ca: cá, cã, cả, cầ; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 460 | `public ai` | - |
| 461 | `ai cong cong` | cong: cong, công, cổng, cộng |
| 462 | `dich vu ai cong cong` | dich: dịch, đích, địch; cong: cong, công, cổng, cộng |
| 463 | `cong cu ai cong cong` | cong: cong, công, cổng, cộng; cu: cù, cũ, cụ, cứ |
| 470 | `bao` | bao: bao, báo, bão, bảo |
| 471 | `nhieu` | nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 472 | `may` | may: may, mày, máy, mây, mấy |
| 473 | `nao` | - |
| 474 | `duoc` | duoc: dược, được |
| 476 | `muc` | muc: múc, mục, mức, mực |
| 477 | `toi` | toi: tôi, tỏi, tối, tội, tới |
| 478 | `thieu` | thieu: thiếu, thiểu, thiệu |
| 479 | `da` | da: dá, đa, đà, đã |
| 480 | `ngay` | ngay: ngay, ngày, ngây |
| 481 | `gio` | gio: gió, giỗ, giờ |
| 482 | `tuan` | tuan: tuân, tuấn, tuần |
| 483 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 484 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 485 | `phan` | phan: phan, phán, phân, phản, phần, phận |
| 486 | `tram` | tram: trám, trăm, trạm |
| 487 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 489 | `tien` | tien: tiên, tiến, tiền, tiện |
| 490 | `phu` | phu: phù, phụ |
| 491 | `cap` | cap: cấp, cập, cặp |
| 492 | `ho` | ho: họ, hồ, hỗ, hộ, hợ |
| 493 | `tro` | tro: trò, trỏ, trở, trợ |
| 494 | `lam` | lam: lam, làm, lâm, lạm, lắm |
| 495 | `moi` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời |
| 506 | `thuong` | thuong: thương, thường, thưởng |
| 507 | `thi` | thi: thi, thì, thí, thị |
| 513 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 514 | `vien` | vien: viên, viền, viễn, viện |
| 515 | `nguoi` | - |
| 517 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 518 | `cong` | cong: cong, công, cổng, cộng |
| 519 | `ty` | - |
| 520 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 521 | `khong` | - |
| 522 | `duoc` | duoc: dược, được |
| 523 | `phai` | - |
| 524 | `thi` | thi: thi, thì, thí, thị |
| 525 | `la` | la: là, lá, lã |
| 526 | `gi` | - |
| 527 | `nao` | - |
| 528 | `cua` | cua: của, cửa |
| 529 | `cho` | cho: cho, chó, chỗ, chờ, chở, chợ |
| 530 | `ve` | ve: vé, vẻ, vẽ, về, vệ |
| 532 | `yeu` | yeu: yêu, yếu |
| 533 | `cau` | cau: câu, cấu, cầu |
| 534 | `bao` | bao: bao, báo, bão, bảo |
| 535 | `dam` | dam: đám, đảm |
| 536 | `lam` | lam: lam, làm, lâm, lạm, lắm |
| 537 | `viec` | - |
| 544 | `the` | the: thẻ, thế, thể |
| 554 | `chu nhat` | chu: chú, chủ, chứ, chữ; nhat: nhất, nhật |
| 555 | `nghi hang tuan` | nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; tuan: tuân, tuấn, tuần |
| 556 | `nghi hang tuan` | nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; tuan: tuân, tuấn, tuần |
| 561 | `ngay le` | ngay: ngay, ngày, ngây; le: le, lê, lẻ, lẽ, lễ, lệ |
| 561 | `tet` | - |
| 563 | `ngay lam viec binh thuong` | ngay: ngay, ngày, ngây; lam: lam, làm, lâm, lạm, lắm; thuong: thương, thường, thưởng |
| 567 | `ban dem` | ban: ban, bàn, bán, bạn, bản, bận; dem: đêm, đếm |
| 567 | `ca dem` | ca: cá, cã, cả, cầ; dem: đêm, đếm |
| 571 | `noi tru` | noi: nói, nơi, nối, nội; tru: trú, trừ, trữ |
| 573 | `ngoai tru` | ngoai: ngoài, ngoại; tru: trú, trừ, trữ |
| 575 | `an trua` | an: án, ăn, ản, ấn |
| 577 | `nha khoa` | nha: nhà, nhá, nhã |
| 579 | `thai san` | thai: thái, thải; san: sản, sẵn |
| 581 | `tai nan` | tai: tai, tài, tái, tại, tải; nan: năn, nạn |
| 586 | `ket noi an toan` | noi: nói, nơi, nối, nội; an: án, ăn, ản, ấn; toan: toàn, toán |
| 587 | `xac thuc nhieu lop` | thuc: thúc, thục, thức, thực; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu; lop: lốp, lớp |
| 588 | `thiet bi duoc phe duyet` | thiet: thiết, thiệt; bi: bí, bị; duoc: dược, được |
| 589 | `thiet bi duoc quan ly` | thiet: thiết, thiệt; bi: bí, bị; duoc: dược, được; quan: quan, quán, quân, quản, quần, quận |
| 590 | `khong de nguoi khong co tham quyen` | de: dễ, đe, đè, đẻ, đề, để; co: có, cô, cơ, cố, cổ, cờ, cỡ; tham: thâm, thẩm |
| 591 | `ma hoa` | ma: ma, mà, má, mã, mạ, mả; hoa: hòa, hóa |
| 679 | `^(co\|khong\|yes\|no)\s*[.,:;!?-]` | co: có, cô, cơ, cố, cổ, cờ, cỡ; no: nó, nợ |
| 684 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 686 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 689 | `khong` | - |
| 689 | `no` | no: nó, nợ |
| 791 | `\bnoi\s+(?:ve\|voi\|cho)\b` | noi: nói, nơi, nối, nội; ve: vé, vẻ, vẽ, về, vệ; voi: vôi, vội, với; cho: cho, chó, chỗ, chờ, chở, chợ |
| 833 | `\b(?:does\s+not\s+\|do\s+not\s+\|not\s+)?(?:prohibit\|prohibits\|prohibited\|restrict\|restricts\|restricted\|forbid\|forbidden)\b` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 838 | `\b(?:does\s+not\s+\|do\s+not\s+\|not\s+)?(?:permit\|permits\|permitted\|allow\|allows\|allowed)\b` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 843 | `\b(?:does\s+not\s+\|do\s+not\s+\|not\s+)?(?:require\|requires\|required\|must)\b` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 846 | `\b(?:khong\s+)?(?:cam\|han\s+che)\b` | cam: cảm, cấm; han: hàn, hán, hân, hạn, hẳn |
| 847 | `\b(?:khong\s+)?(?:duoc\s+phep\|cho\s+phep)\b` | duoc: dược, được; cho: cho, chó, chỗ, chờ, chở, chợ |
| 848 | `\b(?:khong\s+)?(?:yeu\s+cau\|bat\s+buoc)\b` | yeu: yêu, yếu; cau: câu, cấu, cầu; bat: bất, bật, bắt; buoc: buộc, bước |
| 854 | `\b(?:does\s+not\|do\s+not\|not\|khong)\b` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 1089 | `moi` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời |
| 1090 | `tat` | tat: tất, tật, tắt |
| 1091 | `ca` | ca: cá, cã, cả, cầ |
| 1092 | `deu` | - |
| 1095 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 1096 | `vien` | vien: viên, viền, viễn, viện |
| 1097 | `nguoi` | - |
| 1099 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 1102 | `day` | day: đây, đầy |
| 1104 | `gio` | gio: gió, giỗ, giờ |
| 1105 | `ngay` | ngay: ngay, ngày, ngây |
| 1106 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 1107 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 1108 | `tuan` | tuan: tuân, tuấn, tuần |
| 1700 | `phu cap` | phu: phù, phụ; cap: cấp, cập, cặp |
| 1700 | `tro cap` | tro: trò, trỏ, trở, trợ; cap: cấp, cập, cặp |
| 1700 | `ho tro` | ho: họ, hồ, hỗ, hộ, hợ; tro: trò, trỏ, trở, trợ |
| 1717 | `khong ap dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 1717 | `khong duoc huong` | duoc: dược, được; huong: huống, hướng, hưởng |
| 1721 | `ap dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 1721 | `duoc phe duyet` | duoc: dược, được |
| 1721 | `thuong xuyen` | thuong: thương, thường, thưởng |
| 1726 | `khong ap dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 1726 | `khong duoc huong` | duoc: dược, được; huong: huống, hướng, hưởng |
| 1739 | `ap dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 1739 | `duoc` | duoc: dược, được |
| 1770 | `co dinh` | co: có, cô, cơ, cố, cổ, cờ, cỡ; dinh: dính, đinh, đình, đính, đỉnh, định |
| 1771 | `quy dinh` | quy: quy, quý, quỳ, quỹ; dinh: dính, đinh, đình, đính, đỉnh, định |
| 1772 | `ghi ro` | ro: rò, rõ |
| 1773 | `neu ro` | neu: nêu, nếu, nệu; ro: rò, rõ |
| 1794 | `cap` | cap: cấp, cập, cặp |
| 1795 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 1796 | `cong` | cong: cong, công, cổng, cộng |
| 1799 | `duoc` | duoc: dược, được |
| 1801 | `ho` | ho: họ, hồ, hỗ, hộ, hợ |
| 1802 | `khoan` | khoan: khoán, khoản |
| 1803 | `khong` | - |
| 1804 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 1806 | `rieng` | - |
| 1809 | `the` | the: thẻ, thế, thể |
| 1810 | `tien` | tien: tiên, tiến, tiền, tiện |
| 1811 | `tro` | tro: trò, trỏ, trở, trợ |
| 1812 | `ty` | - |
| 1813 | `vien` | vien: viên, viền, viễn, viện |
| 1835 | `phu cap` | phu: phù, phụ; cap: cấp, cập, cặp |
| 1835 | `tro cap` | tro: trò, trỏ, trở, trợ; cap: cấp, cập, cặp |
| 1835 | `ho tro` | ho: họ, hồ, hỗ, hộ, hợ; tro: trò, trỏ, trở, trợ |
| 1872 | `\b(?:wfh\|work\s+from\s+home\|lam\s+o\s+nha)\b` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 1879 | `cong` | cong: cong, công, cổng, cộng |
| 1880 | `ty` | - |
| 1881 | `duoc` | duoc: dược, được |
| 1882 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 1883 | `ho` | ho: họ, hồ, hỗ, hộ, hợ |
| 1884 | `tro` | tro: trò, trỏ, trở, trợ |
| 1885 | `tien` | tien: tiên, tiến, tiền, tiện |
| 1886 | `phu` | phu: phù, phụ |
| 1887 | `cap` | cap: cấp, cập, cặp |
| 1891 | `khong` | - |
| 1892 | `ap` | - |
| 1893 | `dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 1894 | `cho` | cho: cho, chó, chỗ, chờ, chở, chợ |
| 1895 | `the` | the: thẻ, thế, thể |
| 1919 | `\b(?:mot\|one\|1\|single\|don le\|ad hoc)\b` | don: dọn, dồn, đón, đơn; le: le, lê, lẻ, lẽ, lễ, lệ; hoc: học, hộc |
| 1920 | `\b(?:mot\|one\|1\|single\|don le\|ad hoc)\b` | don: dọn, dồn, đón, đơn; le: le, lê, lẻ, lẽ, lễ, lệ; hoc: học, hộc |
| 1929 | `neu ` | neu: nêu, nếu, nệu |
| 1931 | `truong hop` | truong: trương, trường, trưởng; hop: họp, hợp |
| 1932 | `ngay ` | ngay: ngay, ngày, ngây |
| 1933 | `day ` | day: đây, đầy |
| 1934 | `mot ` | - |
| 1936 | `ad hoc` | hoc: học, hộc |
| 1938 | `thuong xuyen` | thuong: thương, thường, thưởng |
| 2566 | `di muon` | di: di, dì, dị, đi; muon: muốn, muộn, mượn |
| 2566 | `toi tre` | toi: tôi, tỏi, tối, tội, tới |
| 2569 | `toi nay` | toi: tôi, tỏi, tối, tội, tới |
| 2569 | `cung ngay` | cung: cùng, cũng; ngay: ngay, ngày, ngây |
| 2569 | `same day` | day: đây, đầy |
| 2570 | `ngay mai` | ngay: ngay, ngày, ngây |
| 2570 | `ngay khac` | ngay: ngay, ngày, ngây; khac: khác, khắc |
| 2570 | `next day` | day: đây, đầy |
| 2573 | `bu trong cung ngay` | trong: trọng, trống; cung: cùng, cũng; ngay: ngay, ngày, ngây |
| 2573 | `quan ly chap thuan` | quan: quan, quán, quân, quản, quần, quận; thuan: thuẫn, thuận |
| 2575 | `bu trong cung ngay` | trong: trọng, trống; cung: cùng, cũng; ngay: ngay, ngày, ngây |
| 2586 | `khong duoc tu y bu sang ngay khac` | duoc: dược, được; tu: tu, tư, tủ, tứ, từ, tử, tự; sang: sàng, sáng; ngay: ngay, ngày, ngây; khac: khác, khắc |
| 2586 | `not make up on another day` | day: đây, đầy |
| 2589 | `bu sang ngay khac` | sang: sàng, sáng; ngay: ngay, ngày, ngây; khac: khác, khắc |
| 2589 | `another day` | day: đây, đầy |
| 2599 | `on-call` | - |
| 2599 | `on call` | - |
| 2599 | `truc` | truc: trúc, trực |
| 2600 | `su co` | su: sư, sứ, sử, sự; co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 2600 | `lam them` | lam: lam, làm, lâm, lạm, lắm |
| 2604 | `on-call` | - |
| 2604 | `khong tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 2607 | `thoi gian thuc te xu ly` | thuc: thúc, thục, thức, thực; te: tế, tệ |
| 2609 | `khong tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 2611 | `thoi gian thuc te xu ly` | thuc: thúc, thục, thức, thực; te: tế, tệ |
| 2622 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 2623 | `cham cong` | cham: chăm, chạm, chấm, chậm; cong: cong, công, cổng, cộng |
| 2627 | `nghia vu cham cong` | nghia: nghiá, nghĩa; cham: chăm, chạm, chấm, chậm; cong: cong, công, cổng, cộng |
| 2627 | `van phai cham cong` | van: văn, vấn, vẫn, vận; cham: chăm, chạm, chấm, chậm; cong: cong, công, cổng, cộng |
| 2631 | `nghia vu cham cong` | nghia: nghiá, nghĩa; cham: chăm, chạm, chấm, chậm; cong: cong, công, cổng, cộng |
| 2631 | `van phai cham cong` | van: văn, vấn, vẫn, vận; cham: chăm, chạm, chấm, chậm; cong: cong, công, cổng, cộng |
| 2658 | `(?<!khong\s)\bduoc\s+` | duoc: dược, được |
| 2708 | `ba me` | ba: bà, bá, bã |
| 2708 | `bo me` | bo: bỏ, bố, bổ, bộ |
| 2708 | `cha me` | cha: chá, chã |
| 2709 | `mat` | mat: mát, mất, mật, mắt, mặt |
| 2709 | `chet` | - |
| 2709 | `qua doi` | qua: quá, quả; doi: dõi, dồi, đòi, đôi, đối, đổi, đội, đời, đợi |
| 2710 | `huong luong` | huong: huống, hướng, hưởng; luong: luồng, lương, lường, lượng |
| 2713 | `\bnghi viec rieng huong luong\b\|\bpaid bereavement\b` | nghi: nghi, nghĩ, nghỉ, nghị; huong: huống, hướng, hưởng; luong: luồng, lương, lường, lượng |
| 2716 | `nghi viec rieng khong huong luong` | nghi: nghi, nghĩ, nghỉ, nghị; huong: huống, hướng, hưởng; luong: luồng, lương, lường, lượng |
| 2717 | `\b(?:cha/me\|cha me\|ba me\|bo me\|parent)\b` | cha: chá, chã; ba: bà, bá, bã; bo: bỏ, bố, bổ, bộ |
| 2720 | `\b(?:chet\|qua doi\|death\|died)\b` | qua: quá, quả; doi: dõi, dồi, đòi, đôi, đối, đổi, đội, đời, đợi |
| 2744 | `phep` | - |
| 2744 | `nghi hang nam` | nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; nam: nam, năm, nấm, nắm, nằm |
| 2747 | `\bchua(?:\s+lam)?\s+du\s+(?:mot\|1)\s+nam\b` | chua: chưa, chứa, chữa; lam: lam, làm, lâm, lạm, lắm; du: du, dù, dư, dụ, dữ, dự, đu, đủ; nam: nam, năm, nấm, nắm, nằm |
| 2748 | `\bchua(?:\s+lam)?\s+du\s+12\s+thang\b` | chua: chưa, chứa, chữa; lam: lam, làm, lâm, lạm, lắm; du: du, dù, dư, dụ, dữ, dự, đu, đủ; thang: thang, tháng, thăng, thắng, thẳng |
| 2749 | `\b(?:under\|less than)\s+(?:one\|1)\s+year\b` | than: thần, thắn |
| 2753 | `theo ty le` | le: le, lê, lẻ, lẽ, lễ, lệ |
| 2753 | `tuong ung voi thoi gian` | tuong: tương, tưởng, tượng; voi: vôi, vội, với |
| 2792 | `\b(?:su\s+dung\|dung\|use)\s+` | su: sư, sứ, sử, sự; dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 2798 | `\b(?:khong\|not)\s+$` | - |
| 2811 | `lam gi truoc` | lam: lam, làm, lâm, lạm, lắm |
| 2811 | `do first` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 2819 | `gi` | - |
| 2820 | `lam` | lam: lam, làm, lâm, lạm, lắm |
| 2821 | `ly` | - |
| 2824 | `nguoi` | - |
| 2825 | `phai` | - |
| 2826 | `quan` | quan: quan, quán, quân, quản, quần, quận |
| 2827 | `the` | the: thẻ, thế, thể |
| 2828 | `truoc` | - |
| 2833 | `truoc` | - |
| 2847 | `bao mat` | bao: bao, báo, bão, bảo; mat: mát, mất, mật, mắt, mặt |
| 2851 | `yeu cau` | yeu: yêu, yếu; cau: câu, cấu, cầu |
| 2852 | `bao dam` | bao: bao, báo, bão, bảo; dam: đám, đảm |
| 2853 | `can tuan thu` | can: cân, căn, cần, cận; tuan: tuân, tuấn, tuần; thu: thu, thú, thư, thủ, thứ, thử |
| 2854 | `tuan thu` | tuan: tuân, tuấn, tuần; thu: thu, thú, thư, thủ, thứ, thử |
| 2860 | `an toan` | an: án, ăn, ản, ấn; toan: toàn, toán |
| 2861 | `bao dam` | bao: bao, báo, bão, bảo; dam: đám, đảm |
| 2861 | `dam bao` | dam: đám, đảm; bao: bao, báo, bão, bảo |
| 2861 | `gi` | - |
| 2904 | `[ \t]+(?:is\|la\|serves as\|giu vai tro\|dam nhan)[ \t]+(?:the[ \t]+)?\b` | la: là, lá, lã; tro: trò, trỏ, trở, trợ; dam: đám, đảm; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; the: thẻ, thế, thể |
| 2922 | ` la ` | la: là, lá, lã |
| 2922 | ` co phai ` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 2977 | `khong` | - |
| 2977 | `duoc` | duoc: dược, được |
| 2977 | `phai` | - |
| 2977 | `trong` | trong: trọng, trống |
| 2987 | `\bbao nhieu (ngay\|gio\|phut\|tuan\|thang\|nam\|lan\|nguoi\|kg\|tan\|km\|lit)\b` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu; ngay: ngay, ngày, ngây; gio: gió, giỗ, giờ; tuan: tuân, tuấn, tuần; thang: thang, tháng, thăng, thắng, thẳng; nam: nam, năm, nấm, nắm, nằm; lan: lan, lân, lãn, lần, lẫn, lặn; tan: tan, tán, tân, tăn, tấn, tần, tận |
| 2989 | `(?:\d[\d.,]*\|mot\|hai\|ba\|bon\|nam\|sau\|bay\|tam\|chin\|muoi)\s*` | hai: hai, hài, hại, hải; ba: bà, bá, bã; nam: nam, năm, nấm, nắm, nằm; sau: sau, sáu, sâu; bay: bày, bảy, bẫy; tam: tám, tâm, tạm, tấm, tầm, tắm |
| 3008 | `khong` | - |
| 3008 | `duoc` | duoc: dược, được |
| 3008 | `phai` | - |
| 3008 | `trong` | trong: trọng, trống |
| 3016 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 3016 | `khong` | - |
| 3016 | `no` | no: nó, nợ |
| 3026 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 3026 | `khong` | - |
| 3026 | `no` | no: nó, nợ |
| 3081 | `gio cot loi` | gio: gió, giỗ, giờ; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 3083 | `khung bat dau` | bat: bất, bật, bắt; dau: dấu, dầu, đau, đâu, đầu |
| 3085 | `khung ket thuc` | thuc: thúc, thục, thức, thực |
| 3098 | `gio cot loi` | gio: gió, giỗ, giờ; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 3100 | `buoi sang` | sang: sàng, sáng |
| 3100 | `buoi chieu` | chieu: chiếu, chiều |
| 3108 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 3108 | `lam viec tu xa` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 3116 | `nha` | nha: nhà, nhá, nhã |
| 3222 | `cong` | cong: cong, công, cổng, cộng |
| 3222 | `ty` | - |
| 3245 | `\b(?:nghi\|phep\|leave)\b` | nghi: nghi, nghĩ, nghỉ, nghị |
| 3246 | `\b(?:truoc\|advance\|notice)\b` | - |
| 3249 | `\b(?:hon\|tren\|more than\|over)\s+(\d+)\s+(?:ngay\|day)` | hon: hôn, hơn; than: thần, thắn; ngay: ngay, ngày, ngây; day: đây, đầy |
| 3250 | `\b(\d+)\s+(?:ngay\|day)` | ngay: ngay, ngày, ngây; day: đây, đầy |
| 3260 | `\bphep nam\s+(\d+)-(\d+)\s+ngay\s+truoc\s+it nhat\s+(\d+)\s+ngay` | nam: nam, năm, nấm, nắm, nằm; ngay: ngay, ngày, ngây; nhat: nhất, nhật |
| 3267 | `\bphep nam\s+tren\s+(\d+)\s+ngay\s+truoc\s+it nhat\s+(\d+)\s+ngay` | nam: nam, năm, nấm, nắm, nằm; ngay: ngay, ngày, ngây; nhat: nhất, nhật |
| 3285 | `\b(?:truoc\|bao truoc\|xin truoc\|gui truoc\|advance notice)\s+(?:it nhat\s+)?(\d+)\s+(?:ngay\|day)` | bao: bao, báo, bão, bảo; nhat: nhất, nhật; ngay: ngay, ngày, ngây; day: đây, đầy |
| 3314 | `dang ky` | dang: dang, dạng, đang, đáng, đăng, đằng, đẳng; ky: ký, kỳ, kỵ, kỷ, kỹ |
| 3319 | `dang ky` | dang: dang, dạng, đang, đáng, đăng, đằng, đẳng; ky: ký, kỳ, kỵ, kỷ, kỹ |
| 3319 | `ngay lam viec lien truoc` | ngay: ngay, ngày, ngây; lam: lam, làm, lâm, lạm, lắm; lien: liên, liền |
| 3322 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 3325 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 3330 | `may gio duoc ve` | may: may, mày, máy, mây, mấy; gio: gió, giỗ, giờ; duoc: dược, được; ve: vé, vẻ, vẽ, về, vệ |
| 3330 | `gio duoc ve` | gio: gió, giỗ, giờ; duoc: dược, được; ve: vé, vẻ, vẽ, về, vệ |
| 3330 | `ket thuc` | thuc: thúc, thục, thức, thực |
| 3337 | `khung bat dau` | bat: bất, bật, bắt; dau: dấu, dầu, đau, đâu, đầu |
| 3338 | `khung ket thuc` | thuc: thúc, thục, thức, thực |
| 3354 | `buoi chieu` | chieu: chiếu, chiều |
| 3355 | `buoi sang` | sang: sàng, sáng |
| 3356 | `bat dau` | bat: bất, bật, bắt; dau: dấu, dầu, đau, đâu, đầu |
| 3357 | `ket thuc` | thuc: thúc, thục, thức, thực |
| 3360 | `\b(?:gio cot loi\|core hours?)\b` | gio: gió, giỗ, giờ; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 3363 | `\b(?:khung bat dau\|khung ket thuc\|nghi trua\|lunch break\|gio cot loi\|core hours?)\b` | bat: bất, bật, bắt; dau: dấu, dầu, đau, đâu, đầu; thuc: thúc, thục, thức, thực; nghi: nghi, nghĩ, nghỉ, nghị; gio: gió, giỗ, giờ; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 3393 | `lam bao nhieu gio` | lam: lam, làm, lâm, lạm, lắm; bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu; gio: gió, giỗ, giờ |
| 3394 | `lam may gio` | lam: lam, làm, lâm, lạm, lắm; may: may, mày, máy, mây, mấy; gio: gió, giỗ, giờ |
| 3395 | `lam bao nhieu tieng` | lam: lam, làm, lâm, lạm, lắm; bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 3396 | `lam may tieng` | lam: lam, làm, lâm, lạm, lắm; may: may, mày, máy, mây, mấy |
| 3406 | `tong thoi gian lam viec` | lam: lam, làm, lâm, lạm, lắm |
| 3407 | `thoi gian lam viec tieu chuan` | lam: lam, làm, lâm, lạm, lắm |
| 3420 | `ngay` | ngay: ngay, ngày, ngây |
| 3420 | `moi ngay` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời; ngay: ngay, ngày, ngây |
| 3420 | `mot ngay` | ngay: ngay, ngày, ngây |
| 3420 | `per day` | day: đây, đầy |
| 3421 | `tuan` | tuan: tuân, tuấn, tuần |
| 3421 | `moi tuan` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời; tuan: tuân, tuấn, tuần |
| 3421 | `mot tuan` | tuan: tuân, tuấn, tuần |
| 3434 | `\d+(?:[.,]\d+)?\s*(?:gio\|hours?)\s*(?:/\|moi\s+\|per\s+)` | gio: gió, giỗ, giờ; moi: môi, mọi, mỏi, mối, mỗi, mới, mời |
| 3459 | `gio cot loi` | gio: gió, giỗ, giờ; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 3460 | `gio cot loi` | gio: gió, giỗ, giờ; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 3461 | `bat dau` | bat: bất, bật, bắt; dau: dấu, dầu, đau, đâu, đầu |
| 3462 | `vao` | - |
| 3462 | `lam` | lam: lam, làm, lâm, lạm, lắm |
| 3464 | `khung bat dau` | bat: bất, bật, bắt; dau: dấu, dầu, đau, đâu, đầu |
| 3464 | `bat dau linh hoat` | bat: bất, bật, bắt; dau: dấu, dầu, đau, đâu, đầu |
| 3465 | `ket thuc` | thuc: thúc, thục, thức, thực |
| 3466 | `khung ket thuc` | thuc: thúc, thục, thức, thực |
| 3466 | `ket thuc tuong ung` | thuc: thúc, thục, thức, thực; tuong: tương, tưởng, tượng |
| 3467 | `khung gio` | gio: gió, giỗ, giờ |
| 3468 | `khung gio` | gio: gió, giỗ, giờ |
| 3468 | `thoi gian lam viec` | lam: lam, làm, lâm, lạm, lắm |
| 3473 | `gio cot loi` | gio: gió, giỗ, giờ; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 3475 | `khung bat dau` | bat: bất, bật, bắt; dau: dấu, dầu, đau, đâu, đầu |
| 3476 | `bat dau linh hoat` | bat: bất, bật, bắt; dau: dấu, dầu, đau, đâu, đầu |
| 3478 | `khung ket thuc` | thuc: thúc, thục, thức, thực |
| 3479 | `ket thuc tuong ung` | thuc: thúc, thục, thức, thực; tuong: tương, tưởng, tượng |
| 3481 | `nghi trua` | nghi: nghi, nghĩ, nghỉ, nghị |
| 3568 | `ngay` | ngay: ngay, ngày, ngây |
| 3568 | `tuan` | tuan: tuân, tuấn, tuần |
| 3568 | `day` | day: đây, đầy |
| 3659 | `luong` | luong: luồng, lương, lường, lượng |
| 3660 | `ngay nao` | ngay: ngay, ngày, ngây |
| 3660 | `ngay tra` | ngay: ngay, ngày, ngây; tra: trá, trã, trả |
| 3668 | `tra luong` | tra: trá, trã, trả; luong: luồng, lương, lường, lượng |
| 3671 | `tai nan` | tai: tai, tài, tái, tại, tải; nan: năn, nạn |
| 3679 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 3679 | `lam viec tu xa` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 3680 | `tai nan` | tai: tai, tài, tái, tại, tải; nan: năn, nạn |
| 3697 | `ngay tra luong` | ngay: ngay, ngày, ngây; tra: trá, trã, trả; luong: luồng, lương, lường, lượng |
| 3714 | `dua` | dua: dựa, đũa, đưa |
| 3714 | `gui` | - |
| 3714 | `chia se` | se: sẻ, sẽ |
| 3718 | `mat khau` | mat: mát, mất, mật, mắt, mặt; khau: khấu, khẩu |
| 3720 | `khoa api` | - |
| 3721 | `token truy cap` | cap: cấp, cập, cặp |
| 3730 | `dua` | dua: dựa, đũa, đưa |
| 3730 | `gui` | - |
| 3730 | `chia se` | se: sẻ, sẽ |
| 3739 | `cam chia se` | cam: cảm, cấm; se: sẻ, sẽ |
| 3739 | `khong duoc chia se` | duoc: dược, được; se: sẻ, sẽ |
| 3739 | `do not share` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 3747 | `chi duoc chia se` | chi: chi, chí, chỉ, chị; duoc: dược, được; se: sẻ, sẽ |
| 3748 | `duoc chia se khi` | duoc: dược, được; se: sẻ, sẽ |
| 3749 | `chia se khi co phe duyet` | se: sẻ, sẽ; co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 3750 | `may share if` | may: may, mày, máy, mây, mấy |
| 3755 | `tru khi` | tru: trú, trừ, trữ |
| 3755 | `ngoai tru` | ngoai: ngoài, ngoại; tru: trú, trừ, trữ |
| 3791 | `khi nao` | - |
| 3792 | `tham gia` | tham: thâm, thẩm; gia: gia, già, giá, giã, giả |
| 3792 | `duoc huong` | duoc: dược, được; huong: huống, hướng, hưởng |
| 3815 | `phu cap` | phu: phù, phụ; cap: cấp, cập, cặp |
| 3816 | `phu cap` | phu: phù, phụ; cap: cấp, cập, cặp |
| 3817 | `phu cap` | phu: phù, phụ; cap: cấp, cập, cặp |
| 3883 | `khi nao` | - |
| 3884 | `tham gia` | tham: thâm, thẩm; gia: gia, già, giá, giã, giả |
| 3884 | `duoc huong` | duoc: dược, được; huong: huống, hướng, hưởng |
| 3894 | `duoc` | duoc: dược, được |
| 3897 | `tham` | tham: thâm, thẩm |
| 3905 | `sau thu viec` | sau: sau, sáu, sâu; thu: thu, thú, thư, thủ, thứ, thử |
| 3906 | `hoan thanh thu viec` | hoan: hoàn, hoãn; thu: thu, thú, thư, thủ, thứ, thử |
| 3907 | `nhan vien chinh thuc` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; vien: viên, viền, viễn, viện; chinh: chính, chỉnh; thuc: thúc, thục, thức, thực |
| 3910 | `sau thu viec` | sau: sau, sáu, sâu; thu: thu, thú, thư, thủ, thứ, thử |
| 3911 | `sau khi hoan thanh` | sau: sau, sáu, sâu; hoan: hoàn, hoãn |
| 3911 | `thu viec` | thu: thu, thú, thư, thủ, thứ, thử |
| 3912 | `nhan vien chinh thuc` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; vien: viên, viền, viễn, viện; chinh: chính, chỉnh; thuc: thúc, thục, thức, thực |
| 3920 | `danh sach bao hiem` | danh: dành, đánh; sach: sách, sạch; bao: bao, báo, bão, bảo |
| 3921 | `danh sach bao hiem` | danh: dành, đánh; sach: sách, sạch; bao: bao, báo, bão, bảo |
| 3924 | `dieu khoan loai tru` | khoan: khoán, khoản; tru: trú, trừ, trữ |
| 3925 | `dieu khoan loai tru` | khoan: khoán, khoản; tru: trú, trừ, trữ |
| 3938 | `khong quy dinh` | quy: quy, quý, quỳ, quỹ; dinh: dính, đinh, đình, đính, đỉnh, định |
| 3939 | `khong neu` | neu: nêu, nếu, nệu |
| 3940 | `khong xac dinh` | dinh: dính, đinh, đình, đính, đỉnh, định |
| 3941 | `khong co ty le co dinh` | co: có, cô, cơ, cố, cổ, cờ, cỡ; le: le, lê, lẻ, lẽ, lễ, lệ; dinh: dính, đinh, đình, đính, đỉnh, định |
| 3945 | `no fixed` | no: nó, nợ |
| 3962 | `^(?:co\|khong\|yes\|no)\b[\s,.:;-]*` | co: có, cô, cơ, cố, cổ, cờ, cỡ; no: nó, nợ |
| 3968 | `(?:\s+(?:dung\|phai)\s+khong\|\s+khong)$` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |

### `app/services/grounded_answer_service.py` (1268)

| Dòng | Cue | Từ có thể va chạm |
|---:|---|---|
| 151 | `(?<!\d)\d+(?:[.,]\d+)?\s*(?:nguoi\|nhan\s+su\|nhan\s+vien\|employees?\|people)\b` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; su: sư, sứ, sử, sự; vien: viên, viền, viễn, viện |
| 160 | `(?<!\d)(?:[01]?\d\|2[0-3])(?:[:h][0-5]\d)?\s*(?:-\|\u2013\|\u2014\|den\|to)\s*(?:[01]?\d\|2[0-3])(?:[:h][0-5]\d)?` | to: tố, tổ, tờ |
| 166 | `(?<!\d)\d+(?:[.,]\d+)?\s*(?:phut\|gio\|ngay\|tuan\|thang\|nam\|minutes?\|hours?\|days?\|weeks?\|months?\|years?)\b` | gio: gió, giỗ, giờ; ngay: ngay, ngày, ngây; tuan: tuân, tuấn, tuần; thang: thang, tháng, thăng, thắng, thẳng; nam: nam, năm, nấm, nắm, nằm |
| 196 | `ket noi an toan` | noi: nói, nơi, nối, nội; an: án, ăn, ản, ấn; toan: toàn, toán |
| 197 | `xac thuc nhieu lop` | thuc: thúc, thục, thức, thực; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu; lop: lốp, lớp |
| 198 | `thiet bi duoc phe duyet` | thiet: thiết, thiệt; bi: bí, bị; duoc: dược, được |
| 199 | `thiet bi duoc quan ly` | thiet: thiết, thiệt; bi: bí, bị; duoc: dược, được; quan: quan, quán, quân, quản, quần, quận |
| 200 | `khong de nguoi khong co tham quyen` | de: dễ, đe, đè, đẻ, đề, để; co: có, cô, cơ, cố, cổ, cờ, cỡ; tham: thâm, thẩm |
| 201 | `ma hoa` | ma: ma, mà, má, mã, mạ, mả; hoa: hòa, hóa |
| 219 | `bao` | bao: bao, báo, bão, bảo |
| 220 | `cap` | cap: cấp, cập, cặp |
| 221 | `dai` | dai: dài, dải, đại |
| 222 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 223 | `duoc` | duoc: dược, được |
| 226 | `hien` | hien: hiển, hiện |
| 227 | `ho` | ho: họ, hồ, hỗ, hộ, hợ |
| 228 | `luong` | luong: luồng, lương, lường, lượng |
| 229 | `lan` | lan: lan, lân, lãn, lần, lẫn, lặn |
| 230 | `lau` | - |
| 231 | `moi` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời |
| 232 | `mot` | - |
| 233 | `muc` | muc: múc, mục, mức, mực |
| 234 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 235 | `nao` | - |
| 236 | `ngay` | ngay: ngay, ngày, ngây |
| 237 | `nhieu` | nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 238 | `phan` | phan: phan, phán, phân, phản, phần, phận |
| 239 | `phu` | phu: phù, phụ |
| 245 | `tai` | tai: tai, tài, tái, tại, tải |
| 246 | `tham` | tham: thâm, thẩm |
| 247 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 248 | `tien` | tien: tiên, tiến, tiền, tiện |
| 249 | `toi` | toi: tôi, tỏi, tối, tội, tới |
| 250 | `tram` | tram: trám, trăm, trạm |
| 251 | `tro` | tro: trò, trỏ, trở, trợ |
| 252 | `thuoc` | thuoc: thuộc, thước |
| 253 | `trieu` | - |
| 259 | `ca` | ca: cá, cã, cả, cầ |
| 260 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 261 | `day` | day: đây, đầy |
| 263 | `deu` | - |
| 264 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 265 | `dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 269 | `gio` | gio: gió, giỗ, giờ |
| 270 | `khong` | - |
| 274 | `moi` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời |
| 275 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 276 | `ngay` | ngay: ngay, ngày, ngây |
| 277 | `nguoi` | - |
| 278 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 279 | `phai` | - |
| 280 | `tat` | tat: tất, tật, tắt |
| 281 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 282 | `tien` | tien: tiên, tiến, tiền, tiện |
| 283 | `tro` | tro: trò, trỏ, trở, trợ |
| 284 | `tuan` | tuan: tuân, tuấn, tuần |
| 285 | `vien` | vien: viên, viền, viễn, viện |
| 292 | `ben` | - |
| 292 | `cong` | cong: cong, công, cổng, cộng |
| 292 | `ty` | - |
| 292 | `khoang` | - |
| 292 | `thi` | thi: thi, thì, thí, thị |
| 294 | `du lieu` | du: du, dù, dư, dụ, dữ, dự, đu, đủ |
| 295 | `an toan` | an: án, ăn, ản, ấn; toan: toàn, toán |
| 295 | `bao mat` | bao: bao, báo, bão, bảo; mat: mát, mất, mật, mắt, mặt |
| 300 | `ai` | - |
| 305 | `bi` | bi: bí, bị |
| 317 | `cau hoi goi y` | cau: câu, cấu, cầu; hoi: hỏi, hồi, hội; goi: gói, gọi, gợi |
| 318 | `cau hoi kiem thu` | cau: câu, cấu, cầu; hoi: hỏi, hồi, hội; kiem: kiếm, kiểm; thu: thu, thú, thư, thủ, thứ, thử |
| 319 | `cau hoi tham khao` | cau: câu, cấu, cầu; hoi: hỏi, hồi, hội; tham: thâm, thẩm |
| 320 | `cau hoi mau` | cau: câu, cấu, cầu; hoi: hỏi, hồi, hội; mau: mâu, mẫu |
| 321 | `tinh huong mau` | tinh: tình, tính, tỉnh; huong: huống, hướng, hưởng; mau: mâu, mẫu |
| 322 | `ky vong cau tra loi` | ky: ký, kỳ, kỵ, kỷ, kỹ; vong: vòng, vọng; cau: câu, cấu, cầu; tra: trá, trã, trả; loi: lõi, lối, lỗi, lội, lời, lợi |
| 323 | `cau tra loi ai` | cau: câu, cấu, cầu; tra: trá, trã, trả; loi: lõi, lối, lỗi, lội, lời, lợi |
| 327 | `expected ai answer` | - |
| 331 | `kiem thu rag` | kiem: kiếm, kiểm; thu: thu, thú, thư, thủ, thứ, thử |
| 333 | `no-answer test` | no: nó, nợ |
| 336 | `muc luc` | muc: múc, mục, mức, mực; luc: lúc, lục, lực |
| 337 | `danh muc tai lieu` | danh: dành, đánh; muc: múc, mục, mức, mực; tai: tai, tài, tái, tại, tải |
| 338 | `tai lieu lien quan` | tai: tai, tài, tái, tại, tải; lien: liên, liền; quan: quan, quán, quân, quản, quần, quận |
| 339 | `lich su phien ban` | su: sư, sứ, sử, sự; ban: ban, bàn, bán, bạn, bản, bận |
| 340 | `kiem soat tai lieu` | kiem: kiếm, kiểm; tai: tai, tài, tái, tại, tải |
| 346 | `khong tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 347 | `khong duoc` | duoc: dược, được |
| 348 | `khong phai` | - |
| 349 | `khong cam` | cam: cảm, cấm |
| 350 | `khong bi han che` | bi: bí, bị; han: hàn, hán, hân, hạn, hẳn |
| 351 | `khong bi gioi han` | bi: bí, bị; han: hàn, hán, hân, hạn, hẳn |
| 352 | `khong thay the` | the: thẻ, thế, thể |
| 353 | `duoc phep` | duoc: dược, được |
| 354 | `bat buoc` | bat: bất, bật, bắt; buoc: buộc, bước |
| 355 | `bo sung` | bo: bỏ, bố, bổ, bộ |
| 356 | `phai` | - |
| 357 | `tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 375 | `an` | an: án, ăn, ản, ấn |
| 377 | `bao` | bao: bao, báo, bão, bảo |
| 378 | `cao` | cao: cáo, cạo |
| 379 | `cap` | cap: cấp, cập, cặp |
| 380 | `che` | - |
| 381 | `chuong` | - |
| 386 | `dieu` | - |
| 387 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 388 | `du` | du: du, dù, dư, dụ, dữ, dự, đu, đủ |
| 389 | `giam` | giam: giám, giảm |
| 390 | `hang` | hang: hàng, hãng, hạng, hằng |
| 391 | `ho` | ho: họ, hồ, hỗ, hộ, hợ |
| 392 | `hoi` | hoi: hỏi, hồi, hội |
| 393 | `hop` | hop: họp, hợp |
| 394 | `ke` | ke: kê, kế, kể, kệ |
| 395 | `kien` | kien: kiến, kiện |
| 396 | `khach` | - |
| 397 | `kiem` | kiem: kiếm, kiểm |
| 399 | `lieu` | - |
| 400 | `mat` | mat: mát, mất, mật, mắt, mặt |
| 401 | `noi` | noi: nói, nơi, nối, nội |
| 402 | `phap` | - |
| 406 | `quyen` | - |
| 407 | `rieng` | - |
| 410 | `soc` | - |
| 411 | `thu` | thu: thu, thú, thư, thủ, thứ, thử |
| 412 | `thong` | thong: thông, thống |
| 413 | `tin` | tin: tin, tín |
| 414 | `toan` | toan: toàn, toán |
| 415 | `trinh` | - |
| 416 | `truc` | truc: trúc, trực |
| 417 | `tuan` | tuan: tuân, tuấn, tuần |
| 418 | `tu` | tu: tu, tư, tủ, tứ, từ, tử, tự |
| 419 | `uy` | - |
| 423 | `ban` | ban: ban, bàn, bán, bạn, bản, bận |
| 423 | `bo` | bo: bỏ, bố, bổ, bộ |
| 423 | `hoi` | hoi: hỏi, hồi, hội |
| 423 | `khoi` | khoi: khôi, khỏi, khối, khởi |
| 423 | `phong` | phong: phong, phòng, phóng, phỏng |
| 423 | `trung` | trung: trùng, trưng |
| 423 | `uy` | - |
| 423 | `van` | van: văn, vấn, vẫn, vận |
| 425 | `ai` | - |
| 428 | `ban` | ban: ban, bàn, bán, bạn, bản, bận |
| 429 | `bo` | bo: bỏ, bố, bổ, bộ |
| 432 | `cong` | cong: cong, công, cổng, cộng |
| 436 | `chuyen` | chuyen: chuyên, chuyến, chuyển, chuyện |
| 437 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 438 | `dieu` | - |
| 440 | `doc` | doc: đọc, đốc, độc |
| 443 | `giam` | giam: giám, giảm |
| 446 | `gioi` | - |
| 448 | `hanh` | - |
| 449 | `khoi` | khoi: khôi, khỏi, khối, khởi |
| 451 | `nghe` | nghe: nghề, nghệ |
| 454 | `phu` | phu: phù, phụ |
| 457 | `phong` | phong: phong, phòng, phóng, phỏng |
| 458 | `san` | san: sản, sẵn |
| 461 | `toi` | toi: tôi, tỏi, tối, tội, tới |
| 462 | `tong` | - |
| 463 | `trach` | - |
| 464 | `truong` | truong: trương, trường, trưởng |
| 465 | `thieu` | thieu: thiếu, thiểu, thiệu |
| 466 | `to` | to: tố, tổ, tờ |
| 467 | `ty` | - |
| 468 | `van` | van: văn, vấn, vẫn, vận |
| 495 | `due to` | to: tố, tổ, tờ |
| 500 | `ly do` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 501 | `nguyen nhan` | nguyen: nguyên, nguyễn, nguyện; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 504 | `dung de` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng; de: dễ, đe, đè, đẻ, đề, để |
| 505 | `lam gi` | lam: lam, làm, lâm, lạm, lắm |
| 506 | `dung lam gi` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng; lam: lam, làm, lâm, lạm, lắm |
| 513 | `co phai` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 514 | `dung khong` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 515 | `phai khong` | - |
| 518 | `do ` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 521 | `khong` | - |
| 521 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 521 | `dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 521 | `phai` | - |
| 521 | `no` | no: nó, nợ |
| 522 | `toi da` | toi: tôi, tỏi, tối, tội, tới; da: dá, đa, đà, đã |
| 522 | `khong qua` | qua: quá, quả |
| 523 | `toi da` | toi: tôi, tỏi, tối, tội, tới; da: dá, đa, đà, đã |
| 523 | `khong qua` | qua: quá, quả |
| 531 | `bao` | bao: bao, báo, bão, bảo |
| 531 | `nhieu` | nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 531 | `cua` | cua: của, cửa |
| 531 | `duoc` | duoc: dược, được |
| 540 | `do not provide` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 587 | ` duoc quy dinh nhu the nao` | duoc: dược, được; quy: quy, quý, quỳ, quỹ; dinh: dính, đinh, đình, đính, đỉnh, định; the: thẻ, thế, thể |
| 588 | ` duoc thuc hien nhu the nao` | duoc: dược, được; thuc: thúc, thục, thức, thực; hien: hiển, hiện; the: thẻ, thế, thể |
| 589 | ` duoc ap dung nhu the nao` | duoc: dược, được; dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng; the: thẻ, thế, thể |
| 817 | `no_selected_sources` | no: nó, nợ |
| 1934 | `dai` | dai: dài, dải, đại |
| 1934 | `luong` | luong: luồng, lương, lường, lượng |
| 2166 | `llm_no_answer_sentinel` | no: nó, nợ |
| 2222 | `llm_no_answer_like_json` | no: nó, nợ |
| 2748 | ` is the controlling semantic relation.` | the: thẻ, thế, thể |
| 2921 | ` only when no displayed source directly supports the required values.` | no: nó, nợ; the: thẻ, thế, thể |
| 3024 | ` la ` | la: là, lá, lã |
| 3032 | ` la ` | la: là, lá, lã |
| 3088 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 3153 | `tai lieu mau` | tai: tai, tài, tái, tại, tải; mau: mâu, mẫu |
| 3154 | `trang ` | trang: trạng, trắng |
| 3155 | `chinh sach nghi cua nguoi lao dong` | chinh: chính, chỉnh; sach: sách, sạch; nghi: nghi, nghĩ, nghỉ, nghị; cua: của, cửa; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 3239 | `tai` | tai: tai, tài, tái, tại, tải |
| 3239 | `chon` | - |
| 3239 | `lam` | lam: lam, làm, lâm, lạm, lắm |
| 3283 | `public ai` | - |
| 3283 | `ai cong cong` | cong: cong, công, cổng, cộng |
| 3283 | `dich vu ai cong cong` | dich: dịch, đích, địch; cong: cong, công, cổng, cộng |
| 3283 | `cong cu ai` | cong: cong, công, cổng, cộng; cu: cù, cũ, cụ, cứ |
| 3284 | `kho ma nguon` | ma: ma, mà, má, mã, mạ, mả |
| 3284 | `kho ca nhan` | ca: cá, cã, cả, cầ; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 3285 | `email ca nhan` | ca: cá, cã, cả, cầ; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 3294 | ` la ai` | la: là, lá, lã |
| 3295 | ` ai` | - |
| 3319 | `(?:co phai la\|phai la\|\bla\b\|\bis\b\|\bare\b)\s+(.+?)(?:\s+(?:khong\|dung khong\|phai khong)\|[?.]\|$)` | co: có, cô, cơ, cố, cổ, cờ, cỡ; la: là, lá, lã; dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 3559 | `thong bao` | thong: thông, thống; bao: bao, báo, bão, bảo |
| 3560 | `ngay` | ngay: ngay, ngày, ngây |
| 3560 | `ngay khi co the` | ngay: ngay, ngày, ngây; co: có, cô, cơ, cố, cổ, cờ, cỡ; the: thẻ, thế, thể |
| 3564 | `thanh toan` | toan: toàn, toán |
| 3565 | `cham dut` | cham: chăm, chạm, chấm, chậm |
| 3565 | `nghi viec` | nghi: nghi, nghĩ, nghỉ, nghị |
| 3581 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 3582 | `vien` | vien: viên, viền, viễn, viện |
| 3586 | `xu` | - |
| 3587 | `ly` | - |
| 3588 | `viec` | - |
| 3589 | `duoc` | duoc: dược, được |
| 3590 | `quy` | quy: quy, quý, quỳ, quỹ |
| 3591 | `dinh` | dinh: dính, đinh, đình, đính, đỉnh, định |
| 3721 | `moi` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời |
| 3721 | `tat ca` | tat: tất, tật, tắt; ca: cá, cã, cả, cầ |
| 3721 | `deu` | - |
| 3758 | `bao lau` | bao: bao, báo, bão, bảo |
| 3759 | `chua du` | chua: chưa, chứa, chữa; du: du, dù, dư, dụ, dữ, dự, đu, đủ |
| 3760 | `it nhat` | nhat: nhất, nhật |
| 3761 | `khong qua` | qua: quá, quả |
| 3764 | `sau ` | sau: sau, sáu, sâu |
| 3765 | `toi da` | toi: tôi, tỏi, tối, tội, tới; da: dá, đa, đà, đã |
| 3766 | `toi thieu` | toi: tôi, tỏi, tối, tội, tới; thieu: thiếu, thiểu, thiệu |
| 3769 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 3770 | `lam viec tu xa` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 3778 | `gio` | gio: gió, giỗ, giờ |
| 3779 | `gio` | gio: gió, giỗ, giờ |
| 3780 | `ngay` | ngay: ngay, ngày, ngây |
| 3780 | `day` | day: đây, đầy |
| 3781 | `ngay` | ngay: ngay, ngày, ngây |
| 3781 | `day` | day: đây, đầy |
| 3782 | `tuan` | tuan: tuân, tuấn, tuần |
| 3783 | `tuan` | tuan: tuân, tuấn, tuần |
| 3784 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 3785 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 3786 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 3787 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 3836 | `nghi hang nam` | nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; nam: nam, năm, nấm, nắm, nằm |
| 3836 | `nghi phep nam` | nghi: nghi, nghĩ, nghỉ, nghị; nam: nam, năm, nấm, nắm, nằm |
| 3836 | `phep nam` | nam: nam, năm, nấm, nắm, nằm |
| 3840 | `dieu kien binh thuong` | kien: kiến, kiện; thuong: thương, thường, thưởng |
| 3841 | `chua thanh nien` | chua: chưa, chứa, chữa |
| 3842 | `khuyet tat` | tat: tất, tật, tắt |
| 3843 | `nang nhoc` | nang: nâng, năng, nẵng, nặng |
| 3844 | `doc hai` | doc: đọc, đốc, độc; hai: hai, hài, hại, hải |
| 3845 | `nguy hiem` | - |
| 3846 | `muc nghi` | muc: múc, mục, mức, mực; nghi: nghi, nghĩ, nghỉ, nghị |
| 3847 | `so ngay` | so: so, sơ, số, sổ, sở, sợ; ngay: ngay, ngày, ngây |
| 3863 | `doi tuong` | doi: dõi, dồi, đòi, đôi, đối, đổi, đội, đời, đợi; tuong: tương, tưởng, tượng |
| 3864 | `muc nghi` | muc: múc, mục, mức, mực; nghi: nghi, nghĩ, nghỉ, nghị |
| 3865 | `so ngay` | so: so, sơ, số, sổ, sở, sợ; ngay: ngay, ngày, ngây |
| 3889 | `khong` | - |
| 3889 | `no` | no: nó, nợ |
| 4178 | `khong thuoc` | thuoc: thuộc, thước |
| 4178 | `khong phai` | - |
| 4178 | `khong` | - |
| 4184 | `bao nhieu` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 4235 | `cua` | cua: của, cửa |
| 4235 | `chinh` | chinh: chính, chỉnh |
| 4235 | `sach` | sach: sách, sạch |
| 4235 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 4235 | `duoc` | duoc: dược, được |
| 4235 | `moi` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời |
| 4305 | `toi thieu` | toi: tôi, tỏi, tối, tội, tới; thieu: thiếu, thiểu, thiệu |
| 4305 | `muc min` | muc: múc, mục, mức, mực |
| 4307 | `toi da` | toi: tôi, tỏi, tối, tội, tới; da: dá, đa, đà, đã |
| 4307 | `muc max` | muc: múc, mục, mức, mực |
| 4309 | `khoang` | - |
| 4309 | `dai` | dai: dài, dải, đại |
| 4310 | `tu` | tu: tu, tư, tủ, tứ, từ, tử, tự |
| 4310 | `den` | - |
| 4327 | `khoang` | - |
| 4327 | `dai` | dai: dài, dải, đại |
| 4358 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 4360 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 4495 | `ngay` | ngay: ngay, ngày, ngây |
| 4496 | `tuan` | tuan: tuân, tuấn, tuần |
| 4497 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 4498 | `tien` | tien: tiên, tiến, tiền, tiện |
| 4499 | `tro` | tro: trò, trỏ, trở, trợ |
| 4500 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 4501 | `day` | day: đây, đầy |
| 4522 | `khong` | - |
| 4525 | `loai` | - |
| 4526 | `loai` | - |
| 4530 | `dac` | - |
| 4530 | `biet` | biet: biết, biệt |
| 4531 | `dac` | - |
| 4531 | `biet` | biet: biết, biệt |
| 4545 | ` muc ` | muc: múc, mục, mức, mực |
| 4545 | ` doi tuong ` | doi: dõi, dồi, đòi, đôi, đối, đổi, đội, đời, đợi; tuong: tương, tưởng, tượng |
| 4664 | `tai sao` | tai: tai, tài, tái, tại, tải |
| 4674 | `ai` | - |
| 4708 | `gio` | gio: gió, giỗ, giờ |
| 4709 | `gio` | gio: gió, giỗ, giờ |
| 4710 | `ngay` | ngay: ngay, ngày, ngây |
| 4710 | `day` | day: đây, đầy |
| 4711 | `ngay` | ngay: ngay, ngày, ngây |
| 4711 | `day` | day: đây, đầy |
| 4712 | `tuan` | tuan: tuân, tuấn, tuần |
| 4713 | `tuan` | tuan: tuân, tuấn, tuần |
| 4714 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 4715 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 4716 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 4717 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 4718 | `nguoi` | - |
| 4718 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 4719 | `nguoi` | - |
| 4719 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 4720 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 4720 | `trieu` | - |
| 4721 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 4721 | `trieu` | - |
| 4927 | `cong` | cong: cong, công, cổng, cộng |
| 4927 | `ty` | - |
| 4927 | `duoc` | duoc: dược, được |
| 4927 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 4927 | `ho` | ho: họ, hồ, hỗ, hộ, hợ |
| 4927 | `tro` | tro: trò, trỏ, trở, trợ |
| 4927 | `tien` | tien: tiên, tiến, tiền, tiện |
| 4953 | `cong` | cong: cong, công, cổng, cộng |
| 4954 | `cua` | cua: của, cửa |
| 4955 | `duoc` | duoc: dược, được |
| 4956 | `khong` | - |
| 4957 | `khoan` | khoan: khoán, khoản |
| 4958 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 4959 | `rieng` | - |
| 4960 | `tien` | tien: tiên, tiến, tiền, tiện |
| 4961 | `tro` | tro: trò, trỏ, trở, trợ |
| 4962 | `vien` | vien: viên, viền, viễn, viện |
| 4997 | `phu cap` | phu: phù, phụ; cap: cấp, cập, cặp |
| 4997 | `tro cap` | tro: trò, trỏ, trở, trợ; cap: cấp, cập, cặp |
| 4997 | `ho tro` | ho: họ, hồ, hỗ, hộ, hợ; tro: trò, trỏ, trở, trợ |
| 5003 | `ap dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 5004 | `khong ap dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 5005 | `duoc phe duyet` | duoc: dược, được |
| 5027 | `lam bao nhieu gio` | lam: lam, làm, lâm, lạm, lắm; bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu; gio: gió, giỗ, giờ |
| 5028 | `lam may gio` | lam: lam, làm, lâm, lạm, lắm; may: may, mày, máy, mây, mấy; gio: gió, giỗ, giờ |
| 5038 | `gio cot loi` | gio: gió, giỗ, giờ; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 5039 | `khung gio lam` | gio: gió, giỗ, giờ; lam: lam, làm, lâm, lạm, lắm |
| 5040 | `khung bat dau` | bat: bất, bật, bắt; dau: dấu, dầu, đau, đâu, đầu |
| 5041 | `khung ket thuc` | thuc: thúc, thục, thức, thực |
| 5046 | `vao` | - |
| 5046 | `lam` | lam: lam, làm, lâm, lạm, lắm |
| 5052 | `tong thoi gian lam viec` | lam: lam, làm, lâm, lạm, lắm |
| 5053 | `thoi gian lam viec tieu chuan` | lam: lam, làm, lâm, lạm, lắm |
| 5054 | `khung bat dau linh hoat` | bat: bất, bật, bắt; dau: dấu, dầu, đau, đâu, đầu |
| 5055 | `khung ket thuc tuong ung` | thuc: thúc, thục, thức, thực; tuong: tương, tưởng, tượng |
| 5056 | `gio cot loi` | gio: gió, giỗ, giờ; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 5093 | `cuoi` | cuoi: cuối, cưới |
| 5093 | `ket hon` | hon: hôn, hơn |
| 5094 | `con toi` | con: con, còn, cơn, cồn; toi: tôi, tỏi, tối, tội, tới |
| 5094 | `con de` | con: con, còn, cơn, cồn; de: dễ, đe, đè, đẻ, đề, để |
| 5094 | `con nuoi` | con: con, còn, cơn, cồn |
| 5094 | `my child` | - |
| 5099 | `ba me` | ba: bà, bá, bã |
| 5099 | `bo me` | bo: bỏ, bố, bổ, bộ |
| 5099 | `cha me` | cha: chá, chã |
| 5101 | `mat` | mat: mát, mất, mật, mắt, mặt |
| 5101 | `chet` | - |
| 5101 | `qua doi` | qua: quá, quả; doi: dõi, dồi, đòi, đôi, đối, đổi, đội, đời, đợi |
| 5105 | `nghi` | nghi: nghi, nghĩ, nghỉ, nghị |
| 5105 | `phep` | - |
| 5109 | `su co` | su: sư, sứ, sử, sự; co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 5112 | `khan cap` | khan: khăn, khẩn; cap: cấp, cập, cặp |
| 5122 | `bao truoc` | bao: bao, báo, bão, bảo |
| 5123 | `gui don truoc` | don: dọn, dồn, đón, đơn |
| 5124 | `xin truoc` | - |
| 5125 | `truoc bao lau` | bao: bao, báo, bão, bảo |
| 5130 | `khong luong` | luong: luồng, lương, lường, lượng |
| 5130 | `dai ngay` | dai: dài, dải, đại; ngay: ngay, ngày, ngây |
| 5132 | `\b(\d+)\s*ngay\b` | ngay: ngay, ngày, ngây |
| 5135 | `\b(?:hon\|tren\|more than\|over)\s+$` | hon: hôn, hơn; than: thần, thắn |
| 5137 | `\b(?:duoi\|it hon\|less than\|under)\s+$` | hon: hôn, hơn; than: thần, thắn |
| 5141 | `bi sot` | bi: bí, bị |
| 5141 | `om dau` | dau: dấu, dầu, đau, đâu, đầu |
| 5141 | `bi om` | bi: bí, bị |
| 5145 | `nghi viec` | nghi: nghi, nghĩ, nghỉ, nghị |
| 5145 | `cham dut` | cham: chăm, chạm, chấm, chậm |
| 5145 | `thoi viec` | - |
| 5149 | `phep chua dung` | chua: chưa, chứa, chữa; dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 5149 | `phep chua nghi` | chua: chưa, chứa, chữa; nghi: nghi, nghĩ, nghỉ, nghị |
| 5149 | `phep con lai` | con: con, còn, cơn, cồn; lai: lái, lại |
| 5172 | `\bnghi khong luong dai ngay\b` | nghi: nghi, nghĩ, nghỉ, nghị; luong: luồng, lương, lường, lượng; dai: dài, dải, đại; ngay: ngay, ngày, ngây |
| 5179 | `nghi khong huong luong` | nghi: nghi, nghĩ, nghỉ, nghị; huong: huống, hướng, hưởng; luong: luồng, lương, lường, lượng |
| 5181 | `\bde nghi tu\s+\d+\s+ngay\b` | de: dễ, đe, đè, đẻ, đề, để; nghi: nghi, nghĩ, nghỉ, nghị; tu: tu, tư, tủ, tứ, từ, tử, tự; ngay: ngay, ngày, ngây |
| 5223 | `dang nghi phep` | dang: dang, dạng, đang, đáng, đăng, đằng, đẳng; nghi: nghi, nghĩ, nghỉ, nghị |
| 5224 | `nhan vien nghi` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; vien: viên, viền, viễn, viện; nghi: nghi, nghĩ, nghỉ, nghị |
| 5225 | `quyen nghi` | nghi: nghi, nghĩ, nghỉ, nghị |
| 5230 | `nguoi thay the` | the: thẻ, thế, thể |
| 5230 | `phuong an hop ly` | an: án, ăn, ản, ấn; hop: họp, hợp |
| 5231 | `dong y` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 5235 | `ghi nhan thoi gian thuc te` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; thuc: thúc, thục, thức, thực; te: tế, tệ |
| 5236 | `thoi gian thuc te xu ly` | thuc: thúc, thục, thức, thực; te: tế, tệ |
| 5242 | `ket hon` | hon: hôn, hơn |
| 5246 | `cha/me` | cha: chá, chã |
| 5246 | `cha me` | cha: chá, chã |
| 5246 | `ba me` | ba: bà, bá, bã |
| 5246 | `bo me` | bo: bỏ, bố, bổ, bộ |
| 5247 | `chet` | - |
| 5247 | `qua doi` | qua: quá, quả; doi: dõi, dồi, đòi, đôi, đối, đổi, đội, đời, đợi |
| 5253 | `om dau` | dau: dấu, dầu, đau, đâu, đầu |
| 5253 | `khan cap` | khan: khăn, khẩn; cap: cấp, cập, cặp |
| 5254 | `thong bao ngay` | thong: thông, thống; bao: bao, báo, bão, bảo; ngay: ngay, ngày, ngây |
| 5254 | `ngay khi co the` | ngay: ngay, ngày, ngây; co: có, cô, cơ, cố, cổ, cờ, cỡ; the: thẻ, thế, thể |
| 5257 | `cham dut` | cham: chăm, chạm, chấm, chậm |
| 5259 | `phep chua nghi` | chua: chưa, chứa, chữa; nghi: nghi, nghĩ, nghỉ, nghị |
| 5259 | `nghi hang nam chua nghi` | nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; nam: nam, năm, nấm, nắm, nằm; chua: chưa, chứa, chữa |
| 5278 | `nghi viec rieng huong` | nghi: nghi, nghĩ, nghỉ, nghị; huong: huống, hướng, hưởng |
| 5279 | `luong` | luong: luồng, lương, lường, lượng |
| 5286 | `\bcon(?:\s+(?:de\|nuoi))?\s+ket hon\b` | con: con, còn, cơn, cồn; de: dễ, đe, đè, đẻ, đề, để; hon: hôn, hơn |
| 5289 | `\bket hon\b` | hon: hôn, hơn |
| 5300 | `nghi viec rieng huong luong` | nghi: nghi, nghĩ, nghỉ, nghị; huong: huống, hướng, hưởng; luong: luồng, lương, lường, lượng |
| 5308 | `nghi viec rieng khong huong luong` | nghi: nghi, nghĩ, nghỉ, nghị; huong: huống, hướng, hưởng; luong: luồng, lương, lường, lượng |
| 5315 | `cha/me` | cha: chá, chã |
| 5315 | `cha me` | cha: chá, chã |
| 5315 | `ba me` | ba: bà, bá, bã |
| 5315 | `bo me` | bo: bỏ, bố, bổ, bộ |
| 5320 | `chet` | - |
| 5327 | `cham dut` | cham: chăm, chạm, chấm, chậm |
| 5327 | `thanh toan` | toan: toàn, toán |
| 5531 | `bang` | bang: bang, băng, bảng, bằng |
| 5536 | `dai` | dai: dài, dải, đại |
| 5566 | ` chinh sach ` | chinh: chính, chỉnh; sach: sách, sạch |
| 5566 | ` noi quy ` | noi: nói, nơi, nối, nội; quy: quy, quý, quỳ, quỹ |
| 5566 | ` quy che ` | quy: quy, quý, quỳ, quỹ |
| 5581 | ` nhan vien ` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; vien: viên, viền, viễn, viện |
| 5582 | ` nguoi lao dong ` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 5585 | ` co the ` | co: có, cô, cơ, cố, cổ, cờ, cỡ; the: thẻ, thế, thể |
| 5586 | ` duoc ` | duoc: dược, được |
| 5587 | ` bao nhieu ` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 5588 | ` may gio ` | may: may, mày, máy, mây, mấy; gio: gió, giỗ, giờ |
| 5589 | ` trong khoang ` | trong: trọng, trống |
| 5590 | ` la ` | la: là, lá, lã |
| 5591 | ` neu ` | neu: nêu, nếu, nệu |
| 5592 | ` thi ` | thi: thi, thì, thí, thị |
| 5599 | `chinh` | chinh: chính, chỉnh |
| 5600 | `sach` | sach: sách, sạch |
| 5601 | `noi` | noi: nói, nơi, nối, nội |
| 5602 | `quy` | quy: quy, quý, quỳ, quỹ |
| 5603 | `che` | - |
| 5607 | `cua` | cua: của, cửa |
| 5608 | `va` | va: và, vá, vã |
| 5838 | ` la ` | la: là, lá, lã |
| 5839 | `co phai` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 5840 | `dung khong` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 5841 | `phai khong` | - |
| 6003 | `duyet` | - |
| 6003 | `phe duyet` | - |
| 6006 | ` ai ` | - |
| 6012 | `nguoi phe duyet mo phong` | mo: mô, mơ, mỏ, mổ, mộ, mở; phong: phong, phòng, phóng, phỏng |
| 6016 | `yeu cau dieu chinh` | yeu: yêu, yếu; cau: câu, cấu, cầu; chinh: chính, chỉnh |
| 6021 | `yeu cau` | yeu: yêu, yếu; cau: câu, cấu, cầu |
| 6022 | `dieu chinh` | chinh: chính, chỉnh |
| 6023 | `ngoai le` | ngoai: ngoài, ngoại; le: le, lê, lẻ, lẽ, lễ, lệ |
| 6024 | `quan ly truc tiep` | quan: quan, quán, quân, quản, quần, quận; truc: trúc, trực |
| 6032 | `quan ly truc tiep` | quan: quan, quán, quân, quản, quần, quận; truc: trúc, trực |
| 6036 | `nguoi phe duyet` | - |
| 6038 | `quan ly truc tiep` | quan: quan, quán, quân, quản, quần, quận; truc: trúc, trực |
| 6038 | `phong nhan su` | phong: phong, phòng, phóng, phỏng; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; su: sư, sứ, sử, sự |
| 6058 | `khoa ky cong` | ky: ký, kỳ, kỵ, kỷ, kỹ; cong: cong, công, cổng, cộng |
| 6059 | `sau khi khoa ky` | sau: sau, sáu, sâu; ky: ký, kỳ, kỵ, kỷ, kỹ |
| 6059 | `after the period is locked` | the: thẻ, thế, thể |
| 6060 | `dieu chinh muon` | chinh: chính, chỉnh; muon: muốn, muộn, mượn |
| 6060 | `yeu cau dac biet` | yeu: yêu, yếu; cau: câu, cấu, cầu; biet: biết, biệt |
| 6063 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 6064 | `gio cot loi` | gio: gió, giỗ, giờ; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 6065 | `giu nguyen` | nguyen: nguyên, nguyễn, nguyện |
| 6065 | `nhu khi lam tai van phong` | lam: lam, làm, lâm, lạm, lắm; tai: tai, tài, tái, tại, tải; van: văn, vấn, vẫn, vận; phong: phong, phòng, phóng, phỏng |
| 6068 | `di muon` | di: di, dì, dị, đi; muon: muốn, muộn, mượn |
| 6068 | `toi tre` | toi: tôi, tỏi, tối, tội, tới |
| 6068 | `ve som` | ve: vé, vẻ, vẽ, về, vệ |
| 6069 | `bu trong cung ngay` | trong: trọng, trống; cung: cùng, cũng; ngay: ngay, ngày, ngây |
| 6069 | `make up in the same day` | the: thẻ, thế, thể; day: đây, đầy |
| 6070 | `khong duoc tu y bu sang ngay khac` | duoc: dược, được; tu: tu, tư, tủ, tứ, từ, tử, tự; sang: sàng, sáng; ngay: ngay, ngày, ngây; khac: khác, khắc |
| 6070 | `not make up on another day` | day: đây, đầy |
| 6073 | `on-call` | - |
| 6073 | `on call` | - |
| 6073 | `truc` | truc: trúc, trực |
| 6074 | `su co` | su: sư, sứ, sử, sự; co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 6074 | `lam them` | lam: lam, làm, lâm, lạm, lắm |
| 6075 | `khong tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 6075 | `thoi gian thuc te xu ly` | thuc: thúc, thục, thức, thực; te: tế, tệ |
| 6078 | `quen check` | - |
| 6079 | `yeu cau dieu chinh` | yeu: yêu, yếu; cau: câu, cấu, cầu; chinh: chính, chỉnh |
| 6080 | `trong vong` | trong: trọng, trống; vong: vòng, vọng |
| 6080 | `ngay lam viec` | ngay: ngay, ngày, ngây; lam: lam, làm, lâm, lạm, lắm |
| 6080 | `bang chung` | bang: bang, băng, bảng, bằng; chung: chúng, chứng |
| 6084 | `gio cot loi` | gio: gió, giỗ, giờ; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 6087 | `gio` | gio: gió, giỗ, giờ |
| 6088 | `thoi gian lam viec` | lam: lam, làm, lâm, lạm, lắm |
| 6089 | `lich lam viec` | lam: lam, làm, lâm, lạm, lắm |
| 6099 | `\btruc\b(?!\s+tiep\b)` | truc: trúc, trực |
| 6100 | `truc` | truc: trúc, trực |
| 6120 | `nghi trua` | nghi: nghi, nghĩ, nghỉ, nghị |
| 6123 | `lam bao nhieu gio` | lam: lam, làm, lâm, lạm, lắm; bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu; gio: gió, giỗ, giờ |
| 6123 | `lam may gio` | lam: lam, làm, lâm, lạm, lắm; may: may, mày, máy, mây, mấy; gio: gió, giỗ, giờ |
| 6129 | `nghi trua` | nghi: nghi, nghĩ, nghỉ, nghị |
| 6135 | `tong thoi gian lam viec` | lam: lam, làm, lâm, lạm, lắm |
| 6136 | `thoi gian lam viec tieu chuan` | lam: lam, làm, lâm, lạm, lắm |
| 6155 | `linh vuc hoat dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 6171 | `o dau` | dau: dấu, dầu, đau, đâu, đầu |
| 6171 | `tai dau` | tai: tai, tài, tái, tại, tải; dau: dấu, dầu, đau, đâu, đầu |
| 6174 | `van phong` | van: văn, vấn, vẫn, vận; phong: phong, phòng, phóng, phỏng |
| 6192 | `chinh sach` | chinh: chính, chỉnh; sach: sách, sạch |
| 6193 | `cong ty` | cong: cong, công, cổng, cộng |
| 6194 | `theo chinh` | chinh: chính, chỉnh |
| 6209 | `bao mat` | bao: bao, báo, bão, bảo; mat: mát, mất, mật, mắt, mặt |
| 6212 | `yeu cau` | yeu: yêu, yếu; cau: câu, cấu, cầu |
| 6212 | `bao dam` | bao: bao, báo, bão, bảo; dam: đám, đảm |
| 6212 | `can tuan thu` | can: cân, căn, cần, cận; tuan: tuân, tuấn, tuần; thu: thu, thú, thư, thủ, thứ, thử |
| 6212 | `tuan thu` | tuan: tuân, tuấn, tuần; thu: thu, thú, thư, thủ, thứ, thử |
| 6215 | `an toan` | an: án, ăn, ản, ấn; toan: toàn, toán |
| 6216 | `bao dam` | bao: bao, báo, bão, bảo; dam: đám, đảm |
| 6216 | `dam bao` | dam: đám, đảm; bao: bao, báo, bão, bảo |
| 6216 | `gi` | - |
| 6233 | `bao mat` | bao: bao, báo, bão, bảo; mat: mát, mất, mật, mắt, mặt |
| 6236 | `yeu cau` | yeu: yêu, yếu; cau: câu, cấu, cầu |
| 6236 | `bao dam` | bao: bao, báo, bão, bảo; dam: đám, đảm |
| 6236 | `can tuan thu` | can: cân, căn, cần, cận; tuan: tuân, tuấn, tuần; thu: thu, thú, thư, thủ, thứ, thử |
| 6236 | `tuan thu` | tuan: tuân, tuấn, tuần; thu: thu, thú, thư, thủ, thứ, thử |
| 6239 | `an toan` | an: án, ăn, ản, ấn; toan: toàn, toán |
| 6240 | `bao dam` | bao: bao, báo, bão, bảo; dam: đám, đảm |
| 6240 | `dam bao` | dam: đám, đảm; bao: bao, báo, bão, bảo |
| 6240 | `gi` | - |
| 6258 | `mat khau` | mat: mát, mất, mật, mắt, mặt; khau: khấu, khẩu |
| 6258 | `ma otp` | ma: ma, mà, má, mã, mạ, mả |
| 6259 | `mat khau` | mat: mát, mất, mật, mắt, mặt; khau: khấu, khẩu |
| 6259 | `thong tin xac thuc` | thong: thông, thống; tin: tin, tín; thuc: thúc, thục, thức, thực |
| 6260 | `cam chia se` | cam: cảm, cấm; se: sẻ, sẽ |
| 6260 | `khong duoc chia se` | duoc: dược, được; se: sẻ, sẽ |
| 6260 | `do not share` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 6263 | `ma nguon` | ma: ma, mà, má, mã, mạ, mả |
| 6264 | `ma nguon` | ma: ma, mà, má, mã, mạ, mả |
| 6264 | `kho ma nguon` | ma: ma, mà, má, mã, mạ, mả |
| 6265 | `ca nhan` | ca: cá, cã, cả, cầ; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 6265 | `duoc phep` | duoc: dược, được |
| 6265 | `cam` | cam: cảm, cấm |
| 6265 | `khong duoc` | duoc: dược, được |
| 6268 | `email ca nhan` | ca: cá, cã, cả, cầ; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 6268 | `file cong viec` | cong: cong, công, cổng, cộng |
| 6269 | `email ca nhan` | ca: cá, cã, cả, cầ; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 6269 | `ung dung chat ca nhan` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng; ca: cá, cã, cả, cầ; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 6269 | `o dia ca nhan` | dia: đĩa, địa; ca: cá, cã, cả, cầ; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 6270 | `du lieu` | du: du, dù, dư, dụ, dữ, dự, đu, đủ |
| 6270 | `tai lieu` | tai: tai, tài, tái, tại, tải |
| 6270 | `cam` | cam: cảm, cấm |
| 6270 | `khong duoc` | duoc: dược, được |
| 6273 | `public ai` | - |
| 6273 | `ai cong cong` | cong: cong, công, cổng, cộng |
| 6273 | `cong cu ai` | cong: cong, công, cổng, cộng; cu: cù, cũ, cụ, cứ |
| 6274 | `cong cu ai` | cong: cong, công, cổng, cộng; cu: cù, cũ, cụ, cứ |
| 6274 | `dich vu ai cong cong` | dich: dịch, đích, địch; cong: cong, công, cổng, cộng |
| 6274 | `public ai` | - |
| 6274 | `ma nguon doc quyen` | ma: ma, mà, má, mã, mạ, mả; doc: đọc, đốc, độc |
| 6275 | `khong nhap` | nhap: nháp, nhập |
| 6275 | `khong duoc` | duoc: dược, được |
| 6275 | `cam` | cam: cảm, cấm |
| 6275 | `do not` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 6278 | `ket qua ai` | qua: quá, quả |
| 6278 | `ai tao` | - |
| 6278 | `ai output` | - |
| 6278 | `bang chung test` | bang: bang, băng, bảng, bằng; chung: chúng, chứng |
| 6279 | `ket qua ai` | qua: quá, quả |
| 6279 | `ai output` | - |
| 6279 | `kiem chung` | kiem: kiếm, kiểm; chung: chúng, chứng |
| 6279 | `xac minh` | - |
| 6279 | `bang chung` | bang: bang, băng, bảng, bằng; chung: chúng, chứng |
| 6280 | `khong duoc` | duoc: dược, được |
| 6280 | `khong thay the` | the: thẻ, thế, thể |
| 6280 | `phai` | - |
| 6284 | `tai khoan bi lo` | tai: tai, tài, tái, tại, tải; khoan: khoán, khoản; bi: bí, bị; lo: lỗ, lộ |
| 6285 | `lo tai khoan` | lo: lỗ, lộ; tai: tai, tài, tái, tại, tải; khoan: khoán, khoản |
| 6286 | `lo thong tin xac thuc` | lo: lỗ, lộ; thong: thông, thống; tin: tin, tín; thuc: thúc, thục, thức, thực |
| 6291 | `bao ngay` | bao: bao, báo, bão, bảo; ngay: ngay, ngày, ngây |
| 6294 | `dang nhap bat thuong` | dang: dang, dạng, đang, đáng, đăng, đằng, đẳng; nhap: nháp, nhập; bat: bất, bật, bắt; thuong: thương, thường, thưởng |
| 6295 | `thong tin xac thuc` | thong: thông, thống; tin: tin, tín; thuc: thúc, thục, thức, thực |
| 6297 | `bao` | bao: bao, báo, bão, bảo |
| 6314 | `ma nguon` | ma: ma, mà, má, mã, mạ, mả |
| 6316 | `mat khau` | mat: mát, mất, mật, mắt, mặt; khau: khấu, khẩu |
| 6330 | `dua` | dua: dựa, đũa, đưa |
| 6330 | `gui` | - |
| 6330 | `chia se` | se: sẻ, sẽ |
| 6334 | `mat khau` | mat: mát, mất, mật, mắt, mặt; khau: khấu, khẩu |
| 6336 | `khoa api` | - |
| 6337 | `token truy cap` | cap: cấp, cập, cặp |
| 6353 | `cam chia se` | cam: cảm, cấm; se: sẻ, sẽ |
| 6354 | `khong duoc chia se` | duoc: dược, được; se: sẻ, sẽ |
| 6356 | `do not share` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 6377 | `cong` | cong: cong, công, cổng, cộng |
| 6414 | `tra luong` | tra: trá, trã, trả; luong: luồng, lương, lường, lượng |
| 6415 | `ngay nghi` | ngay: ngay, ngày, ngây; nghi: nghi, nghĩ, nghỉ, nghị |
| 6415 | `rest day` | day: đây, đầy |
| 6416 | `tra luong` | tra: trá, trã, trả; luong: luồng, lương, lường, lượng |
| 6417 | `ngay nghi` | ngay: ngay, ngày, ngây; nghi: nghi, nghĩ, nghỉ, nghị |
| 6417 | `ngay le` | ngay: ngay, ngày, ngây; le: le, lê, lẻ, lẽ, lễ, lệ |
| 6417 | `rest day` | day: đây, đầy |
| 6421 | `tai nan` | tai: tai, tài, tái, tại, tải; nan: năn, nạn |
| 6422 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 6422 | `lam viec tu xa` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 6423 | `tai nan` | tai: tai, tài, tái, tại, tải; nan: năn, nạn |
| 6424 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 6424 | `lam viec tu xa` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 6431 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 6431 | `lam viec tu xa` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 6445 | `giam doc ` | giam: giám, giảm; doc: đọc, đốc, độc |
| 6446 | `truong ` | truong: trương, trường, trưởng |
| 6451 | `phu trach ` | phu: phù, phụ |
| 6463 | `thanh` | - |
| 6463 | `lap` | lap: lập, lắp, lặp |
| 6482 | `nam thanh lap` | nam: nam, năm, nấm, nắm, nằm; lap: lập, lắp, lặp |
| 6486 | `khoang` | - |
| 6488 | `quy mo` | quy: quy, quý, quỳ, quỹ; mo: mô, mơ, mỏ, mổ, mộ, mở |
| 6491 | `khach hang muc tieu` | hang: hàng, hãng, hạng, hằng; muc: múc, mục, mức, mực |
| 6493 | `khach` | - |
| 6507 | `tra` | tra: trá, trã, trả |
| 6507 | `luong` | luong: luồng, lương, lường, lượng |
| 6527 | `toi da` | toi: tôi, tỏi, tối, tội, tới; da: dá, đa, đà, đã |
| 6527 | `khong qua` | qua: quá, quả |
| 6576 | `doi tuong` | doi: dõi, dồi, đòi, đôi, đối, đổi, đội, đời, đợi; tuong: tương, tưởng, tượng |
| 6576 | `muc nghi` | muc: múc, mục, mức, mực; nghi: nghi, nghĩ, nghỉ, nghị |
| 6576 | `so ngay` | so: so, sơ, số, sổ, sở, sợ; ngay: ngay, ngày, ngây |
| 6647 | `cua` | cua: của, cửa |
| 6647 | `chinh` | chinh: chính, chỉnh |
| 6647 | `sach` | sach: sách, sạch |
| 6647 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 6647 | `duoc` | duoc: dược, được |
| 6647 | `moi` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời |
| 6667 | `toi` | toi: tôi, tỏi, tối, tội, tới |
| 6667 | `toi da` | toi: tôi, tỏi, tối, tội, tới; da: dá, đa, đà, đã |
| 6669 | `ngay` | ngay: ngay, ngày, ngây |
| 6669 | `tuan` | tuan: tuân, tuấn, tuần |
| 6670 | `ngay/tuan` | ngay: ngay, ngày, ngây; tuan: tuân, tuấn, tuần |
| 6670 | `ngay` | ngay: ngay, ngày, ngây |
| 6670 | `tuan` | tuan: tuân, tuấn, tuần |
| 6675 | `luong` | luong: luồng, lương, lường, lượng |
| 6676 | `ngay tra luong` | ngay: ngay, ngày, ngây; tra: trá, trã, trả; luong: luồng, lương, lường, lượng |
| 6681 | `tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 6697 | `dong` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 6697 | `tinh` | tinh: tình, tính, tỉnh |
| 6697 | `toan` | toan: toàn, toán |
| 6731 | `khong co dinh` | co: có, cô, cơ, cố, cổ, cờ, cỡ; dinh: dính, đinh, đình, đính, đỉnh, định |
| 6732 | `khong quy dinh` | quy: quy, quý, quỳ, quỹ; dinh: dính, đinh, đình, đính, đỉnh, định |
| 6733 | `ty le cu the duoc cap nhat theo` | le: le, lê, lẻ, lẽ, lễ, lệ; cu: cù, cũ, cụ, cứ; the: thẻ, thế, thể; duoc: dược, được; cap: cấp, cập, cặp; nhat: nhất, nhật |
| 6735 | `specific rate is updated according to` | to: tố, tổ, tờ |
| 6737 | `no fixed` | no: nó, nợ |
| 6747 | `khong tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 6747 | `tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 6822 | `tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 6832 | `tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 6836 | `khong tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 6846 | `khong tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 7191 | `^(co\|khong\|yes\|no)\s*[.,:;!?-]` | co: có, cô, cơ, cố, cổ, cờ, cỡ; no: nó, nợ |
| 7196 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 7199 | `khong` | - |
| 7199 | `no` | no: nó, nợ |
| 7204 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 7230 | `do ` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 7232 | `can ` | can: cân, căn, cần, cận |
| 7357 | `total_to_first_generation_ms` | to: tố, tổ, tờ |
| 7606 | `ai duyet` | - |
| 7607 | `cham cong` | cham: chăm, chạm, chấm, chậm; cong: cong, công, cổng, cộng |
| 7610 | `quan ly truc tiep` | quan: quan, quán, quân, quản, quần, quận; truc: trúc, trực |
| 7610 | `phe duyet` | - |
| 7610 | `duyet` | - |
| 7613 | `khoa ky cong` | ky: ký, kỳ, kỵ, kỷ, kỹ; cong: cong, công, cổng, cộng |
| 7616 | `sau khi khoa ky` | sau: sau, sáu, sâu; ky: ký, kỳ, kỵ, kỷ, kỹ |
| 7616 | `after the period is locked` | the: thẻ, thế, thể |
| 7617 | `yeu cau dac biet` | yeu: yêu, yếu; cau: câu, cấu, cầu; biet: biết, biệt |
| 7617 | `dieu chinh muon` | chinh: chính, chỉnh; muon: muốn, muộn, mượn |
| 7621 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 7622 | `ngay mai` | ngay: ngay, ngày, ngây |
| 7622 | `dang ky` | dang: dang, dạng, đang, đáng, đăng, đằng, đẳng; ky: ký, kỳ, kỵ, kỷ, kỹ |
| 7626 | `dang ky` | dang: dang, dạng, đang, đáng, đăng, đằng, đẳng; ky: ký, kỳ, kỵ, kỷ, kỹ |
| 7627 | `ngay lam viec lien truoc` | ngay: ngay, ngày, ngây; lam: lam, làm, lâm, lạm, lắm; lien: liên, liền |
| 7627 | `truoc` | - |
| 7632 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 7633 | `cham cong` | cham: chăm, chạm, chấm, chậm; cong: cong, công, cổng, cộng |
| 7638 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 7639 | `nghia vu cham cong` | nghia: nghiá, nghĩa; cham: chăm, chạm, chấm, chậm; cong: cong, công, cổng, cộng |
| 7639 | `van phai cham cong` | van: văn, vấn, vẫn, vận; cham: chăm, chạm, chấm, chậm; cong: cong, công, cổng, cộng |
| 7643 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 7644 | `gio cot loi` | gio: gió, giỗ, giờ; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 7647 | `gio cot loi` | gio: gió, giỗ, giờ; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 7647 | `giu nguyen` | nguyen: nguyên, nguyễn, nguyện |
| 7647 | `nhu khi lam tai van phong` | lam: lam, làm, lâm, lạm, lắm; tai: tai, tài, tái, tại, tải; van: văn, vấn, vẫn, vận; phong: phong, phòng, phóng, phỏng |
| 7653 | `quen cham cong` | cham: chăm, chạm, chấm, chậm; cong: cong, công, cổng, cộng |
| 7654 | `quen check-in` | - |
| 7655 | `quen check-out` | - |
| 7656 | `quen checkout` | - |
| 7664 | `quen check-in` | - |
| 7665 | `quen check-out` | - |
| 7666 | `quen cham cong` | cham: chăm, chạm, chấm, chậm; cong: cong, công, cổng, cộng |
| 7670 | `yeu cau` | yeu: yêu, yếu; cau: câu, cấu, cầu |
| 7671 | `ngay lam viec` | ngay: ngay, ngày, ngây; lam: lam, làm, lâm, lạm, lắm |
| 7671 | `working day` | day: đây, đầy |
| 7671 | `business day` | day: đây, đầy |
| 7676 | `di muon` | di: di, dì, dị, đi; muon: muốn, muộn, mượn |
| 7676 | `toi tre` | toi: tôi, tỏi, tối, tội, tới |
| 7677 | `toi nay` | toi: tôi, tỏi, tối, tội, tới |
| 7677 | `cung ngay` | cung: cùng, cũng; ngay: ngay, ngày, ngây |
| 7677 | `same day` | day: đây, đầy |
| 7678 | `ngay mai` | ngay: ngay, ngày, ngây |
| 7678 | `ngay khac` | ngay: ngay, ngày, ngây; khac: khác, khắc |
| 7678 | `next day` | day: đây, đầy |
| 7681 | `bu trong cung ngay` | trong: trọng, trống; cung: cùng, cũng; ngay: ngay, ngày, ngây |
| 7681 | `same day` | day: đây, đầy |
| 7683 | `bu sang ngay khac` | sang: sàng, sáng; ngay: ngay, ngày, ngây; khac: khác, khắc |
| 7683 | `ngay khac` | ngay: ngay, ngày, ngây; khac: khác, khắc |
| 7683 | `another day` | day: đây, đầy |
| 7683 | `next day` | day: đây, đầy |
| 7687 | `di muon` | di: di, dì, dị, đi; muon: muốn, muộn, mượn |
| 7687 | `toi tre` | toi: tôi, tỏi, tối, tội, tới |
| 7692 | `on-call` | - |
| 7692 | `on call` | - |
| 7692 | `truc` | truc: trúc, trực |
| 7693 | `su co` | su: sư, sứ, sử, sự; co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 7693 | `lam them` | lam: lam, làm, lâm, lạm, lắm |
| 7697 | `on-call` | - |
| 7697 | `on call` | - |
| 7698 | `khong tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 7698 | `thoi gian thuc te xu ly` | thuc: thúc, thục, thức, thực; te: tế, tệ |
| 7714 | `\b\d+\s+(?:ngay\|working days?\|business days?)\b` | ngay: ngay, ngày, ngây |
| 7742 | `ha?` | ha: hà, há, hã, hạ, hả |
| 7744 | `nghi` | nghi: nghi, nghĩ, nghỉ, nghị |
| 7744 | `phep` | - |
| 7746 | `tao don` | don: dọn, dồn, đón, đơn |
| 7746 | `gui don` | don: dọn, dồn, đón, đơn |
| 7749 | `nghi luon` | nghi: nghi, nghĩ, nghỉ, nghị; luon: luôn, lươn |
| 7749 | `ngay` | ngay: ngay, ngày, ngây |
| 7757 | `luong phe duyet` | luong: luồng, lương, lường, lượng |
| 7758 | `tao yeu cau tren hrm` | yeu: yêu, yếu; cau: câu, cấu, cầu |
| 7759 | `quan ly truc tiep` | quan: quan, quán, quân, quản, quần, quận; truc: trúc, trực |
| 7760 | `trang thai cuoi cung` | trang: trạng, trắng; thai: thái, thải; cuoi: cuối, cưới; cung: cùng, cũng |
| 7785 | `tai nan` | tai: tai, tài, tái, tại, tải; nan: năn, nạn |
| 7787 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 7787 | `lam viec tu xa` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 7801 | `tai nan` | tai: tai, tài, tái, tại, tải; nan: năn, nạn |
| 7802 | `lam viec tu xa` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 7803 | `khong mac dinh` | dinh: dính, đinh, đình, đính, đỉnh, định |
| 7809 | `dua tren` | dua: dựa, đũa, đưa |
| 7809 | `hoan canh` | hoan: hoàn, hoãn; canh: cạnh, cảnh |
| 7809 | `bang chung` | bang: bang, băng, bảng, bằng; chung: chúng, chứng |
| 7824 | `tu van` | tu: tu, tư, tủ, tứ, từ, tử, tự; van: văn, vấn, vẫn, vận |
| 7826 | `may buoi` | may: may, mày, máy, mây, mấy |
| 7826 | `bao nhieu buoi` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 7835 | `tu van` | tu: tu, tư, tủ, tứ, từ, tử, tự; van: văn, vấn, vẫn, vận |
| 7839 | `\b(?:nam\|year)\b` | nam: nam, năm, nấm, nắm, nằm |
| 7856 | `ai` | - |
| 7858 | `ma nguon` | ma: ma, mà, má, mã, mạ, mả |
| 7858 | `code noi bo` | noi: nói, nơi, nối, nội; bo: bỏ, bố, bổ, bộ |
| 7860 | `nhap` | nhap: nháp, nhập |
| 7860 | `dua` | dua: dựa, đũa, đưa |
| 7873 | `khong nhap` | nhap: nháp, nhập |
| 7873 | `do not enter` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 7874 | `ma nguon` | ma: ma, mà, má, mã, mạ, mả |
| 7875 | `ai cong cong` | cong: cong, công, cổng, cộng |
| 7875 | `public ai` | - |
| 7875 | `public generative ai` | - |
| 7889 | `nghi phep` | nghi: nghi, nghĩ, nghỉ, nghị |
| 7889 | `on leave` | - |
| 7890 | `su co` | su: sư, sứ, sử, sự; co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 7891 | `thoi gian` | - |
| 7891 | `gio phat sinh` | gio: gió, giỗ, giờ; phat: phát, phạt |
| 7917 | `nguoi thay the` | the: thẻ, thế, thể |
| 7917 | `on-call` | - |
| 7918 | `dong y` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 7918 | `thong nhat` | thong: thông, thống; nhat: nhất, nhật |
| 7919 | `ghi nhan thoi gian` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 7978 | `\b(?:theo\|according to\|under\|pursuant to)\s*$` | to: tố, tổ, tờ |
| 7989 | `ngay thuong` | ngay: ngay, ngày, ngây; thuong: thương, thường, thưởng |
| 7990 | `ngay lam viec binh thuong` | ngay: ngay, ngày, ngây; lam: lam, làm, lâm, lạm, lắm; thuong: thương, thường, thưởng |
| 7994 | `ngay nghi hang tuan` | ngay: ngay, ngày, ngây; nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; tuan: tuân, tuấn, tuần |
| 7994 | `chu nhat` | chu: chú, chủ, chứ, chữ; nhat: nhất, nhật |
| 7995 | `ngay le` | ngay: ngay, ngày, ngây; le: le, lê, lẻ, lẽ, lễ, lệ |
| 7995 | `ngay nghi co huong luong` | ngay: ngay, ngày, ngây; nghi: nghi, nghĩ, nghỉ, nghị; co: có, cô, cơ, cố, cổ, cờ, cỡ; huong: huống, hướng, hưởng; luong: luồng, lương, lường, lượng |
| 7995 | `tet` | - |
| 7996 | `lam them vao ban dem` | lam: lam, làm, lâm, lạm, lắm; ban: ban, bàn, bán, bạn, bản, bận; dem: đêm, đếm |
| 7997 | `lam viec ban dem` | lam: lam, làm, lâm, lạm, lắm; ban: ban, bàn, bán, bạn, bản, bận; dem: đêm, đếm |
| 8002 | `\blam them ngay lam viec binh thuong\b` | lam: lam, làm, lâm, lạm, lắm; ngay: ngay, ngày, ngây; thuong: thương, thường, thưởng |
| 8003 | `\bovertime (?:on )?(?:a )?normal workday\b` | - |
| 8006 | `\blam them ngay nghi hang tuan\b` | lam: lam, làm, lâm, lạm, lắm; ngay: ngay, ngày, ngây; nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; tuan: tuân, tuấn, tuần |
| 8007 | `\bovertime (?:on )?(?:a )?(?:weekly rest\|weekend\|sunday)\b` | - |
| 8010 | `\blam them ngay le\b` | lam: lam, làm, lâm, lạm, lắm; ngay: ngay, ngày, ngây; le: le, lê, lẻ, lẽ, lễ, lệ |
| 8011 | `\bovertime (?:on )?(?:a )?(?:public )?holiday\b` | - |
| 8014 | `\blam them vao ban dem\b` | lam: lam, làm, lâm, lạm, lắm; ban: ban, bàn, bán, bạn, bản, bận; dem: đêm, đếm |
| 8018 | `\blam viec ban dem\b` | lam: lam, làm, lâm, lạm, lắm; ban: ban, bàn, bán, bạn, bản, bận; dem: đêm, đếm |
| 8053 | `thuong` | thuong: thương, thường, thưởng |
| 8054 | `bao nhieu` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 8054 | `muc tieu` | muc: múc, mục, mức, mực |
| 8055 | `thang luong` | thang: thang, tháng, thăng, thắng, thẳng; luong: luồng, lương, lường, lượng |
| 8144 | `on-call` | - |
| 8144 | `on call` | - |
| 8144 | `ca truc` | ca: cá, cã, cả, cầ; truc: trúc, trực |
| 8146 | `su co` | su: sư, sứ, sử, sự; co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 8149 | `thoi gian` | - |
| 8149 | `gio` | gio: gió, giỗ, giờ |
| 8149 | `lam them` | lam: lam, làm, lâm, lạm, lắm |
| 8156 | `on-call` | - |
| 8156 | `on call` | - |
| 8156 | `ca truc` | ca: cá, cã, cả, cầ; truc: trúc, trực |
| 8157 | `khong tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 8159 | `thoi gian thuc te xu ly` | thuc: thúc, thục, thức, thực; te: tế, tệ |
| 8163 | `lam them` | lam: lam, làm, lâm, lạm, lắm |
| 8173 | `on-call` | - |
| 8173 | `on call` | - |
| 8173 | `ca truc` | ca: cá, cã, cả, cầ; truc: trúc, trực |
| 8178 | `khong tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 8179 | `khong tinh toan bo` | tinh: tình, tính, tỉnh; toan: toàn, toán; bo: bỏ, bố, bổ, bộ |
| 8180 | `khong phai toan bo` | toan: toàn, toán; bo: bỏ, bố, bổ, bộ |
| 8182 | `not all on-call` | - |
| 8189 | `thoi gian thuc te xu ly` | thuc: thúc, thục, thức, thực; te: tế, tệ |
| 8190 | `thoi gian xu ly su co` | su: sư, sứ, sử, sự; co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 8191 | `thoi gian xu ly incident` | - |
| 8197 | `ghi nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 8197 | `danh gia ot` | danh: dành, đánh; gia: gia, già, giá, giã, giả |
| 8238 | `it nhat` | nhat: nhất, nhật |
| 8238 | `toi thieu` | toi: tôi, tỏi, tối, tội, tới; thieu: thiếu, thiểu, thiệu |
| 8249 | `xu ly the nao` | the: thẻ, thế, thể |
| 8250 | `duoc xu ly` | duoc: dược, được |
| 8251 | `tinh the nao` | tinh: tình, tính, tỉnh; the: thẻ, thế, thể |
| 8252 | `duoc tinh` | duoc: dược, được; tinh: tình, tính, tỉnh |
| 8260 | `lam them` | lam: lam, làm, lâm, lạm, lắm |
| 8300 | `it nhat` | nhat: nhất, nhật |
| 8300 | `toi thieu` | toi: tôi, tỏi, tối, tội, tới; thieu: thiếu, thiểu, thiệu |
| 8355 | `it nhat` | nhat: nhất, nhật |
| 8355 | `toi thieu` | toi: tôi, tỏi, tối, tội, tới; thieu: thiếu, thiểu, thiệu |
| 8372 | `thuong` | thuong: thương, thường, thưởng |
| 8373 | `lam them` | lam: lam, làm, lâm, lạm, lắm |
| 8486 | `khoan ho tro nao` | khoan: khoán, khoản; ho: họ, hồ, hỗ, hộ, hợ; tro: trò, trỏ, trở, trợ |
| 8487 | `ho tro nao` | ho: họ, hồ, hỗ, hộ, hợ; tro: trò, trỏ, trở, trợ |
| 8488 | `phu cap nao` | phu: phù, phụ; cap: cấp, cập, cặp |
| 8489 | `phu cap gi` | phu: phù, phụ; cap: cấp, cập, cặp |
| 8558 | `phu cap` | phu: phù, phụ; cap: cấp, cập, cặp |
| 8558 | `tro cap` | tro: trò, trỏ, trở, trợ; cap: cấp, cập, cặp |
| 8558 | `ho tro` | ho: họ, hồ, hỗ, hộ, hợ; tro: trò, trỏ, trở, trợ |
| 8599 | `^(?:nhan\s+vien\|nguoi\s+lao\s+dong)\s+duoc\s+phe\s+duyet\s+che\s+do\s+` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; vien: viên, viền, viễn, viện; dong: dong, dòng, đóng, đông, đống, đồng, động; duoc: dược, được; do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 8638 | `phu cap` | phu: phù, phụ; cap: cấp, cập, cặp |
| 8638 | `tro cap` | tro: trò, trỏ, trở, trợ; cap: cấp, cập, cặp |
| 8638 | `ho tro` | ho: họ, hồ, hỗ, hộ, hợ; tro: trò, trỏ, trở, trợ |
| 8640 | `ap dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 8641 | `khong ap dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 8642 | `duoc phe duyet` | duoc: dược, được |
| 8678 | `cong` | cong: cong, công, cổng, cộng |
| 8678 | `ty` | - |
| 8678 | `duoc` | duoc: dược, được |
| 8678 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 8678 | `ho` | ho: họ, hồ, hỗ, hộ, hợ |
| 8678 | `tro` | tro: trò, trỏ, trở, trợ |
| 8678 | `tien` | tien: tiên, tiến, tiền, tiện |
| 8697 | `neu ` | neu: nêu, nếu, nệu |
| 8699 | `truong hop` | truong: trương, trường, trưởng; hop: họp, hợp |
| 8700 | `ngay ` | ngay: ngay, ngày, ngây |
| 8701 | `day ` | day: đây, đầy |
| 8702 | `mot ` | - |
| 8704 | `ad hoc` | hoc: học, hộc |
| 8706 | `thuong xuyen` | thuong: thương, thường, thưởng |
| 8722 | `khong` | - |
| 8722 | `ap` | - |
| 8722 | `dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 8722 | `duoc` | duoc: dược, được |
| 8722 | `cho` | cho: cho, chó, chỗ, chờ, chở, chợ |
| 8722 | `the` | the: thẻ, thế, thể |
| 8728 | `cong` | cong: cong, công, cổng, cộng |
| 8728 | `ty` | - |
| 8728 | `duoc` | duoc: dược, được |
| 8728 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 8728 | `ho` | ho: họ, hồ, hỗ, hộ, hợ |
| 8728 | `tro` | tro: trò, trỏ, trở, trợ |
| 8728 | `tien` | tien: tiên, tiến, tiền, tiện |
| 8739 | `\b(?:wfh\|work\s+from\s+home\|lam\s+o\s+nha)\b` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 8740 | `\b(?:don\s+le\|ad\s*hoc\|single)\b` | don: dọn, dồn, đón, đơn; le: le, lê, lẻ, lẽ, lễ, lệ; hoc: học, hộc |
| 8746 | `\b(?:single\|mot\|one\|1)\b` | - |
| 8746 | `\b(?:ngay\|day\|hom)\b` | ngay: ngay, ngày, ngây; day: đây, đầy |
| 8751 | `^(?:ap\s+dung\s+(?:khi\|cho)\|for\|when)\s+` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng; cho: cho, chó, chỗ, chờ, chở, chợ |
| 8783 | `ap dung` | dung: dùng, dụng, dừng, dựng, đúng, đụng, đứng, đừng |
| 8784 | `bao gom` | bao: bao, báo, bão, bảo |
| 8785 | `co the` | co: có, cô, cơ, cố, cổ, cờ, cỡ; the: thẻ, thế, thể |
| 8786 | `dien ra` | dien: diễn, diện, điền, điện; ra: rà, rã |
| 8787 | `duoc` | duoc: dược, được |
| 8788 | `gom` | - |
| 8789 | `khong` | - |
| 8790 | `la ` | la: là, lá, lã |
| 8791 | `thuc hien` | thuc: thúc, thục, thức, thực; hien: hiển, hiện |
| 8792 | `tu dong` | tu: tu, tư, tủ, tứ, từ, tử, tự; dong: dong, dòng, đóng, đông, đống, đồng, động |
| 8890 | `phep` | - |
| 8890 | `nghi hang nam` | nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; nam: nam, năm, nấm, nắm, nằm |
| 8893 | `\bchua(?:\s+lam)?\s+du\s+(?:mot\|1)\s+nam\b` | chua: chưa, chứa, chữa; lam: lam, làm, lâm, lạm, lắm; du: du, dù, dư, dụ, dữ, dự, đu, đủ; nam: nam, năm, nấm, nắm, nằm |
| 8894 | `\bchua(?:\s+lam)?\s+du\s+12\s+thang\b` | chua: chưa, chứa, chữa; lam: lam, làm, lâm, lạm, lắm; du: du, dù, dư, dụ, dữ, dự, đu, đủ; thang: thang, tháng, thăng, thắng, thẳng |
| 8895 | `\b(?:under\|less than)\s+(?:one\|1)\s+year\b` | than: thần, thắn |
| 8899 | `\btinh\s+theo\s+ty\s+le\s+tuong\s+ung\s+voi\s+thoi\s+gian\s+lam\s+viec\b` | tinh: tình, tính, tỉnh; le: le, lê, lẻ, lẽ, lễ, lệ; tuong: tương, tưởng, tượng; voi: vôi, vội, với; lam: lam, làm, lâm, lạm, lắm |
| 8907 | ` thang: phep nam ` | thang: thang, tháng, thăng, thắng, thẳng; nam: nam, năm, nấm, nắm, nằm |
| 8941 | `sau` | sau: sau, sáu, sâu |
| 8960 | `bao` | bao: bao, báo, bão, bảo |
| 8968 | `cho` | cho: cho, chó, chỗ, chờ, chở, chợ |
| 8974 | `trong` | trong: trọng, trống |
| 8984 | `ai` | - |
| 8998 | `than` | than: thần, thắn |
| 9000 | `the` | the: thẻ, thế, thể |
| 9002 | `an` | an: án, ăn, ản, ấn |
| 9004 | `to` | to: tố, tổ, tờ |
| 9006 | `on` | - |
| 9014 | `do` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 9023 | `my` | - |
| 9026 | `can` | can: cân, căn, cần, cận |
| 9072 | `sau ` | sau: sau, sáu, sâu |
| 9073 | `neu ` | neu: nêu, nếu, nệu |
| 9075 | `chua du` | chua: chưa, chứa, chữa; du: du, dù, dư, dụ, dữ, dự, đu, đủ |
| 9076 | `cu du` | cu: cù, cũ, cụ, cứ; du: du, dù, dư, dụ, dữ, dự, đu, đủ |
| 9077 | `it hon` | hon: hôn, hơn |
| 9078 | `nhieu hon` | nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu; hon: hôn, hơn |
| 9084 | `less than` | than: thần, thắn |
| 9085 | `more than` | than: thần, thắn |
| 9105 | `bao` | bao: bao, báo, bão, bảo |
| 9106 | `bao nhieu` | bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 9107 | `chinh` | chinh: chính, chỉnh |
| 9108 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 9109 | `duoc` | duoc: dược, được |
| 9112 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 9113 | `sach` | sach: sách, sạch |
| 9115 | `vien` | vien: viên, viền, viễn, viện |
| 9122 | `tang them` | tang: tang, tăng, tảng, tầng, tặng |
| 9123 | `giam` | giam: giám, giảm |
| 9124 | `ty le` | le: le, lê, lẻ, lẽ, lễ, lệ |
| 9125 | `tuong ung` | tuong: tương, tưởng, tượng |
| 9126 | `duoc tinh` | duoc: dược, được; tinh: tình, tính, tỉnh |
| 9127 | `khong duoc` | duoc: dược, được |
| 9204 | `dac biet` | biet: biết, biệt |
| 9206 | `chua thanh nien` | chua: chưa, chứa, chữa |
| 9206 | `khuyet tat` | tat: tất, tật, tắt |
| 9208 | `dieu kien binh thuong` | kien: kiến, kiện; thuong: thương, thường, thưởng |
| 9245 | `nghi hang nam` | nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; nam: nam, năm, nấm, nắm, nằm |
| 9245 | `nghi phep nam` | nghi: nghi, nghĩ, nghỉ, nghị; nam: nam, năm, nấm, nắm, nằm |
| 9245 | `phep nam` | nam: nam, năm, nấm, nắm, nằm |
| 9252 | `dieu kien binh thuong` | kien: kiến, kiện; thuong: thương, thường, thưởng |
| 9253 | `chua thanh nien` | chua: chưa, chứa, chữa |
| 9254 | `khuyet tat` | tat: tất, tật, tắt |
| 9255 | `nang nhoc` | nang: nâng, năng, nẵng, nặng |
| 9256 | `doc hai` | doc: đọc, đốc, độc; hai: hai, hài, hại, hải |
| 9257 | `nguy hiem` | - |
| 9258 | `dac biet` | biet: biết, biệt |
| 9261 | `dang ky` | dang: dang, dạng, đang, đáng, đăng, đằng, đẳng; ky: ký, kỳ, kỵ, kỷ, kỹ |
| 9262 | `lien tuc` | lien: liên, liền; tuc: tục, tức |
| 9263 | `tang them` | tang: tang, tăng, tảng, tầng, tặng |
| 9264 | `tham nien` | tham: thâm, thẩm |
| 9265 | `truoc it nhat` | nhat: nhất, nhật |
| 9316 | `phu cap` | phu: phù, phụ; cap: cấp, cập, cặp |
| 9316 | `truc` | truc: trúc, trực |
| 9319 | `lam gi truoc` | lam: lam, làm, lâm, lạm, lắm |
| 9319 | `do first` | do: do, dò, dở, đo, đó, đỏ, đồ, đổ, độ |
| 9342 | `chinh` | chinh: chính, chỉnh |
| 9343 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 9344 | `nguoi` | - |
| 9345 | `sach` | sach: sách, sạch |
| 9347 | `vien` | vien: viên, viền, viễn, viện |
| 9355 | `bao mat` | bao: bao, báo, bão, bảo; mat: mát, mất, mật, mắt, mặt |
| 9361 | `duoc ghi nhan` | duoc: dược, được; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 9362 | `khong duoc ghi nhan` | duoc: dược, được; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 9363 | `phai ghi nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 9364 | `ghi nhan thoi gian thuc te` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; thuc: thúc, thục, thức, thực; te: tế, tệ |
| 9370 | `bao mat` | bao: bao, báo, bão, bảo; mat: mát, mất, mật, mắt, mặt |
| 9374 | `yeu cau` | yeu: yêu, yếu; cau: câu, cấu, cầu |
| 9375 | `bao dam` | bao: bao, báo, bão, bảo; dam: đám, đảm |
| 9376 | `can tuan thu` | can: cân, căn, cần, cận; tuan: tuân, tuấn, tuần; thu: thu, thú, thư, thủ, thứ, thử |
| 9377 | `tuan thu` | tuan: tuân, tuấn, tuần; thu: thu, thú, thư, thủ, thứ, thử |
| 9383 | `an toan` | an: án, ăn, ản, ấn; toan: toàn, toán |
| 9384 | `bao dam` | bao: bao, báo, bão, bảo; dam: đám, đảm |
| 9384 | `dam bao` | dam: đám, đảm; bao: bao, báo, bão, bảo |
| 9384 | `gi` | - |
| 9390 | `khong cam` | cam: cảm, cấm |
| 9391 | `duoc quyen` | duoc: dược, được |
| 9393 | `may discuss` | may: may, mày, máy, mây, mấy |
| 9394 | `may share` | may: may, mày, máy, mây, mấy |
| 9399 | `phu cap on-call` | phu: phù, phụ; cap: cấp, cập, cặp |
| 9399 | `phu cap on call` | phu: phù, phụ; cap: cấp, cập, cặp |
| 9399 | `on-call bu` | - |
| 9399 | `on call bu` | - |
| 9401 | `truoc` | - |
| 9434 | `^\d+[.)]?\s+on-?call\s+` | - |
| 9439 | ` de` | de: dễ, đe, đè, đẻ, đề, để |
| 9439 | ` to` | to: tố, tổ, tờ |
| 9446 | ` de` | de: dễ, đe, đè, đẻ, đề, để |
| 9446 | ` to` | to: tố, tổ, tờ |
| 9476 | `chinh minh` | chinh: chính, chỉnh |
| 9477 | `chinh toi` | chinh: chính, chỉnh; toi: tôi, tỏi, tối, tội, tới |
| 9478 | `cua toi` | cua: của, cửa; toi: tôi, tỏi, tối, tội, tới |
| 9479 | `my own` | - |
| 9488 | `noi ve` | noi: nói, nơi, nối, nội; ve: vé, vẻ, vẽ, về, vệ |
| 9489 | `noi cho` | noi: nói, nơi, nối, nội; cho: cho, chó, chỗ, chờ, chở, chợ |
| 9490 | `trao doi` | doi: dõi, dồi, đòi, đôi, đối, đổi, đội, đời, đợi |
| 9491 | `chia se` | se: sẻ, sẽ |
| 9492 | `cung cap` | cung: cùng, cũng; cap: cấp, cập, cặp |
| 9505 | `ma nguon` | ma: ma, mà, má, mã, mạ, mả |
| 9506 | `khong dua ma nguon` | dua: dựa, đũa, đưa; ma: ma, mà, má, mã, mạ, mả |
| 9508 | `email ca nhan` | ca: cá, cã, cả, cầ; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 9508 | `file cong viec` | cong: cong, công, cổng, cộng |
| 9510 | `khong tu gui` | tu: tu, tư, tủ, tứ, từ, tử, tự |
| 9510 | `email ca nhan` | ca: cá, cã, cả, cầ; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 9511 | `public ai` | - |
| 9511 | `ai cong cong` | cong: cong, công, cổng, cộng |
| 9512 | `khong nhap` | nhap: nháp, nhập |
| 9512 | `dich vu ai cong cong` | dich: dịch, đích, địch; cong: cong, công, cổng, cộng |
| 9512 | `public ai` | - |
| 9515 | `ket qua ai` | qua: quá, quả |
| 9515 | `ai tao` | - |
| 9515 | `ai output` | - |
| 9515 | `bang chung test` | bang: bang, băng, bảng, bằng; chung: chúng, chứng |
| 9517 | `khong trinh bay` | bay: bày, bảy, bẫy |
| 9517 | `bang chung kiem thu` | bang: bang, băng, bảng, bằng; chung: chúng, chứng; kiem: kiếm, kiểm; thu: thu, thú, thư, thủ, thứ, thử |
| 9521 | `tai khoan bi lo` | tai: tai, tài, tái, tại, tải; khoan: khoán, khoản; bi: bí, bị; lo: lỗ, lộ |
| 9522 | `lo tai khoan` | lo: lỗ, lộ; tai: tai, tài, tái, tại, tải; khoan: khoán, khoản |
| 9523 | `lo thong tin xac thuc` | lo: lỗ, lộ; thong: thông, thống; tin: tin, tín; thuc: thúc, thục, thức, thực |
| 9528 | `bao ngay` | bao: bao, báo, bão, bảo; ngay: ngay, ngày, ngây |
| 9541 | `tu ngay dau` | tu: tu, tư, tủ, tứ, từ, tử, tự; ngay: ngay, ngày, ngây; dau: dấu, dầu, đau, đâu, đầu |
| 9541 | `ngay dau` | ngay: ngay, ngày, ngây; dau: dấu, dầu, đau, đâu, đầu |
| 9541 | `tu luc nhan viec` | tu: tu, tư, tủ, tứ, từ, tử, tự; luc: lúc, lục, lực; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 9541 | `from first day` | day: đây, đầy |
| 9548 | `ngay` | ngay: ngay, ngày, ngây |
| 9548 | `dau` | dau: dấu, dầu, đau, đâu, đầu |
| 9548 | `khong` | - |
| 9548 | `day` | day: đây, đầy |
| 9552 | `tu ngay` | tu: tu, tư, tủ, tứ, từ, tử, tự; ngay: ngay, ngày, ngây |
| 9552 | `sau thu viec` | sau: sau, sáu, sâu; thu: thu, thú, thư, thủ, thứ, thử |
| 9558 | `\bkhong\s+co\b` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 9578 | `khi nao` | - |
| 9579 | `tham gia` | tham: thâm, thẩm; gia: gia, già, giá, giã, giả |
| 9579 | `duoc huong` | duoc: dược, được; huong: huống, hướng, hưởng |
| 9589 | `duoc` | duoc: dược, được |
| 9593 | `nao` | - |
| 9594 | `tham` | tham: thâm, thẩm |
| 9612 | `tu ngay nhan viec` | tu: tu, tư, tủ, tứ, từ, tử, tự; ngay: ngay, ngày, ngây; nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 9613 | `sau thu viec` | sau: sau, sáu, sâu; thu: thu, thú, thư, thủ, thứ, thử |
| 9614 | `\bkhong\s+co\b` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 9626 | `theo danh sach bao hiem` | danh: dành, đánh; sach: sách, sạch; bao: bao, báo, bão, bảo |
| 9628 | `dieu khoan loai tru` | khoan: khoán, khoản; tru: trú, trừ, trữ |
| 9672 | `gio cot loi` | gio: gió, giỗ, giờ; cot: cốt, cột; loi: lõi, lối, lỗi, lội, lời, lợi |
| 9674 | `bat dau` | bat: bất, bật, bắt; dau: dấu, dầu, đau, đâu, đầu |
| 9675 | `ket thuc` | thuc: thúc, thục, thức, thực |
| 9678 | `buoi chieu` | chieu: chiếu, chiều |
| 9679 | `buoi sang` | sang: sàng, sáng |
| 9709 | `may gio duoc ve` | may: may, mày, máy, mây, mấy; gio: gió, giỗ, giờ; duoc: dược, được; ve: vé, vẻ, vẽ, về, vệ |
| 9709 | `gio duoc ve` | gio: gió, giỗ, giờ; duoc: dược, được; ve: vé, vẻ, vẽ, về, vệ |
| 9709 | `when can i leave` | can: cân, căn, cần, cận |
| 9711 | `vao luc` | luc: lúc, lục, lực |
| 9711 | `bat dau` | bat: bất, bật, bắt; dau: dấu, dầu, đau, đâu, đầu |
| 9712 | ` duoc ve` | duoc: dược, được; ve: vé, vẻ, vẽ, về, vệ |
| 9712 | `ket thuc` | thuc: thúc, thục, thức, thực |
| 9717 | `(?<!\d)([01]?\d\|2[0-3])(?:[:h]([0-5]\d))?\s*(?:gio\|hours?\|h\b)` | gio: gió, giỗ, giờ |
| 9734 | `khung bat dau` | bat: bất, bật, bắt; dau: dấu, dầu, đau, đâu, đầu |
| 9736 | `khung ket thuc` | thuc: thúc, thục, thức, thực |
| 9781 | ` according to` | to: tố, tổ, tờ |
| 9790 | `khong quy dinh` | quy: quy, quý, quỳ, quỹ; dinh: dính, đinh, đình, đính, đỉnh, định |
| 9791 | `khong co dinh` | co: có, cô, cơ, cố, cổ, cờ, cỡ; dinh: dính, đinh, đình, đính, đỉnh, định |
| 9792 | `khong an dinh` | an: án, ăn, ản, ấn; dinh: dính, đinh, đình, đính, đỉnh, định |
| 9795 | `no fixed` | no: nó, nợ |
| 9830 | `ben` | - |
| 9830 | `cong` | cong: cong, công, cổng, cộng |
| 9830 | `ty` | - |
| 9830 | `khoang` | - |
| 9841 | `dai luong` | dai: dài, dải, đại; luong: luồng, lương, lường, lượng |
| 9841 | `gross/thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 9858 | `gross/thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 9872 | `luong` | luong: luồng, lương, lường, lượng |
| 9875 | `dai` | dai: dài, dải, đại |
| 9875 | `khoang` | - |
| 9878 | `tu` | tu: tu, tư, tủ, tứ, từ, tử, tự |
| 9878 | `den` | - |
| 9878 | `muc` | muc: múc, mục, mức, mực |
| 9879 | `muc min` | muc: múc, mục, mức, mực |
| 9880 | `muc max` | muc: múc, mục, mức, mực |
| 9884 | `vi tri` | vi: vì, ví, vị; tri: trì, trí, trị |
| 9966 | `(\d+\s*ngay)\s*\bket hon\b` | ngay: ngay, ngày, ngây; hon: hôn, hơn |
| 9967 | `(?<!con\s)\bket hon\b\s*[-:\|]?\s*(\d+\s*ngay)\b` | con: con, còn, cơn, cồn; hon: hôn, hơn; ngay: ngay, ngày, ngây |
| 9972 | `\bcon ket hon\b\s*[-:\|]?\s*(\d+\s*ngay)\b` | con: con, còn, cơn, cồn; hon: hôn, hơn; ngay: ngay, ngày, ngây |
| 10003 | `thoi gian` | - |
| 10003 | `ghi nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 10006 | `ghi nhan thoi gian thuc te` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; thuc: thúc, thục, thức, thực; te: tế, tệ |
| 10006 | `thoi gian thuc te xu ly` | thuc: thúc, thục, thức, thực; te: tế, tệ |
| 10008 | `kich hoat nguoi thay the` | the: thẻ, thế, thể |
| 10021 | `dang nghi phep` | dang: dang, dạng, đang, đáng, đăng, đằng, đẳng; nghi: nghi, nghĩ, nghỉ, nghị |
| 10022 | `dau moi` | dau: dấu, dầu, đau, đâu, đầu; moi: môi, mọi, mỏi, mối, mỗi, mới, mời |
| 10025 | `tinh huong nguyen tac` | tinh: tình, tính, tỉnh; huong: huống, hướng, hưởng; nguyen: nguyên, nguyễn, nguyện; tac: tác, tắc |
| 10028 | `dong y` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 10032 | `dong y` | dong: dong, dòng, đóng, đông, đống, đồng, động |
| 10047 | `om dau` | dau: dấu, dầu, đau, đâu, đầu |
| 10048 | `thong bao ngay` | thong: thông, thống; bao: bao, báo, bão, bảo; ngay: ngay, ngày, ngây |
| 10048 | `ngay khi co the` | ngay: ngay, ngày, ngây; co: có, cô, cơ, cố, cổ, cờ, cỡ; the: thẻ, thế, thể |
| 10052 | `cham dut` | cham: chăm, chạm, chấm, chậm |
| 10053 | `thanh toan` | toan: toàn, toán |
| 10055 | `phep chua nghi` | chua: chưa, chứa, chữa; nghi: nghi, nghĩ, nghỉ, nghị |
| 10055 | `nghi hang nam chua nghi` | nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; nam: nam, năm, nấm, nắm, nằm; chua: chưa, chứa, chữa |
| 10071 | `nghi` | nghi: nghi, nghĩ, nghỉ, nghị |
| 10071 | `huong` | huong: huống, hướng, hưởng |
| 10071 | `luong` | luong: luồng, lương, lường, lượng |
| 10074 | `o nha` | nha: nhà, nhá, nhã |
| 10074 | `lam viec tu xa` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 10075 | `ngay` | ngay: ngay, ngày, ngây |
| 10075 | `day` | day: đây, đầy |
| 10079 | `lam bao nhieu` | lam: lam, làm, lâm, lạm, lắm; bao: bao, báo, bão, bảo; nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 10080 | `lam may` | lam: lam, làm, lâm, lạm, lắm; may: may, mày, máy, mây, mấy |
| 10081 | `thoi gian lam viec` | lam: lam, làm, lâm, lạm, lắm |
| 10082 | `nghi trua` | nghi: nghi, nghĩ, nghỉ, nghị |
| 10104 | `phu cap` | phu: phù, phụ; cap: cấp, cập, cặp |
| 10104 | `tro cap` | tro: trò, trỏ, trở, trợ; cap: cấp, cập, cặp |
| 10104 | `ho tro` | ho: họ, hồ, hỗ, hộ, hợ; tro: trò, trỏ, trở, trợ |
| 10104 | `chi tra` | chi: chi, chí, chỉ, chị; tra: trá, trã, trả |
| 10104 | `tien an` | tien: tiên, tiến, tiền, tiện; an: án, ăn, ản, ấn |
| 10113 | `dai luong` | dai: dài, dải, đại; luong: luồng, lương, lường, lượng |
| 10114 | `khung luong` | luong: luồng, lương, lường, lượng |
| 10115 | `bang luong` | bang: bang, băng, bảng, bằng; luong: luồng, lương, lường, lượng |
| 10120 | `luong` | luong: luồng, lương, lường, lượng |
| 10121 | `tham khao` | tham: thâm, thẩm |
| 10161 | `it nhat` | nhat: nhất, nhật |
| 10161 | `toi thieu` | toi: tôi, tỏi, tối, tội, tới; thieu: thiếu, thiểu, thiệu |
| 10177 | `cua` | cua: của, cửa |
| 10179 | `chinh` | chinh: chính, chỉnh |
| 10180 | `sach` | sach: sách, sạch |
| 10181 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 10182 | `duoc` | duoc: dược, được |
| 10183 | `moi` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời |
| 10184 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 10185 | `vien` | vien: viên, viền, viễn, viện |
| 10186 | `trong` | trong: trọng, trống |
| 10187 | `khoang` | - |
| 10188 | `nao` | - |
| 10226 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 10226 | `lam viec tu xa` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 10282 | `tra luong` | tra: trá, trã, trả; luong: luồng, lương, lường, lượng |
| 10284 | `ngay` | ngay: ngay, ngày, ngây |
| 10304 | `nghi` | nghi: nghi, nghĩ, nghỉ, nghị |
| 10306 | `huong` | huong: huống, hướng, hưởng |
| 10306 | `huong luong` | huong: huống, hướng, hưởng; luong: luồng, lương, lường, lượng |
| 10309 | `ket` | - |
| 10309 | `hon` | hon: hôn, hơn |
| 10310 | `ket` | - |
| 10311 | `hon` | hon: hôn, hơn |
| 10314 | `toi` | toi: tôi, tỏi, tối, tội, tới |
| 10315 | `toi da` | toi: tôi, tỏi, tối, tội, tới; da: dá, đa, đà, đã |
| 10315 | `khong qua` | qua: quá, quả |
| 10318 | `ngay` | ngay: ngay, ngày, ngây |
| 10318 | `tuan` | tuan: tuân, tuấn, tuần |
| 10319 | `ngay/tuan` | ngay: ngay, ngày, ngây; tuan: tuân, tuấn, tuần |
| 10319 | `ngay` | ngay: ngay, ngày, ngây |
| 10319 | `tuan` | tuan: tuân, tuấn, tuần |
| 10345 | `it nhat` | nhat: nhất, nhật |
| 10347 | `chu nhat` | chu: chú, chủ, chứ, chữ; nhat: nhất, nhật |
| 10348 | `ngay nghi hang tuan` | ngay: ngay, ngày, ngây; nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; tuan: tuân, tuấn, tuần |
| 10350 | `ngay le` | ngay: ngay, ngày, ngây; le: le, lê, lẻ, lẽ, lễ, lệ |
| 10350 | `tet` | - |
| 10352 | `lam` | lam: lam, làm, lâm, lạm, lắm |
| 10352 | `viec` | - |
| 10352 | `ban` | ban: ban, bàn, bán, bạn, bản, bận |
| 10352 | `dem` | dem: đêm, đếm |
| 10353 | `lam viec ban dem` | lam: lam, làm, lâm, lạm, lắm; ban: ban, bàn, bán, bạn, bản, bận; dem: đêm, đếm |
| 10355 | `lam them vao ban dem` | lam: lam, làm, lâm, lạm, lắm; ban: ban, bàn, bán, bạn, bản, bận; dem: đêm, đếm |
| 10357 | `nghi` | nghi: nghi, nghĩ, nghỉ, nghị |
| 10357 | `hang` | hang: hàng, hãng, hạng, hằng |
| 10357 | `tuan` | tuan: tuân, tuấn, tuần |
| 10359 | `ngay nghi hang tuan` | ngay: ngay, ngày, ngây; nghi: nghi, nghĩ, nghỉ, nghị; hang: hàng, hãng, hạng, hằng; tuan: tuân, tuấn, tuần |
| 10367 | `lam o nha` | lam: lam, làm, lâm, lạm, lắm; nha: nhà, nhá, nhã |
| 10368 | `lam viec tu xa` | lam: lam, làm, lâm, lạm, lắm; tu: tu, tư, tủ, tứ, từ, tử, tự; xa: xá, xã, xạ |
| 10409 | `phu cap` | phu: phù, phụ; cap: cấp, cập, cặp |
| 10409 | `tro cap` | tro: trò, trỏ, trở, trợ; cap: cấp, cập, cặp |
| 10409 | `ho tro` | ho: họ, hồ, hỗ, hộ, hợ; tro: trò, trỏ, trở, trợ |
| 10434 | `nhan su` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; su: sư, sứ, sử, sự |
| 10438 | `phan` | phan: phan, phán, phân, phản, phần, phận |
| 10439 | `tram` | tram: trám, trăm, trạm |
| 10445 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 10446 | `vien` | vien: viên, viền, viễn, viện |
| 10452 | `nguoi` | - |
| 10453 | `lam` | lam: lam, làm, lâm, lạm, lắm |
| 10454 | `viec` | - |
| 10455 | `thuoc` | thuoc: thuộc, thước |
| 10456 | `khoi` | khoi: khôi, khỏi, khối, khởi |
| 10457 | `voi` | voi: vôi, vội, với |
| 10458 | `cung` | cung: cùng, cũng |
| 10459 | `the` | the: thẻ, thế, thể |
| 10461 | `khoang` | - |
| 10462 | `bao` | bao: bao, báo, bão, bảo |
| 10463 | `nhieu` | nhieu: nhiêu, nhiếu, nhiều, nhiễu, nhiệu |
| 10468 | `trong` | trong: trọng, trống |
| 10473 | `nhan vien` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn; vien: viên, viền, viễn, viện |
| 10494 | `phut` | - |
| 10495 | `phut` | - |
| 10496 | `phut` | - |
| 10497 | `gio` | gio: gió, giỗ, giờ |
| 10498 | `tieng` | - |
| 10498 | `gio` | gio: gió, giỗ, giờ |
| 10499 | `gio` | gio: gió, giỗ, giờ |
| 10500 | `gio` | gio: gió, giỗ, giờ |
| 10501 | `ngay` | ngay: ngay, ngày, ngây |
| 10502 | `day` | day: đây, đầy |
| 10502 | `ngay` | ngay: ngay, ngày, ngây |
| 10503 | `ngay` | ngay: ngay, ngày, ngây |
| 10504 | `tuan` | tuan: tuân, tuấn, tuần |
| 10505 | `tuan` | tuan: tuân, tuấn, tuần |
| 10506 | `tuan` | tuan: tuân, tuấn, tuần |
| 10507 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 10508 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 10509 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 10510 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 10511 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 10512 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 10530 | `ngay` | ngay: ngay, ngày, ngây |
| 10531 | `day` | day: đây, đầy |
| 10532 | `tuan` | tuan: tuân, tuấn, tuần |
| 10534 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 10536 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 10541 | `(?:\bmoi\s+\|\bmot\s+\|/\|\bper\s+)(ngay\|day\|tuan\|week\|thang\|month\|nam\|year)\b` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời; ngay: ngay, ngày, ngây; day: đây, đầy; tuan: tuân, tuấn, tuần; thang: thang, tháng, thăng, thắng, thẳng; nam: nam, năm, nấm, nắm, nằm |
| 10552 | `(?:phut\|minutes?\|gio\|hours?\|ngay\|days?\|tuan\|weeks?\|thang\|months?\|nam\|years?)\b` | gio: gió, giỗ, giờ; ngay: ngay, ngày, ngây; tuan: tuân, tuấn, tuần; thang: thang, tháng, thăng, thắng, thẳng; nam: nam, năm, nấm, nắm, nằm |
| 10558 | `phut` | - |
| 10559 | `phut` | - |
| 10560 | `gio` | gio: gió, giỗ, giờ |
| 10561 | `gio` | gio: gió, giỗ, giờ |
| 10562 | `day` | day: đây, đầy |
| 10562 | `ngay` | ngay: ngay, ngày, ngây |
| 10563 | `ngay` | ngay: ngay, ngày, ngây |
| 10564 | `tuan` | tuan: tuân, tuấn, tuần |
| 10565 | `tuan` | tuan: tuân, tuấn, tuần |
| 10566 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 10567 | `thang` | thang: thang, tháng, thăng, thắng, thẳng |
| 10568 | `nam` | nam: nam, năm, nấm, nắm, nằm |
| 10576 | `\s*/\s*(ngay\|day\|tuan\|week\|thang\|month\|nam\|year)\b` | ngay: ngay, ngày, ngây; day: đây, đầy; tuan: tuân, tuấn, tuần; thang: thang, tháng, thăng, thắng, thẳng; nam: nam, năm, nấm, nắm, nằm |
| 10581 | `(?:moi\|per)\s+(ngay\|day\|tuan\|week\|thang\|month\|nam\|year)\s*$` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời; ngay: ngay, ngày, ngây; day: đây, đầy; tuan: tuân, tuấn, tuần; thang: thang, tháng, thăng, thắng, thẳng; nam: nam, năm, nấm, nắm, nằm |
| 10687 | `\s*/\s*(?:ngay\|tuan\|thang\|nam\|day\|week\|month\|year)\b` | ngay: ngay, ngày, ngây; tuan: tuân, tuấn, tuần; thang: thang, tháng, thăng, thắng, thẳng; nam: nam, năm, nấm, nắm, nằm; day: đây, đầy |
| 10721 | `cua` | cua: của, cửa |
| 10723 | `chinh` | chinh: chính, chỉnh |
| 10724 | `sach` | sach: sách, sạch |
| 10725 | `co` | co: có, cô, cơ, cố, cổ, cờ, cỡ |
| 10726 | `duoc` | duoc: dược, được |
| 10727 | `moi` | moi: môi, mọi, mỏi, mối, mỗi, mới, mời |
| 10728 | `nhan` | nhan: nhân, nhãn, nhạn, nhấn, nhẫn, nhận, nhắn |
| 10729 | `vien` | vien: viên, viền, viễn, viện |
| 10730 | `trong` | trong: trọng, trống |
| 10731 | `khoang` | - |
| 10732 | `nao` | - |
| 10735 | `bat` | bat: bất, bật, bắt |
| 10735 | `dau` | dau: dấu, dầu, đau, đâu, đầu |
| 10736 | `vao` | - |
| 10736 | `lam` | lam: lam, làm, lâm, lạm, lắm |
| 10738 | `ket` | - |
| 10738 | `thuc` | thuc: thúc, thục, thức, thực |
| 10739 | `cot` | cot: cốt, cột |
| 10739 | `loi` | loi: lõi, lối, lỗi, lội, lời, lợi |
| 10740 | `linh` | - |
| 10740 | `hoat` | - |
| 10783 | `bat` | bat: bất, bật, bắt |
| 10783 | `dau` | dau: dấu, dầu, đau, đâu, đầu |
| 10786 | `ket` | - |
| 10786 | `thuc` | thuc: thúc, thục, thức, thực |
| 10790 | `cot` | cot: cốt, cột |
| 10790 | `loi` | loi: lõi, lối, lỗi, lội, lời, lợi |
| 10792 | `linh` | - |
| 10792 | `hoat` | - |
