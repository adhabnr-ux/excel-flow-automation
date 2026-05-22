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
         leading=1.4):
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
    bg = hexrgb(pal["bg"])
    fg = hexrgb(pal["text"])
    ac = hexrgb(pal["accent"])
    dark_bg = sum(bg) < 384
    dim = tuple(int(a * 0.55 + b * 0.45) for a, b in zip(fg, bg))
    codebg = tuple(min(255, c + 30) for c in bg) if dark_bg else (222, 222, 230)

    # Subtle accent tint for decorative background elements
    if dark_bg:
        ac_subtle = tuple(int(a * 0.38 + b * 0.62) for a, b in zip(ac, bg))
    else:
        ac_subtle = tuple(int(a * 0.10 + b * 0.90) for a, b in zip(ac, bg))

    BAR_W = 10    # left accent bar width (pt)
    BAR_H = 8     # top accent bar height (pt)
    M = 88        # left/right margin from content area edge
    CX = BAR_W + M   # x where content text starts
    CW = S - CX - M  # content text width

    pdf = FPDF(unit="pt", format=(S, S))
    pdf.set_auto_page_break(False)

    for s in spec["slides"]:
        pdf.add_page()
        kind = s.get("kind", "content")

        # ── Background ────────────────────────────────────────────────────────
        pdf.set_fill_color(*bg)
        pdf.rect(0, 0, S, S, "F")

        # ── Top accent bar ────────────────────────────────────────────────────
        pdf.set_fill_color(*ac)
        pdf.rect(0, 0, S, BAR_H, "F")

        # ── Left accent bar ───────────────────────────────────────────────────
        pdf.set_fill_color(*ac)
        pdf.rect(0, BAR_H, BAR_W, S - BAR_H, "F")

        # ══════════════════════════════════════════════════════════════════════
        if kind in ("cover", "close"):
        # ══════════════════════════════════════════════════════════════════════

            # Decorative corner block (top-right) — creates visual energy
            corner = 310
            pdf.set_fill_color(*ac_subtle)
            pdf.rect(S - corner, BAR_H, corner, corner, "F")

            # Second smaller inner corner block for depth
            inner = 180
            inner_color = tuple(int(a * 0.55 + b * 0.45) for a, b in zip(ac_subtle, bg))
            pdf.set_fill_color(*inner_color)
            pdf.rect(S - inner, BAR_H, inner, inner, "F")

            y = 235
            if s.get("header"):
                hc = ac if s.get("header_accent") else dim
                y = draw(pdf, s["header"], CX, y, CW, "B", 34, hc, "C") + 20

            if s.get("title"):
                y = draw(pdf, s["title"], CX, y, CW, "B", 68, fg, "C") + 16

            # Centered accent divider
            if s.get("subtext") or s.get("close_text") or s.get("body"):
                bar_x = CX + (CW - 100) // 2
                pdf.set_fill_color(*ac)
                pdf.rect(bar_x, y, 100, 5, "F")
                y += 28

            if s.get("subtext"):
                y = draw(pdf, s["subtext"], CX, y, CW, "", 34, ac, "C") + 18

            if s.get("body"):
                y = draw(pdf, s["body"], CX, y, CW, "", 30, fg, "C") + 18

            if s.get("close_text"):
                draw(pdf, s["close_text"], CX, y, CW, "", 30, fg, "C")

            if s.get("footer_note"):
                draw(pdf, s["footer_note"], CX, S - 215, CW, "I", 21, dim, "C")

            if s.get("handle"):
                # Separator then handle
                pdf.set_fill_color(*dim)
                pdf.rect(CX, S - 152, CW, 1, "F")
                draw(pdf, s["handle"], CX, S - 140, CW, "B", 28, ac, "C")

        # ══════════════════════════════════════════════════════════════════════
        else:  # content and formula slides
        # ══════════════════════════════════════════════════════════════════════

            y = BAR_H + 108

            if s.get("header"):
                hc = ac if s.get("header_accent") else dim
                y = draw(pdf, s["header"], CX, y, CW, "B", 30, hc, "L") + 8
                # Underline beneath header text
                ul_color = ac if s.get("header_accent") else dim
                pdf.set_fill_color(*ul_color)
                pdf.rect(CX, y, 115, 2, "F")
                y += 22

            if s.get("title"):
                y = draw(pdf, s["title"], CX, y, CW, "B", 54, fg, "L") + 22

            if s.get("code"):
                pdf.set_font("Courier", "", 22)
                clh = 22 * 1.44
                clines = wrap_lines(pdf, san(s["code"]), CW - 66)
                boxh = len(clines) * clh + 38
                # Code block background
                pdf.set_fill_color(*codebg)
                pdf.rect(CX, y, CW, boxh, "F")
                # Accent left border on code block
                pdf.set_fill_color(*ac)
                pdf.rect(CX, y, 5, boxh, "F")
                cy = y + 19
                pdf.set_text_color(*ac)
                for ln in clines:
                    pdf.set_xy(CX + 22, cy)
                    pdf.cell(CW - 30, clh, ln)
                    cy += clh
                y += boxh + 26

            if s.get("body"):
                y = draw(pdf, s["body"], CX, y, CW, "", 30, fg, "L")

            # Slide number badge — accent-colored rectangle, bottom-right
            if s.get("footer"):
                bw, bh = 100, 40
                bx = S - M - bw
                by = S - M - bh + 14
                pdf.set_fill_color(*ac)
                pdf.rect(bx, by, bw, bh, "F")
                pdf.set_font("Helvetica", "B", 22)
                pdf.set_text_color(*bg)
                pdf.set_xy(bx, by + 5)
                pdf.cell(bw, bh - 10, san(s["footer"]), align="C")

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
