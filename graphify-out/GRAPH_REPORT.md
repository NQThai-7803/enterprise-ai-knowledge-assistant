> **Bản đồ tham khảo, không phải nguồn sự thật.** Commit code được quét: `19840409b051e3b397d5861995f52e7ede2434ee`. Phạm vi: `app/`, `frontend/src/`, `scripts/` (trừ `scripts/eval/`), 289 file .py/.ts/.tsx/.ps1/.sh. Trích xuất bằng AST, không gọi LLM hay API ngoài. Không quét `docs/`, `artifacts/`, `tests/`, `data/`, `uat/`. Luôn đọc code thật trước khi sửa; graph có thể lỗi thời so với commit trên.

# Graph Report - Enterprise AI Knowledge Assistant  (2026-11-05)

## Corpus Check
- 289 files · ~156,190 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3424 nodes · 12075 edges · 129 communities (101 shown, 28 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 978 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `19840409`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Claim-evidence validation
- Admin analytics
- Application exceptions
- Prompt hit ranking and matching
- Grounded answer structured facts
- Document service
- Document text extraction
- Grounded answer orchestration
- Release audit scripts
- Frontend API client
- ORM models and benchmarks
- Citation mapping and validation
- Frontend admin pages
- User management
- Department management
- Context builder and excerpts
- Answer drafting and repair
- Settings and web search intent
- Question analysis and subclaims
- Seed scripts
- Shared schemas and services
- Document API routes
- Document worker tasks
- File storage
- Chat streaming and SSE
- Feedback
- Frontend SSE and auth tokens
- Alembic migrations
- Document processing pipeline
- Rate limiting and dependencies
- Retrieval interfaces
- Audit logging
- Request middleware
- Embeddings
- Frontend app shell
- Authentication
- Structured retrieval records
- Web search providers
- App startup and health
- Chat API routes
- Minor: documents.py
- Minor: service.py
- Minor: _prompt_hit_alignment_score()
- Minor: reranker.py
- Minor: _structured_value_repair_generation()
- Minor: observability/metrics.py
- Minor: AdminMonitoringService
- Minor: DocumentPermissionService
- Minor: permissions.py
- Minor: tesseract_provider.py
- Minor: admin_monitoring_service.py
- Minor: follow_up_resolver.py
- Minor: DocumentPermissionsPage.tsx
- Minor: ChatSession
- Minor: is_non_answer_context()
- Minor: QuestionAnalysis
- Minor: ChatPage.tsx
- Minor: keyword_repository.py
- Minor: semantic_service.py
- Minor: v1/auth.py
- Minor: PageAwareTokenChunker
- Minor: LLMMessage
- Minor: ProviderHealth
- Minor: web_search/registry.py
- Minor: departments.py
- Minor: metadata.py
- Minor: prompt_builder.py
- Minor: secret_value()
- Minor: retrieval/models.py
- Minor: list_users()
- Minor: conversation_context_builder.py
- Minor: DocumentUploadPage.tsx
- Minor: config.py
- Minor: collections_abc
- Minor: LLMError
- Minor: search_permitted_chunks()
- Minor: audit_logs.py
- Minor: dataclasses
- Minor: admin.py
- Minor: page_aware_chunker.py
- Minor: ChunkingError
- Minor: LLMFailureCode
- Minor: ToastProvider.tsx
- Minor: v1/web_search.py
- Minor: leave_relations.py
- Minor: DocumentChunkRepository
- Minor: _PromptTruncationGuard
- Minor: get_admin_health()
- Minor: _overtime_rate_facts()
- Minor: grounded_output.py
- Minor: env.py
- Minor: llm/models.py
- Minor: logging.py
- Minor: app.mocked.spec.ts
- Minor: audit_log_repository.py
- Minor: _corresponding_work_time_answer()
- Minor: refresh_token_repository.py
- Minor: metrics()
- Minor: _parse_generation_response()
- Minor: _passive_action_polarity_is_contradicted
- Minor: .get_providers()
- Minor: _structured_policy_clause_repair_generat
- Minor: smoke_corpus_v2.ps1
- Minor: run_integration_lanes.sh

## God Nodes (most connected - your core abstractions)
1. `Settings` - 170 edges
2. `_fold_for_person_match()` - 131 edges
3. `PromptSourceRegistry` - 111 edges
4. `fold_text()` - 91 edges
5. `analyze_question()` - 85 edges
6. `get_settings()` - 83 edges
7. `ApplicationError` - 78 edges
8. `AuditContext` - 73 edges
9. `GroundedAnswerService` - 68 edges
10. `get_db_session()` - 62 edges

## Surprising Connections (you probably didn't know these)
- `_evaluate_existing()` --uses--> `ClaimEvidenceStatus`  [INFERRED]
  scripts/release/task0353c2e_eval.py → app/services/claim_evidence_validation_service.py
- `_registry()` --calls--> `PromptSource`  [EXTRACTED]
  scripts/release/task0353c2e_eval.py → app/citations/models.py
- `_registry()` --calls--> `PromptSourceRegistry`  [EXTRACTED]
  scripts/release/task0353c2e_eval.py → app/citations/models.py
- `_load()` --uses--> `Base`  [INFERRED]
  scripts/benchmark/hnsw_exact_knn.py → app/db/base.py
- `_load()` --calls--> `Department`  [INFERRED]
  scripts/benchmark/hnsw_exact_knn.py → app/models/department.py

## Import Cycles
- None detected.

## Communities (129 total, 28 thin omitted)

### Community 0 - "Claim-evidence validation"
Cohesion: 0.05
Nodes (82): fold_text(), monetary_value_numbers(), monetary_value_period_pairs(), requested_monetary_period(), _answer_claims_unspecified_but_source_has_value(), _answer_has_grounded_signal(), _answer_introduces_person_name(), _answer_is_low_substance() (+74 more)

### Community 1 - "Admin analytics"
Cohesion: 0.10
Nodes (60): export_admin_report(), get_admin_analytics_overview(), get_admin_audit_analytics(), get_admin_chat_analytics(), get_admin_feedback_analytics(), get_admin_llm_analytics(), get_admin_ocr_analytics(), get_admin_search_analytics() (+52 more)

### Community 2 - "Application exceptions"
Cohesion: 0.04
Nodes (38): ApplicationError, AuditMetadataInvalidError, AuditOperationFailedError, ChatMessageContentInvalidError, ChatMessageContentTooLongError, ChatMessageMetricsInvalidError, ChatRetrievalFailedError, CitationMappingFailedApplicationError (+30 more)

### Community 3 - "Prompt hit ranking and matching"
Cohesion: 0.05
Nodes (63): HybridRetrievalHit, analyze_question(), retrieval_query_variants(), _answer_body_after_reference_prefix(), _asks_about_purpose(), _asks_for_full_range(), _asks_for_quantity(), _asks_role_assignment_question() (+55 more)

### Community 4 - "Grounded answer structured facts"
Cohesion: 0.05
Nodes (71): ClaimRepairFeedback, _allowance_condition_tail(), _allowance_fact_matches_question(), _allowance_fact_question_match_score(), _allowance_subject_before_amount(), _answer_contains_source_person_name(), _answer_contains_source_unit(), _answer_has_grounded_substance() (+63 more)

### Community 5 - "Document service"
Cohesion: 0.08
Nodes (36): BusinessValidationError, DocumentFilenameInvalidError, DocumentFileSignatureInvalidError, DocumentFileUnavailableError, DuplicateDocumentError, EmptyFileError, FileTooLargeError, InternalServerError (+28 more)

### Community 6 - "Document text extraction"
Cohesion: 0.07
Nodes (31): SupportedDocumentType, DocumentExtractionError, DocumentExtractionFailureCode, PDFExtractionError, PDFExtractionFailureCode, _build_extraction_result(), _coerce_source(), _copy_page_with_metadata() (+23 more)

### Community 7 - "Grounded answer orchestration"
Cohesion: 0.06
Nodes (38): ConversationContext, GroundingStatus, ChatSessionNotFoundError, build_accessible_document_filter(), LLMGenerationResult, RetrievalReranker, _adjacent_hit_from_chunk(), _AnswerDraft (+30 more)

### Community 8 - "Release audit scripts"
Cohesion: 0.07
Nodes (35): main(), validate_runtime(), _validate_runtime_path(), ask(), assert_status(), authorized(), login(), main() (+27 more)

### Community 9 - "Frontend API client"
Cohesion: 0.06
Nodes (50): ApiRequestOptions, buildUrl(), download(), DownloadResponse, fetchWithTimeout(), filenameFromDisposition(), QueryParams, QueryPrimitive (+42 more)

### Community 10 - "ORM models and benchmarks"
Cohesion: 0.14
Nodes (27): Base, downgrade(), upgrade(), ChatMessage, Department, DocumentChunk, DocumentPermission, ChatMessageRole (+19 more)

### Community 11 - "Citation mapping and validation"
Cohesion: 0.08
Nodes (32): CitationError, CitationFailureCode, CitationMappingError, CitationPermissionRevalidationError, CitationValidationError, _append_unique_candidate(), _claim_for_marker(), _contains_folded_term() (+24 more)

### Community 12 - "Frontend admin pages"
Cohesion: 0.16
Nodes (40): apiClient, safeErrorMessage(), DocumentStatus, DataTable(), PageHeader(), Badge(), BadgeTone, toneClasses (+32 more)

### Community 13 - "User management"
Cohesion: 0.09
Nodes (20): LastActiveAdminError, SelfModificationNotAllowedError, UserEmailAlreadyExistsError, count_active_admins(), count_active_users_by_department(), count_users(), create(), get_by_email() (+12 more)

### Community 14 - "Department management"
Cohesion: 0.08
Nodes (19): DepartmentCodeAlreadyExistsError, DepartmentHasDocumentsError, DepartmentInUseError, DepartmentNameAlreadyExistsError, count_departments(), create(), delete(), _department_filter_conditions() (+11 more)

### Community 15 - "Context builder and excerpts"
Cohesion: 0.08
Nodes (42): _attendance_relation_excerpt(), _base_budget_text(), _budget_structural_line_indexes(), _bullet_multi_value_line(), _claim_focused_excerpt(), _collapse_whitespace(), _contains_folded_token(), _fold_text() (+34 more)

### Community 16 - "Answer drafting and repair"
Cohesion: 0.07
Nodes (42): StructuredGroundedClaim, PromptSourceRegistry, _allowed_source_identifiers(), _annual_leave_answer_mismatches_bound_relation(), _change_answer_missing_source_change(), _claim_repair_source_limit(), _hits_have_multi_value_duration_evidence(), _is_placeholder_like_json_answer() (+34 more)

### Community 17 - "Settings and web search intent"
Cohesion: 0.06
Nodes (7): _optional_secret_file_value(), Settings, _validate_database_url_value(), _validate_redis_url_value(), SearchIntent, WebSearchIntentClassifier, KnowledgeSourceMode

### Community 18 - "Question analysis and subclaims"
Cohesion: 0.07
Nodes (30): _asks_for_amount(), _asks_for_count(), _asks_for_date(), _asks_for_definition(), _asks_for_duration(), _asks_for_explanation(), _asks_for_list(), _asks_for_organization() (+22 more)

### Community 19 - "Seed scripts"
Cohesion: 0.09
Nodes (25): hash_password(), main(), normalize_admin_email(), resolve_admin_password(), run_seed_command(), seed_development_admin(), SeedAdminError, validate_admin_password() (+17 more)

### Community 20 - "Shared schemas and services"
Cohesion: 0.11
Nodes (16): ChatSessionTitleTooLongError, VisibleChatMessageRow, ChatSessionListRow, ChatMessageRead, ChatSessionDetail, CitationRead, build_pagination_meta(), calculate_offset() (+8 more)

### Community 21 - "Document API routes"
Cohesion: 0.12
Nodes (14): get_audit_context(), create_document_permission(), delete_document(), delete_document_permission(), download_document(), get_document_detail(), get_document_status(), list_document_permissions() (+6 more)

### Community 22 - "Document worker tasks"
Cohesion: 0.11
Nodes (20): DocumentProcessingOutcome, DocumentProcessingClaimOutcome, DocumentProcessingClaimResult, DocumentProcessingStatusService, sanitize_processing_error(), run_async(), _claim_outcome_to_processing_outcome(), _claim_result_to_task_result() (+12 more)

### Community 23 - "File storage"
Cohesion: 0.08
Nodes (10): load_pdf_bytes_for_extraction(), PDFStorageReadError, FileStorage, _build_file_storage(), get_file_storage(), LocalFileStorage, StorageConflictError, StorageError (+2 more)

### Community 24 - "Chat streaming and SSE"
Cohesion: 0.11
Nodes (13): ChatAnswerResult, encode_sse(), _is_safe_sse_field(), SSEEventStateError, SSEEventWriter, ChatAnswerResponse, _cancel_task(), ChatStreamService (+5 more)

### Community 25 - "Feedback"
Cohesion: 0.10
Nodes (15): list_feedback_report(), upsert_message_feedback(), _apply_report_scope_and_filters(), count_report(), FeedbackReportFilters, FeedbackReportRow, FeedbackRow, get_owned_assistant_message_id() (+7 more)

### Community 26 - "Frontend SSE and auth tokens"
Cohesion: 0.10
Nodes (25): base64UrlDecode(), buildHeaders(), decodeJwtPayload(), ensureFreshAccessToken(), isAccessTokenExpired(), refreshAccessToken(), ChatStreamRequest, fetchStreamResponse() (+17 more)

### Community 27 - "Alembic migrations"
Cohesion: 0.06
Nodes (13): upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), upgrade(), downgrade(), upgrade() (+5 more)

