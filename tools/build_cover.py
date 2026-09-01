#!/usr/bin/env python3
"""Build the GitHub profile cover banner.

    python3 tools/build_cover.py [--stats] [--refresh] [--date YYYY-MM-DD]

Pipeline: screenshots are pulled from bulnik.dev (cached under assets/src/ and
reused when the site is unreachable), decoded and downscaled with dwebp, inlined
into an SVG as data URIs, and rasterised with rsvg-convert at 2x.

Requires: python3, dwebp (libwebp-tools), rsvg-convert (librsvg2-bin).
"""

import argparse
import base64
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import grid
import layout

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / 'tools'
CACHE = ROOT / 'assets' / 'src'
ICON_CACHE = ROOT / 'assets' / 'icons'
OUT = ROOT / 'assets'

SITE = 'https://bulnik.dev'
SCALE = 2                       # 1280x560 logical -> 2560x1120 delivered

# Five production cases, visually distinct from each other, filling the strip
# edge to edge. Edit this list to change what it shows; the banner never names
# them — keep it at five entries or adjust TILE_W in layout.py to match.
SCREENSHOTS = (
    ('med-platform', '/projects/gallery/analytics-showcase/00.webp',
                     '/projects/gallery/analytics-showcase/00-white.webp'),
    ('tv-adtech', '/projects/gallery/slot-placement/00.webp',
                  '/projects/gallery/slot-placement/00-white.webp'),
    ('marketplace-mvp', '/projects/gallery/voltparts/02.webp',
                        '/projects/gallery/voltparts/02-white.webp'),
    ('ai-editorial', '/projects/gallery/typst-docs/00.webp',
                     '/projects/gallery/typst-docs/00-white.webp'),
    ('smart-parking', '/projects/covers/parking-dashboard.webp',
                      '/projects/covers/parking-dashboard-white.webp'),
)

THEME_INDEX = {'dark': 1, 'light': 2}

# Brand marks come from Simple Icons (CC0); the hexes are the ones that project
# publishes for each brand. Every icon is a single path on a 24x24 canvas.
ICON_SOURCE = 'https://cdn.jsdelivr.net/npm/simple-icons@15/icons/{slug}.svg'
BRAND_COLOURS = {
    'go': '#00ADD8',
    'typescript': '#3178C6',
    'python': '#3776AB',
    'rust': '#000000',
    'kubernetes': '#326CE5',
    'docker': '#2496ED',
    'gitlab': '#FC6D26',
    'postgresql': '#4169E1',
    'solana': '#9945FF',
}


def fetch(url, target, refresh):
    """Download unless cached. A live site is preferred; the cache is the fallback.

    curl rather than urllib: it is present on the runners and here, and it does
    not inherit whatever TLS stack the local Python happens to be built against.
    """
    if target.exists() and not refresh:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ['curl', '-sSfL', '--max-time', '30', '-o', str(target), url],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        if target.exists() and target.stat().st_size:
            print(f'  ! {url} unreachable — using cached copy')
            return target
        target.unlink(missing_ok=True)
        raise SystemExit(f'cannot fetch {url} and no cached copy: {result.stderr.strip()}')
    return target


def data_uri(webp_path, width, height):
    """Decode webp and downscale to the exact device size the tile occupies."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as handle:
        png_path = Path(handle.name)
    try:
        subprocess.run(
            ['dwebp', '-quiet', '-resize', str(width), str(height),
             str(webp_path), '-o', str(png_path)],
            check=True,
        )
        encoded = base64.b64encode(png_path.read_bytes()).decode('ascii')
    finally:
        png_path.unlink(missing_ok=True)
    return f'data:image/png;base64,{encoded}'


def load_icons(refresh):
    """Return {slug: (path_data, brand_colour)} for the technology row."""
    icons = {}
    for slug, colour in BRAND_COLOURS.items():
        cached = fetch(ICON_SOURCE.format(slug=slug),
                       ICON_CACHE / f'{slug}.svg', refresh)
        markup = cached.read_text(encoding='utf-8')
        match = re.search(r'<path[^>]*\sd="([^"]+)"', markup)
        if not match:
            raise SystemExit(f'no path found in {cached}')
        icons[slug] = (match.group(1), colour)
    return icons


def rasterise(svg, destination):
    """Render through rsvg-convert with the vendored fonts made discoverable."""
    with tempfile.TemporaryDirectory() as workdir:
        work = Path(workdir)
        (work / 'fonts').symlink_to(TOOLS / 'fonts')
        svg_path = work / 'cover.svg'
        svg_path.write_text(svg, encoding='utf-8')

        environment = dict(os.environ, XDG_DATA_HOME=str(work))
        subprocess.run(
            ['rsvg-convert',
             '-w', str(layout.CANVAS_W * SCALE),
             '-h', str(layout.CANVAS_H * SCALE),
             '-o', str(destination), str(svg_path)],
            check=True, env=environment,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stats', action='store_true',
                        help='print the activity distribution')
    parser.add_argument('--refresh', action='store_true',
                        help='re-download the screenshots even when cached')
    parser.add_argument('--date', help='pin the last day of the grid (YYYY-MM-DD)')
    arguments = parser.parse_args()

    today = date.fromisoformat(arguments.date) if arguments.date else date.today()
    days, start, end = grid.build(today)

    if arguments.stats:
        summary = grid.stats(days, today)
        print(f'window      {start} .. {end}  ({grid.WEEKS} weeks)')
        print(f'past days   {summary["past_days"]}   future {summary["future_days"]}')
        print(f'total       {summary["total"]}')
        print(f'per day     min {summary["min_per_day"]}  max {summary["max_per_day"]}')
        levels = '  '.join(f'L{lvl} {count}' for lvl, count in summary['levels'].items())
        print(f'levels      {levels}')

    icons = load_icons(arguments.refresh)

    OUT.mkdir(parents=True, exist_ok=True)
    for theme, column in THEME_INDEX.items():
        print(f'building {theme}')
        images = []
        for entry in SCREENSHOTS:
            slug, path = entry[0], entry[column]
            cached = fetch(SITE + path, CACHE / f'{slug}-{theme}.webp', arguments.refresh)
            images.append(data_uri(cached, layout.TILE_W * SCALE, layout.TILE_H * SCALE))

        svg = layout.render(days, images, icons, theme)
        destination = OUT / f'cover-{theme}.png'
        rasterise(svg, destination)
        size_kb = destination.stat().st_size // 1024
        print(f'  -> {destination.relative_to(ROOT)}  '
              f'{layout.CANVAS_W * SCALE}x{layout.CANVAS_H * SCALE}  {size_kb} KB')


if __name__ == '__main__':
    main()
