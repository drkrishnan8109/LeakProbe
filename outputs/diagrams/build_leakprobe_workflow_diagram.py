"""Render the current LeakProbe workflow/status diagram as a hand-drawn-style PNG."""
from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "outputs" / "diagrams" / "leakprobe-current-status-hand-drawn.png"
W, H = 1600, 2500
INK = "#12315C"
BLUE = "#1575B8"
TEAL = "#0C7887"
ORANGE = "#CA8311"
GREEN = "#317A45"
PAPER = "#FFFEFA"
PALE_BLUE = "#EAF5FC"
PALE_TEAL = "#E8F6F4"
PALE_ORANGE = "#FFF4DD"
PALE_GREEN = "#EEF7ED"
GRAY = "#52677E"

FONT_REGULAR = "/System/Library/Fonts/Supplemental/ChalkboardSE.ttc"
FONT_BOLD = "/System/Library/Fonts/Supplemental/ChalkboardSE.ttc"
FONT_MARKER = "/System/Library/Fonts/MarkerFelt.ttc"


def font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)


TITLE = font(FONT_MARKER, 76, 1)
SUBTITLE = font(FONT_REGULAR, 34, 1)
SECTION = font(FONT_MARKER, 43, 1)
CARD_TITLE = font(FONT_BOLD, 33, 1)
BODY = font(FONT_REGULAR, 30, 1)
BODY_BOLD = font(FONT_BOLD, 30, 1)
SMALL = font(FONT_REGULAR, 26, 1)
METRIC_SMALL = font(FONT_BOLD, 25, 1)
NUMBER = font(FONT_MARKER, 35, 1)


def text(draw, xy, value, use_font=BODY, fill=INK, anchor=None):
    draw.text(xy, value, font=use_font, fill=fill, anchor=anchor)


def wobbly_box(draw, box, fill, outline, radius=28, width=5, seed=0):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    # Offset echo strokes give the clean vector layout a light marker-sketch edge.
    rng = random.Random(seed)
    echo = (x0 + rng.choice([-3, -2, 2, 3]), y0 + rng.choice([-2, 2]),
            x1 + rng.choice([-3, -2, 2, 3]), y1 + rng.choice([-2, 2]))
    draw.rounded_rectangle(echo, radius=radius, outline=outline, width=2)


def section_header(draw, y, number, title, color):
    draw.ellipse((72, y, 126, y + 54), fill=color, outline=INK, width=2)
    text(draw, (99, y + 27), str(number), NUMBER, "white", anchor="mm")
    text(draw, (147, y + 25), title, SECTION, INK, anchor="lm")


def arrow(draw, x, y0, y1, color=BLUE):
    draw.line((x, y0, x, y1 - 12), fill=color, width=6)
    draw.polygon([(x - 12, y1 - 18), (x + 12, y1 - 18), (x, y1)], fill=color)


def centered_lines(draw, x, y, lines, use_font=BODY, fill=INK, line_gap=42):
    for i, line in enumerate(lines):
        text(draw, (x, y + i * line_gap), line, use_font, fill)


