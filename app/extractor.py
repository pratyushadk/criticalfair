"""Single streamed Claude vision call, grounded on local perception IDs. Results are cached per drawing hash."""
import base64
import json
import os
import re
import time
from pathlib import Path

import anthropic

from .drawing import api_image_bytes
from .perception import Perception
from .prompts import MODE_BALLOONED, MODE_UNBALLOONED, PROMPT, SYSTEM
from .schemas import Extraction

MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5")
EFFORT = os.getenv("CLAUDE_EFFORT", "medium")
FAST_MODE = os.getenv("CLAUDE_FAST_MODE", "1") == "1"
ROOT = Path(__file__).resolve().parent.parent
CACHE_DIRS = [ROOT / "samples" / "cache", ROOT / "output" / "cache"]


class ExtractionError(RuntimeError):
    pass


def has_api_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _n(v, total) -> int:
    return round(v * 1000 / total)


def build_prompt(p: Perception) -> str:
    toks = "\n".join(f"{t.id} \"{t.text}\" @ ({_n(t.box[0], p.width)},{_n(t.box[1], p.height)})-"
                     f"({_n(t.box[2], p.width)},{_n(t.box[3], p.height)})" for t in p.tokens) or "(none)"
    circ = "\n".join(f"{c.id} centre ({_n(c.cx, p.width)},{_n(c.cy, p.height)}) r={_n(c.r, p.width)} "
                     f"number={c.digits or '?'}" for c in p.circles) or "(none)"
    mode = MODE_BALLOONED if p.has_balloons else MODE_UNBALLOONED
    return PROMPT.format(tokens=toks, circles=circ, mode=mode)


def cached(sha: str) -> Extraction | None:
    for d in CACHE_DIRS:
        f = d / f"{sha}.json"
        if f.exists():
            return Extraction.model_validate_json(f.read_text())
    return None


def _save_cache(sha: str, ext: Extraction):
    d = CACHE_DIRS[1]
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{sha}.json").write_text(ext.model_dump_json(indent=1))


def estimate_seconds(p: Perception) -> float:
    """Rough ETA for the Claude call, used for the progress bar."""
    expected = max(8, len(p.tokens) * 0.6 + len(p.circles))
    return 10 + expected * (0.9 if FAST_MODE else 2.0)


def expected_count(p: Perception) -> int:
    digits = sum(1 for c in p.circles if c.digits)
    return max(digits, int(len(p.tokens) * 0.6), 5)


ITEM_RE = re.compile(r'"tokens"\s*:\s*\[([^\]]*)\][^{}]*?"name"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*'
                     r'"notation"\s*:\s*"((?:[^"\\]|\\.)*)"')


def partial_items(text: str) -> list[tuple[list[str], str, str]]:
    """Characteristics completed so far in a partially streamed JSON response: (token_ids, name, notation)."""
    out = []
    for m in ITEM_RE.finditer(text):
        toks = re.findall(r"T\d+", m.group(1))
        try:
            name, notation = json.loads(f'"{m.group(2)}"'), json.loads(f'"{m.group(3)}"')
        except ValueError:
            name, notation = m.group(2), m.group(3)
        out.append((toks, name, notation))
    return out


def extract(img, p: Perception, sha: str, on_progress=None) -> Extraction:
    """on_progress(streamed_text, elapsed_s) is called while the response streams."""
    hit = cached(sha)
    if hit:
        return hit
    data, media_type = api_image_bytes(img)
    content = [{"type": "image", "source": {"type": "base64", "media_type": media_type,
                                            "data": base64.standard_b64encode(data).decode()}},
               {"type": "text", "text": build_prompt(p)}]
    client = anthropic.Anthropic()
    kwargs = dict(model=MODEL, max_tokens=32000, system=SYSTEM, thinking={"type": "adaptive"},
                  output_config={"effort": EFFORT}, messages=[{"role": "user", "content": content}],
                  output_format=Extraction)
    betas = ["server-side-fallback-2026-07-01"]
    attempts = [dict(speed="fast", betas=betas + ["fast-mode-2026-02-01"])] if FAST_MODE else []
    attempts.append(dict(betas=betas))
    start = time.time()
    last_err = None
    for extra in attempts:
        try:
            text = ""
            with client.beta.messages.stream(fallbacks="default", **kwargs, **extra) as stream:
                for delta in stream.text_stream:
                    text += delta
                    if on_progress:
                        on_progress(text, time.time() - start)
                final = stream.get_final_message()
            break
        except anthropic.RateLimitError as e:
            last_err = e
            continue  # fast-mode has its own rate limit: fall back to standard speed
        except anthropic.BadRequestError as e:
            last_err = e
            if "speed" in extra:
                continue  # fast mode not enabled for this org/model
            raise ExtractionError(f"Claude rejected the request: {e.message}") from e
        except anthropic.AuthenticationError as e:
            raise ExtractionError("Invalid ANTHROPIC_API_KEY.") from e
        except anthropic.APIStatusError as e:
            raise ExtractionError(f"Claude API error {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise ExtractionError("Could not reach the Claude API.") from e
    else:
        raise ExtractionError(f"Claude API unavailable: {last_err}")

    if final.stop_reason == "refusal":
        raise ExtractionError("Claude declined to analyse this drawing.")
    if final.stop_reason == "max_tokens":
        raise ExtractionError("Response truncated - drawing has too many characteristics for one pass.")
    ext = getattr(final, "parsed_output", None)
    if ext is None:
        try:
            ext = Extraction.model_validate_json(text)
        except Exception as e:
            raise ExtractionError("Claude returned output that did not match the schema.") from e
    _save_cache(sha, ext)
    return ext


def dump_debug(p: Perception, ext: Extraction, path: Path):
    path.write_text(json.dumps({"prompt": build_prompt(p), "extraction": ext.model_dump()}, indent=1))