### Community 28 - "Document processing pipeline"
Cohesion: 0.12
Nodes (11): get_settings(), TextChunker, create_document_chunker(), ChunkingResult, create_extraction_router(), create_document_processing_pipeline(), DocumentProcessingMetadata, DocumentProcessingPipeline (+3 more)

### Community 29 - "Rate limiting and dependencies"
Cohesion: 0.12
Nodes (23): enforce_chat_rate_limit(), enforce_feedback_rate_limit(), enforce_login_rate_limit(), enforce_refresh_rate_limit(), enforce_upload_rate_limit(), get_document_processing_enqueue(), require_roles(), role_dependency() (+15 more)

### Community 30 - "Retrieval interfaces"
Cohesion: 0.10
Nodes (16): create_embedding_provider(), SentenceTransformerEmbeddingProvider, HybridRetrievalService, KeywordRetrievalService, RetrievalService, create_hybrid_retrieval_service(), create_keyword_retrieval_service(), create_semantic_retrieval_service() (+8 more)

### Community 31 - "Audit logging"
Cohesion: 0.14
Nodes (21): AuditEventType, AuditTargetType, AuditDateRangeInvalidError, AuditEventInvalidError, AuditFilterInvalidError, AuditReportForbiddenError, calculate_total_pages(), AuditContext (+13 more)

