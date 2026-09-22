#!/usr/bin/env python3
"""Prepare PDF evidence for agent-assisted LaTeX reconstruction; compile reviewed TeX."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import pymupdf as fitz


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(source, directory):
    source, directory = Path(source).resolve(), Path(directory).resolve()
    if directory.exists():
        raise ValueError('Use a fresh evidence directory; existing files are never overwritten.')
    before = sha(source)
    doc = fitz.open(source)
    if doc.needs_pass:
        raise ValueError('An unlocked PDF is required.')
    directory.mkdir(parents=True)
    pages = []
    for index, page in enumerate(doc):
        # JSON preserves spans/fonts/positions and links for reconstruction; no solving.
        blocks = page.get_text('dict', flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)['blocks']
        preview = f'page-{index+1:03}.png'
        page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(directory/preview)
        text = page.get_text(sort=True)
        (directory/f'page-{index+1:03}.txt').write_text(text)
        pages.append({'page':index+1, 'size':list(page.rect), 'rotation':page.rotation,
                      'blocks':blocks, 'links':page.get_links(), 'preview':preview,
                      'needs_visual_transcription':not text.strip()})
    pdftotext = shutil.which('pdftotext')
    if pdftotext:
        subprocess.run([pdftotext,'-layout',str(source),str(directory/'layout.txt')],check=True)
    if sha(source)!=before:
        raise ValueError('Source changed during evidence extraction.')
    manifest={'source_sha256':before, 'pages':pages, 'tools':{
        name:shutil.which(name) for name in ('pdftotext','latexmk','xelatex','lualatex','pdflatex')}}
    (directory/'evidence.json').write_text(json.dumps(manifest,indent=2,default=lambda x:list(x)))
    print(json.dumps({'evidence':str(directory),'pages':len(doc),'source_unchanged':True}))


def compile_tex(source, directory, engine):
    source, directory = Path(source).resolve(), Path(directory).resolve()
    if directory.exists():
        raise ValueError('Use a fresh build directory to protect previous results.')
    binary=shutil.which(engine)
    if binary is None:
        raise ValueError(f'{engine} is not installed. Deliver source as uncompiled, or install a TeX distribution.')
    directory.mkdir(parents=True)
    # Run only agent-reviewed source. Disabling shell escape is not a full sandbox.
    command=[binary,'-no-shell-escape','-interaction=nonstopmode','-halt-on-error',
             '-file-line-error',f'-output-directory={directory}',str(source)]
    for _ in range(2):
        result=subprocess.run(command,cwd=source.parent,capture_output=True,text=True,timeout=120)
        (directory/'compiler-output.txt').write_text(result.stdout+result.stderr)
        if result.returncode:
            raise ValueError(f'Compilation failed; inspect {directory / "compiler-output.txt"}')
    log=(directory/(source.stem+'.log')).read_text(errors='replace')
    warnings=[line for line in log.splitlines() if any(term in line for term in
              ('Overfull','Missing character','undefined','LaTeX Warning'))]
    pdf=directory/(source.stem+'.pdf')
    if not pdf.exists():
        raise ValueError('Compiler did not produce a PDF.')
    print(json.dumps({'pdf':str(pdf),'warnings':warnings,'visual_review':'required'}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('source');p.add_argument('directory')
    p=sub.add_parser('compile');p.add_argument('source');p.add_argument('directory')
    p.add_argument('--engine',choices=['xelatex','lualatex','pdflatex'],default='xelatex')
    args=parser.parse_args()
    if args.command=='prepare':prepare(args.source,args.directory)
    else:compile_tex(args.source,args.directory,args.engine)

if __name__=='__main__':main()
