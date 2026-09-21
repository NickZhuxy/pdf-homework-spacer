#!/usr/bin/env python3
"""Plan and insert answer space using original PDF vector fragments."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import pymupdf as fitz

SIZES = {'small': 72, 'medium': 144, 'large': 252}
PATTERN = re.compile(r'^\s*(?:(?:Question|Problem|Exercise|Q)\s*\d+\b|\d{1,2}[.)]\s+)', re.I)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_source(path):
    doc = fitz.open(path)
    if doc.needs_pass:
        raise ValueError('Encrypted PDF: provide an unlocked copy.')
    if doc.get_toc() or doc.embfile_count() or doc.get_ocgs():
        raise ValueError('Outlines, attachments or layers are unsupported; refusing to discard source features.')
    for page in doc:
        if page.rotation:
            page.remove_rotation()
        if list(page.annots() or []) or list(page.widgets() or []) or page.get_links():
            raise ValueError('Links, annotations or forms are unsupported; refusing to remove or flatten source content.')
    return doc


def blank_rows(page):
    # 144 dpi catches thin rules, math and image ink; coordinates are PDF points.
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csGRAY, alpha=False, annots=False)
    samples = pix.samples
    return [min(samples[y * pix.stride:y * pix.stride + pix.width]) == 255 for y in range(pix.height)]


def safe(rows, y):
    k = round(y * 2)
    return 3 <= k < len(rows) - 3 and all(rows[k - 3:k + 4])


def snap(rows, y, radius=18):
    candidates = [k / 2 for k in range(max(3, int((y-radius)*2)), min(len(rows)-3, int((y+radius)*2)+1)) if safe(rows, k / 2)]
    if not candidates:
        raise ValueError(f'No clear horizontal cut near y={y:.1f}; review the page layout.')
    return min(candidates, key=lambda v: abs(v-y))


def inspect(path, size):
    doc = load_source(path)
    pages, warnings = [], []
    for page in doc:
        lines = []
        for b in page.get_text('dict')['blocks']:
            for line in b.get('lines', []):
                text = ''.join(s['text'] for s in line['spans'])
                lines.append({'text': text, 'bbox': list(line['bbox'])})
        lines.sort(key=lambda l: (l['bbox'][1], l['bbox'][0]))
        starts = [l for l in lines if PATTERN.match(l['text'])]
        # Multiple columns need semantic ordering, not horizontal strips.
        if starts and max(l['bbox'][0] for l in starts)-min(l['bbox'][0] for l in starts) > page.rect.width * .18:
            warnings.append(f'Page {page.number+1}: possible columns or inconsistent indentation.')
        if not starts:
            warnings.append(f'Page {page.number+1}: no recognized question starts; inspect scan/continuation/unnumbered content.')
        rows = blank_rows(page)
        inserts = []
        for start in starts[1:]:
            try:
                y = snap(rows, start['bbox'][1]-5, radius=8)
                if y >= start['bbox'][1]:
                    raise ValueError('Boundary falls inside the next question.')
                inserts.append({'after_y': y, 'space_pt': SIZES[size], 'label': 'Before '+start['text'][:70]})
            except ValueError as e:
                warnings.append(f'Page {page.number+1}: {e}')
        if starts:
            ink = [i for i, white in enumerate(rows) if not white]
            # Includes any footer. Agent must move this boundary before footer if appropriate.
            last = (max(ink)+1)/2 if ink else 0
            if last+5 < page.rect.height-3:
                inserts.append({'after_y': snap(rows, last+5, radius=3), 'space_pt': SIZES[size], 'label': 'End of page: verify question ends here, not on next page'})
            else:
                warnings.append(f'Page {page.number+1}: no bottom cut; add a reviewed endpoint.')
        pages.append({'page': page.number+1, 'width': page.rect.width, 'height': page.rect.height, 'insertions': inserts, 'lines': lines})
    return {'version': 1, 'source_sha256': digest(path), 'mode': 'uniform', 'size': size,
            'reviewed': False, 'warnings': warnings, 'pages': pages}


def build(source, plan_path, output, layout):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError('Choose a new output path; source and existing outputs are never overwritten.')
    map_path = output.with_suffix('.map.json')
    if map_path.exists() or map_path.resolve() in {source.resolve(), output.resolve(), Path(plan_path).resolve()}:
        raise ValueError('QA map path must be new and distinct from source, plan and output.')
    source_hash = digest(source)
    plan = json.loads(Path(plan_path).read_text())
    if plan['source_sha256'] != digest(source):
        raise ValueError('Plan belongs to a different source PDF.')
    if not plan.get('reviewed'):
        raise ValueError('Review question boundaries and warnings, then set reviewed=true in the plan.')
    src = load_source(source)
    if [p['page'] for p in plan['pages']] != list(range(1, len(src)+1)):
        raise ValueError('Plan must cover every source page exactly once, in order.')
    dst = fitz.open()
    mappings, gaps = [], []
    for spec, page in zip(plan['pages'], src):
        w, h = page.rect.width, page.rect.height
        rows = blank_rows(page)
        inserts = spec['insertions']
        last = 0
        for ins in inserts:
            y, amount = float(ins['after_y']), float(ins['space_pt'])
            if not (math.isfinite(y) and math.isfinite(amount) and last < y < h and 0 <= amount <= 7200):
                raise ValueError('Invalid, unordered, or excessive insertion.')
            if not safe(rows, y):
                raise ValueError(f'Page {page.number+1}: cut y={y} crosses visible ink.')
            last = y
        out_h = h + sum(i['space_pt'] for i in inserts) if layout == 'tablet' else h
        if out_h > 14400:
            raise ValueError('Tablet page exceeds 200 inches. Use print layout.')
        out = dst.new_page(width=w, height=out_h)
        cursor = 0.0

        def new_page():
            nonlocal out, cursor
            out = dst.new_page(width=w, height=out_h)
            cursor = 0.0

        def put_strip(top, bottom, reserve=0):
            nonlocal cursor
            # Keep a short answer area with the prompt whenever the entire fragment fits.
            if cursor and bottom-top+reserve <= out_h and bottom-top+reserve > out_h-cursor:
                new_page()
            while bottom-top > .001:
                available = out_h-cursor
                if available < 8:
                    new_page()
                    available = out_h
                end = min(bottom, top+available)
                if end < bottom-.001:
                    cuts = [k/2 for k in range(int((top+8)*2), min(len(rows)-3, int(end*2))) if safe(rows,k/2)]
                    if not cuts:
                        if cursor:
                            new_page()
                            continue
                        raise ValueError('An unbroken figure exceeds the paper height; use tablet layout or a larger page.')
                    end = max(cuts)
                clip = fitz.Rect(0, top, w, end)
                rect = fitz.Rect(0, cursor, w, cursor+end-top)
                # Blank source strips have no contents to copy.
                if page.get_contents():
                    out.show_pdf_page(rect, src, page.number, clip=clip)
                mappings.append({'source_page': page.number+1, 'source_rect': list(clip), 'output_page': out.number+1, 'output_rect': list(rect)})
                cursor += end-top
                top = end
                if top < bottom-.001:
                    new_page()

        top = 0.0
        for ins in inserts:
            boundary, amount = float(ins['after_y']), float(ins['space_pt'])
            put_strip(top, boundary, min(amount, 48))
            remaining = amount
            while remaining > .001:
                if out_h-cursor < .001:
                    new_page()
                take = min(remaining, out_h-cursor)
                gaps.append({'output_page': out.number+1, 'rect': [0,cursor,w,cursor+take], 'label': ins.get('label','')})
                cursor += take
                remaining -= take
            top = boundary
        put_strip(top, h)
    # Full visible source coverage, at original scale, is the invariant; extraction
    # can include hidden text from clipped Form XObjects and is not proof of fidelity.
    for p in src:
        fragments = [m for m in mappings if m['source_page']==p.number+1]
        assert abs(fragments[0]['source_rect'][1]) < .01
        assert abs(fragments[-1]['source_rect'][3]-p.rect.height)<.01
        for a,b in zip(fragments,fragments[1:]):
            assert abs(a['source_rect'][3]-b['source_rect'][1])<.01
    if digest(source) != source_hash:
        raise ValueError('Source changed during processing; refusing to publish output.')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental overwrite, including symlink targets.
    with output.open('xb') as stream:
        stream.write(dst.tobytes(garbage=4, deflate=True))
    report = {'source_sha256': source_hash, 'source_unchanged': digest(source)==source_hash, 'output_pages': len(dst), 'layout': layout, 'fragments': mappings, 'answer_spaces': gaps}
    with map_path.open('x') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({'output': str(output), 'pages': len(dst), 'coverage': 'complete', 'visual_review': 'required'}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('plan')
    p.add_argument('source'); p.add_argument('plan')
    p.add_argument('--size', choices=SIZES, default='medium')
    p = sub.add_parser('build')
    p.add_argument('source'); p.add_argument('plan'); p.add_argument('output')
    p.add_argument('--layout', choices=['print','tablet'], default='print')
    args = parser.parse_args()
    if args.command == 'plan':
        if Path(args.plan).exists():
            raise ValueError('Plan already exists; choose a new path.')
        Path(args.plan).write_text(json.dumps(inspect(args.source,args.size),indent=2))
        print(args.plan)
    else:
        build(args.source,args.plan,args.output,args.layout)

if __name__ == '__main__':
    main()
