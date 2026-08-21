from copy import deepcopy
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree


REFERENCE = Path(r"E:\api\LangGraph-trip-planner\tmp\resume_template_edit\reference-最新版本.docx")
OUTPUT = Path(r"E:\api\LangGraph-trip-planner\output\李海涛_Java后端_AI能力增强_项目时间倒序版.docx")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def qn(tag):
    prefix, local = tag.split(":")
    return f"{{{NS[prefix]}}}{local}"


def direct_paragraphs(body):
    return [child for child in body if child.tag == qn("w:p")]


def runs(paragraph):
    return paragraph.xpath("./w:r", namespaces=NS)


def set_run_text(run, text):
    for child in list(run):
        if child.tag in {qn("w:t"), qn("w:tab"), qn("w:br"), qn("w:cr")}:
            run.remove(child)
    text_node = etree.Element(qn("w:t"))
    text_node.set(XML_SPACE, "preserve")
    text_node.text = text
    run.append(text_node)


def clear_run_text(run):
    for child in list(run):
        if child.tag in {qn("w:t"), qn("w:tab"), qn("w:br"), qn("w:cr")}:
            run.remove(child)


def set_simple_text(paragraph, text):
    paragraph_runs = runs(paragraph)
    if not paragraph_runs:
        new_run = etree.Element(qn("w:r"))
        paragraph.append(new_run)
        paragraph_runs = [new_run]
    for run in paragraph_runs:
        clear_run_text(run)
    set_run_text(paragraph_runs[0], text)


def set_segments(paragraph, segments):
    paragraph_runs = runs(paragraph)
    for run in paragraph_runs:
        clear_run_text(run)
    for index, text in segments.items():
        if index >= len(paragraph_runs):
            raise IndexError(f"Run {index} missing in template paragraph")
        set_run_text(paragraph_runs[index], text)


def make_skill_heading(template, label):
    paragraph = deepcopy(template)
    paragraph_runs = runs(paragraph)
    for run in paragraph_runs:
        clear_run_text(run)
    set_run_text(paragraph_runs[0], "• ")
    set_run_text(paragraph_runs[-1], label)
    return paragraph


def make_numbered_skill(template, number, text):
    paragraph = deepcopy(template)
    paragraph_runs = runs(paragraph)
    for run in paragraph_runs:
        clear_run_text(run)
    set_run_text(paragraph_runs[0], f"{number}.  ")
    target = paragraph_runs[1] if len(paragraph_runs) > 1 else paragraph_runs[0]
    set_run_text(target, text)
    return paragraph


def make_project_header(template, date, title, role, left_gap=10, right_gap=10):
    paragraph = deepcopy(template)
    paragraph_runs = runs(paragraph)
    for run in paragraph_runs:
        clear_run_text(run)
    # Reuse the template's date/title/role run colors and weights.
    set_run_text(paragraph_runs[0], date + (" " * left_gap))
    set_run_text(paragraph_runs[9], title + (" " * right_gap))
    set_run_text(paragraph_runs[12], role)
    return paragraph


def make_label_line(template, label, text):
    paragraph = deepcopy(template)
    paragraph_runs = runs(paragraph)
    for run in paragraph_runs:
        clear_run_text(run)
    set_run_text(paragraph_runs[0], label)
    target = paragraph_runs[1] if len(paragraph_runs) > 1 else paragraph_runs[0]
    set_run_text(target, text)
    return paragraph


def make_simple(template, text):
    paragraph = deepcopy(template)
    set_simple_text(paragraph, text)
    return paragraph


def make_labeled_bullet(template, label, text):
    paragraph = deepcopy(template)
    paragraph_runs = runs(paragraph)
    for run in paragraph_runs:
        clear_run_text(run)
    set_run_text(paragraph_runs[0], label)
    target = paragraph_runs[1] if len(paragraph_runs) > 1 else paragraph_runs[0]
    set_run_text(target, text)
    return paragraph


