"""Run perception + Claude on drawings and print results with timings (bypasses cache)."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from app import extractor
from app.drawing import load_drawing
from app.perception import perceive

for p in sys.argv[1:]:
    d = load_drawing(Path(p).name, Path(p).read_bytes())
    t0 = time.time(); P = perceive(d.image, d.pdf_text); t1 = time.time()
    tmp = f"tmp-{time.time()}"
    ext = extractor.extract(d.image, P, tmp)
    (extractor.CACHE_DIRS[1] / f"{tmp}.json").unlink(missing_ok=True)
    t2 = time.time()
    print(f"\n=== {Path(p).name}: perception {t1-t0:.1f}s, claude {t2-t1:.1f}s, balloons_mode={P.has_balloons}, "
          f"{len(ext.characteristics)} chars")
    print("  drawing:", ext.drawing.model_dump(exclude_none=True))
    for c in ext.characteristics:
        print(f"  b={c.balloon} {c.circle} {c.tokens} | {c.name}: {c.notation} | {c.type} | tool={c.tool} "
              f"| conf={c.confidence} | {c.issue or ''}")
    print("  ignored:", ext.ignored_circles, "warnings:", ext.warnings)
