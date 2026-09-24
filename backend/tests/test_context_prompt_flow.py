"""Regression tests verifying context prompt flow and evidence gating.

Validates:
1. User task prompt directly reaches LLM synthesis prompt with full fidelity.
2. Tasks with unclassified/arbitrary categories do NOT cause abstention when evidence exists.
3. Hard-negative prompts with genuine lack of repository evidence still trigger abstention.
4. Different user task prompts produce distinct, task-specific context output.
"""

from pathlib import Path
import tempfile
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.application.container import ApplicationContainer
from app.application.domain.intent import parse_intent_heuristics
from app.application.dto import AgentContextRequest, AgentContextResponse
from app.application.ports.llm_provider import LLMProviderPort
from app.models.provider import ProviderType
from app.services.evidence_service import EvidenceService
from app.services.intent_parser import IntentParserService
from app.services.source_search_service import SourceSearchService
from app.services.workspace_authorization_service import WorkspaceAuthorizationService


class RecordingMockLLM(LLMProviderPort):
    def __init__(self, provider_type: ProviderType = ProviderType.LM_STUDIO, default_model: str = "qwen2.5-coder:7b") -> None:
        self.provider_type = provider_type
        self.default_model = default_model
        self.prompts: list[str] = []
        self.system_prompts: list[Optional[str]] = []
        self.models: list[Optional[str]] = []

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        self.prompts.append(prompt)
        self.system_prompts.append(system_prompt)
        self.models.append(model or self.default_model)
        # If this is the intent parse call (asking for JSON schema), return structured intent
        if "JSON" in prompt or (system_prompt and "JSON" in system_prompt):
            if "Router" in prompt or "latency" in prompt or "rate limiting" in prompt:
                return '{"task_summary": "Router task", "category": "network_routing", "extracted_symbols": ["Router", "get", "post"], "relevant_file_hints": ["app.py"], "is_vague": false, "actions": ["optimize", "middleware"], "target_entities": ["Router", "latency"]}'
            return '{"task_summary": "Process payment webhook", "category": "payment_integration", "extracted_symbols": ["WebhookHandler"], "relevant_file_hints": ["webhook.py"], "is_vague": false, "actions": ["process", "validate"], "target_entities": ["payment webhook", "signature"]}'
        # If this is task synthesis call, return task-tailored markdown
        return f"### Task Plan for: {prompt[:40]}...\n1. Inspect symbols\n2. Implement modifications\n3. Complete verification"

    async def check_health(self) -> Any:
        mock_health = MagicMock()
        mock_health.is_reachable = True
        mock_health.active_model = self.default_model
        mock_health.loaded_models = []
        mock_health.quantization_warning = None
        return mock_health

    async def list_models(self) -> list[Any]:
        return []

    async def discover_models(self, *args: Any, **kwargs: Any) -> Any:
        mock_res = MagicMock()
        mock_res.is_reachable = True
        mock_res.models = []
        return mock_res


@pytest.mark.asyncio
async def test_user_prompt_reaches_model_synthesis():
    """Verify the exact user prompt is forwarded into the model prompt during context synthesis."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "payments_repo"
        repo_path.mkdir()
        (repo_path / "webhook.py").write_text("class WebhookHandler:\n    def handle_payment(self, payload): pass\n")

        recording_llm = RecordingMockLLM()
        container = ApplicationContainer.create()
        container.llm_provider = recording_llm
        container.intent_parser = IntentParserService(recording_llm)
        container.cognee_service = MagicMock()
        container.indexing_service = MagicMock()
        container.indexing_service.discover_files.return_value = [repo_path / "webhook.py"]
        container.indexing_service.filter_files.return_value = [repo_path / "webhook.py"]

        mock_pkg = MagicMock()
        mock_pkg.markdown = "# Base AST Summary"
        mock_pkg.sections = []
        mock_pkg.references = []
        container.context_service = MagicMock()
        container.context_service.generate_context_package = AsyncMock(return_value=mock_pkg)

        auth_svc = WorkspaceAuthorizationService(workspace_roots=[Path(tmp_dir)])
        container.workspace_auth = auth_svc

        context_uc = container.get_context_use_cases()

        user_task = "Implement Stripe payment webhook verification in WebhookHandler with replay attack prevention"
        req = AgentContextRequest(
            task_prompt=user_task,
            repository_path=str(repo_path),
            dataset_name="payments_repo",
        )

        resp = await context_uc.get_agent_context(req)

        assert isinstance(resp, AgentContextResponse)
        assert resp.success is True
        assert resp.model_invoked is True
        assert resp.inference_status == "completed"

        # The user task prompt must appear in the synthesis prompt
        synthesis_prompt = recording_llm.prompts[-1]
        assert user_task in synthesis_prompt
        assert "Developer Task" in synthesis_prompt

        # The synthesized markdown must be in the response content
        assert "Task Plan for: # Developer Task" in resp.context_markdown


@pytest.mark.asyncio
async def test_unclassified_category_does_not_abstain_when_evidence_exists():
    """Verify evidence gating succeeds for novel domains without hardcoded category gates."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "nlp_repo"
        repo_path.mkdir()
        (repo_path / "tokenizer.py").write_text("class BpeTokenizer:\n    def encode(self, text): return []\n")

        task_prompt = "Tune the BpeTokenizer vocabulary merge rules"
        parsed_intent = parse_intent_heuristics(task_prompt)
        assert parsed_intent.category not in ["authentication", "payment", "database"]

        repo_files = [repo_path / "tokenizer.py"]
        matching_symbols = ["BpeTokenizer", "encode"]

        evidence = EvidenceService.assess_evidence(
            task_prompt=task_prompt,
            intent=parsed_intent,
            repo_summary=MagicMock(frameworks=[], key_components=[]),
            indexed_files=repo_files,
            relevant_snippets=["class BpeTokenizer:\n    def encode(self, text): return []\n"],
            matched_file_rels=["tokenizer.py"],
            structural_symbols=matching_symbols,
            structural_relationships=[],
        )

        # Must pass because relevant code evidence is present
        assert evidence.abstained is False
        assert evidence.evidence_state in ["sufficient", "partial"]