def replace_range(body, original_paragraphs, start, end, replacements):
    first = original_paragraphs[start]
    insertion_index = list(body).index(first)
    for index in range(start, end + 1):
        paragraph = original_paragraphs[index]
        if paragraph.getparent() is body:
            body.remove(paragraph)
    for offset, paragraph in enumerate(replacements):
        body.insert(insertion_index + offset, paragraph)


def set_page_break_before(paragraph):
    p_pr = paragraph.find("w:pPr", NS)
    if p_pr is None:
        p_pr = etree.Element(qn("w:pPr"))
        paragraph.insert(0, p_pr)
    if p_pr.find("w:pageBreakBefore", NS) is None:
        p_pr.append(etree.Element(qn("w:pageBreakBefore")))


def build_project_block(
    templates,
    *,
    date,
    title,
    role,
    stack,
    headings_and_bullets,
    address=None,
    gaps=(10, 10),
    section_break_after_first_heading=None,
):
    block = [
        make_project_header(templates["header"], date, title, role, gaps[0], gaps[1]),
        make_label_line(templates["tech"], "技术栈：", stack),
    ]
    if address:
        block.append(make_label_line(templates["address"], "项目地址：", address))
    for heading_index, (heading, bullet_texts) in enumerate(headings_and_bullets):
        block.append(make_simple(templates["subheading"], heading))
        if heading_index == 0 and section_break_after_first_heading is not None:
            block.append(deepcopy(section_break_after_first_heading))
        for bullet in bullet_texts:
            block.append(make_simple(templates["bullet"], bullet))
    block.append(deepcopy(templates["blank"]))
    return block