### Community 32 - "Request middleware"
Cohesion: 0.09
Nodes (14): _content_length_over_limit(), _header_value(), RequestBodyTooLargeError, RequestObservabilityMiddleware, send_wrapper(), _scope_headers(), _send_request_too_large(), new_request_id() (+6 more)

### Community 33 - "Embeddings"
Cohesion: 0.15
Nodes (12): EmbeddingProvider, EmbeddingError, EmbeddingFailureCode, _coerce_values(), EmbeddingBatch, EmbeddingVector, _is_normalized(), _to_embedding_rows() (+4 more)

### Community 34 - "Frontend app shell"
Cohesion: 0.14
Nodes (26): AuthenticatedUser, UserRole, App(), AccessDeniedState(), AuthContextValue, useAuth(), LoginPage(), ProtectedRoute() (+18 more)

### Community 35 - "Authentication"
Cohesion: 0.14
Nodes (15): AccessTokenInvalidError, InvalidCredentialsError, RefreshTokenInvalidError, TokenExpiredError, UserInactiveError, AccessTokenPayload, create_access_token(), decode_access_token() (+7 more)

### Community 36 - "Structured retrieval records"
Cohesion: 0.11
Nodes (27): question_terms(), _asks_for_security_controls(), _asks_regular_night_work(), build_structured_records(), _contains_folded_token(), _contains_folded_word(), _has_policy_polarity(), _is_mismatched_regular_night_percentage() (+19 more)

