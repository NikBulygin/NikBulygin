"""SVG composition for the profile cover.

Two rules drive the layout: the activity grid is the dominant element and the
screenshot strip is a compact accent above it, and the grid area carries nothing
but activity — no project labels, no annotations tying bursts to cases. Project
names live in the README table underneath, not in the banner.

Palette values are lifted from personalpage `app/assets/css/brand-tokens.css`
(`ink` and `white` themes) so the cover and the site read as one design.
"""

from xml.sax.saxutils import escape

CANVAS_W = 1280
CANVAS_H = 560
PAD = 56
RIGHT = CANVAS_W - PAD          # 1224 — every block ends here

# Screenshot strip. Five 16:9 tiles span the content width exactly:
# 5 * 224 + 4 * 12 == 1168 == RIGHT - PAD, so the row ends flush with the grid
# and the legend instead of trailing off into empty canvas.
TILE_W = 224
TILE_H = 126
TILE_GAP = 12
TILE_Y = 160
TILE_R = 8

# Technology row
STACK_Y = 126
ICON_SIZE = 16
ICON_LABEL_GAP = 6
STACK_ITEM_GAP = 20
STACK_FONT = 13
MONO_ADVANCE = 0.6              # JetBrains Mono advances a flat 0.6em per glyph
MIN_ICON_CONTRAST = 1.8         # below this a brand colour vanishes into the background

STACK_ITEMS = (
    ('go', 'Go'),
    ('typescript', 'TypeScript'),
    ('python', 'Python'),
    ('rust', 'Rust'),
    ('kubernetes', 'Kubernetes'),
    ('docker', 'Docker'),
    ('gitlab', 'GitLab'),
    ('postgresql', 'PostgreSQL'),
    ('solana', 'Solana'),
)

# Activity grid. Pitch is chosen so 53 columns land exactly on RIGHT.
GRID_X = 90                     # PAD + room for the weekday labels
GRID_Y = 334
CELL = 16
PITCH = 21.5                    # 90 + 52 * 21.5 + 16 == 1224
CELL_R = 3
LEGEND_Y = 512
MONTH_LABEL_GAP = 3             # columns a month needs to earn its own label

MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')

THEMES = {
    'dark': {
        'bg': '#0a0a0c',
        'border': '#22222a',
        'text': '#f5f5f7',
        'dim': '#a1a1aa',
        'faint': '#8b8b96',
        'accent': '#10b981',
        'empty': '#17171d',
        'ramp': ('#0e4c37', '#15805c', '#10b981', '#6ee7b7'),
    },
    'light': {
        'bg': '#f4f7f6',
        'border': '#d5ded9',
        'text': '#0b1210',
        'dim': '#3d4a44',
        'faint': '#5f6d67',
        'accent': '#047857',
        'empty': '#e2e8e5',
        'ramp': ('#d1fae5', '#6ee7b7', '#10b981', '#047857'),
    },
}

NAME = 'NIKITA BULYGIN'
TITLE = 'Senior Full-Stack Developer · CTO'
SITE = 'bulnik.dev'


