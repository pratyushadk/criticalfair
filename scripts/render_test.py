"""Full pipeline (cached) -> review + clean overlays in output/."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from app import extractor, validation, overlay
from app.drawing import load_drawing
from app.perception import perceive
for p in sys.argv[1:]:
    d = load_drawing(Path(p).name, Path(p).read_bytes())
    t = time.time(); P = perceive(d.image, d.pdf_text)
    ext = extractor.extract(d.image, P, d.sha256)
    rows, issues = validation.build(ext, P)
    overlay.place_balloons(d.image, rows)
    stem = Path(p).stem[:20].replace(" ", "_")
    overlay.draw(d.image, rows, clean=True).save(f"output/{stem}_clean.png")
    overlay.draw(d.image, rows).save(f"output/{stem}_review.png")
    print(f"{stem}: {time.time()-t:.1f}s rows={len(rows)} flagged={sum(r['flagged'] for r in rows)}")
    for r in rows: print(f"  #{r['id']:>4} {r['zone']:>3} {r['name'][:38]:38} | {r['notation'][:28]:28} | {r['tool']:12} | {'; '.join(r['flags'])[:90]}")
    for i in issues: print("  ISSUE", i["kind"], i["text"])
