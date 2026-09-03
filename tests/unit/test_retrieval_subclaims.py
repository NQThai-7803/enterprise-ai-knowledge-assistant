from app.retrieval.subclaims import information_need_queries


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