def _luminance(colour):
    channels = []
    for offset in (1, 3, 5):
        value = int(colour[offset:offset + 2], 16) / 255
        channels.append(value / 12.92 if value <= 0.04045
                        else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(one, other):
    first, second = _luminance(one), _luminance(other)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


def _num(value):
    """Trim trailing zeros so identical geometry yields identical bytes."""
    text = f'{value:.3f}'.rstrip('0').rstrip('.')
    return text or '0'


def _text(x, y, content, *, size, fill, weight=400, family='Inter', anchor='start',
          spacing=None):
    attrs = [
        f'x="{_num(x)}"', f'y="{_num(y)}"',
        f'font-family="{family}"', f'font-size="{_num(size)}"',
        f'font-weight="{weight}"', f'fill="{fill}"',
    ]
    if anchor != 'start':
        attrs.append(f'text-anchor="{anchor}"')
    if spacing:
        attrs.append(f'letter-spacing="{_num(spacing)}"')
    return f'<text {" ".join(attrs)}>{escape(content)}</text>'


def _month_labels(days, theme):
    """One label per month change, placed on the column that starts it.

    A month that owns fewer than MONTH_LABEL_GAP columns would collide with the
    next label, so it yields to it — otherwise the sliver of the month the
    window opens on prints straight through its successor.
    """
    marks = []
    previous = None
    for column in range(52):
        month = days[column * 7]['date'].month
        if month != previous:
            if marks and column - marks[-1][0] < MONTH_LABEL_GAP:
                marks[-1] = (column, month)
            else:
                marks.append((column, month))
            previous = month

    return [
        _text(GRID_X + column * PITCH, GRID_Y - 10, MONTHS[month - 1],
              size=12, fill=theme['faint'])
        for column, month in marks
    ]


def _grid_cells(days, theme):
    out = []
    for index, day in enumerate(days):
        column, row = divmod(index, 7)
        fill = theme['empty'] if day['level'] == 0 else theme['ramp'][day['level'] - 1]
        x = GRID_X + column * PITCH
        y = GRID_Y + row * PITCH
        out.append(
            f'<rect x="{_num(x)}" y="{_num(y)}" width="{CELL}" height="{CELL}" '
            f'rx="{CELL_R}" fill="{fill}"/>'
        )
    return out


def _legend(theme):
    swatch, gap = 12, 3
    less_w, more_w, pad = 29, 34, 8
    block = 5 * swatch + 4 * gap
    x = RIGHT - (less_w + pad + block + pad + more_w)

    out = [_text(x, LEGEND_Y, 'Less', size=12, fill=theme['faint'])]
    sx = x + less_w + pad
    sy = LEGEND_Y - swatch + 2
    for fill in (theme['empty'],) + tuple(theme['ramp']):
        out.append(
            f'<rect x="{_num(sx)}" y="{_num(sy)}" width="{swatch}" height="{swatch}" '
            f'rx="2.5" fill="{fill}"/>'
        )
        sx += swatch + gap
    out.append(_text(RIGHT, LEGEND_Y, 'More', size=12, fill=theme['faint'],
                     anchor='end'))
    return out


def _stack_row(icons, theme):
    """Brand marks with their names.

    Labels are set in JetBrains Mono, whose advance width is a flat 0.6em, so
    the row lays out arithmetically — no text measurement, and the geometry is
    identical wherever it renders. A brand colour that would disappear into the
    background (Rust's black on the dark theme) falls back to the text colour.
    """
    out = []
    x = PAD
    for slug, label in STACK_ITEMS:
        path, brand = icons[slug]
        colour = brand if _contrast(brand, theme['bg']) >= MIN_ICON_CONTRAST else theme['text']
        scale = ICON_SIZE / 24
        out.append(
            f'<g transform="translate({_num(x)},{_num(STACK_Y - ICON_SIZE + 3)}) '
            f'scale({_num(scale)})"><path d="{path}" fill="{colour}"/></g>'
        )
        x += ICON_SIZE + ICON_LABEL_GAP
        out.append(_text(x, STACK_Y, label, size=STACK_FONT, fill=theme['dim'],
                         family='JetBrains Mono'))
        x += len(label) * STACK_FONT * MONO_ADVANCE + STACK_ITEM_GAP
    return out


def _tiles(images, theme):
    """Screenshot strip: no captions, no project names — just the frames."""
    out = []
    for index, data_uri in enumerate(images):
        x = PAD + index * (TILE_W + TILE_GAP)
        out.append(
            f'<clipPath id="tile{index}">'
            f'<rect x="{x}" y="{TILE_Y}" width="{TILE_W}" height="{TILE_H}" rx="{TILE_R}"/>'
            f'</clipPath>'
        )
        out.append(
            f'<image x="{x}" y="{TILE_Y}" width="{TILE_W}" height="{TILE_H}" '
            f'clip-path="url(#tile{index})" preserveAspectRatio="xMidYMid slice" '
            f'href="{data_uri}"/>'
        )
        out.append(
            f'<rect x="{x}" y="{TILE_Y}" width="{TILE_W}" height="{TILE_H}" rx="{TILE_R}" '
            f'fill="none" stroke="{theme["border"]}" stroke-width="1"/>'
        )
    return out


def render(days, images, icons, theme_name):
    theme = THEMES[theme_name]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{CANVAS_W}" height="{CANVAS_H}" viewBox="0 0 {CANVAS_W} {CANVAS_H}">',
        f'<rect width="{CANVAS_W}" height="{CANVAS_H}" fill="{theme["bg"]}"/>',

        _text(PAD, 64, NAME, size=38, weight=600, fill=theme['text'], spacing=0.5),
        _text(RIGHT, 64, SITE, size=16, weight=500, fill=theme['accent'], anchor='end'),
        _text(PAD, 98, TITLE, size=17, fill=theme['dim']),
    ]
    parts += _stack_row(icons, theme)
    parts += _tiles(images, theme)
    parts += _month_labels(days, theme)

    for row, label in ((1, 'Mon'), (3, 'Wed'), (5, 'Fri')):
        parts.append(_text(GRID_X - 8, GRID_Y + row * PITCH + 12, label,
                           size=12, fill=theme['faint'], anchor='end'))

    parts += _grid_cells(days, theme)
    parts += _legend(theme)
    parts.append('</svg>')
    return '\n'.join(parts)
