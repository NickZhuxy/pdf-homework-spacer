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
```

| Option | What it does |
|---|---|
| `small` / `medium` / `large` | Adds 1 / 2 / 3.5 inches after each question |
| `adaptive` | Quickly skims questions to estimate space, without solving them |
| `print` | Keeps the original paper size; adds pages as needed (default) |
| `tablet` | Makes each original page taller |

You can also request custom space for individual questions. Default: medium spacing, print layout. The agent reviews question boundaries and verifies the output.

## White space only

The original file stays byte-for-byte unchanged. A separate PDF preserves the original questions, equations, figures, and existing whitespace at their original scale. No answers, labels, page numbers, lines, or decorations are added.

The helper stops when it cannot preserve content safely. Links, annotations, forms, outlines, attachments, and layers are currently unsupported. Scans and complex layouts need visual boundary review. Nothing is silently flattened, removed, or rewritten.

## Development

Python 3.10+ and PyMuPDF are required. The PDF helper runs locally with no network or model API calls; adaptive estimates use the agent's current model.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r skills/pdf-homework-spacer/scripts/requirements.txt
python skills/pdf-homework-spacer/scripts/test_space_pdf.py
```

Tests check source hashes, rendered fragment fidelity, blank-only insertions, spacing amounts, and unsafe-input rejection across all preset/layout combinations. Real PDFs also require visual inspection.