### Community 37 - "Web search providers"
Cohesion: 0.14
Nodes (13): WebSearchError, WebSearchResults, normalize_web_search_provider_name(), web_search_provider_display_name(), BingWebSearchProvider, _dict_items(), DuckDuckGoWebSearchProvider, _flatten_duckduckgo_related() (+5 more)

### Community 38 - "App startup and health"
Cohesion: 0.12
Nodes (17): check_redis_connection(), HealthLiveResponse, HealthReadyResponse, live(), ready(), application_error_handler(), _audit_validation_error_code(), _feedback_validation_error_code() (+9 more)

### Community 39 - "Chat API routes"
Cohesion: 0.14
Nodes (11): get_current_user(), get_grounded_answer_service(), create_chat_session(), delete_chat_session(), list_chat_sessions(), read_chat_session(), stream_chat_message(), submit_chat_message() (+3 more)

### Community 40 - "Minor: documents.py"
Cohesion: 0.10
Nodes (9): get_document_upload_limits(), DocumentDetailResponse, DocumentListItem, DocumentPermissionUpdate, DocumentSafeResponse, DocumentStatusResponse, DocumentUploadMetadata, DocumentUploadResponse (+1 more)

### Community 41 - "Minor: service.py"
Cohesion: 0.10
Nodes (11): render_web_result_source_context_item(), clean_web_text(), _is_blocked_hostname(), _is_hidden(), normalize_web_url(), _visible_character(), _VisibleTextExtractor, WebSearchFailureCode (+3 more)

### Community 42 - "Minor: _prompt_hit_alignment_score()"
Cohesion: 0.08
Nodes (22): _contains_folded_phrase(), _contains_number_unit(), _is_person_lookup_question(), _named_entity_evidence_is_missing(), _named_service_category_is_present(), _prompt_attendance_policy_score(), _prompt_hit_alignment_score(), _prompt_non_answer_context_penalty() (+14 more)

### Community 43 - "Minor: reranker.py"
Cohesion: 0.13
Nodes (22): _alignment_score(), _coerce_score(), create_retrieval_reranker(), _has_person_name_sequence(), _has_role_person_association(), HeuristicRetrievalReranker, _important_term_coverage_score(), _is_name_token_candidate() (+14 more)

