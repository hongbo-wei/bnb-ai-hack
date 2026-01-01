import httpx

from app.config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL, LLM_PROVIDER, OLLAMA_BASE
from app.schemas import RiskProfile


class LLMAdvisor:
    def recommend(
        self,
        profile: RiskProfile,
        objective: str,
        signals: list[str],
        risk_score: float,
        allocation: dict,
        user_context: str | None = None,
    ) -> tuple[str, str]:
        if LLM_PROVIDER == "none" or (LLM_PROVIDER == "openai" and not LLM_API_KEY):
            recommendation = "Use a conservative, diversified basket with strict stop-loss rules."
            rationale = f"Heuristic mode; signals: {', '.join(signals[:3])}."
            return recommendation, rationale

        context_line = f"User context: {user_context}.\n" if user_context else ""
        prompt = (
            "You are an investment advisor. Return a concise recommendation and rationale.\n"
            f"Risk tolerance: {profile.risk_tolerance}. Horizon: {profile.horizon_days} days. "
            f"Max drawdown: {profile.max_drawdown}. Objective: {objective}.\n"
            f"{context_line}"
            f"Signals: {', '.join(signals)}. Risk score: {risk_score}. Allocation hint: {allocation}."
        )
        if LLM_PROVIDER == "openai":
            payload = {
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            }
            headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
            response = httpx.post(f"{LLM_API_BASE}/chat/completions", json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]["content"]
            return message.strip(), "LLM-generated rationale"

        if LLM_PROVIDER == "ollama":
            try:
                payload = {
                    "model": LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                }
                response = httpx.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=30)
                if response.status_code == 404:
                    payload = {"model": LLM_MODEL, "prompt": prompt, "stream": False}
                    response = httpx.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=30)
                response.raise_for_status()
                if "message" in response.json():
                    message = response.json().get("message", {}).get("content", "")
                else:
                    message = response.json().get("response", "")
                return message.strip(), "LLM-generated rationale"
            except httpx.HTTPError:
                recommendation = "Use a conservative, diversified basket with strict stop-loss rules."
                rationale = f"Heuristic fallback; signals: {', '.join(signals[:3])}."
                return recommendation, rationale

        return "LLM provider not supported", ""  # Defensive fallback.