@pytest.mark.asyncio
async def test_hard_negative_genuine_lack_of_evidence_abstains():
    """Verify truth boundary guarantee: task on non-existent feature in empty repo abstains."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "empty_repo"
        repo_path.mkdir()
        (repo_path / "hello.py").write_text("print('hello world')\n")

        task_prompt = "Configure OAuth2 JWT bearer token authorization"
        parsed_intent = parse_intent_heuristics(task_prompt)

        evidence = EvidenceService.assess_evidence(
            task_prompt=task_prompt,
            intent=parsed_intent,
            repo_summary=MagicMock(frameworks=[], key_components=[]),
            indexed_files=[repo_path / "hello.py"],
            relevant_snippets=[],
            matched_file_rels=[],
            structural_symbols=[],
            structural_relationships=[],
        )

        # Must abstain because there is zero evidence of auth/oauth in the repository
        assert evidence.abstained is True
        assert evidence.evidence_state in ["insufficient", "none"]


@pytest.mark.asyncio
async def test_different_tasks_produce_distinct_synthesized_contexts():
    """Verify context generation produces distinct outputs tailored to each specific task."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "multi_repo"
        repo_path.mkdir()
        (repo_path / "app.py").write_text("class Router:\n    def get(self): pass\n    def post(self): pass\n")

        recording_llm = RecordingMockLLM()
        container = ApplicationContainer.create()
        container.llm_provider = recording_llm
        container.intent_parser = IntentParserService(recording_llm)
        container.cognee_service = MagicMock()
        container.indexing_service = MagicMock()
        container.indexing_service.discover_files.return_value = [repo_path / "app.py"]
        container.indexing_service.filter_files.return_value = [repo_path / "app.py"]

        mock_pkg = MagicMock()
        mock_pkg.markdown = "# Base AST Summary"
        mock_pkg.sections = []
        mock_pkg.references = []
        container.context_service = MagicMock()
        container.context_service.generate_context_package = AsyncMock(return_value=mock_pkg)

        auth_svc = WorkspaceAuthorizationService(workspace_roots=[Path(tmp_dir)])
        container.workspace_auth = auth_svc

        context_uc = container.get_context_use_cases()

        resp_a = await context_uc.get_agent_context(
            AgentContextRequest(
                task_prompt="Optimize GET request latency in Router",
                repository_path=str(repo_path),
                dataset_name="multi_repo",
            )
        )
        resp_b = await context_uc.get_agent_context(
            AgentContextRequest(
                task_prompt="Add rate limiting middleware to POST requests in Router",
                repository_path=str(repo_path),
                dataset_name="multi_repo",
            )
        )

        assert resp_a.success is True
        assert resp_b.success is True
        # Both outputs must differ because the model was prompted with distinct developer tasks
        assert resp_a.context_markdown != resp_b.context_markdown
        assert "Optimize GET request latency" in recording_llm.prompts[1]
        assert "Add rate limiting middleware" in recording_llm.prompts[3]
