"""Kiểm thử đơn vị cho tầng `p06.planning` và hệ thống prompt templates có phiên bản.

1. File này giải quyết vấn đề gì?
   Xác minh độ tin cậy của bộ nạp/băm/kết xuất prompt (`prompt_loader.py`), sự tách biệt
   tuyệt đối giữa bản nháp LLM và metadata thẩm quyền (`draft_dtos.py`), cơ chế lập kế hoạch
   chống bịa dữ liệu (`StoryPlanner`), ranh giới phê duyệt (`SimulatedMerchantApprovalBoundary`),
   và bộ chọn chủ đề tuần tự tôn trọng bất biến `I-04` (`ArcSequencer`).
2. Trách nhiệm chính của module là gì?
   Kiểm thử tích cực, âm tính, biên (edge cases) và chống đột biến cho toàn bộ thành phần trong
   `p06.planning` cùng các tệp `prompts/*.txt`.
3. Module này liên kết với các thành phần nào?
   Kiểm thử `p06.planning`, `p06.providers.MockLLMProvider`, `p06.adapters.P05KnowledgeAdapter`,
   cùng dữ liệu fixture `e01_verified_skus.json`, `e01_story_plans.json`, `catalog_seed.json`.
4. Input và output chính là gì?
   Input là các tệp prompt thật, bản chụp tri thức P05, kịch bản `MockLLMProvider`, và `StoryPlan`;
   Output là xác nhận toàn bộ bất biến `I-02`, `I-04`, `Gate G6` và hash LF đa nền tảng.
5. Có những constraints hoặc invariants quan trọng nào?
   - Dùng `MockLLMProvider` (`UNIT_TEST`) hoàn toàn offline và tất định.
   - Không làm yếu bất kỳ assertion nào; bao phủ đầy đủ ca âm tính (extra fields, fabricated refs,
     cross-tenant, ineligible SKU, stale/wrong approval status, SKU switch leak).
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from p06.adapters import P05KnowledgeAdapter
from p06.adapters.p05_knowledge_adapter import _load_p05_modules
from p06.planning import (
    DEFAULT_PROMPTS_DIR,
    ArcSequencer,
    ChunkDraftLLMOutput,
    MerchantGoalInput,
    PromptTemplate,
    SimulatedMerchantApprovalBoundary,
    StoryArcDraftLLMOutput,
    StoryPlanDraftLLMOutput,
    StoryPlanner,
    StoryTopicDraftLLMOutput,
    TopicSelectionResult,
    compute_prompt_hashes,
    load_prompt_template,
    render_prompt_template,
)
from p06.providers import MockBehavior, MockLLMProvider, MockResponseStep
from p06.schemas import (
    BreakpointType,
    StoryArc,
    StoryCheckpoint,
    StoryChunkRole,
    StoryPlan,
    StoryPlanApprovalStatus,
    StoryTopic,
)

P06_ROOT: Path = Path(__file__).resolve().parents[2]
E01_SEED_PATH: Path = P06_ROOT / "data" / "products" / "e01_verified_skus.json"
E01_PLANS_PATH: Path = P06_ROOT / "data" / "story_plans" / "e01_story_plans.json"
P05_DIR: Path = P06_ROOT.parent / "knowledge-verification"
P05_CATALOG_SEED_PATH: Path = P05_DIR / "data" / "catalog_seed.json"

E01_TENANT = "tenant-p06-poc-01"
P05_SEED_TENANT = "tenant-demo-01"
FIXED_TS = datetime(2026, 11, 26, 12, 30, 0, tzinfo=timezone.utc)


def _make_adapter(seed_path: Path = E01_SEED_PATH) -> tuple[P05KnowledgeAdapter, Any, Any]:
    """Khởi tạo adapter P05 độc lập từ bản sao kho tri thức."""
    p05_schemas, p05_gate = _load_p05_modules(P05_DIR)
    store = p05_gate.VersionedKnowledgeStore.from_seed_file(seed_path).clone()
    return P05KnowledgeAdapter(store=store, p05_dir=P05_DIR), store, p05_schemas


def _load_e01_plan(plan_key: str = "product_education_10m") -> StoryPlan:
    """Nạp một `StoryPlan` chuẩn từ bộ fixture `e01_story_plans.json`."""
    raw = json.loads(E01_PLANS_PATH.read_text(encoding="utf-8"))
    return StoryPlan.model_validate(raw["plans"][plan_key])


@pytest.fixture()
def local_tmp_dir() -> Iterator[Path]:
    """Tạo thư mục tạm trong `.pytest_cache` thuộc workspace để tránh lỗi quyền Temp trên Windows."""
    cache_root = P06_ROOT / ".pytest_cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_root, prefix="p06_plan_test_") as tmp_dir:
        yield Path(tmp_dir)


class TestPromptLoaderAndTemplates:
    """Kiểm thử nạp prompt, chuẩn hóa LF SHA-256 và render an toàn quanh JSON."""

    def test_load_all_default_prompts_and_compute_hashes(self) -> None:
        expected_files = ("rewrite.txt", "story_generation.txt", "story_planner.txt")
        hashes = compute_prompt_hashes()
        assert list(hashes.keys()) == list(expected_files)

        for filename in expected_files:
            tmpl = load_prompt_template(filename)
            assert isinstance(tmpl, PromptTemplate)
            assert tmpl.name == filename
            assert tmpl.version == "v0.1"
            assert tmpl.path == (DEFAULT_PROMPTS_DIR / filename).resolve()
            assert len(tmpl.sha256) == 64
            assert hashes[filename] == tmpl.sha256
            assert "<untrusted_knowledge_data>" in tmpl.content
            assert "</untrusted_knowledge_data>" in tmpl.content

    def test_lf_normalized_sha256_identical_across_crlf_cr_lf(self, local_tmp_dir: Path) -> None:
        lf_body = "PROMPT_VERSION: v0.1\nXin chào {{name}}.\n{\"ok\": true}\n"
        crlf_body = lf_body.replace("\n", "\r\n")
        cr_body = lf_body.replace("\n", "\r")

        p_lf = local_tmp_dir / "lf.txt"
        p_crlf = local_tmp_dir / "crlf.txt"
        p_cr = local_tmp_dir / "cr.txt"
        p_lf.write_bytes(lf_body.encode("utf-8"))
        p_crlf.write_bytes(crlf_body.encode("utf-8"))
        p_cr.write_bytes(cr_body.encode("utf-8"))

        t_lf = load_prompt_template(p_lf)
        t_crlf = load_prompt_template(p_crlf)
        t_cr = load_prompt_template(p_cr)

        assert t_lf.sha256 == t_crlf.sha256 == t_cr.sha256
        assert "\r" not in t_crlf.content
        assert "\r" not in t_cr.content

        custom_hashes = compute_prompt_hashes(prompts_dir=local_tmp_dir)
        assert list(custom_hashes.keys()) == ["cr.txt", "crlf.txt", "lf.txt"]
        assert len(set(custom_hashes.values())) == 1

    def test_load_prompt_fails_closed_on_missing_or_blank_version(
        self,
        local_tmp_dir: Path,
    ) -> None:
        missing_hdr = local_tmp_dir / "no_version.txt"
        missing_hdr.write_text("Nội dung không có header\n", encoding="utf-8")
        with pytest.raises(ValueError, match="PROMPT_VERSION"):
            load_prompt_template(missing_hdr)

        blank_hdr = local_tmp_dir / "blank_version.txt"
        blank_hdr.write_text("PROMPT_VERSION:   \nNội dung\n", encoding="utf-8")
        with pytest.raises(ValueError, match="PROMPT_VERSION"):
            load_prompt_template(blank_hdr)

        with pytest.raises(FileNotFoundError):
            load_prompt_template("does_not_exist.txt", prompts_dir=local_tmp_dir)

    def test_render_all_three_prompts_preserves_json_braces_and_delimiters(self) -> None:
        planner_tmpl = load_prompt_template("story_planner.txt")
        rendered_planner = render_prompt_template(
            planner_tmpl,
            {
                "session_goal": "Giới thiệu mật ong",
                "pinned_skus": "SKU-HONEY-01",
                "mandatory_messages": '["Không dùng cho trẻ dưới 1 tuổi"]',
                "prohibited_topics": '["Chữa bệnh"]',
                "target_duration_sec": "600",
                "untrusted_knowledge_block": '{"sku_id": "SKU-HONEY-01", "note": "{{ignored}}"}',
            },
        )
        assert '{"sku_id": "SKU-HONEY-01", "note": "{{ignored}}"}' in rendered_planner
        assert "<untrusted_knowledge_data>\n" in rendered_planner
        assert "\n</untrusted_knowledge_data>" in rendered_planner
        assert '"arcs": [' in rendered_planner

        gen_tmpl = load_prompt_template("story_generation.txt")
        gen_vars = {
            "active_sku_id": "SKU-HONEY-01",
            "session_goal": "Giới thiệu mật ong",
            "arc_title": "Arc Mật Ong",
            "topic_id": "topic-01",
            "topic_title": "Cách pha mật ong",
            "talking_points": '["Pha nước ấm dưới 50 độ C"]',
            "mandatory_messages": '["Không dùng cho trẻ dưới 1 tuổi"]',
            "prohibited_topics": '["Chữa bệnh"]',
            "max_duration_sec": "20",
            "played_history_summary": "Chưa có lượt nào.",
            "untrusted_knowledge_block": "Dữ liệu mật ong",
        }
        rendered_gen = render_prompt_template(gen_tmpl, gen_vars)
        assert "SKU-HONEY-01" in rendered_gen
        assert '"cited_evidence_ids":' in rendered_gen

        rewrite_tmpl = load_prompt_template("rewrite.txt")
        rewrite_vars = {
            **gen_vars,
            "previous_draft_text": "Bản nháp cũ bị lỗi giá.",
            "failure_reasons": '["PRICE_MISMATCH"]',
            "retry_attempt": "1",
            "max_retries": "2",
        }
        rendered_rewrite = render_prompt_template(rewrite_tmpl, rewrite_vars)
        assert "PRICE_MISMATCH" in rendered_rewrite
        assert "1 / 2" in rendered_rewrite

    def test_render_fails_closed_on_missing_variable_or_malformed_placeholder(
        self,
        local_tmp_dir: Path,
    ) -> None:
        planner_tmpl = load_prompt_template("story_planner.txt")
        with pytest.raises(ValueError, match="Thiếu biến bắt buộc"):
            render_prompt_template(planner_tmpl, {"session_goal": "abc"})

        bad_tmpl_path = local_tmp_dir / "bad_placeholder.txt"
        bad_tmpl_path.write_text(
            "PROMPT_VERSION: v0.1\nXin chào {{valid_key}} và {{bad-key}}\n",
            encoding="utf-8",
        )
        bad_tmpl = load_prompt_template(bad_tmpl_path)
        with pytest.raises(ValueError, match="placeholder không hợp lệ"):
            render_prompt_template(bad_tmpl, {"valid_key": "ok"})

        unclosed_path = local_tmp_dir / "unclosed.txt"
        unclosed_path.write_text(
            "PROMPT_VERSION: v0.1\nXin chào {{valid_key}} và {{unclosed\n",
            encoding="utf-8",
        )
        unclosed_tmpl = load_prompt_template(unclosed_path)
        with pytest.raises(ValueError, match="chưa được đóng"):
            render_prompt_template(unclosed_tmpl, {"valid_key": "ok"})


class TestUntrustedDraftDTOs:
    """Kiểm thử DTO bản nháp LLM từ chối mọi metadata thẩm quyền (`extra='forbid'`)."""

    @pytest.mark.parametrize(
        "forbidden_field,forbidden_value",
        [
            ("tenant_id", "tenant-spoof"),
            ("session_id", "session-spoof"),
            ("session_epoch", 99),
            ("approval_status", "APPROVED"),
            ("approved_by", "llm-self-approve"),
            ("approved_at", "2026-11-26T00:00:00Z"),
            ("knowledge_version", 99),
            ("ocop_version", 99),
            ("rights_version", 99),
            ("verification_status", "VERIFIED"),
            ("verified_by_gate_decision_id", "gate-spoof"),
            ("verified_at", "2026-11-26T00:00:00Z"),
            ("is_eligible", True),
        ],
    )
    def test_draft_dtos_reject_trusted_metadata_fields(
        self,
        forbidden_field: str,
        forbidden_value: Any,
    ) -> None:
        topic_payload: dict[str, Any] = {"topic_id": "t-1", "title": "Chủ đề 1"}
        with pytest.raises(ValidationError):
            StoryTopicDraftLLMOutput.model_validate({**topic_payload, forbidden_field: forbidden_value})

        arc_payload: dict[str, Any] = {
            "arc_id": "a-1",
            "title": "Arc 1",
            "target_duration_sec": 120,
            "topics": [topic_payload],
        }
        with pytest.raises(ValidationError):
            StoryArcDraftLLMOutput.model_validate({**arc_payload, forbidden_field: forbidden_value})

        plan_payload: dict[str, Any] = {"arcs": [arc_payload]}
        with pytest.raises(ValidationError):
            StoryPlanDraftLLMOutput.model_validate({**plan_payload, forbidden_field: forbidden_value})

        chunk_payload: dict[str, Any] = {
            "text": "Mật ong hoa cà phê nguyên chất.",
            "role": StoryChunkRole.PRODUCT_STORY.value,
            "breakpoint_type": BreakpointType.TOPIC_END.value,
        }
        with pytest.raises(ValidationError):
            ChunkDraftLLMOutput.model_validate({**chunk_payload, forbidden_field: forbidden_value})

    def test_arc_draft_rejects_reviewed_by_merchant_and_sku_mismatch(self) -> None:
        with pytest.raises(ValidationError):
            StoryArcDraftLLMOutput.model_validate(
                {
                    "arc_id": "a-1",
                    "title": "Arc 1",
                    "target_duration_sec": 120,
                    "reviewed_by_merchant": True,
                    "topics": [{"topic_id": "t-1", "title": "Topic 1"}],
                }
            )

        with pytest.raises(ValidationError):
            StoryArcDraftLLMOutput(
                arc_id="a-1",
                title="Arc 1",
                sku_id="SKU-HONEY-01",
                target_duration_sec=120,
                topics=[
                    StoryTopicDraftLLMOutput(
                        topic_id="t-1",
                        title="Topic 1",
                        sku_id="SKU-TEA-02",
                    )
                ],
            )


class TestStoryPlannerAndApprovalBoundary:
    """Kiểm thử `StoryPlanner.draft_plan()` và `SimulatedMerchantApprovalBoundary`."""

    def _valid_goal(self) -> MerchantGoalInput:
        return MerchantGoalInput(
            tenant_id=E01_TENANT,
            session_id="session-planner-01",
            plan_id="plan-planner-01",
            plan_revision=1,
            session_goal="Giới thiệu mật ong và trà Shan Tuyết",
            pinned_sku_ids=["SKU-HONEY-01", "SKU-TEA-02"],
            target_duration_sec=400,
            mandatory_messages=["Không dùng mật ong cho trẻ dưới 1 tuổi"],
            prohibited_topics=["Chữa bệnh"],
        )

    def _valid_llm_plan_payload(self) -> dict[str, Any]:
        return {
            "arcs": [
                {
                    "arc_id": "arc-honey",
                    "title": "Giới thiệu Mật ong Đắk Lắk",
                    "sku_id": "SKU-HONEY-01",
                    "target_duration_sec": 200,
                    "breakpoint_hint": "ARC_BOUNDARY",
                    "preview_text": "Nguồn gốc và cách pha mật ong.",
                    "topics": [
                        {
                            "topic_id": "topic-honey-usage",
                            "title": "Cách pha nước ấm dưới 50 độ C",
                            "sku_id": "SKU-HONEY-01",
                            "is_mandatory": True,
                            "fact_refs": ["ev-e01-honey-usage"],
                            "allowed_claim_ids": ["clm-e01-honey-allowed-01"],
                            "talking_points": ["Không dùng cho trẻ dưới 1 tuổi."],
                        }
                    ],
                },
                {
                    "arc_id": "arc-tea",
                    "title": "Giới thiệu Trà Shan Tuyết",
                    "sku_id": "SKU-TEA-02",
                    "target_duration_sec": 200,
                    "breakpoint_hint": "ARC_BOUNDARY",
                    "preview_text": "Cách pha trà 85-90 độ C.",
                    "topics": [
                        {
                            "topic_id": "topic-tea-brewing",
                            "title": "Nhiệt độ pha trà Shan Tuyết",
                            "sku_id": "SKU-TEA-02",
                            "is_mandatory": True,
                            "fact_refs": ["ev-e01-tea-usage"],
                            "allowed_claim_ids": ["clm-e01-tea-allowed-02"],
                            "talking_points": ["Pha ở 85-90 độ C."],
                        }
                    ],
                },
            ]
        }

    def test_draft_plan_returns_draft_only_and_captures_live_versions(self) -> None:
        adapter, _, _ = _make_adapter(E01_SEED_PATH)
        provider = MockLLMProvider(
            response_sequence=[
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=self._valid_llm_plan_payload(),
                )
            ]
        )
        planner = StoryPlanner(llm_provider=provider, knowledge_verifier=adapter)

        plan, telemetry = planner.draft_plan(self._valid_goal(), request_id="req-plan-01")

        assert plan.approval_status == StoryPlanApprovalStatus.DRAFT
        assert plan.approved_by is None
        assert plan.approved_at is None
        assert plan.knowledge_versions_by_sku == {"SKU-HONEY-01": 1, "SKU-TEA-02": 1}
        assert [arc.position for arc in plan.arcs] == [1, 2]
        assert all(arc.reviewed_by_merchant is False for arc in plan.arcs)
        assert telemetry.prompt_version == "v0.1"
        assert telemetry.raw_response_valid is True

    def test_draft_plan_rejects_ineligible_missing_and_cross_tenant_sku(self) -> None:
        adapter, _, _ = _make_adapter(P05_CATALOG_SEED_PATH)
        provider = MockLLMProvider(
            response_sequence=[
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=self._valid_llm_plan_payload(),
                )
            ]
        )
        planner = StoryPlanner(llm_provider=provider, knowledge_verifier=adapter)

        # SKU-CASHEW-03 có OCOP PENDING -> is_eligible=False.
        ineligible_goal = MerchantGoalInput(
            tenant_id=P05_SEED_TENANT,
            session_id="sess-1",
            plan_id="plan-1",
            session_goal="Test ineligible",
            pinned_sku_ids=["SKU-CASHEW-03"],
        )
        with pytest.raises(ValueError, match="không đủ điều kiện"):
            planner.draft_plan(ineligible_goal, request_id="req-ineligible")

        missing_goal = MerchantGoalInput(
            tenant_id=P05_SEED_TENANT,
            session_id="sess-1",
            plan_id="plan-1",
            session_goal="Test missing",
            pinned_sku_ids=["SKU-DOES-NOT-EXIST"],
        )
        with pytest.raises(KeyError):
            planner.draft_plan(missing_goal, request_id="req-missing")

        cross_tenant_goal = MerchantGoalInput(
            tenant_id="other-tenant-99",
            session_id="sess-1",
            plan_id="plan-1",
            session_goal="Test cross tenant",
            pinned_sku_ids=["SKU-HONEY-01"],
        )
        with pytest.raises(PermissionError):
            planner.draft_plan(cross_tenant_goal, request_id="req-cross-tenant")

    def test_draft_plan_rejects_fabricated_fact_refs_and_claim_ids(self) -> None:
        adapter, _, _ = _make_adapter(E01_SEED_PATH)

        bad_ev_payload = self._valid_llm_plan_payload()
        bad_ev_payload["arcs"][0]["topics"][0]["fact_refs"] = ["ev-fabricated-999"]
        provider_bad_ev = MockLLMProvider(
            response_sequence=[
                MockResponseStep(behavior=MockBehavior.VALID_JSON, payload=bad_ev_payload)
            ]
        )
        with pytest.raises(ValueError, match="fact_refs"):
            StoryPlanner(provider_bad_ev, adapter).draft_plan(
                self._valid_goal(),
                request_id="req-bad-ev",
            )

        bad_claim_payload = self._valid_llm_plan_payload()
        bad_claim_payload["arcs"][0]["topics"][0]["allowed_claim_ids"] = ["clm-fabricated-999"]
        provider_bad_claim = MockLLMProvider(
            response_sequence=[
                MockResponseStep(behavior=MockBehavior.VALID_JSON, payload=bad_claim_payload)
            ]
        )
        with pytest.raises(ValueError, match="allowed_claim_ids"):
            StoryPlanner(provider_bad_claim, adapter).draft_plan(
                self._valid_goal(),
                request_id="req-bad-claim",
            )

        # Trộn evidence của TEA vào topic của HONEY cũng phải bị chặn.
        cross_sku_ev_payload = self._valid_llm_plan_payload()
        cross_sku_ev_payload["arcs"][0]["topics"][0]["fact_refs"] = ["ev-e01-tea-usage"]
        provider_cross = MockLLMProvider(
            response_sequence=[
                MockResponseStep(behavior=MockBehavior.VALID_JSON, payload=cross_sku_ev_payload)
            ]
        )
        with pytest.raises(ValueError, match="fact_refs"):
            StoryPlanner(provider_cross, adapter).draft_plan(
                self._valid_goal(),
                request_id="req-cross-ev",
            )

    def test_simulated_merchant_approval_boundary_transitions(self) -> None:
        adapter, _, _ = _make_adapter(E01_SEED_PATH)
        provider = MockLLMProvider(
            response_sequence=[
                MockResponseStep(
                    behavior=MockBehavior.VALID_JSON,
                    payload=self._valid_llm_plan_payload(),
                )
            ]
        )
        draft_plan, _ = StoryPlanner(provider, adapter).draft_plan(
            self._valid_goal(),
            request_id="req-approve-flow",
        )

        approved = SimulatedMerchantApprovalBoundary.approve_plan(
            draft_plan,
            approved_by="synthetic-owner-01",
            approved_at=FIXED_TS,
        )
        assert approved.approval_status == StoryPlanApprovalStatus.APPROVED
        assert approved.approved_by == "synthetic-owner-01"
        assert approved.approved_at == FIXED_TS
        assert draft_plan.approval_status == StoryPlanApprovalStatus.DRAFT

        # Không được phép duyệt lại kế hoạch đã APPROVED, INVALIDATED hoặc SUPERSEDED.
        with pytest.raises(ValueError, match="DRAFT hoặc REVIEW_REQUIRED"):
            SimulatedMerchantApprovalBoundary.approve_plan(
                approved,
                approved_by="owner-2",
                approved_at=FIXED_TS,
            )

        for disallowed_status in (
            StoryPlanApprovalStatus.INVALIDATED,
            StoryPlanApprovalStatus.SUPERSEDED,
        ):
            disallowed_plan = StoryPlan.model_validate(
                {**draft_plan.model_dump(), "approval_status": disallowed_status}
            )
            with pytest.raises(ValueError, match="DRAFT hoặc REVIEW_REQUIRED"):
                SimulatedMerchantApprovalBoundary.approve_plan(
                    disallowed_plan,
                    approved_by="owner-2",
                    approved_at=FIXED_TS,
                )


class TestArcSequencer:
    """Kiểm thử `ArcSequencer.select_next_topic()` và khóa bất biến `I-04`."""

    def _make_checkpoint(
        self,
        plan: StoryPlan,
        *,
        active_sku_id: str = "SKU-HONEY-01",
        current_arc_id: str = "arc-edu-honey-01",
        next_topic_id: str | None = "topic-edu-honey-usage",
    ) -> StoryCheckpoint:
        return StoryCheckpoint(
            tenant_id=plan.tenant_id,
            session_id=plan.session_id,
            session_epoch=1,
            plan_id=plan.plan_id,
            plan_revision=plan.plan_revision,
            active_sku_id=active_sku_id,
            current_arc_id=current_arc_id,
            next_topic_id=next_topic_id,
        )

    def test_select_next_topic_honors_i04_and_sequences_without_mutation(self) -> None:
        plan = _load_e01_plan("product_education_10m")
        checkpoint = self._make_checkpoint(
            plan,
            active_sku_id="SKU-HONEY-01",
            current_arc_id="arc-edu-honey-01",
            next_topic_id="topic-edu-honey-usage",
        )
        completed: set[str] = set()
        excluded: set[str] = set()

        res1 = ArcSequencer.select_next_topic(
            plan,
            checkpoint,
            active_sku_id="SKU-HONEY-01",
            completed_topic_ids=completed,
            excluded_topic_ids=excluded,
        )
        assert res1.should_terminate is False
        assert res1.selected_arc_id == "arc-edu-honey-01"
        assert res1.selected_topic is not None
        assert res1.selected_topic.topic_id == "topic-edu-honey-usage"
        assert res1.next_topic_id_after_selection == "topic-edu-honey-quality"
        assert res1.next_arc_id_after_selection == "arc-edu-honey-01"
        assert completed == set()
        assert excluded == set()

        # Hoàn tất topic 1 -> chọn topic 2 của đúng SKU-HONEY-01, không tràn sang SKU-TEA-02!
        res2 = ArcSequencer.select_next_topic(
            plan,
            self._make_checkpoint(
                plan,
                active_sku_id="SKU-HONEY-01",
                current_arc_id="arc-edu-honey-01",
                next_topic_id="topic-edu-honey-quality",
            ),
            active_sku_id="SKU-HONEY-01",
            completed_topic_ids={"topic-edu-honey-usage"},
        )
        assert res2.should_terminate is False
        assert res2.selected_topic is not None
        assert res2.selected_topic.topic_id == "topic-edu-honey-quality"
        assert res2.next_topic_id_after_selection is None
        assert res2.next_arc_id_after_selection is None

        # Hoàn tất cả 2 topic của SKU-HONEY-01 -> dừng sạch, không bao giờ tự nhảy sang SKU-TEA-02.
        res_done = ArcSequencer.select_next_topic(
            plan,
            self._make_checkpoint(
                plan,
                active_sku_id="SKU-HONEY-01",
                current_arc_id="arc-edu-honey-01",
                next_topic_id=None,
            ),
            active_sku_id="SKU-HONEY-01",
            completed_topic_ids={"topic-edu-honey-usage", "topic-edu-honey-quality"},
        )
        assert res_done.should_terminate is True
        assert res_done.selected_topic is None
        assert res_done.selected_arc_id is None
        assert res_done.termination_reason == "ALL_ELIGIBLE_TOPICS_COMPLETED"

    def test_select_next_topic_handles_excluded_topics_and_sku_switch_only_via_checkpoint(self) -> None:
        plan = _load_e01_plan("product_education_10m")
        # checkpoint.next_topic_id trỏ tới topic bị loại trừ -> nhảy sang topic còn lại của SKU đó.
        res_excluded = ArcSequencer.select_next_topic(
            plan,
            self._make_checkpoint(plan, next_topic_id="topic-edu-honey-usage"),
            active_sku_id="SKU-HONEY-01",
            completed_topic_ids=set(),
            excluded_topic_ids={"topic-edu-honey-usage"},
        )
        assert res_excluded.should_terminate is False
        assert res_excluded.selected_topic is not None
        assert res_excluded.selected_topic.topic_id == "topic-edu-honey-quality"

        # Nếu P08 đổi active_sku_id + checkpoint.active_sku_id sang SKU-TEA-02 thì mới chọn chủ đề trà.
        res_tea = ArcSequencer.select_next_topic(
            plan,
            self._make_checkpoint(
                plan,
                active_sku_id="SKU-TEA-02",
                current_arc_id="arc-edu-tea-02",
                next_topic_id=None,
            ),
            active_sku_id="SKU-TEA-02",
            completed_topic_ids={"topic-edu-honey-usage", "topic-edu-honey-quality"},
        )
        assert res_tea.should_terminate is False
        assert res_tea.selected_arc_id == "arc-edu-tea-02"
        assert res_tea.selected_topic is not None
        assert res_tea.selected_topic.topic_id == "topic-edu-tea-brewing"
        assert res_tea.next_topic_id_after_selection == "topic-edu-tea-storage"

    def test_select_next_topic_rejects_unapproved_plan_or_i04_violation(self) -> None:
        plan = _load_e01_plan("product_education_10m")
        draft_payload = plan.model_dump()
        draft_payload["approval_status"] = StoryPlanApprovalStatus.DRAFT
        draft_payload["approved_by"] = None
        draft_payload["approved_at"] = None
        draft_plan = StoryPlan.model_validate(draft_payload)

        checkpoint = self._make_checkpoint(plan)
        with pytest.raises(ValueError, match="APPROVED"):
            ArcSequencer.select_next_topic(draft_plan, checkpoint, "SKU-HONEY-01", set())

        # Lệch active_sku_id với checkpoint.active_sku_id (vi phạm I-04).
        with pytest.raises(ValueError, match="I-04"):
            ArcSequencer.select_next_topic(plan, checkpoint, "SKU-TEA-02", set())

        # active_sku_id không thuộc pinned_sku_ids.
        bad_cp = self._make_checkpoint(plan, active_sku_id="SKU-OTHER-99")
        with pytest.raises(ValueError, match="I-04"):
            ArcSequencer.select_next_topic(plan, bad_cp, "SKU-OTHER-99", set())

    def test_select_next_topic_optional_vs_mandatory_and_general_arc(self) -> None:
        plan = StoryPlan(
            plan_id="plan-mixed-01",
            tenant_id=E01_TENANT,
            session_id="sess-mixed-01",
            plan_revision=1,
            approval_status=StoryPlanApprovalStatus.APPROVED,
            approved_by="synthetic-owner-01",
            approved_at=FIXED_TS,
            session_goal="Test mixed optional and general topics",
            pinned_sku_ids=["SKU-HONEY-01", "SKU-TEA-02"],
            arcs=[
                StoryArc(
                    arc_id="arc-opening",
                    position=1,
                    title="Mở đầu chung",
                    sku_id=None,
                    target_duration_sec=30,
                    topics=[
                        StoryTopic(
                            topic_id="topic-opt-greeting",
                            title="Chào khán giả",
                            sku_id=None,
                            is_mandatory=False,
                        )
                    ],
                ),
                StoryArc(
                    arc_id="arc-honey",
                    position=2,
                    title="Mật ong",
                    sku_id="SKU-HONEY-01",
                    target_duration_sec=120,
                    topics=[
                        StoryTopic(
                            topic_id="topic-honey-main",
                            title="Mật ong chính",
                            sku_id=None,
                            is_mandatory=True,
                        )
                    ],
                ),
                StoryArc(
                    arc_id="arc-tea",
                    position=3,
                    title="Trà",
                    sku_id="SKU-TEA-02",
                    target_duration_sec=120,
                    topics=[
                        StoryTopic(
                            topic_id="topic-tea-main",
                            title="Trà chính",
                            sku_id="SKU-TEA-02",
                            is_mandatory=True,
                        )
                    ],
                ),
            ],
        )
        cp = StoryCheckpoint(
            tenant_id=E01_TENANT,
            session_id="sess-mixed-01",
            session_epoch=1,
            plan_id="plan-mixed-01",
            plan_revision=1,
            active_sku_id="SKU-HONEY-01",
            current_arc_id="arc-opening",
            next_topic_id=None,
        )

        # Khi include_optional=True và next_topic_id=None: ưu tiên mandatory của SKU-HONEY-01 trước,
        # và không bao giờ chạm arc-tea (SKU-TEA-02).
        res_mand = ArcSequencer.select_next_topic(plan, cp, "SKU-HONEY-01", set())
        assert res_mand.selected_topic is not None
        assert res_mand.selected_topic.topic_id == "topic-honey-main"
        assert res_mand.next_topic_id_after_selection == "topic-opt-greeting"

        # Khi include_optional=False và mandatory đã xong -> dừng sạch.
        res_stop = ArcSequencer.select_next_topic(
            plan,
            cp,
            "SKU-HONEY-01",
            completed_topic_ids={"topic-honey-main"},
            include_optional=False,
        )
        assert res_stop.should_terminate is True
        assert TopicSelectionResult.model_validate(res_stop.model_dump()).should_terminate is True
