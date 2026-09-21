"""Synthetic regression checks; run with Python in a temporary directory."""
import json
import tempfile
from pathlib import Path
import pymupdf as fitz
from space_pdf import inspect, build, load_source, digest


def test():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        source = root/'source.pdf'
        doc = fitz.open()
        p = doc.new_page(width=612,height=792)
        for y, text in [(48,'Practice problems'),(100,'1. Explain the meaning of the derivative.'),(190,'2. Sketch the curve and label its intercepts.'),(350,'3. Prove the stated identity. Give each step.')]:
            p.insert_text((48,y),text,fontsize=12)
        p.draw_rect(fitz.Rect(60,210,260,315))
        p.draw_line((60,315),(250,220))
        p.insert_text((290,770),'1')
        doc.save(source)
        original_hash = digest(source)
        for size in ['small','medium','large']:
            plan = inspect(source,size)
            assert len(plan['pages'][0]['insertions'])==3
            # Put final gap before the footer for this known fixture.
            plan['pages'][0]['insertions'][-1]['after_y']=370
            plan['reviewed']=True
            plan_path=root/(size+'.json')
            plan_path.write_text(json.dumps(plan))
            for layout in ['print','tablet']:
                out=root/(size+'-'+layout+'.pdf')
                build(source,plan_path,out,layout)
                assert digest(source)==original_hash
                result=fitz.open(out)
                mapping=json.loads(out.with_suffix('.map.json').read_text())
                src=fitz.open(source)
                for frag in mapping['fragments']:
                    assert frag['output_page'] is not None
                    a=src[frag['source_page']-1].get_pixmap(matrix=fitz.Matrix(2,2),clip=fitz.Rect(frag['source_rect']),alpha=False)
                    b=result[frag['output_page']-1].get_pixmap(matrix=fitz.Matrix(2,2),clip=fitz.Rect(frag['output_rect']),alpha=False)
                    assert (a.width,a.height)==(b.width,b.height)
                    aa,bb=a.samples,b.samples
                    error=sum(abs(x-y)>20 for x,y in zip(aa,bb))/len(aa)
                    assert error < .005, (layout,size,error)
                for gap in mapping['answer_spaces']:
                    pix = result[gap['output_page']-1].get_pixmap(clip=fitz.Rect(gap['rect']), colorspace=fitz.csGRAY, alpha=False)
                    assert min(pix.samples)==255, 'Added regions must be purely white'
                assert sum(g['rect'][3]-g['rect'][1] for g in mapping['answer_spaces'])==3*{'small':72,'medium':144,'large':252}[size]
                if layout=='print':
                    assert all(p.rect.height==792 for p in result)
                else:
                    assert len(result)==1
        # Unsafe cuts, unreviewed plans and altered source bindings must fail.
        valid=json.loads(plan_path.read_text())
        for change in ['ink','review','hash']:
            bad=json.loads(json.dumps(valid))
            if change=='ink': bad['pages'][0]['insertions'][0]['after_y']=95
            if change=='review': bad['reviewed']=False
            if change=='hash': bad['source_sha256']='incorrect'
            bad_path=root/'bad.json'; bad_path.write_text(json.dumps(bad))
            try:
                build(source,bad_path,root/(change+'.pdf'),'print')
            except ValueError:
                pass
            else:
                raise AssertionError('Expected rejection: '+change)
        # A scanned source has no inferred numbering; keep it for visual planning.
        scan=fitz.open(); scan.new_page().insert_image(fitz.Rect(0,0,612,792),stream=doc[0].get_pixmap().tobytes('png'))
        scan.save(root/'scan.pdf')
        assert inspect(root/'scan.pdf','medium')['warnings']
        # Existing handwriting may not disappear silently.
        annotated=fitz.open(source); annotated[0].add_text_annot((30,30),'Keep this')
        annotated.save(root/'annotated.pdf')
        try:
            load_source(root/'annotated.pdf')
        except ValueError:
            pass
        else:
            raise AssertionError('Annotations must be surfaced')
        linked=fitz.open(source)
        linked[0].insert_link({'kind':fitz.LINK_URI, 'from':fitz.Rect(48,85,300,105), 'uri':'https://example.com'})
        linked.save(root/'linked.pdf')
        try:
            load_source(root/'linked.pdf')
        except ValueError:
            pass
        else:
            raise AssertionError('Links may not be silently dropped')
        try:
            build(source,plan_path,source,'print')
        except ValueError:
            pass
        else:
            raise AssertionError('Source overwrite must be rejected')
        assert digest(source)==original_hash
        rotated=fitz.open(source); rotated[0].set_rotation(90); rotated.save(root/'rotated.pdf')
        normalized=load_source(root/'rotated.pdf')
        assert normalized[0].rotation==0
        assert normalized[0].rect.width==792
        print('PASS: all sizes/layouts, rendered fragment fidelity, gap totals, guardrails, scan, annotations, links, rotation, source hash, blank-only insertions')

if __name__=='__main__':
    test()
