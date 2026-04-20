"""LLM-as-judge critic for arcade-evals.

:class:`SmartCritic` evaluates a tool-call argument by sending the expected
and actual values to a judge LLM and parsing its numeric score. It plugs
into the existing :class:`~arcade_evals.critic.Critic` interface via the
``async_evaluate()`` path added in this release, so it co-exists seamlessly
with deterministic critics (Binary/Numeric/Similarity/etc.).

Key properties:

* **Modes** — an enum selects the evaluation dimension (similarity,
  correctness, relevance, completeness, coherence, or custom).
* **Customizable prompts** — users can override the system prompt and/or
  the criteria prompt; otherwise sensible defaults from
  :mod:`arcade_evals.smart_critic_prompts` are used.
* **Deterministic output parsing** — the LLM is instructed to return a
  strict JSON object; the parser falls back to markdown-block extraction
  and regex before giving up with score 0.
* **Provider-agnostic judge** — the judge can run on OpenAI or Anthropic,
  resolved per-critic or via CLI flags; falls back to the eval's own
  provider/model when no judge is configured.
* **Cost-aware** — smart critics are skipped in the cost matrix
  (``_is_smart_critic`` marker) so they are only called once per pairing.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, ClassVar

from arcade_evals.critic import Critic
from arcade_evals.smart_critic_mode import SmartCriticMode
from arcade_evals.smart_critic_prompts import (
    CUSTOM_OUTPUT_FORMAT_INSTRUCTIONS,
    DEFAULT_SYSTEM_PROMPT,
    MODE_RUBRICS,
    RubricCriterion,
    build_rubric_output_instructions,
    build_user_message,
    score_rubric_response,
)

logger = logging.getLogger(__name__)


_ENV_KEY_FOR_PROVIDER = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


@dataclass
class SmartCritic(Critic):
    """LLM-based critic for semantic / qualitative scoring.

    Every built-in :class:`SmartCriticMode` (SIMILARITY, CORRECTNESS,
    RELEVANCE, COMPLETENESS, COHERENCE) uses a fixed yes/partial/no rubric
    whose final score is computed deterministically in Python. Only
    :attr:`SmartCriticMode.CUSTOM` takes a free-form ``criteria_prompt``
    and returns a single float score directly from the judge.

    Args:
        critic_field: Name of the tool-call argument this critic evaluates.
        weight: Weight for this critic (float or :class:`FuzzyWeight`).
        mode: Which built-in evaluation rubric to use, or CUSTOM for a
            user-defined prompt. CUSTOM requires ``criteria_prompt``.
        judge_provider: Override provider for the judge LLM (``"openai"`` or
            ``"anthropic"``). If not set, the eval's provider is used.
        judge_model: Override model for the judge LLM. If not set, the eval's
            model is used.
        system_prompt: Override the default judge system prompt. The
            output-format contract (rubric or free-score) is always appended
            so parsing still works.
        criteria_prompt: User-defined criteria text. Required when
            ``mode is SmartCriticMode.CUSTOM``; rejected otherwise (use
            CUSTOM mode if you need custom criteria).
        match_threshold: Score (after clamping to [0, 1], before weighting)
            at which :meth:`async_evaluate` reports a match.
    """

    mode: SmartCriticMode = SmartCriticMode.CORRECTNESS
    judge_provider: str | None = None
    judge_model: str | None = None
    system_prompt: str | None = None
    criteria_prompt: str | None = None
    match_threshold: float = 0.7

    # Runtime context injected by EvalSuite before evaluation. Init=False so
    # they aren't part of the constructor signature.
    _runtime_eval_provider: str | None = field(default=None, init=False, repr=False)
    _runtime_eval_model: str | None = field(default=None, init=False, repr=False)
    _runtime_eval_api_key: str | None = field(default=None, init=False, repr=False)
    _runtime_cli_provider: str | None = field(default=None, init=False, repr=False)
    _runtime_cli_model: str | None = field(default=None, init=False, repr=False)
    _runtime_judge_override: bool = field(default=False, init=False, repr=False)

    # Class-level marker — EvalCase._create_cost_matrix skips critics where
    # this is truthy so LLM calls aren't doubled during assignment scoring.
    _is_smart_critic: ClassVar[bool] = True

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.mode is SmartCriticMode.CUSTOM:
            if not self.criteria_prompt:
                raise ValueError(
                    "CUSTOM mode requires a 'criteria_prompt' describing how "
                    "to evaluate the actual vs expected value."
                )
        elif self.criteria_prompt is not None:
            # Built-in modes use their fixed rubric; accepting a free-form
            # criteria_prompt here would silently bypass the rubric's
            # determinism. Force the user to pick CUSTOM if they really want
            # their own text.
            raise ValueError(
                "criteria_prompt is only valid for SmartCriticMode.CUSTOM. "
                "Built-in modes use their fixed rubric; switch to CUSTOM "
                "mode if you need user-defined criteria."
            )

    # ------------------------------------------------------------------
    # Runtime injection
    # ------------------------------------------------------------------
    def configure_runtime(
        self,
        eval_provider: str | None,
        eval_model: str | None,
        eval_api_key: str | None,
        *,
        cli_judge_provider: str | None = None,
        cli_judge_model: str | None = None,
        judge_override: bool = False,
    ) -> None:
        """Inject eval context; see :meth:`Critic.configure_runtime`."""
        self._runtime_eval_provider = eval_provider
        self._runtime_eval_model = eval_model
        self._runtime_eval_api_key = eval_api_key
        self._runtime_cli_provider = cli_judge_provider
        self._runtime_cli_model = cli_judge_model
        self._runtime_judge_override = judge_override

    def _resolve_judge(self) -> tuple[str, str]:
        """Resolve which (provider, model) to use for the judge LLM.

        Precedence (highest first):

        1. CLI override: ``cli_judge_*`` when ``judge_override=True``
        2. Per-critic: ``self.judge_provider`` + ``self.judge_model``
        3. CLI default: ``cli_judge_*`` when not overridden
        4. Eval fallback: ``eval_provider`` + ``eval_model``
        """
        provider: str | None
        model: str | None
        if self._runtime_judge_override and self._runtime_cli_model:
            provider = self._runtime_cli_provider or self._runtime_eval_provider
            model = self._runtime_cli_model
        elif self.judge_model:
            provider = self.judge_provider or self._runtime_eval_provider
            model = self.judge_model
        elif self._runtime_cli_model:
            provider = self._runtime_cli_provider or self._runtime_eval_provider
            model = self._runtime_cli_model
        else:
            provider = self._runtime_eval_provider
            model = self._runtime_eval_model

        if not provider or not model:
            raise RuntimeError(
                "SmartCritic could not resolve a judge provider/model. Provide "
                "judge_provider and judge_model on the critic, pass "
                "--judge-model on the CLI, or let the critic inherit the "
                "eval's running model by adding it to the EvalSuite."
            )
        return provider, model

    def _resolve_api_key(self, provider: str) -> str:
        """Return the API key for ``provider``.

        Reuses the eval's API key when the judge provider matches the eval
        provider; otherwise falls back to the well-known env var for that
        provider. Raises :class:`RuntimeError` with a clear message if no key
        is available, rather than letting the LLM client fail opaquely.
        """
        if provider == self._runtime_eval_provider and self._runtime_eval_api_key:
            return self._runtime_eval_api_key

        env_var = _ENV_KEY_FOR_PROVIDER.get(provider)
        if env_var:
            env_value = os.environ.get(env_var)
            if env_value:
                return env_value
            raise RuntimeError(
                f"SmartCritic could not find an API key for judge provider "
                f"'{provider}'. Set {env_var} in the environment, or run the "
                f"eval with the same provider so the eval's API key can be "
                f"reused."
            )

        # Unknown provider (not in our env map) — surface the real cause
        # rather than interpolating None into the env-var name.
        supported = ", ".join(sorted(_ENV_KEY_FOR_PROVIDER))
        raise RuntimeError(
            f"SmartCritic has no API-key source for judge provider "
            f"'{provider}'. Supported providers: {supported}. Configure the "
            f"critic to use one of them, or run the eval with this provider "
            f"so the eval's API key can be reused."
        )

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------
    def _rubric(self) -> tuple[RubricCriterion, ...] | None:
        """Return the rubric for this critic, or None for CUSTOM mode.

        Only :attr:`SmartCriticMode.CUSTOM` has no rubric — every other
        built-in mode is rubric-scored.
        """
        return MODE_RUBRICS.get(self.mode)

    def _build_prompt(self, expected: Any, actual: Any) -> tuple[str, str]:
        """Return ``(system_prompt, user_prompt)``.

        The output-format instructions are always appended to the system
        prompt — users overriding ``system_prompt`` don't need to remember
        to include them, which keeps response parsing reliable.

        Rubric modes emit the rubric's yes/partial/no contract in the
        system prompt and carry the values in the user message. CUSTOM
        mode inlines the user's criteria and uses the free-score contract.
        """
        base_system = self.system_prompt or DEFAULT_SYSTEM_PROMPT
        rubric = self._rubric()

        if rubric is not None:
            system = base_system + build_rubric_output_instructions(rubric)
            user = build_user_message(
                "Evaluate the EXPECTED vs ACTUAL values against the rubric "
                "given in the system prompt.",
                expected,
                actual,
            )
        else:
            # CUSTOM mode — __post_init__ guaranteed criteria_prompt is set.
            # Default to empty string in the type narrower just for mypy;
            # the path is unreachable at runtime thanks to __post_init__.
            criteria_prompt = self.criteria_prompt or ""
            system = base_system + CUSTOM_OUTPUT_FORMAT_INSTRUCTIONS
            user = build_user_message(criteria_prompt, expected, actual)

        return system, user

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------
    # Regex fallbacks used only when provider-native JSON mode fails. Both
    # patterns are tolerant of prose surrounding the JSON object.
    _JSON_OBJECT_RE: ClassVar[re.Pattern[str]] = re.compile(r"\{.*\}", re.DOTALL)
    _MARKDOWN_BLOCK_RE: ClassVar[re.Pattern[str]] = re.compile(
        r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL
    )

    def _parse_response(self, text: str) -> tuple[float, str, dict[str, float] | None]:
        """Extract ``(clamped_score, reasoning, breakdown)`` from the LLM response.

        ``breakdown`` is a per-criterion score dict when the critic is using
        rubric mode, otherwise ``None``.

        Parsing strategy:

        1. ``json.loads`` the full response (works when provider JSON mode
           or prefill is active).
        2. JSON inside a markdown code block (```json ... ``` or ``` ... ```).
        3. Regex-matched outermost JSON object.
        4. Fallback — score 0.0, reasoning explains the parse failure.

        When rubric mode is active, step 5 applies the rubric aggregation;
        otherwise (CUSTOM mode only) we read a free-score ``score`` float.
        """
        payload = self._try_parse_json(text)
        if payload is None:
            match = self._MARKDOWN_BLOCK_RE.search(text)
            if match:
                payload = self._try_parse_json(match.group(1))
        if payload is None:
            match = self._JSON_OBJECT_RE.search(text)
            if match:
                payload = self._try_parse_json(match.group(0))
        if payload is None:
            return 0.0, "Unable to parse judge response as JSON.", None

        reasoning_raw = payload.get("reasoning", "")
        reasoning = str(reasoning_raw) if reasoning_raw is not None else ""

        rubric = self._rubric()
        if rubric is not None:
            criteria_values = payload.get("criteria")
            if not isinstance(criteria_values, dict):
                # Some judges flatten the rubric keys to the top level
                # instead of nesting under "criteria" — accept that too.
                criteria_values = {c.key: payload.get(c.key, "no") for c in rubric}
            score, breakdown = score_rubric_response(rubric, criteria_values)
            return score, reasoning, breakdown

        raw_score = payload.get("score", 0.0)
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            return 0.0, f"Judge returned non-numeric score: {raw_score!r}", None
        score = max(0.0, min(1.0, score))
        return score, reasoning, None

    @staticmethod
    def _try_parse_json(text: str) -> dict[str, Any] | None:
        try:
            parsed = json.loads(text.strip())
        except (json.JSONDecodeError, ValueError):
            return None
        return parsed if isinstance(parsed, dict) else None

    # ------------------------------------------------------------------
    # Evaluation — async_evaluate is the primary entry point; the sync
    # evaluate() below exists only as a clear error surface for callers
    # that haven't migrated to the async path yet.
    # ------------------------------------------------------------------
    async def async_evaluate(self, expected: Any, actual: Any) -> dict[str, Any]:
        """Call the judge LLM and return the scored result dict.

        Returns a dict containing:

        * ``match``: bool, whether the raw score (before weighting) meets
          :attr:`match_threshold`.
        * ``score``: float, the weighted score (raw score * critic weight).
        * ``comment``: str, the judge's one-line reasoning.
        * ``criteria_breakdown``: dict[str, float] when rubric mode is
          active — per-criterion weighted contributions to the raw score.
          Absent in CUSTOM mode (which uses the free-score prompt).
        """
        provider, model = self._resolve_judge()
        api_key = self._resolve_api_key(provider)

        system, user = self._build_prompt(expected, actual)
        response_text = await self._call_llm(
            system, user, provider=provider, model=model, api_key=api_key
        )
        score, reasoning, breakdown = self._parse_response(response_text)

        weighted_score = score * self.resolved_weight
        result: dict[str, Any] = {
            "match": score >= self.match_threshold,
            "score": weighted_score,
            "comment": reasoning,
        }
        if breakdown is not None:
            result["criteria_breakdown"] = breakdown
        return result

    def evaluate(self, expected: Any, actual: Any) -> dict[str, Any]:
        """Sync entry point — smart critics require async evaluation.

        Kept adjacent to :meth:`async_evaluate` so the two variants live
        in the same section of the file. The sync signature has to exist
        because :class:`Critic` declares it ``@abstractmethod``; calling
        it on a :class:`SmartCritic` always raises.
        """
        raise RuntimeError(
            "SmartCritic requires async evaluation. It is called automatically "
            "via EvalCase.evaluate_async() during EvalSuite.run(); if you are "
            "invoking a critic directly in a test, use "
            "'await critic.async_evaluate(...)' instead."
        )

    # ------------------------------------------------------------------
    # LLM transport
    # ------------------------------------------------------------------
    async def _call_llm(
        self,
        system: str,
        user: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ) -> str:
        """Dispatch to the provider-specific call helper.

        Kept as a single entry point so tests can replace it with a single
        :class:`AsyncMock` and verify the judge was invoked with the right
        prompt, regardless of provider.
        """
        if provider is None or model is None or api_key is None:
            # Lazy resolution when called directly (e.g., in unit tests that
            # mock _call_llm but still want sensible defaults).
            prov, mod = self._resolve_judge()
            provider = provider or prov
            model = model or mod
            api_key = api_key or self._resolve_api_key(provider)

        if provider == "openai":
            return await self._call_openai(system, user, model=model, api_key=api_key)
        if provider == "anthropic":
            return await self._call_anthropic(system, user, model=model, api_key=api_key)
        raise RuntimeError(f"Unsupported judge provider: {provider!r}")

    async def _call_openai(self, system: str, user: str, *, model: str, api_key: str) -> str:
        """Call OpenAI with provider-native JSON mode.

        ``response_format={"type": "json_object"}`` guarantees the response
        body is valid JSON, eliminating the main source of parse-failure
        zero-scores. The temperature-0.0 call still exhibits ~±0.10 jitter
        on borderline cases — see :mod:`smart_critic_prompts` rubric docs
        for how we reduce that further.
        """
        from openai import AsyncOpenAI

        create_kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }

        async with AsyncOpenAI(api_key=api_key) as client:
            try:
                response = await client.chat.completions.create(**create_kwargs)
            except TypeError:
                # Extremely old SDKs won't know response_format — retry without
                # it so we at least return something the regex fallback can
                # parse. Should be unreachable with current pinned SDK.
                create_kwargs.pop("response_format", None)
                response = await client.chat.completions.create(**create_kwargs)

        choice = response.choices[0] if response.choices else None
        if not choice or not choice.message or not choice.message.content:
            return ""
        return str(choice.message.content)

    # Models/model-families that reject assistant prefill. If the API
    # returns the canonical error message we also cache the model here so
    # subsequent calls in the same process skip the retry hop.
    _NO_PREFILL_MODELS: ClassVar[set[str]] = set()

    async def _call_anthropic(self, system: str, user: str, *, model: str, api_key: str) -> str:
        """Call Anthropic.

        Strategy:

        * First attempt uses JSON prefill (``{`` as the last assistant
          message) to force structured output. This reliably works on
          Haiku/Opus/Sonnet generations that accept prefill.
        * Newer models (e.g. ``claude-sonnet-4-6``) reject prefill with
          ``"This model does not support assistant message prefill"``. We
          catch that specific error, retry without the prefill, and cache
          the decision on the class so subsequent calls skip the failed
          attempt.

        Either way the response goes through the same JSON parser, which
        is tolerant of prose surrounding the JSON object.
        """
        try:
            from anthropic import AsyncAnthropic, BadRequestError
        except ImportError as e:  # pragma: no cover - covered by install extras
            raise ImportError(
                "The 'anthropic' package is required to use SmartCritic with "
                "judge_provider='anthropic'. Install it with: pip install anthropic"
            ) from e

        async with AsyncAnthropic(api_key=api_key) as client:
            use_prefill = model not in self._NO_PREFILL_MODELS
            body = await self._anthropic_request(
                client, system=system, user=user, model=model, prefill=use_prefill
            )
            if body is not None:
                return body

            # First call hit the prefill-unsupported error — remember that
            # and retry without prefill. A None return from the helper is
            # the signal to fall through.
            try:
                body = await self._anthropic_request(
                    client, system=system, user=user, model=model, prefill=False
                )
            except BadRequestError:
                return ""
            return body or ""

    @classmethod
    async def _anthropic_request(
        cls,
        client: Any,
        *,
        system: str,
        user: str,
        model: str,
        prefill: bool,
    ) -> str | None:
        """Single Anthropic messages.create call. Returns None if the call
        fails specifically because the model rejects assistant prefill,
        so the caller can retry without it.
        """
        from anthropic import BadRequestError

        messages: list[dict[str, Any]] = [{"role": "user", "content": user}]
        if prefill:
            messages.append({"role": "assistant", "content": "{"})

        try:
            response = await client.messages.create(
                model=model,
                max_tokens=512,
                system=system,
                messages=messages,
                temperature=0.0,
            )
        except BadRequestError as e:
            if prefill and "prefill" in str(e).lower():
                cls._NO_PREFILL_MODELS.add(model)
                return None
            raise

        chunks = []
        for block in response.content or []:
            text = getattr(block, "text", None)
            if text:
                chunks.append(text)
        body = "".join(chunks)
        if prefill and not body.lstrip().startswith("{"):
            # Restore the prefilled "{" so the parser sees a complete object.
            body = "{" + body
        return body