### Community 44 - "Minor: _structured_value_repair_generation()"
Cohesion: 0.07
Nodes (19): _annual_leave_category(), _annual_leave_neighbor_label_category(), _is_narrow_duration_question(), _is_performance_bonus_range_question(), _leave_incident_time_intent(), _performance_bonus_range_facts(), _PerformanceBonusRangeFact, _prompt_value_focus_terms() (+11 more)

### Community 45 - "Minor: observability/metrics.py"
Cohesion: 0.13
Nodes (14): _escape_label_value(), _format_number(), HTTPMetricKey, HTTPMetricSnapshot, MetricsRegistry, normalize_route_path(), prometheus_labels(), prometheus_sample() (+6 more)

### Community 46 - "Minor: AdminMonitoringService"
Cohesion: 0.15
Nodes (10): AdminComponentCheck, AdminQueueStatus, AdminMonitoringService, _application_started_at(), _application_version(), _component_status_from_provider_health(), _migration_source_head(), _overall_health_status() (+2 more)

### Community 47 - "Minor: DocumentPermissionService"
Cohesion: 0.18
Nodes (11): DocumentPermissionAlreadyExistsError, create(), delete(), get_by_document_and_department(), get_by_document_and_id(), get_by_document_and_user(), get_by_id(), list_for_document() (+3 more)

### Community 48 - "Minor: permissions.py"
Cohesion: 0.16
Nodes (16): can_access_department(), can_assign_role(), can_manage_department_users(), can_manage_user(), choose_highest_permission(), ensure_permission(), count_accessible_documents(), count_documents_by_department() (+8 more)

### Community 49 - "Minor: tesseract_provider.py"
Cohesion: 0.14
Nodes (9): OCRHealthResult, OCRImageInput, OCRPageResult, OCRResult, OCRProvider, create_tesseract_ocr_provider(), _parse_available_languages(), _parse_version() (+1 more)

### Community 50 - "Minor: admin_monitoring_service.py"
Cohesion: 0.13
Nodes (17): AdminWorkerInfo, _call_celery_inspect(), _count_table(), _count_where(), _group_counts(), _inspect_worker_ping(), _inspect_worker_snapshot(), _iter_route_paths() (+9 more)

### Community 51 - "Minor: follow_up_resolver.py"
Cohesion: 0.22
Nodes (25): _append_focus_to_previous_question(), _ensure_question(), _expand_explicit_topic_follow_up(), _extract_follow_up_focus(), _extract_previous_mode_topic(), _extract_previous_question_target(), _extract_quantity_topic(), _extract_short_reference_topic() (+17 more)

### Community 52 - "Minor: DocumentPermissionsPage.tsx"
Cohesion: 0.13
Nodes (19): PaginationMeta, ErrorBoundary, ErrorBoundaryState, Button(), ButtonProps, ButtonVariant, variantClasses, ConfirmDialog() (+11 more)

### Community 53 - "Minor: ChatSession"
Cohesion: 0.17
Nodes (16): ChatSession, ConversationMemoryMessageRow, count_visible_by_session(), create(), list_owned_messages_for_memory(), list_recent_visible_owned_messages(), list_visible_by_session(), count_owned() (+8 more)

### Community 54 - "Minor: is_non_answer_context()"
Cohesion: 0.10
Nodes (17): classify_evidence_context(), EvidenceContextKind, _has_answer_bearing_content(), is_non_answer_context(), _claim_repair_feedback(), ClaimEvidenceValidationResult, ClaimEvidenceValidationService, _effective_policy_relation() (+9 more)

### Community 55 - "Minor: QuestionAnalysis"
Cohesion: 0.09
Nodes (19): QuestionAnalysis, _amount_direct_value_repair_allowed(), _direct_value_field_phrases(), _direct_value_pattern_for_analysis(), _duration_direct_value_repair_allowed(), _duration_match_period_units(), _duration_match_unit(), _number_match_is_time_or_date_component() (+11 more)

### Community 56 - "Minor: ChatPage.tsx"
Cohesion: 0.15
Nodes (21): ChatMessage, Citation, MessageCompletedPayload, StreamErrorPayload, ShimmerText(), SpotlightPanel(), AssistantStreamBubble(), AssistantWaiting() (+13 more)

### Community 57 - "Minor: keyword_repository.py"
Cohesion: 0.14
Nodes (15): current_authority_order_expression(), is_historical_query(), _execute_keyword_search(), _fallback_tsquery_text(), _identifier_query_texts(), _is_meaningful_fallback_term(), KeywordRetrievalRepository, KeywordRetrievalRow (+7 more)

### Community 58 - "Minor: semantic_service.py"
Cohesion: 0.25
Nodes (11): RetrievalError, RetrievalFailureCode, _row_to_hit(), validate_active_retrieval_user(), validate_min_keyword_rank(), validate_relevance_threshold(), validate_retrieval_query(), validate_top_k() (+3 more)

