from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


@dataclass
class CycleSummary:
    selected: int
    executed: int
    rejected: int
    reasons: Dict[str, int]


class LLMAdvisor:
    """LLM advisor for summary + candidate ranking."""

    def __init__(
        self,
        enabled: bool = False,
        provider: str = "mock",
        api_key: str = "",
        api_key_env: str = "OPENAI_API_KEY",
        api_base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        timeout_seconds: int = 12,
        max_retries: int = 1,
        retry_delay_ms: int = 250,
        max_tokens: int = 256,
        score_scale: float = 10.0,
        score_candidates_limit: int = 30,
        request_mode: str = "openai",
    ) -> None:
        self.enabled = enabled
        self.provider = (provider or "mock").strip().lower()
        self.api_key = (api_key or "").strip()
        self.api_key_env = (api_key_env or "").strip()
        self.api_base_url = (api_base_url or "https://api.openai.com/v1").strip().rstrip("/")
        self.model = (model or "gpt-4o-mini").strip()
        self.temperature = float(temperature)
        self.timeout_seconds = max(1, int(timeout_seconds))
        self.max_retries = max(0, int(max_retries))
        self.retry_delay_ms = max(0, int(retry_delay_ms))
        self.max_tokens = max(32, int(max_tokens))
        self.score_scale = max(0.1, float(score_scale))
        self.score_candidates_limit = max(1, int(score_candidates_limit))
        self.request_mode = (request_mode or "openai").strip().lower()
        self._last_meta: Dict[str, Any] = {"status": "disabled"}

    def _normalize_text(self, value: Any) -> str:
        return str(value or "").strip()

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _clamp(self, value: float, lo: float, hi: float) -> float:
        return lo if value < lo else hi if value > hi else value

    def _resolve_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            env_key = os.getenv(self.api_key_env)
            if env_key:
                return env_key
        return ""

    def _prompt_payload(self, candidates: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
        return json.dumps(
            {
                "instruction": (
                    "Score each candidate and return a JSON object only. "
                    "rank_reason must mention why a candidate should be prioritized. "
                    "Score_delta range: -10 to 10 but do not exceed the requested scale."
                ),
                "context": context,
                "candidates": candidates,
            },
            ensure_ascii=False,
            indent=2,
        )

    def _extract_json_object(self, raw: str) -> Dict[str, Any]:
        if not raw:
            return {}

        trimmed = self._normalize_text(raw)
        try:
            return json.loads(trimmed)
        except json.JSONDecodeError:
            pass

        start = trimmed.find("{")
        end = trimmed.rfind("}")
        if start < 0 or end <= start:
            return {}
        try:
            return json.loads(trimmed[start : end + 1])
        except json.JSONDecodeError:
            return {}

    def _normalize_score_items(
        self,
        candidates: List[Dict[str, Any]],
        payload: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        candidate_map = {self._normalize_text(item.get("id")): item for item in candidates}
        results: Dict[str, Dict[str, Any]] = {}

        entries = payload.get("candidates")
        if not isinstance(entries, list):
            return results

        for item in entries:
            if not isinstance(item, dict):
                continue
            candidate_id = self._normalize_text(item.get("id"))
            if not candidate_id or candidate_id not in candidate_map:
                continue

            raw_score = self._safe_float(item.get("score_delta"), 0.0)
            conf = self._safe_float(item.get("confidence"), 0.5)
            reason = self._normalize_text(item.get("reason"))

            results[candidate_id] = {
                "score_delta": self._clamp(raw_score, -self.score_scale, self.score_scale),
                "confidence": self._clamp(conf, 0.0, 1.0),
                "reason": reason or "No reason",
            }

        return results

    def _mock_scores(
        self,
        candidates: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        results: Dict[str, Dict[str, Any]] = {}
        for candidate in candidates:
            candidate_id = self._normalize_text(candidate.get("id"))
            if not candidate_id:
                continue

            conf = self._safe_float(candidate.get("confidence"), 0.5)
            edge = self._safe_float(candidate.get("expected_edge_bps"), 0.0)
            base_score = self._safe_float(candidate.get("base_score"), 0.0)
            regime_conf = self._safe_float(candidate.get("regime_confidence"), 0.5)
            raw = (conf - 0.5) * 4.0 + (edge / 80.0) + (regime_conf - 0.5) * 2.0 + (base_score / 80.0)

            # deterministic pseudo-rationale for debugging and traceability
            direction = self._normalize_text(candidate.get("direction"))
            if direction == "BUY" and conf >= 0.7 and edge > 0:
                reason = "high confidence long signal"
            elif direction == "SELL" and conf >= 0.7 and edge > 0:
                reason = "high confidence short signal"
            elif edge < 0:
                reason = "negative edge candidate"
            else:
                reason = "baseline statistical score"

            results[candidate_id] = {
                "score_delta": self._clamp(raw, -self.score_scale, self.score_scale),
                "confidence": self._clamp(conf, 0.0, 1.0),
                "reason": reason,
            }

        return results

    def _build_openai_payload(self, candidates: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        candidate_block = self._prompt_payload(candidates, context)
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a deterministic trading ranker. "
                        "Use only provided candidate IDs. "
                        "Return strictly JSON object format:"
                        " {\"candidates\": [{\"id\":\"id\",\"score_delta\": number,"
                        " \"confidence\":0~1 number, \"reason\":\"short rationale\"}],"
                        " \"summary\":\"...\", \"status\":\"ok\" }."
                    ),
                },
                {
                    "role": "user",
                    "content": candidate_block,
                },
            ],
            "temperature": self._clamp(self.temperature, 0.0, 1.0),
            "max_tokens": self.max_tokens,
        }

    def _post(self, url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Optional[str]:
        last_error = ""
        for _ in range(max(1, self.max_retries + 1)):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=self.timeout_seconds)
                status = response.status_code
                if status >= 500:
                    raise requests.RequestException(f"upstream error: {status}")
                response.raise_for_status()
                return response.text
            except requests.RequestException as exc:
                last_error = str(exc)
                if self.retry_delay_ms:
                    time.sleep(self.retry_delay_ms / 1000.0)
                continue
        self._last_meta = {
            "status": "error",
            "provider": self.provider,
            "request_mode": self.request_mode,
            "error": last_error,
        }
        return None

    def _parse_openai_like(self, raw: str) -> Dict[str, Any]:
        payload = self._extract_json_object(raw)
        if not payload:
            return {}
        if isinstance(payload.get("choices"), list) and payload["choices"]:
            message = payload.get("choices")[0]
            if isinstance(message, dict):
                msg = message.get("message")
                if isinstance(msg, dict):
                    content = self._extract_json_object(self._normalize_text(msg.get("content")))
                    if content:
                        return content
        return payload

    def _score_candidates_llm(self, candidates: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        api_key = self._resolve_api_key()
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        endpoint = self._resolve_endpoint()
        payload = self._build_openai_payload(candidates, context)
        raw = self._post(endpoint, headers=headers, payload=payload)
        if not raw:
            return {}

        parsed = self._parse_openai_like(raw)
        if not parsed:
            self._last_meta = {
                "status": "parse_error",
                "provider": self.provider,
                "request_mode": self.request_mode,
            }
            return {}

        normalized = self._normalize_score_items(candidates, parsed)
        if not normalized:
            self._last_meta = {
                "status": "parse_error",
                "provider": self.provider,
                "request_mode": self.request_mode,
            }
            return {}

        self._last_meta = {
            "status": "ok",
            "provider": self.provider,
            "request_mode": self.request_mode,
            "candidate_count": len(candidates),
            "scored_count": len(normalized),
            "summary": self._normalize_text(parsed.get("summary")),
        }
        return normalized

    def _resolve_endpoint(self) -> str:
        mode = self.request_mode
        if self.provider == "ollama" or mode == "ollama":
            return f"{self.api_base_url}/api/chat"
        if mode in {"openai_compat", "openai-compatible", "openai"}:
            return f"{self.api_base_url}/chat/completions"
        return f"{self.api_base_url}/chat/completions"
    def score_candidates(
        self,
        candidates: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        if not self.enabled:
            self._last_meta = {"status": "disabled"}
            return {}

        limited = candidates[: self.score_candidates_limit]
        if not limited:
            self._last_meta = {"status": "no_candidates"}
            return {}

        if self.provider in {"mock", "noop", "mock-only"}:
            result = self._mock_scores(limited, context)
            self._last_meta = {
                "status": "mock",
                "provider": self.provider,
                "request_mode": self.request_mode,
                "candidate_count": len(limited),
                "scored_count": len(result),
            }
            return result

        if self.request_mode in {"openai", "openai_compat", "openai-compatible", "ollama"} or self.provider in {"ollama", "openai", "openai_compat", "openai-compatible"}:
            return self._score_candidates_llm(limited, context)

        self._last_meta = {
            "status": "unsupported_mode",
            "provider": self.provider,
            "request_mode": self.request_mode,
        }
        return {}

    def get_last_metadata(self) -> Dict[str, Any]:
        return dict(self._last_meta)

    def explain(self, summary: CycleSummary) -> str:
        if not self.enabled:
            return "LLM disabled: rule-based summary mode."

        if self.provider in {"mock", "noop", "mock-only"}:
            top = f"Executed {summary.executed} orders, selected {summary.selected} candidates"
            rej = f"Rejected {summary.rejected} cases" if summary.rejected else "No rejection"
            reasons = ", ".join([f"{k}:{v}" for k, v in summary.reasons.items()])
            return f"[Mock AI] Cycle summary: {top}, {rej}, reasons: {reasons}"

        if self._last_meta.get("status") == "ok":
            return "LLM ranking used for candidate prioritization in this cycle."

        return "LLM ranking unavailable; fallback to rule-based ranking was used."

    def suggest_learning_task(self) -> List[str]:
        return [
            "Classify profit/loss by strategy and propose next-epoch parameters",
            "Reduce leverage caps automatically when win-rate drops",
            "Tighten entry ban rules for symbols with high slippage",
        ]



