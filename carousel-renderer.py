#!/usr/bin/env python3
"""Excel Flow carousel renderer.

Renders a carousel_spec object into a square, multi-page PDF suitable for a
LinkedIn native document ("carousel") post.

Usage:
    python3 carousel-renderer.py <spec.json> <output.pdf>

<spec.json> is the `carousel_spec` object taken from a post in the weekly
content JSON. Deterministic: same spec in -> same PDF out. Only dependency is
fpdf2 (pure Python). Uses the built-in Helvetica/Courier core fonts, so no
font files are required anywhere.
"""
import json
import sys

try:
    from fpdf import FPDF
except ImportError:
    sys.exit("ERROR: fpdf2 not installed. Run: pip install fpdf2")


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# Core fonts are latin-1 only; map common Unicode punctuation to safe equivalents.
_SAN = {
    "—": "-", "–": "-", "‑": "-",
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "…": "...", "→": "->", " ": " ", "•": "-",
}


def san(t):
    if not t:
        return ""
    for k, v in _SAN.items():
        t = t.replace(k, v)
    return t.encode("latin-1", "ignore").decode("latin-1")


def wrap_lines(pdf, text, w):
    """Greedy word wrap to width w; respects explicit newlines."""
    out = []
    for para in text.split("\n"):
        if para == "":
            out.append("")
            continue
        line = ""
        for word in para.split(" "):
            trial = word if not line else line + " " + word
            if pdf.get_string_width(trial) <= w or not line:
                line = trial
            else:
                out.append(line)
                line = word
        out.append(line)
    return out


def draw(pdf, text, x, y, w, style, size, color, align="L", family="Helvetica",
         leading=1.35):
    """Draw wrapped text starting at (x, y). Returns the y below the block."""
    pdf.set_font(family, style, size)
    pdf.set_text_color(*color)
    lh = size * leading
    for ln in wrap_lines(pdf, san(text), w):
        pdf.set_xy(x, y)
        pdf.cell(w, lh, ln, align=align)
        y += lh
    return y


def render(spec, out_path):
    S = spec.get("size_px", 1080)
    pal = spec["palette"]
    bg, fg, ac = hexrgb(pal["bg"]), hexrgb(pal["text"]), hexrgb(pal["accent"])
    dark_bg = sum(bg) < 384
    dim = tuple(int(a * 0.55 + b * 0.45) for a, b in zip(fg, bg))
    codebg = tuple(min(255, c + 26) for c in bg) if dark_bg else (236, 236, 240)
    M = 90
    CW = S - 2 * M

    pdf = FPDF(unit="pt", format=(S, S))
    pdf.set_auto_page_break(False)

    for s in spec["slides"]:
        pdf.add_page()
        pdf.set_fill_color(*bg)
        pdf.rect(0, 0, S, S, "F")
        kind = s.get("kind", "content")

        if kind in ("cover", "close"):
            y = 250
            if s.get("header"):
                hc = ac if s.get("header_accent") else dim
                y = draw(pdf, s["header"], M, y, CW, "B", 34, hc, "C") + 26
            if s.get("title"):
                y = draw(pdf, s["title"], M, y, CW, "B", 70, fg, "C") + 28
            if s.get("subtext"):
                y = draw(pdf, s["subtext"], M, y, CW, "", 33, ac, "C") + 20
            if s.get("body"):
                y = draw(pdf, s["body"], M, y, CW, "", 30, fg, "C") + 20
            if s.get("close_text"):
                draw(pdf, s["close_text"], M, y, CW, "", 30, fg, "C")
            if s.get("footer_note"):
                draw(pdf, s["footer_note"], M, S - 210, CW, "I", 21, dim, "C")
            if s.get("handle"):
                draw(pdf, s["handle"], M, S - 135, CW, "B", 24, ac, "C")
        else:
            y = 120
            if s.get("header"):
                hc = ac if s.get("header_accent") else dim
                y = draw(pdf, s["header"], M, y, CW, "B", 34, hc, "L") + 30
            if s.get("title"):
                y = draw(pdf, s["title"], M, y, CW, "B", 54, fg, "L") + 28
            if s.get("code"):
                pdf.set_font("Courier", "", 22)
                clh = 22 * 1.42
                clines = wrap_lines(pdf, san(s["code"]), CW - 48)
                boxh = len(clines) * clh + 36
                pdf.set_fill_color(*codebg)
                pdf.rect(M, y, CW, boxh, "F")
                cy = y + 18
                pdf.set_text_color(*ac)
                for ln in clines:
                    pdf.set_xy(M + 24, cy)
                    pdf.cell(CW - 48, clh, ln)
                    cy += clh
                y += boxh + 30
            if s.get("body"):
                y = draw(pdf, s["body"], M, y, CW, "", 30, fg, "L")
            if s.get("footer"):
                draw(pdf, s["footer"], M, S - 120, CW, "", 26, dim, "L")

    pdf.output(out_path)
    return len(spec["slides"])


def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python3 carousel-renderer.py <spec.json> <output.pdf>")
    with open(sys.argv[1], encoding="utf-8") as f:
        spec = json.load(f)
    n = render(spec, sys.argv[2])
    print(f"OK: rendered {n} slides -> {sys.argv[2]}")


if __name__ == "__main__":
    main()