### Community 59 - "Minor: v1/auth.py"
Cohesion: 0.20
Nodes (12): login(), logout(), me(), refresh(), _token_pair_response(), AuthenticatedUserDataResponse, AuthenticatedUserResponse, LoginRequest (+4 more)

### Community 60 - "Minor: PageAwareTokenChunker"
Cohesion: 0.22
Nodes (6): TextChunk, _ChunkSegment, _DraftChunk, _join_segments(), PageAwareTokenChunker, _unique_pages_from_segments()

### Community 61 - "Minor: LLMMessage"
Cohesion: 0.17
Nodes (9): AnthropicLLMProvider, _build_gemini_payload(), GeminiLLMProvider, _is_retryable_status(), _provider_error_code(), build_llm_request(), LLMMessage, LLMRequest (+1 more)

### Community 62 - "Minor: ProviderHealth"
Cohesion: 0.15
Nodes (4): LLMProvider, BaseHTTPProvider, LLMProviderManager, ProviderHealth

### Community 63 - "Minor: web_search/registry.py"
Cohesion: 0.15
Nodes (5): WebSearchProvider, WebSearchProviderManager, WebSearchProviderHealth, BaseHTTPWebSearchProvider, create_web_search_provider_registry()

### Community 64 - "Minor: departments.py"
Cohesion: 0.20
Nodes (6): create_department(), delete_department(), get_department(), list_departments(), update_department(), DepartmentResponse

### Community 65 - "Minor: metadata.py"
Cohesion: 0.23
Nodes (16): AuditEvent, AuditMetadataError, AuditScalar, _coerce_safe_scalar(), _is_sensitive_key(), _normalize_key(), sanitize_audit_metadata(), _sanitize_metadata_value() (+8 more)

### Community 66 - "Minor: prompt_builder.py"
Cohesion: 0.19
Nodes (19): render_context(), render_context_item(), render_source_context(), render_user_reference_history(), SelectedContextItem, _asks_for_security_controls(), build_failed_claim_repair_prompt(), build_grounded_prompt() (+11 more)

### Community 67 - "Minor: secret_value()"
Cohesion: 0.11
Nodes (4): AzureOpenAILLMProvider, bearer_headers(), secret_value(), LLMProviderCapabilities

### Community 68 - "Minor: retrieval/models.py"
Cohesion: 0.21
Nodes (17): _coerce_weight(), _first_ranked_keyword_hits(), _first_ranked_semantic_hits(), _fuse_chunk(), fuse_retrieval_hits(), FusedRetrievalResult, _hybrid_sort_key(), _validate_fusion_configuration() (+9 more)

### Community 69 - "Minor: list_users()"
Cohesion: 0.17
Nodes (5): create_user(), delete_user(), get_user(), list_users(), update_user()

### Community 70 - "Minor: conversation_context_builder.py"
Cohesion: 0.18
Nodes (8): _conversation_role_label(), ConversationContextBuilder, ConversationPromptMessage, prompt_messages_from_rows(), render_conversation_history(), render_conversation_message(), render_conversation_retrieval_query(), ResolvedConversationQuestion

### Community 71 - "Minor: DocumentUploadPage.tsx"
Cohesion: 0.15
Nodes (12): isApiError(), useToast(), SoftSignalBackground(), TextArea, LoginForm, loginSchema, DocumentUploadPage(), formatDepartmentOption() (+4 more)

### Community 72 - "Minor: config.py"
Cohesion: 0.18
Nodes (12): _database_password_is_placeholder(), _is_local_provider_host(), _is_placeholder_secret(), _llm_url_is_local(), _model_or_default(), _secret_is_empty(), _uses_localhost(), _validate_cors_origin() (+4 more)

### Community 73 - "Minor: collections_abc"
Cohesion: 0.39
Nodes (7): append_v1_if_missing(), _is_local_host(), _is_safe_request_id(), safe_request_id(), validate_base_url(), normalize_finish_reason(), provider_display_name()

### Community 74 - "Minor: LLMError"
Cohesion: 0.19
Nodes (8): LLMError, create_llm_provider(), normalize_provider_name(), create_provider_registry(), LLMProviderRegistry, provider_configuration_health(), _required_model(), _selected_model()

### Community 75 - "Minor: search_permitted_chunks()"
Cohesion: 0.15
Nodes (6): _exact_permitted_knn_statement(), _retrieval_rows(), RetrievalRow, search_permitted_chunks(), SemanticRetrievalRepository, SemanticSearchRepository

### Community 76 - "Minor: audit_logs.py"
Cohesion: 0.20
Nodes (4): list_audit_logs(), AuditOutcome, AuditLogListResponse, AuditLogRead

