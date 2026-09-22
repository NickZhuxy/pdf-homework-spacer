# PDF Homework Spacer

An agent skill that adds writing space between homework questions—without retyping the questions or changing their appearance.

## Use

Install the `skills/pdf-homework-spacer` folder in your agent's skills directory. For Codex:

```sh
git clone https://github.com/NickZhuxy/pdf-homework-spacer.git
mkdir -p ~/.codex/skills
ln -s "$(pwd)/pdf-homework-spacer/skills/pdf-homework-spacer" ~/.codex/skills/pdf-homework-spacer
```

Attach a PDF and ask:

```text
$pdf-homework-spacer medium
$pdf-homework-spacer adaptive, tablet layout
$pdf-homework-spacer tex
$pdf-homework-spacer adaptive tex
```

| Option | What it does |
|---|---|
| `small` / `medium` / `large` | Adds 1 / 2 / 3.5 inches after each question |
| `adaptive` | Quickly skims questions to estimate space, without solving them |
| `print` | Keeps the original paper size; adds pages as needed (default) |
| `tablet` | Makes each original page taller |

You can also request custom space for individual questions. Default: medium spacing, print layout. The agent reviews question boundaries and verifies the output. The original file stays byte-for-byte unchanged. A separate PDF preserves the original questions, equations, figures, and existing whitespace at their original scale. 

Output files keep the original name with `_spaced` appended before `.pdf`: `Homework 01.pdf` → `Homework 01_spaced.pdf`. Existing files are never overwritten.

Ordinary web, email, internal page links, and named footnote destinations (such as LaTeX `Hfootnote.1`) remain clickable and move with the original content. Annotations and forms still require preservation support.

## Editable LaTeX

Add `tex` to request editable LaTeX and a compiled preview, or use `tex` alone without adding space. The agent reuses matching source when available; otherwise it reconstructs text and equations from PDF extraction and visual inspection. Diagrams may remain original figure assets. This produces editable source, not a guarantee of the original LaTeX or identical layout.

Uses local PyMuPDF, optional Poppler extraction, and an installed TeX engine (XeLaTeX by default). No paid conversion service is required. The original PDF remains untouched. LaTeX files are saved beside the input PDF by default, with the compiled preview in a separate subfolder to prevent overwriting the original.

## Development

Python 3.10+ and PyMuPDF are required. The PDF helper runs locally with no network or model API calls; adaptive estimates use the agent's current model.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r skills/pdf-homework-spacer/scripts/requirements.txt
python skills/pdf-homework-spacer/scripts/test_space_pdf.py
# Optional: requires XeLaTeX
python skills/pdf-homework-spacer/scripts/test_tex_workspace.py
```

Tests check source hashes, rendered fragment fidelity, blank-only insertions, spacing amounts, and unsafe-input rejection across all preset/layout combinations. Real PDFs also require visual inspection.
