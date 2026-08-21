import json
import sys
from pathlib import Path
from zipfile import ZipFile

from docx import Document
from docx.oxml.ns import qn


def main():
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    doc = Document(source)
    rows = []
    for i, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text.replace("\t", "↹").replace("\n", " / ")
        p_pr = paragraph._p.pPr
        shading = ""
        num_pr = False
        section_break = False
        if p_pr is not None:
            shd = p_pr.find(qn("w:shd"))
            if shd is not None:
                shading = shd.get(qn("w:fill"), "")
            num_pr = p_pr.find(qn("w:numPr")) is not None
            section_break = p_pr.find(qn("w:sectPr")) is not None
        run = paragraph.runs[0] if paragraph.runs else None
        rows.append(
            {
                "index": i,
                "style": paragraph.style.name,
                "text": text,
                "shading": shading,
                "numbering": num_pr,
                "section_break": section_break,
                "alignment": str(paragraph.alignment),
                "left_indent_pt": paragraph.paragraph_format.left_indent.pt if paragraph.paragraph_format.left_indent else None,
                "right_indent_pt": paragraph.paragraph_format.right_indent.pt if paragraph.paragraph_format.right_indent else None,
                "first_line_indent_pt": paragraph.paragraph_format.first_line_indent.pt if paragraph.paragraph_format.first_line_indent else None,
                "space_before_pt": paragraph.paragraph_format.space_before.pt if paragraph.paragraph_format.space_before else None,
                "space_after_pt": paragraph.paragraph_format.space_after.pt if paragraph.paragraph_format.space_after else None,
                "line_spacing": str(paragraph.paragraph_format.line_spacing),
                "first_run_font": run.font.name if run else None,
                "first_run_size_pt": run.font.size.pt if run and run.font.size else None,
                "first_run_bold": run.bold if run else None,
                "first_run_color": str(run.font.color.rgb) if run and run.font.color and run.font.color.rgb else None,
            }
        )

    with ZipFile(source) as archive:
        parts = [
            {"path": info.filename, "size": info.file_size, "crc": f"{info.CRC:08X}"}
            for info in archive.infolist()
        ]

    payload = {
        "source": str(source),
        "sections": len(doc.sections),
        "paragraphs": rows,
        "package_parts": parts,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for row in rows:
        if row["text"].strip() or row["index"] < 6:
            print(
                f"{row['index']:03d}|{row['style']}|sh={row['shading']}|"
                f"num={'Y' if row['numbering'] else ''}|sect={'Y' if row['section_break'] else ''}|"
                f"font={row['first_run_font']}|size={row['first_run_size_pt']}|"
                f"bold={row['first_run_bold']}|{row['text']}"
            )


if __name__ == "__main__":
    main()