def build():
    image = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(image)

    # Header
    draw.rounded_rectangle((55, 28, 1545, 205), radius=40, fill=PALE_BLUE)
    text(draw, (W // 2, 87), "LeakProbe: current status and next steps", TITLE, INK, anchor="mm")
    text(draw, (W // 2, 157), "How the cases, reference simulations, and evaluation fit together",
         SUBTITLE, BLUE, anchor="mm")

    # Panel 1: distinguish observed cases from candidate reference simulations.
    section_header(draw, 235, 1, "Two different data sets", TEAL)
    wobbly_box(draw, (60, 305, 785, 760), PALE_TEAL, TEAL, seed=1)
    wobbly_box(draw, (815, 305, 1540, 760), PALE_BLUE, BLUE, seed=2)
    text(draw, (92, 345), "CASES: 500 total (current)", CARD_TITLE, TEAL)
    centered_lines(draw, 94, 407, [
        "400 development: 320 leak, 80 normal",
        "100 held-out test: 80 leak, 20 normal",
        "Each case is one noisy six-hour sensor record",
        "with a hidden answer for scoring.",
        "6 hours at 15-minute intervals = 25 time points.",
    ], SMALL, INK, 48)
    text(draw, (847, 345), "REFERENCE PATTERNS: 579 total", CARD_TITLE, BLUE)
    centered_lines(draw, 849, 407, [
        "24 profiles for each of 24 candidate leak pipes",
        "(576 leak profiles) plus 3 normal profiles.",
        "A pattern is a simulated sensor profile for one",
        "scenario and parameter combination, not a case.",
        "Each test case compares 7 pipes x 24 + 3 = 171.",
    ], SMALL, INK, 48)
    text(draw, (800, 784), "Development cases were used to select the dataset-specific rejection cutoffs;", SMALL, GRAY, anchor="mm")
    text(draw, (800, 818), "the detector is a physics-based matcher, not a model trained on those cases.", SMALL, GRAY, anchor="mm")

    arrow(draw, 800, 835, 874)

    # Panel 2: what happens to a held-out case.
    section_header(draw, 887, 2, "How one held-out case gets a decision", BLUE)
    wobbly_box(draw, (60, 958, 1540, 1274), "#FFFFFF", BLUE, seed=3)
    step_y = [1013, 1085, 1157, 1229]
    steps = [
        "Read that test case’s existing pressure and flow data",
        "Compare it with normal and candidate-pipe reference patterns",
        "Rank hypotheses by normalized fit error; lower is better",
        "Reject a weak top leak fit as uncertain, then score it",
    ]
    for i, (y, label) in enumerate(zip(step_y, steps), 1):
        draw.ellipse((92, y - 19, 132, y + 21), fill=PALE_BLUE, outline=BLUE, width=3)
        text(draw, (112, y + 1), str(i), SMALL, BLUE, anchor="mm")
        text(draw, (157, y + 1), label, BODY, INK, anchor="lm")
    text(draw, (800, 1300), "Uncertain is counted as no leak alarm in binary metrics and reported separately.", SMALL, GRAY, anchor="mm")

    arrow(draw, 800, 1324, 1362)

    # Panel 3: held-out result after applying the full-coverage rejection threshold.
    section_header(draw, 1375, 3, "Full observations · 100 held-out cases", ORANGE)
    wobbly_box(draw, (60, 1446, 1540, 1948), PALE_ORANGE, ORANGE, seed=4)
    text(draw, (105, 1480), "With cutoff 64.2958 · confusion matrix", CARD_TITLE, ORANGE)
    # compact 2x2 matrix with readable labels and values
    draw.rounded_rectangle((95, 1530, 905, 1780), radius=18, fill="#FFFFFF", outline=ORANGE, width=3)
    text(draw, (505, 1554), "Predicted leak", SMALL, BLUE, anchor="mm")
    text(draw, (765, 1554), "Predicted normal", SMALL, BLUE, anchor="mm")
    draw.line((110, 1580, 890, 1580), fill=ORANGE, width=2)
    text(draw, (122, 1630), "Actual leak", SMALL, INK, anchor="lm")
    text(draw, (505, 1630), "32 alarmed", BODY_BOLD, GREEN, anchor="mm")
    text(draw, (765, 1630), "48 no alarm", BODY_BOLD, ORANGE, anchor="mm")
    draw.line((110, 1674, 890, 1674), fill=ORANGE, width=2)
    text(draw, (122, 1720), "Actual normal", SMALL, INK, anchor="lm")
    text(draw, (505, 1720), "3 false alarms", BODY_BOLD, ORANGE, anchor="mm")
    text(draw, (765, 1720), "17 no alarm", BODY_BOLD, GREEN, anchor="mm")

    text(draw, (958, 1536), "Detector metrics", CARD_TITLE, ORANGE)
    centered_lines(draw, 958, 1582, [
        "Accuracy: 49%",
        "Precision: 91.4%",
        "Recall: 40%",
        "Specificity: 85%",
        "Balanced accuracy: 62.5%",
        "F1: 55.7%",
        "Uncertain: 38 of 100",
    ], METRIC_SMALL, INK, 29)
    draw.rounded_rectangle((96, 1805, 1504, 1907), radius=18, fill="#FFFDF7", outline=ORANGE, width=3)
    text(draw, (122, 1836), "Before cutoff: 61/80 leaks found, 12/20 normal cases raised alarms; balanced accuracy 58.1%.", SMALL, INK)
    text(draw, (122, 1868), "After cutoff: 32/80 leaks found, 3/20 normal cases raised alarms; balanced accuracy 62.5%.", SMALL, INK)
    text(draw, (800, 1971), "Exact pipe: 41/80 leaks before cutoff, 26/80 after. Sparse cutoff: 5.9836.", SMALL, GRAY, anchor="mm")

    arrow(draw, 800, 1994, 2032)

    # Panel 4: explain the operating tradeoff and next evaluation steps.
    section_header(draw, 2045, 4, "What the result says and what to do next", GREEN)
    wobbly_box(draw, (60, 2115, 785, 2380), PALE_GREEN, GREEN, seed=5)
    wobbly_box(draw, (815, 2115, 1540, 2380), PALE_BLUE, BLUE, seed=6)
    text(draw, (90, 2150), "THRESHOLD TRADE-OFF", CARD_TITLE, GREEN)
    centered_lines(draw, 92, 2204, [
        "False alarms: 12 to 3 of 20 normals.",
        "Detected leaks: 61 to 32 of 80 leaks.",
        "38 cases were marked uncertain.",
        "Fewer alarms, more missed leaks.",
    ], SMALL, INK, 39)
    text(draw, (844, 2150), "NEXT EVALUATION", CARD_TITLE, BLUE)
    centered_lines(draw, 846, 2204, [
        "Compare results across cutoff values.",
        "Choose cutoff using development data only.",
        "Keep held-out cases untouched.",
        "Compare other statistical predictors.",
    ], SMALL, INK, 39)

    # Footer
    text(draw, (800, 2450), "Thresholds are specific to stored data; generated results are not field performance.", SMALL, GRAY, anchor="mm")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, format="PNG", optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    build()
