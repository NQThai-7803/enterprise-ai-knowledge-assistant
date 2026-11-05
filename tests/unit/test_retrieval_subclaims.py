from app.retrieval.subclaims import information_need_queries


def test_amount_and_frequency_remain_one_structured_value_request() -> None:
    assert (
        information_need_queries(
            "Tien mua do ergonomic duoc ho tro bao nhieu va bao lau duoc mot lan?"
        )
        == ()
    )
    assert (
        information_need_queries(
            "How much is the home-office benefit and how often is it available?"
        )
        == ()
    )


def test_compound_vietnamese_question_keeps_subject_for_each_need() -> None:
    question = "Nhân viên hybrid có yêu cầu bảo mật gì và có phụ cấp gì?"

    assert information_need_queries(question) == (
        "Nhân viên hybrid có yêu cầu bảo mật gì",
        "Nhân viên hybrid có phụ cấp gì",
    )


def test_single_need_question_is_not_rewritten() -> None:
    assert information_need_queries("Phụ cấp ăn trưa là bao nhiêu?") == ()


def test_no_diacritic_compound_question_has_backend_defined_subclaims() -> None:
    question = "Nhan vien hybrid duoc remote may ngay va phai bao dam an toan gi?"

    assert information_need_queries(question) == (
        "Nhan vien hybrid duoc remote may ngay",
        "Nhan vien hybrid phai bao dam an toan gi",
    )


def test_compound_attribute_query_carries_entity_subject_to_later_need() -> None:
    question = "Engineering Manager thuoc grade nao va dai luong bao nhieu?"

    assert information_need_queries(question) == (
        "Engineering Manager thuoc grade nao",
        "Engineering Manager dai luong bao nhieu",
    )


def test_later_clause_modal_is_not_used_as_the_first_clause_subject_boundary() -> None:
    question = (
        "Moi thang phu cap an trua bao nhieu va han muc noi tru NovaCare moi nam la bao nhieu?"
    )

    assert information_need_queries(question) == (
        "Moi thang phu cap an trua bao nhieu",
        "han muc noi tru NovaCare moi nam la bao nhieu",
    )


def test_leading_policy_qualifier_is_carried_to_later_need() -> None:
    question = (
        "Theo ND-HR-003, khung gio lam viec tham chieu la gi va luong hang thang duoc tra ngay nao?"
    )

    assert information_need_queries(question) == (
        "Theo ND-HR-003, khung gio lam viec tham chieu la gi",
        "Theo ND-HR-003 luong hang thang duoc tra ngay nao",
    )


def test_distinct_later_subject_is_not_replaced_by_first_attribute() -> None:
    question = "Khung gio lam viec tham chieu la gi va luong hang thang duoc tra ngay nao?"

    assert information_need_queries(question) == (
        "Khung gio lam viec tham chieu la gi",
        "luong hang thang duoc tra ngay nao",
    )


def test_negation_is_preserved_in_subclaim_query() -> None:
    question = "Nhân viên không được dùng thiết bị cá nhân và phải bật MFA?"

    assert information_need_queries(question)[0].startswith("Nhân viên không")


def test_condition_before_then_is_carried_to_later_need() -> None:
    question = (
        "Neu on-call phai xu ly su co vao Chu nhat thi thoi gian duoc ghi nhan ra sao "
        "va OT bao nhieu?"
    )

    assert information_need_queries(question) == (
        "Neu on-call phai xu ly su co vao Chu nhat thi thoi gian duoc ghi nhan ra sao",
        "Neu on-call OT bao nhieu vao Chu nhat",
    )


def test_paired_vua_construction_creates_two_subject_bound_needs() -> None:
    question = (
        "Tôi là nhân viên hybrid, vậy vừa phải tuân thủ bảo mật gì khi làm ở nhà "
        "vừa được hưởng khoản hỗ trợ nào?"
    )

    assert information_need_queries(question) == (
        "Tôi là nhân viên hybrid phải tuân thủ bảo mật gì khi làm ở nhà",
        "Tôi là nhân viên hybrid được hưởng khoản hỗ trợ nào",
    )


def test_predicate_conjunction_does_not_split_oncall_subject_from_condition() -> None:
    question = (
        "Tôi on-call và phải xử lý incident vào Chủ nhật thì thời gian làm việc "
        "và tiền OT được xử lý thế nào?"
    )

    assert information_need_queries(question) == (
        "Tôi on-call và phải xử lý incident vào Chủ nhật thì thời gian làm việc",
        "tiền OT được xử lý thế nào vào Chủ nhật",
    )


def test_coordinated_policy_objects_create_independent_retrieval_needs() -> None:
    question = (
        "Tôi đang nghỉ phép mà phải hỗ trợ production incident thì công ty xử lý "
        "quyền nghỉ với thời gian phát sinh thế nào?"
    )

    assert information_need_queries(question) == (
        "Tôi đang nghỉ phép mà phải hỗ trợ production incident quyền nghỉ",
        "Tôi đang nghỉ phép mà phải hỗ trợ production incident thời gian phát sinh",
    )


def test_ordinary_with_phrase_is_not_treated_as_coordinated_policy_objects() -> None:
    assert information_need_queries("Tôi làm việc với khách hàng thế nào?") == ()
