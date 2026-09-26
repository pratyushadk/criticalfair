"""Start-page hero: a sample drawing being ballooned and turned into characteristics-sheet rows (loops)."""

# (x, y, text, row description) - positions in the 560x300 SVG blueprint
DIMS = [
    (150, 44, "150.00 ±0.10", "Overall Length"),
    (54, 150, "Ø65.00 ±0.05", "Outer Diameter"),
    (120, 118, "Ø50.00 +0.02/-0", "Bore Diameter"),
    (235, 250, "7.50 ±0.05", "Wall Width"),
    (330, 78, "⌖ Ø0.02 | A | B", "Position of Bore"),
    (300, 196, "Ra 0.8", "Bore Surface Finish"),
    (420, 120, "M10x1.5", "Port Thread"),
    (392, 248, "⏥ 0.05", "Flatness of Face"),
    (330, 280, "4X Ø6.6 THRU", "Mounting Holes"),
]

HERO = r"""
<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"Helvetica Neue",Inter,"Segoe UI",sans-serif;background:transparent;overflow:hidden;color:#1C1C1C}
.hero{height:400px;display:grid;grid-template-columns:0.82fr 1.4fr;gap:34px;padding:30px 30px;background:#fff;
  border:1px solid #E4E4E0;border-radius:8px}
.left{display:flex;flex-direction:column;justify-content:center}
.k{font-size:12px;color:#6B6B66;font-weight:500}
h1{font-size:30px;line-height:1.2;font-weight:650;letter-spacing:-.015em;color:#1C1C1C;margin:10px 0 12px}
.sub{color:#55554F;font-size:14.5px;line-height:1.55;max-width:380px}
.steps{margin-top:22px;border-top:1px solid #EDEDE9}
.st{display:flex;gap:10px;align-items:center;padding:8px 0;border-bottom:1px solid #EDEDE9;font-size:13px;color:#8A8A84;transition:color .3s}
.st i{font-style:normal;width:18px;height:18px;border-radius:50%;border:1px solid #CFCFC9;display:inline-flex;align-items:center;justify-content:center;font-size:10px}
.st.on{color:#1C1C1C} .st.on i{border-color:#1F4E79;background:#1F4E79;color:#fff}
.stage{display:grid;grid-template-columns:1fr 200px;gap:16px;align-items:center}
.board{position:relative;background:#FBFBF9;border:1px solid #D9D9D3;border-radius:4px;padding:8px}
svg{display:block;width:100%;height:auto}
.frame{stroke:#1C1C1C;stroke-width:1.2;fill:none}
.part{stroke:#1C1C1C;stroke-width:1.6;fill:none}
.hatch{stroke:#1C1C1C;stroke-width:.6;opacity:.55}
.dim{stroke:#555;stroke-width:.7}
.cl{stroke:#888;stroke-width:.6}
.tb{fill:#3A3A36;font:600 6.5px -apple-system,sans-serif}
.t{fill:#1C1C1C;font:500 10px "Helvetica Neue",Arial,sans-serif}
.hl{fill:transparent;transition:fill .3s}
.on .hl{fill:rgba(31,78,121,.10)}
.bal{opacity:0;transition:opacity .25s}
.on .bal{opacity:1}
.bal circle{fill:#fff;stroke:#1F4E79;stroke-width:1.3}
.bal text{fill:#1F4E79;font:600 9px -apple-system,sans-serif}
.lead{stroke:#1F4E79;stroke-width:.9;opacity:0;transition:opacity .25s}
.on .lead{opacity:1}
.scan{position:absolute;top:8px;bottom:8px;width:1.5px;left:0;background:#C0392B;opacity:0}
.sheet{background:#fff;border:1px solid #D9D9D3;border-radius:4px;overflow:hidden;font-size:10.5px}
.sh{display:grid;grid-template-columns:22px 1fr;background:#F1F1EE;border-bottom:1px solid #D9D9D3;color:#55554F;font-weight:600}
.sh span,.row span{padding:5px 7px}
.sh span:first-child,.row span:first-child{border-right:1px solid #E4E4E0;text-align:center}
.row{display:grid;grid-template-columns:22px 1fr;border-bottom:1px solid #EDEDE9;color:#1C1C1C;opacity:0;transition:opacity .3s}
.row.in{opacity:1}
.cap{font-size:11px;color:#8A8A84;margin-top:6px}
</style></head><body>
<div class="hero">
  <div class="left">
    <div class="k">First Article Inspection · AS9102</div>
    <h1>Balloon a drawing and fill in the AS9102 report.</h1>
    <div class="sub">Upload an engineering drawing. Critical Fair reads each dimension and GD&amp;T callout,
      places the balloons and prepares the inspection sheet for you to review.</div>
    <div class="steps">
      <div class="st" id="s1"><i>1</i>Read dimensions and tolerances</div>
      <div class="st" id="s2"><i>2</i>Place balloons</div>
      <div class="st" id="s3"><i>3</i>Build the characteristics sheet</div>
    </div>
  </div>
  <div class="stage">
    <div>
      <div class="board" id="board">
        <div class="scan" id="scan"></div>
        <svg viewBox="0 0 560 300" id="svg">
          <rect class="frame" x="4" y="4" width="552" height="292"/>
          <rect class="frame" x="420" y="262" width="136" height="34"/>
          <line class="frame" x1="420" y1="279" x2="556" y2="279"/>
          <text class="tb" x="426" y="274">PART NO  CF-1001  REV B</text>
          <text class="tb" x="426" y="291">MOUNTING SLEEVE   SCALE 1:1</text>
          <rect class="part" x="80" y="70" width="250" height="150"/>
          <rect class="part" x="80" y="100" width="250" height="90"/>
          <g class="hatch">__HATCH__</g>
          <line class="cl" x1="66" y1="145" x2="344" y2="145" stroke-dasharray="14 3 3 3"/>
          <line class="dim" x1="80" y1="52" x2="330" y2="52"/><line class="dim" x1="80" y1="48" x2="80" y2="68"/><line class="dim" x1="330" y1="48" x2="330" y2="68"/>
          <line class="dim" x1="62" y1="70" x2="62" y2="220"/><line class="dim" x1="112" y1="100" x2="112" y2="190"/>
          <line class="dim" x1="200" y1="238" x2="270" y2="238"/>
          <circle class="part" cx="450" cy="150" r="62"/><circle class="part" cx="450" cy="150" r="36"/>
          <circle class="part" cx="450" cy="96" r="5"/><circle class="part" cx="504" cy="150" r="5"/><circle class="part" cx="450" cy="204" r="5"/><circle class="part" cx="396" cy="150" r="5"/>
          <line class="cl" x1="380" y1="150" x2="520" y2="150" stroke-dasharray="14 3 3 3"/><line class="cl" x1="450" y1="80" x2="450" y2="220" stroke-dasharray="14 3 3 3"/>
          __DIMS__
        </svg>
      </div>
      <div class="cap" id="cap">Sample drawing</div>
    </div>
    <div>
      <div class="sheet">
        <div class="sh"><span>#</span><span>Characteristic</span></div>
        <div id="rows">__ROWS__</div>
      </div>
      <div class="cap">Characteristics sheet</div>
    </div>
  </div>
</div>
<script>
const items=[...document.querySelectorAll('.d')], rows=[...document.querySelectorAll('.row')];
const scan=document.getElementById('scan'), board=document.getElementById('board'), cap=document.getElementById('cap');
const S=[1,2,3].map(i=>document.getElementById('s'+i));
const SCAN=5200;
function run(){
  items.forEach(i=>i.classList.remove('on')); rows.forEach(r=>r.classList.remove('in')); S.forEach(s=>s.classList.remove('on'));
  cap.textContent='Sample drawing';
  const w=board.clientWidth; scan.style.transition='none'; scan.style.opacity=.85; scan.style.transform='translateX(8px)';
  S[0].classList.add('on');
  requestAnimationFrame(()=>requestAnimationFrame(()=>{scan.style.transition=`transform ${SCAN}ms linear`; scan.style.transform=`translateX(${w-10}px)`;}));
  const order=items.map(el=>({el,x:+el.dataset.x})).sort((a,b)=>a.x-b.x);
  order.forEach((o,n)=>{
    setTimeout(()=>{
      o.el.classList.add('on'); S[1].classList.add('on');
      cap.textContent=`Sample drawing · ${n+1} characteristic${n?'s':''}`;
      setTimeout(()=>{rows[n].classList.add('in'); S[2].classList.add('on');},400);
    }, o.x/560*SCAN*0.95+200);
  });
  setTimeout(()=>{scan.style.opacity=0;}, SCAN+100);
  setTimeout(run, SCAN+4200);
}
run();
</script></body></html>
"""


def html() -> str:
    hatch = "".join(f'<line x1="{x}" y1="70" x2="{x - 30}" y2="100"/><line x1="{x}" y1="190" x2="{x - 30}" y2="220"/>'
                    for x in range(110, 331, 10))
    dims, rows = [], []
    for n, (x, y, text, name) in enumerate(DIMS, 1):
        w = len(text) * 6.7 + 10
        bx, by = x + w / 2 + 14, y - 16
        dims.append(
            f'<g class="d" data-x="{x}"><rect class="hl" x="{x - w / 2}" y="{y - 12}" width="{w}" height="17"/>'
            f'<text class="t" x="{x}" y="{y}" text-anchor="middle">{text}</text>'
            f'<line class="lead" x1="{x + w / 2}" y1="{y - 6}" x2="{bx - 7}" y2="{by + 4}"/>'
            f'<g class="bal"><circle cx="{bx}" cy="{by}" r="8"/><text x="{bx}" y="{by + 3.2}" text-anchor="middle">{n}</text></g></g>')
        rows.append(f'<div class="row"><span>{n}</span><span>{name}</span></div>')
    return HERO.replace("__HATCH__", hatch).replace("__DIMS__", "".join(dims)).replace("__ROWS__", "".join(rows))
