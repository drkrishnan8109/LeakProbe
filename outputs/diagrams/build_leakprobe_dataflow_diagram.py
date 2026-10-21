"""Render the detailed LeakProbe data and tool-call workflow."""
from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "outputs" / "diagrams" / "leakprobe-workflow-hand-drawn.png"
W, H = 1600, 2500
INK, BLUE, TEAL, ORANGE, GREEN = "#24384a", "#426a83", "#347f8b", "#b77932", "#56805a"
PAPER, PALE_BLUE, PALE_ORANGE, PALE_GREEN = "#fbf7ea", "#dceaf3", "#fff0d6", "#e2f0df"
FONT = "/System/Library/Fonts/Supplemental/ChalkboardSE.ttc"
MARKER = "/System/Library/Fonts/MarkerFelt.ttc"
def f(size, marker=False): return ImageFont.truetype(MARKER if marker else FONT, size, index=1)
TITLE, SUB, HEAD, BODY, SMALL = f(68, True), f(31), f(35, True), f(28), f(23)

def build():
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    def txt(x, y, s, font=BODY, color=INK, anchor=None): d.text((x,y), s, font=font, fill=color, anchor=anchor)
    def card(box, color, seed):
        d.rounded_rectangle(box, 28, fill=color, outline=INK, width=4)
        x0,y0,x1,y1=box; r=random.Random(seed)
        d.rounded_rectangle((x0+r.choice([-3,2]),y0+2,x1+2,y1+r.choice([-2,3])),28,outline=INK,width=2)
    def arrow(y1, y2):
        x=800; d.line((x,y1,x,y2-15), fill=BLUE,width=6); d.polygon([(x-12,y2-20),(x+12,y2-20),(x,y2)],fill=BLUE)
    d.rounded_rectangle((55,28,1545,195),35,fill=PALE_BLUE)
    txt(800,82,"LeakProbe: the full workflow",TITLE,INK,"mm")
    txt(800,145,"Simulate - compare - measure - update",SUB,BLUE,"mm")

    # 1: Network and simulation input
    card((60,225,1540,515),PALE_GREEN,1)
    txt(95,260,"1  Build the network and generate an incident case",HEAD,GREEN)
    txt(110,320,"Net3 water network: reservoir to junctions to pipes; pressure sensors observe selected points.")
    txt(110,365,"python generate_data.py  runs WNTR scenarios: normal operation, leak A, and leak B.")
    txt(110,410,"Leak setup: fixed 16 mm opening begins at 02:20; simulated pressures and flows form the evidence.")
    txt(110,455,"Outputs: noisy observation CSVs + hidden measurement fixtures + candidate prediction profiles.",SMALL)
    arrow(525,565)

    # 2: Choose execution route
    card((60,575,1540,880),PALE_BLUE,2)
    txt(95,610,"2  Choose how the investigation is orchestrated",HEAD,BLUE)
    card((95,675,770,840),"#f7fbfd",3); card((830,675,1505,840),PALE_ORANGE,4)
    txt(125,700,"SCRIPTED DEMO",HEAD,BLUE)
    txt(125,750,"python run_demo.py",BODY,INK)
    txt(125,792,"Python follows a fixed tool sequence; no LLM API call.",SMALL)
    txt(865,700,"OPTIONAL LLM AGENT",HEAD,ORANGE)
    txt(865,750,"python agent.py",BODY,INK)
    txt(865,792,"Nebius / Nemotron selects tools; requires API credentials.",SMALL)
    arrow(890,930)

    # 3: Shared tools, visible call sequence
    card((60,940,1540,1510),"#fffdf5",5)
    txt(95,975,"3  Both routes use the same Python tools",HEAD,TEAL)
    rows=[
      (1045,"get_observations()","Read the case’s noisy sensor time series."),
      (1115,"get_network()","Inspect sensors, candidate leak pipes, and measurement budget."),
      (1185,"get_operation_records()","Check incident / maintenance notes; currently none for Net3."),
      (1255,"compare_hypotheses()","Rank normal and candidate leak-pipe profiles by normalized fit error."),
      (1325,"recommend_measurement()","Choose a feasible gauge location using pressure spread among leading fits."),
      (1395,"collect_demo_measurement(point)","Reveal the stored reading at that point; deduct measurement time."),
      (1460,"compare_hypotheses() again","Re-rank after new evidence; the LLM summarizes findings and uncertainty."),
    ]
    for i,(y,call,purpose) in enumerate(rows,1):
        color=TEAL if i in (1,4,7) else BLUE
        d.ellipse((100,y-20,140,y+20),fill=color)
        txt(120,y,str(i),SMALL,"white","mm")
        txt(165,y,call,SMALL,color,anchor="lm")
        txt(560,y,purpose,SMALL,INK,anchor="lm")
    arrow(1520,1565)

    # 4: Evidence and result example
    card((60,1575,1540,1965),PALE_ORANGE,6)
    txt(95,1610,"4  Why the extra measurement matters",HEAD,ORANGE)
    txt(110,1670,"Upstream sensor readings can leave Leak A and Leak B indistinguishable:")
    txt(140,1720,"before measurement: Leak A fit error 0.1237     Leak B fit error 0.1237",BODY,BLUE)
    txt(140,1770,"normal fit error 11.4270     so evidence favors a leak, not its exact pipe.",BODY,INK)
    txt(110,1830,"The planner selects MA (15 minutes); MB would take 30 minutes and exceed the 20-minute budget.")
    txt(110,1880,"Fixture returns MA pressure 37.809 m; 15 minutes used, 5 remain. A/B pressure gap: 1.632 m.",SMALL)
    arrow(1975,2020)

    # 5: Re-score + trace
    card((60,2030,1540,2390),PALE_BLUE,7)
    txt(95,2065,"5  Re-score, explain, and save the evidence trail",HEAD,BLUE)
    txt(110,2125,"After MA: Leak A 0.1251 · Leak B 1.7522 · normal 11.3799 (lower fit error is a closer match).")
    txt(110,2180,"Scripted route saves outputs/traces/scripted_trace.json; agent route saves outputs/traces/llm_trace.json.")
    txt(110,2235,"Observed limitation: the latest live-agent run used MA’s reading directly and skipped the final tool call.")
    txt(110,2290,"These are generated benchmark readings: useful for a controlled demo, not field confirmation.",SMALL,ORANGE)
    txt(800,2440,"Python validates tool arguments and enforces the measurement budget · no utility controls are connected",SMALL,INK,"mm")
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    im.save(OUTPUT,optimize=True)
    print(OUTPUT)

if __name__ == "__main__": build()
