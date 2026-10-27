"""Section 7's plug for the existing generic Central Mind resource socket.

Registry metadata bootstraps selection; contextual verified evidence can reorder
it. Failures try another provider within a bounded budget, never an echo answer.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
import requests


def failure_code(exc):
    """Stable actionable diagnostics without provider URLs, prompts or secrets."""
    if isinstance(exc, requests.Timeout):
        return "model_request_timed_out"
    if isinstance(exc, requests.ConnectionError):
        return "model_service_unreachable"
    if isinstance(exc, requests.HTTPError):
        status = getattr(exc.response, "status_code", None)
        return f"provider_http_{status}" if status else "provider_http_error"
    safe = {"output_token_limit_reached", "reasoning_without_answer", "empty_model_answer"}
    return str(exc) if str(exc) in safe else type(exc).__name__

try:
    from .resource_selector import rank_resources
    from .interface import provider_name_for, execution_model_for
except ImportError:
    from resource_selector import rank_resources
    from interface import provider_name_for, execution_model_for


def _answer(text, structured_output=None):
    if not isinstance(text, str):
        raise ValueError("provider answer must be text")
    # Strip only explicit provider reasoning boundaries, never guess from prose.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    if "<think>" in text or "</think>" in text:
        raise ValueError("provider returned incomplete reasoning boundaries")
    if text.startswith("```") and text.endswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    if not text or text.startswith("[model error]"):
        raise ValueError("provider returned no usable answer")
    if structured_output == "json":
        json.loads(text)
    return text


class ModelRouter:
    def __init__(self, registry_path, *, availability_probe=None):
        self.registry_path = Path(registry_path)
        data = yaml.safe_load(self.registry_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("llms"), dict):
            raise ValueError("registry must declare an llms mapping")
        self.registry = data
        self.availability_probe = availability_probe

    def _available(self, resource, cache):
        if self.availability_probe is not None:
            return bool(self.availability_probe(resource))
        if provider_name_for(resource) != "ollama":
            return True
        try:
            from .providers.ollama import OllamaProvider
            from .interface import execution_model_for
        except ImportError:
            from providers.ollama import OllamaProvider
            from interface import execution_model_for
        provider = OllamaProvider(api_url=resource.get("api_url"))
        endpoint = provider.api_url
        if endpoint not in cache:
            try:
                cache[endpoint] = (set(provider.models()), None)
            except Exception as exc:
                cache[endpoint] = (set(), failure_code(exc))
        names, error = cache[endpoint]
        if error:
            raise RuntimeError(error)
        model = execution_model_for(resource)
        if ":" not in model.rsplit("/", 1)[-1]:
            model += ":latest"
        return model in names

    def _candidates(self, requirement, source_scores=None):
        requirement = dict(requirement)
        domain = requirement.get("domain", "")
        capability = requirement.get("capability", "")
        hint = self.registry.get("domain_assignments", {}).get(domain, {}).get(capability, {})
        if not isinstance(hint, dict):
            hint = {}
        resources = {}
        for key, entry in self.registry["llms"].items():
            if not isinstance(entry, dict):
                continue
            # Non-generative resources cannot answer a text reasoning request.
            if str(entry.get("kind", "")).lower() in {"embedding", "embed", "image", "audio", "speech", "vision_encoder"}:
                continue
            if provider_name_for(entry) not in {"ollama", "openai", "openai_compat", "http"}:
                continue
            resource = dict(entry)
            # eligible_domains are bootstrap guidance, not model ownership.
            resource.pop("eligible_domains", None)
            tasks = entry.get("best_tasks") or []
            resource["task_quality"] = {
                item["capability"]: item.get("quality", 0)
                for item in tasks if isinstance(item, dict) and item.get("capability")
            }
            profile = entry.get("problem_solving") or {}
            profile_key = {"reason": "multi_step_quality", "plan": "planning_quality",
                           "write": "code_strength", "test": "code_strength", "debug": "code_strength", "answer": "prose_strength"}.get(capability)
            if (
                profile_key
                and capability not in resource["task_quality"]
                and isinstance(profile, dict)
            ):
                resource["task_quality"][capability] = profile.get(profile_key, 0)
            resources[key] = resource
        # Memory's current interface returns counts of verified successful uses,
        # not normalized quality. Keep unqualified/insufficient evidence weak.
        minimum = self.registry.get("routing", {}).get("roster_reordering", {}).get("min_evidence_count", 3)
        learned = {}
        for key, count in (source_scores or {}).items():
            if isinstance(count, (int, float)) and count >= minimum:
                learned[key] = min(float(count) / (float(count) + minimum), 1.0)
        return rank_resources(resources, requirement,
                              bootstrap_priority=hint.get("priority") or [],
                              learned_scores=learned)

    def fulfill(self, *, requirement, call_fn, messages, source_scores=None, max_attempts=None, **context):
        import time
        started = time.time()
        result = self._fulfill(requirement=requirement, call_fn=call_fn, messages=messages,
                               source_scores=source_scores, max_attempts=max_attempts, **context)
        self._debug_record(requirement, result, time.time() - started, source_scores)
        return result

    def _debug_record(self, requirement, result, elapsed, source_scores=None):
        """Append one compact record per model request to the local state debug folder."""
        try:
            import os
            import time
            base = os.environ.get("AI_FRIEND_STATE_DIR")
            if not base:
                return
            directory = Path(base).expanduser() / "debug"
            directory.mkdir(parents=True, exist_ok=True)
            record = {
                "ts": round(time.time(), 3),
                "elapsed_s": round(elapsed, 2),
                "domain": requirement.get("domain"),
                "capability": requirement.get("capability"),
                "structured": requirement.get("structured_output"),
                "ok": result.get("ok"),
                "model": result.get("model"),
                "attempts": result.get("attempts"),
                "output": str(result.get("output", ""))[:12000],
            }
            try:
                record["ranking"] = [
                    {"model": c.key, "score": round(c.score, 1), "reasons": list(c.reasons)}
                    for c in self._candidates(requirement, source_scores)[:4]
                ]
            except Exception as exc:
                record["ranking"] = [{"error": str(exc)[:120]}]
            record["source_scores"] = dict(source_scores or {})
            with (directory / "model_calls.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass

    def _fulfill(self, *, requirement, call_fn, messages, source_scores=None, max_attempts=None, **context):
        routing = self.registry.get("routing") or {}
        budget = max(1, min(int(max_attempts or routing.get("max_attempts_per_capability", 3)), 10))
        attempts = []
        availability_cache = {}
        generation_count = 0
        for candidate in self._candidates(requirement, source_scores):
            try:
                available = self._available(candidate.resource, availability_cache)
            except RuntimeError as exc:
                code = str(exc)
                if code not in {"model_service_unreachable", "model_request_timed_out", "provider_http_error"} and not re.fullmatch(r"provider_http_\d+", code):
                    code = "availability_probe_failed"
                attempts.append({"model": candidate.key, "ok": False, "error": code})
                continue
            if not available:
                attempts.append({"model": candidate.key, "ok": False, "error": "not_available_at_runtime"})
                continue
            if generation_count >= budget:
                break
            generation_count += 1
            try:
                resource = dict(candidate.resource)
                generation = dict(routing.get("structured_generation") or {}) if requirement.get("structured_output") else {}
                generation.update((routing.get("generation_by_capability") or {}).get(str(requirement.get("capability") or "")) or {})
                generation.update(resource.get("generation") or {})
                generation["structured_output"] = requirement.get("structured_output")
                declared_context = resource.get("context_tokens")
                if isinstance(declared_context, int) and isinstance(generation.get("context_tokens"), int):
                    generation["context_tokens"] = min(declared_context, generation["context_tokens"])
                resource["_generation"] = generation
                text = call_fn(candidate.key, resource, messages)
                output = _answer(text, requirement.get("structured_output"))
                return {"ok": True, "output": output, "model": candidate.key,
                        "provider": provider_name_for(candidate.resource),
                        "execution_model": execution_model_for(candidate.resource),
                        "reasons": list(candidate.reasons), "attempts": attempts}
            except Exception as exc:
                # Do not expose provider exception strings: URLs may contain credentials.
                attempts.append({"model": candidate.key, "ok": False, "error": failure_code(exc)})
        return {"ok": False, "output": "", "error": "no available model satisfied the resource requirement",
                "attempts": attempts, "required_resource": dict(requirement)}

    def try_capability(self, *, domain, capability, call_fn, messages, max_attempts=None, source_scores=None):
        result = self.fulfill(requirement={"domain": domain, "capability": capability},
                              call_fn=call_fn, messages=messages,
                              source_scores=source_scores, max_attempts=max_attempts)
        yield from result["attempts"]
        if result["ok"]:
            yield result