def transform(document_xml):
    root = etree.fromstring(document_xml)
    body = root.find("w:body", NS)
    paragraphs = direct_paragraphs(body)
    if len(paragraphs) < 118:
        raise RuntimeError(f"Unexpected template paragraph count: {len(paragraphs)}")

    # Keep education format, only shorten course text for readability.
    set_segments(
        paragraphs[8],
        {0: "主修课程：", 1: "机器学习与应用实践、人工智能、程序设计理论与方法、图像理解与分析、数值分析等。"},
    )
    set_segments(
        paragraphs[11],
        {0: "主修课程：", 1: "数据结构与算法、Java Web、数据库原理、计算机网络、计算机组成原理等。"},
    )

    skill_heading = paragraphs[15]
    skill_line = paragraphs[16]
    blank_a = paragraphs[23]
    blank_b = paragraphs[24]
    skills = [
        make_skill_heading(skill_heading, "后端与业务工程能力"),
        make_numbered_skill(skill_line, 1, "熟练使用 Java，具备良好的编码、调试与问题定位习惯。"),
        make_numbered_skill(skill_line, 2, "熟悉 Spring Boot、MyBatis、MySQL、Redis 等后端技术栈，能够独立完成项目搭建与接口开发。"),
        make_numbered_skill(skill_line, 3, "具备从需求分析、领域对象与数据库设计，到业务状态流、RESTful API 和上线维护的完整项目经验。"),
        make_numbered_skill(skill_line, 4, "具备复杂业务流程与多端协同经验，能够处理权限控制、状态一致性、异常场景和数据可追溯问题。"),
        make_numbered_skill(skill_line, 5, "具备支付宝、阿里云 OSS / DNS、人脸识别、RFID、打印设备等第三方服务与硬件集成经验。"),
        make_numbered_skill(skill_line, 6, "熟悉 Linux、Git、前后端联调与服务器部署，具备线上问题排查和存量系统维护经验。"),
        make_numbered_skill(skill_line, 7, "了解 RabbitMQ、Elasticsearch 等中间件，以及缓存、异步处理和常见性能优化思路。"),
        deepcopy(blank_a),
        deepcopy(blank_b),
        make_skill_heading(skill_heading, "AI Agent 与全栈扩展"),
        make_numbered_skill(skill_line, 1, "熟悉 Python、FastAPI、Pydantic；具备基于 LangGraph / LangChain 设计 Agent Workflow、State、并行节点与 Tool Calling 的项目实践。"),
        make_numbered_skill(skill_line, 2, "了解 MCP、RAG、Embedding、Structured Output、Agent Memory 等方案；可将外部服务接入 Agent，并使用 Vue3 / TypeScript 完成应用联调。"),
    ]
    replace_range(body, paragraphs, 15, 27, skills)

    templates = {
        "header": paragraphs[31],
        "tech": paragraphs[32],
        "address": paragraphs[79],
        "subheading": paragraphs[34],
        "bullet": paragraphs[36],
        # Paragraph 35 carries the template's hidden section break; use a
        # visually equivalent ordinary spacer so the original 3-section
        # document architecture is preserved.
        "blank": paragraphs[53],
    }
    projects = []
    projects += build_project_block(
        templates,
        date="2026-03 ~ 至今",
        title="基于 LangGraph 的多智能体旅行规划系统",
        role="AI应用、后端开发",
        stack="Python、LangGraph、LangChain、MCP、FastAPI、Pydantic、Vue3、TypeScript、高德地图 API",
        address="https://github.com/lht1220/LangGraph-trip-planner",
        gaps=(5, 4),
        section_break_after_first_heading=paragraphs[35],
        headings_and_bullets=[
            (
                "Agent 工作流与工具调用",
                [
                    "基于 LangGraph StateGraph 编排景点、天气、酒店和规划 4 个 Agent，将独立检索任务重构为并行分支，并通过 Join 节点汇聚结果；",
                    "以 Typed State 管理请求、检索结果、规划结果和异常信息，通过 Reducer 处理并行节点的状态更新与错误传播；",
                    "基于 MCP 与 langchain-mcp-adapters 接入高德地图 POI、天气等工具，使 Agent 按上下文自主完成 Tool Calling；",
                    "使用 FastAPI + Pydantic 服务化封装工作流，并抽象 OpenAI Compatible 模型层，支持模型与服务地址切换；",
                    "结合 Haversine 距离、最近邻策略和规则评分完成路线后处理，并通过 Vue3 实现行程展示与交互调整。",
                ],
            )
        ],
    )
    projects += build_project_block(
        templates,
        date="2025-11 ~ 至今",
        title="锐通网络穿透 SaaS 平台",
        role="Java后端、前端",
        stack="Java、Spring Boot、MyBatis、MySQL、Redis、Vue、Linux、支付宝、阿里云 OSS / DNS",
        address="https://nexoraweb.com.cn/",
        gaps=(10, 10),
        headings_and_bullets=[
            (
                "核心业务与系统集成",
                [
                    "参与用户、会员、映射管理和服务器资源分配等核心模块设计，负责数据模型、业务流程及后端接口开发；",
                    "参与端口映射及服务器资源分配逻辑，根据用户服务配置管理服务器与端口资源，保障映射资源有效分配；",
                    "集成支付宝支付，完成订单创建、异步回调、会员权益更新及支付状态一致性处理；",
                    "基于阿里云开放能力实现 DNS 解析自动增删与 OSS 文件存储，打通自定义域名和映射服务配置流程；",
                    "独立完成部分运营后台、关键操作日志与业务追溯功能，并负责 Linux 部署及运行问题排查。",
                ],
            )
        ],
    )
    projects += build_project_block(
        templates,
        date="2025-04 ~ 2025-08",
        title="浙江大学生物实验中心智慧实验室管理平台",
        role="Java后端开发",
        stack="Java、Spring Boot、Spring Security、MyBatis、MySQL、Redis、Android、RFID",
        gaps=(4, 4),
        headings_and_bullets=[
            (
                "业务建模与多端协同",
                [
                    "负责试剂、耗材、申领流转与审核模块的数据模型和业务流程设计；",
                    "围绕入库、申领、领用、归还等场景构建多角色业务状态流，保障数据一致性与全流程可追溯；",
                    "面向 Android 一体机设计试剂领用、归还和入库接口，与 RFID / 扫码现场操作流程联动；",
                    "参与 Spring Security 权限控制、Web / 终端 / 后台接口联调及异常问题排查，支撑统计、审计和安全管控。",
                ],
            )
        ],
    )
    projects += build_project_block(
        templates,
        date="2024-07 ~ 2024-11",
        title="汉江危化品全流程管理信息系统",
        role="Java后端、终端协同",
        stack="Java、Spring Boot、MyBatis、MySQL、Redis、RESTful API、Android、Linux",
        gaps=(6, 6),
        headings_and_bullets=[
            (
                "业务流程与现场终端协同",
                [
                    "负责化学试剂管理模块后端开发，参与业务表结构与接口字段设计，支撑入库、领用、归还、盘库等全生命周期流程；",
                    "实现试剂数据 Excel 批量导入与导出，提升后台数据维护、统计和盘库效率；",
                    "实现 Web 端打印任务与试剂二维码动态生成，对接打印机完成标签打印和唯一标识管理；",
                    "参与 Android 端人脸识别登录、接口联调与异常问题排查，保障 Web、后台和现场终端的数据协同。",
                ],
            )
        ],
    )
    replace_range(body, paragraphs, 31, 95, projects)

    # These were empty gray continuation rows belonging to the removed
    # original project block. They have no content and should not survive as
    # a large blank band between projects and internship.
    for index in (96, 97):
        if paragraphs[index].getparent() is body:
            body.remove(paragraphs[index])

    internship_template = paragraphs[102]
    internship = [
        make_labeled_bullet(
            internship_template,
            "企业级后端开发：",
            "深度参与实验室管理、设备管理、考试系统等项目，从需求分析、数据模型、RESTful API 到上线维护，主要负责 Java 后端与核心业务流程。",
        ),
        make_labeled_bullet(
            internship_template,
            "业务建模与状态管理：",
            "根据实际需求完成领域对象、数据库结构和业务状态流设计，处理多角色流转、数据一致性、追溯和异常场景。",
        ),
        make_labeled_bullet(
            internship_template,
            "多端协同与外部集成：",
            "负责 Web、Android 一体机、第三方硬件与后台服务的接口联调，实践支付宝、人脸识别、RFID / 扫码和打印设备接入。",
        ),
        make_labeled_bullet(
            internship_template,
            "维护交付与能力延伸：",
            "参与存量系统升级、历史问题排查和 Linux 部署，并将业务编排与系统集成经验延伸到 Python / Agent 应用开发。",
        ),
    ]
    replace_range(body, paragraphs, 102, 105, internship)

    # Keep the internship icon and heading together at the start of page 3.
    set_page_break_before(paragraphs[99])

    profile_template = paragraphs[114]
    profiles = [
        make_simple(profile_template, "以 Java 后端和业务系统开发为核心，具备从需求分析、数据建模、业务流程设计到接口实现和上线维护的完整经验。"),
        make_simple(profile_template, "擅长将复杂业务拆分为可维护的领域对象、状态流与服务接口，具备第三方服务、硬件终端和多端系统协同经验。"),
        make_simple(profile_template, "在传统后端能力基础上，具备 Python、LangGraph、MCP 与 Tool Calling 项目实践，能够参与 Agent 业务功能的设计与开发。"),
    ]
    replace_range(body, paragraphs, 114, 117, profiles)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes")


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(REFERENCE, "r") as source:
        document_xml = source.read("word/document.xml")
        updated_xml = transform(document_xml)
        with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as target:
            for info in source.infolist():
                data = updated_xml if info.filename == "word/document.xml" else source.read(info.filename)
                target.writestr(info, data)
    print(OUTPUT)


if __name__ == "__main__":
    main()
