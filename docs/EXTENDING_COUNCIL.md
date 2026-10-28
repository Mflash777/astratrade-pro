# Extending the AI Council

## How a persona works

```python
class Persona(ABC):
    name: str; role: str
    categories: tuple[str, ...]          # which Signal.category values it reads
    def analyze(self, bundle) -> PersonaOpinion   # must return score, confidence, vote, rationale, key_points
```

`bundle` (from `IntelligenceAggregator.bundle`) contains `symbol`, `quote`, `indicators`, `fundamentals`, `macro`, `signals[]` and `summary`. Helpers:

* `self.relevant_signals(bundle)` — filters by `categories`.
* `self.weighted(signals)` → `(score, confidence)` confidence-weighted mean.
* `self.build(bundle, score, confidence, points, fallback_text, evidence)` — assembles the opinion; narration is replaced by the LLM when one is configured.
* `rebut(own, others)` — one line of debate; override for persona-specific rhetoric.

## Add a persona

1. Create `ai_council/personas/esg_analyst.py`:

```python
from .base import Persona, PersonaOpinion

class ESGAnalyst(Persona):
    name = "ESG Analyst"
    role = "Environmental, social and governance risk"
    categories = ("sec", "news", "political")
    system_prompt = "You are an ESG analyst. Concise, no financial advice."

    def analyze(self, bundle):
        sig = self.relevant_signals(bundle)
        score, conf = self.weighted(sig)
        points = [f"{len(sig)} governance-relevant signals", f"Sector: {bundle['fundamentals'].get('sector')}"]
        return self.build(bundle, score * 0.5, conf, points, f"ESG profile for {bundle['symbol']} is {'benign' if score > 0 else 'contested'}.", sig)
```

2. Register it in `ai_council/personas/__init__.py` (`ANALYST_PERSONAS.append(ESGAnalyst)`) and give it a weight in `Optimizer.WEIGHTS`.
3. Add an icon in `frontend/src/components/CouncilPanel.tsx` (`ICONS`). Nothing else changes — the UI renders whatever opinions the API returns.

## Add a data source

1. Create `data_sources/options_flow.py` subclassing `SignalSource`; `fetch(symbol)` returns `list[Signal]` with a new or existing `category`.
2. Append the class to `DEFAULT_SOURCES` in `data_sources/aggregator.py`.
3. Add the category to the `categories` tuple of the personas that should read it.
4. Fallback rule: when the live API is unavailable return deterministic mock data using `self.rng(symbol)` so tests stay stable.

## Plug in an LLM

`ai_council/llm.py` defines `LLMClient.complete(system, prompt, max_tokens) -> str | None`. Built-ins: `MockLLM` (returns `None` → rule-based text), `OpenAIClient`, `AnthropicClient`. To add a provider:

```python
class OllamaClient(LLMClient):
    def complete(self, system, prompt, max_tokens=300):
        r = httpx.post("http://localhost:11434/api/generate", json={"model": "llama3", "system": system, "prompt": prompt, "stream": False}, timeout=60)
        return r.json().get("response")
```

and branch on `LLM_PROVIDER=ollama` in `get_llm_client()`. Numeric scores, votes and the final recommendation never depend on the LLM — it only writes the prose, which keeps the Council auditable and testable.

## Tune the vote

* `vote_from_score(score, threshold=0.2)` in `personas/base.py` sets BUY/SELL thresholds.
* `Optimizer.WEIGHTS` sets persona influence; `Optimizer.synthesize` reduces confidence as dispersion rises.
* `RiskManager` caps its own score at +0.15 so a risk-positive view can never push the panel toward BUY on its own.

## Testing

`backend/tests/test_council.py` asserts: every source yields normalized signals; six opinions + Optimizer; votes sum to six; disclaimer present; determinism under `MockLLM`. Add a test per new persona asserting its vote on a fixed bundle.
