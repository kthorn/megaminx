"""Puzzle-agnostic booklet framework, shared by the megaminx and kilominx
guides. Pure presentation helpers (SVG embedding, banners, page chrome) plus
the HTML/PDF build driver. No puzzle-specific content lives here."""
import pathlib
from minx import puzzle as P

FACE_LETTER_COLORS = {
    'U': '#1565d8', 'F': '#0fa84e', 'R': '#e02020', 'L': '#ff8a00',
    'D': '#7b2fbe', 'BR': '#1565d8', 'BL': '#1565d8',
}


def svg_img(svg, cls='pic', w=None):
    import base64
    b64 = base64.b64encode(svg.encode()).decode()
    style = f' style="width:{w}"' if w else ''
    return f'<img class="{cls}" src="data:image/svg+xml;base64,{b64}"{style}/>'


def expand_alg(alg):
    """'R U2i Ri' -> [('R',1),('U',-1),('U',-1),('R',-1)] as (token,click)."""
    out = []
    for name, times in P.parse_alg(alg):
        step = 1 if times > 0 else -1
        for _ in range(abs(times)):
            out.append((name, step))
    return out


def display_letter(token, click):
    t = 'D' if token == 'DR' else token
    return t + ('i' if click < 0 else '')


def goal_box(inner, caption='Your Goal'):
    return (f'<div class="goal">{inner}'
            f'<div class="goalstar">{caption}</div></div>')


def banner(stage, title):
    return (f'<div class="topbar"><div class="stagebadge">STAGE {stage}:</div>'
            f'<div class="banner">{title}</div></div>')


def holding(text, puzzle_name='Megaminx'):
    return (f'<div class="holding"><span class="holdhead">Holding Your '
            f'{puzzle_name}:</span> {text}</div>')


def tips(items):
    lis = ''.join(f'<li>{i}</li>' for i in items)
    return f'<div class="tips"><span class="tiphead">Tips:</span><ul>{lis}</ul></div>'


def congrats(text):
    return (f'<div class="congrats"><div class="congratsbanner">'
            f'Congratulations!</div><div class="congratsbody">{text}</div></div>')


def F(letter):
    col = FACE_LETTER_COLORS.get(letter.rstrip('i'), '#1565d8')
    return f'<span class="facelet" style="color:{col}">({letter})</span>'


def colorword(word, color):
    return f'<span style="color:{color};font-weight:800">{word}</span>'


def build_html(pages, root):
    """Assemble the full HTML document string (no weasyprint). The `\n` after
    the <meta> tag reproduces make_guide.py's original wrapper exactly, so the
    extracted megaminx HTML stays byte-identical."""
    css = (pathlib.Path(root) / 'build' / 'guide.css').read_text()
    return ('<!DOCTYPE html><html><head><meta charset="utf-8">\n'
            f'<style>{css}</style></head><body>{"".join(pages)}</body></html>')


def render_booklet(pages, out_dir, stem, root):
    """Write <stem>.html and (via weasyprint) <stem>.pdf into out_dir."""
    html = build_html(pages, root)
    (out_dir / f'{stem}.html').write_text(html)
    import weasyprint
    weasyprint.HTML(string=html, base_url=str(root)).write_pdf(
        out_dir / f'{stem}.pdf')
    print(f"wrote {out_dir / f'{stem}.pdf'} ({len(pages)} pages)")
    return html
