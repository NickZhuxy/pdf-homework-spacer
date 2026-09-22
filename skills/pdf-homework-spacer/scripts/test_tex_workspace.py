"""Exercise local extraction and real TeX compilation without a conversion API."""
import json
from pathlib import Path
import tempfile
import pymupdf as fitz
from tex_workspace import prepare, compile_tex, sha

FIXTURE = r'''\documentclass{article}
\usepackage{amsmath,amssymb,hyperref}
\begin{document}
\section*{Practice questions}
1. Differentiate $f(x)=x^2$ and explain your steps.
\[
  p_i=\frac{\exp(x_i)}{\sum_{j=1}^{d}\exp(x_j)}
\]
2. Explain the expression above.\footnote{Keep this reference.}
\href{https://example.com}{Course page}
\end{document}
'''


def test():
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        tex=root/'sample.tex';tex.write_text(FIXTURE)
        compile_tex(tex,root/'build','xelatex')
        pdf=root/'build/sample.pdf';before=sha(pdf)
        prepare(pdf,root/'evidence')
        data=json.loads((root/'evidence/evidence.json').read_text())
        assert data['source_sha256']==before==sha(pdf)
        assert len(data['pages'])==1
        assert (root/'evidence/page-001.png').exists()
        assert 'Differentiate' in (root/'evidence/page-001.txt').read_text()
        assert data['pages'][0]['links']
        assert not data['pages'][0]['needs_visual_transcription']
        try:prepare(pdf,root/'evidence')
        except ValueError:pass
        else:raise AssertionError('Must refuse an existing evidence directory')
        bad=root/'bad.tex';bad.write_text(r'\documentclass{article}\begin{document}\undefinedcommand\end{document}')
        try:compile_tex(bad,root/'bad-build','xelatex')
        except ValueError:pass
        else:raise AssertionError('Compilation failure must be reported')
        print('PASS: real TeX compilation, positioned extraction, previews, links, unchanged PDF, overwrite refusal, compiler failure')

if __name__=='__main__':test()
