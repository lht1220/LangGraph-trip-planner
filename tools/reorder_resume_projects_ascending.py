from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree


SOURCE = Path(r"E:\个人资料\李海涛2024220603046.docx")
OUTPUT = Path(
    r"E:\api\LangGraph-trip-planner\output\李海涛2024220603046_项目经历正序版.docx"
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def paragraph_text(paragraph):
    return "".join(paragraph.xpath(".//w:t/text()", namespaces=NS))


def transform(document_xml):
    root = etree.fromstring(document_xml)
    body = root.find("w:body", NS)
    paragraphs = body.findall("w:p", NS)

    expected = {
        30: "项目经验",
        31: "基于 LangGraph 的多智能体旅行规划系统",
        42: "锐通网络穿透 SaaS 平台",
        52: "浙江大学生物实验中心智慧实验室管理平台",
        60: "汉江危化品全流程管理信息系统",
        70: "实习经历",
    }
    for index, marker in expected.items():
        if marker not in paragraph_text(paragraphs[index]):
            raise ValueError(f"Unexpected template structure at paragraph {index}: {marker}")

    agent = paragraphs[31:42]
    ruitong = paragraphs[42:52]
    zhejiang = paragraphs[52:60]
    hanjiang = paragraphs[60:68]
    trailing_spacers = paragraphs[68:70]

    section_break = agent[4]
    if not section_break.xpath("./w:pPr/w:sectPr", namespaces=NS):
        raise ValueError("Expected section break was not found in the first project block")

    # The template's continuous section break belongs after the first project's
    # gray subheading. Move it with that layout role rather than with the Agent
    # project, so the original page architecture remains unchanged.
    ascending = (
        hanjiang[:3]
        + [section_break]
        + hanjiang[3:]
        + zhejiang
        + ruitong
        + agent[:4]
        + agent[5:]
        + trailing_spacers
    )

    old_project_region = paragraphs[31:70]
    insertion_index = body.index(old_project_region[0])
    for paragraph in old_project_region:
        body.remove(paragraph)
    for offset, paragraph in enumerate(ascending):
        body.insert(insertion_index + offset, paragraph)

    return etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        standalone="yes",
    )


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(SOURCE, "r") as source:
        updated_xml = transform(source.read("word/document.xml"))
        with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as target:
            for info in source.infolist():
                data = updated_xml if info.filename == "word/document.xml" else source.read(info.filename)
                target.writestr(info, data)
    print(OUTPUT)


if __name__ == "__main__":
    main()
