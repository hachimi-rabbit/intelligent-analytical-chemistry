"""Apply the reviewed wording and notes to the existing reproducible slide builder.

The checked-in JSON keeps evidence corrections visible and in one place. Each
replacement must occur exactly once on its slide, so changed upstream results
cannot silently retain a stale textual summary.
"""
import json
from pathlib import Path


def apply_report_evidence(prs):
    spec = json.loads(Path(__file__).with_name('report_evidence.json').read_text())
    if len(prs.slides) != spec['expected_slide_count']:
        raise ValueError('Review slide count before applying evidence corrections')
    for item in spec['slides']:
        slide = prs.slides[item['number'] - 1]
        frames = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                frames.append(shape.text_frame)
            if shape.has_table:
                frames.extend(cell.text_frame for row in shape.table.rows for cell in row.cells)
            if shape.has_chart and shape.chart.has_title:
                frames.append(shape.chart.chart_title.text_frame)
        for old, new in item['replacements']:
            runs = [r for f in frames for p in f.paragraphs for r in p.runs if old in r.text]
            if sum(r.text.count(old) for r in runs) != 1:
                raise ValueError(f'Review slide {item["number"]}: expected one occurrence of {old!r}')
            runs[0].text = runs[0].text.replace(old, new)
        slide.notes_slide.notes_text_frame.text = item['notes']