### Community 77 - "Minor: dataclasses"
Cohesion: 0.19
Nodes (7): get_permitted_ready_chunks_by_ids(), PermittedCitationSourceRow, create_many(), list_by_message(), list_by_message_ids(), MessageCitationRow, _row_from_result()

### Community 78 - "Minor: admin.py"
Cohesion: 0.30
Nodes (13): AdminCountStatistic, AdminDocumentStatistics, AdminFeedbackStatistics, AdminHealthResponse, AdminMessageStatistics, AdminProvidersResponse, AdminQueuesResponse, AdminSessionStatistics (+5 more)

### Community 79 - "Minor: page_aware_chunker.py"
Cohesion: 0.24
Nodes (7): _decode_bounded_window(), split_paragraphs(), split_sentences(), split_text_unit_to_token_windows(), TextUnit, TextUnitKind, TokenCounter

### Community 80 - "Minor: ChunkingError"
Cohesion: 0.18
Nodes (3): ChunkingError, ChunkingFailureCode, TiktokenTokenCounter

### Community 81 - "Minor: LLMFailureCode"
Cohesion: 0.19
Nodes (9): _content_text(), _optional_non_negative_usage(), _parse_anthropic_response(), _usage_from_anthropic(), LLMFailureCode, _candidate_text(), _optional_non_negative_usage(), _parse_gemini_response() (+1 more)

### Community 82 - "Minor: ToastProvider.tsx"
Cohesion: 0.15
Nodes (12): reducer(), ToastAction, ToastContext, ToastContextValue, ToastInput, ToastItem, ToastProvider(), ToastTone (+4 more)

### Community 83 - "Minor: v1/web_search.py"
Cohesion: 0.28
Nodes (6): provider_status(), test_search(), WebSearchProviderStatusResponse, WebSearchResultRead, WebSearchTestRequest, WebSearchTestResponse

### Community 84 - "Minor: leave_relations.py"
Cohesion: 0.31
Nodes (10): _annual_leave_relation_excerpt(), annual_leave_relation_intent(), annual_leave_seniority_increment(), AnnualLeaveRelation, _has_annual_leave_scope(), ordinary_annual_leave_allocation(), requested_seniority_years(), _source_lines() (+2 more)

### Community 85 - "Minor: DocumentChunkRepository"
Cohesion: 0.21
Nodes (5): _coerce_embedding_values(), DocumentChunkCreate, DocumentChunkRepository, _validate_replacement_payload(), build_document_chunk_rows()

### Community 86 - "Minor: _PromptTruncationGuard"
Cohesion: 0.15
Nodes (5): estimate_prompt_tokens(), prompt_budget_exceeded(), prompt_truncation_reason(), _PromptGuardStopError, _PromptTruncationGuard

### Community 87 - "Minor: get_admin_health()"
Cohesion: 0.54
Nodes (7): get_admin_health(), get_admin_providers(), get_admin_queues(), get_admin_statistics(), get_admin_system(), get_admin_version(), get_admin_workers()

### Community 88 - "Minor: _overtime_rate_facts()"
Cohesion: 0.21
Nodes (9): _flattened_overtime_rate_facts(), _is_overtime_rate_question(), _ot_day_type_from_context(), _overtime_rate_facts(), _overtime_rate_row_for_percentage(), _OvertimeRateFact, _requested_ot_day_type(), _structured_claim_missing_bound_overtime_rate() (+1 more)

### Community 89 - "Minor: grounded_output.py"
Cohesion: 0.33
Nodes (9): _answer_contains_citation_marker(), GroundedLLMOutput, _is_citation_only_answer(), parse_grounded_llm_output(), parse_partial_structured_grounded_llm_output(), parse_structured_grounded_llm_output(), _strip_single_json_fence(), StructuredGroundedLLMOutput (+1 more)

### Community 90 - "Minor: env.py"
Cohesion: 0.24
Nodes (6): do_run_migrations(), get_database_url(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), set_database_url()

### Community 91 - "Minor: llm/models.py"
Cohesion: 0.27
Nodes (6): _coerce_non_negative_int(), _coerce_optional_non_negative_int(), _coerce_positive_int(), _coerce_temperature(), LLMFinishReason, LLMUsage

### Community 92 - "Minor: logging.py"
Cohesion: 0.40
Nodes (6): configure_logging_redaction(), _is_sensitive_key(), redact_mapping(), redact_string(), redact_value(), SensitiveDataRedactionFilter

### Community 94 - "Minor: audit_log_repository.py"
Cohesion: 0.47
Nodes (6): AuditLog, _apply_report_filters(), AuditReportFilters, count_report(), create(), list_report()

### Community 95 - "Minor: _corresponding_work_time_answer()"
Cohesion: 0.25
Nodes (7): _corresponding_work_time_answer(), _join_vietnamese_list(), _named_schedule_endpoint_answer(), _question_focused_time_ranges_from_text(), _render_time_range_answer(), _structured_time_range_answer(), _time_range_minutes()

### Community 96 - "Minor: refresh_token_repository.py"
Cohesion: 0.50
Nodes (4): create(), get_by_hash_for_update(), revoke(), revoke_all_active_for_user()

### Community 98 - "Minor: _parse_generation_response()"
Cohesion: 0.33
Nodes (4): _optional_non_negative_usage(), _parse_generation_response(), _strip_visible_reasoning(), _usage_from_openai()

### Community 99 - "Minor: _passive_action_polarity_is_contradicted"
Cohesion: 0.33
Nodes (4): _deadline_window_is_contradicted(), _has_any(), _passive_action_polarity_is_contradicted(), _polarity_is_contradicted()

### Community 100 - "Minor: .get_providers()"
Cohesion: 0.47
Nodes (4): AdminProviderStatus, _llm_provider_status(), _provider_status_from_health(), _web_search_provider_status()

### Community 101 - "Minor: _structured_policy_clause_repair_generat"
Cohesion: 0.33
Nodes (4): _asks_for_scoped_self_policy(), _sensitive_policy_clause_cues(), _starts_policy_list_item(), _structured_policy_clause_repair_generation()

### Community 103 - "Minor: smoke_corpus_v2.ps1"
Cohesion: 0.83
Nodes (3): Ask(), Check-DocumentDenied(), Get-Token()

## Knowledge Gaps
- **28 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings and web search intent` to `Admin analytics`, `Application exceptions`, `Grounded answer structured facts`, `Document text extraction`, `Grounded answer orchestration`, `Release audit scripts`, `Citation mapping and validation`, `Seed scripts`, `Shared schemas and services`, `Chat streaming and SSE`, `Feedback`, `Document processing pipeline`, `Rate limiting and dependencies`, `Retrieval interfaces`, `Audit logging`, `Request middleware`, `Embeddings`, `Authentication`, `Web search providers`, `App startup and health`, `Minor: service.py`, `Minor: reranker.py`, `Minor: observability/metrics.py`, `Minor: AdminMonitoringService`, `Minor: tesseract_provider.py`, `Minor: admin_monitoring_service.py`, `Minor: ChatSession`, `Minor: keyword_repository.py`, `Minor: semantic_service.py`, `Minor: ProviderHealth`, `Minor: web_search/registry.py`, `Minor: conversation_context_builder.py`, `Minor: config.py`, `Minor: collections_abc`, `Minor: LLMError`, `Minor: search_permitted_chunks()`, `Minor: ChunkingError`, `Minor: metrics()`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 74 inferred relationships involving `Settings` (e.g. with `_settings_from_application()` and `ConversationContextBuilder`) actually correct?**
  _`Settings` has 74 INFERRED edges - model-reasoned connections that need verification._
- **Should `Claim-evidence validation` be split into smaller, more focused modules?**
  _Cohesion score 0.05385660890248046 - nodes in this community are weakly interconnected._
- **Why does `AuditContext` connect `Audit logging` to `Minor: departments.py`, `Authentication`, `Grounded answer structured facts`, `Minor: list_users()`, `Document service`, `Chat API routes`, `Minor: documents.py`, `Grounded answer orchestration`, `User management`, `Department management`, `Minor: DocumentPermissionService`, `Shared schemas and services`, `Document API routes`, `Chat streaming and SSE`, `Feedback`, `Minor: v1/auth.py`, `Rate limiting and dependencies`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 86 inferred relationships involving `PromptSourceRegistry` (e.g. with `build_failed_claim_repair_prompt()` and `build_grounded_prompt()`) actually correct?**
  _`PromptSourceRegistry` has 86 INFERRED edges - model-reasoned connections that need verification._
- **Should `Admin analytics` be split into smaller, more focused modules?**
  _Cohesion score 0.09608062709966406 - nodes in this community are weakly interconnected._
- **Why does `GroundedAnswerService` connect `Grounded answer orchestration` to `Claim-evidence validation`, `Application exceptions`, `Prompt hit ranking and matching`, `Grounded answer structured facts`, `Document service`, `Citation mapping and validation`, `Answer drafting and repair`, `Settings and web search intent`, `Chat streaming and SSE`, `Rate limiting and dependencies`, `Retrieval interfaces`, `Audit logging`, `Web search providers`, `Chat API routes`, `Minor: service.py`, `Minor: is_non_answer_context()`, `Minor: semantic_service.py`, `Minor: LLMMessage`, `Minor: ProviderHealth`, `Minor: conversation_context_builder.py`, `Minor: LLMError`, `Minor: page_aware_chunker.py`, `Minor: ChunkingError`, `Minor: grounded_output.py`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._