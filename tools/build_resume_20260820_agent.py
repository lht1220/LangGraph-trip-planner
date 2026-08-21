from copy import deepcopy
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree


REFERENCE = Path(r"E:\个人资料\李海涛2024220603046.docx")
OUTPUT = Path(r"E:\api\LangGraph-trip-planner\output\李海涛_20260820_AI_Agent开发工程师_优化版.docx")

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


def clear_run_text(run):
    for child in list(run):
        if child.tag in {qn("w:t"), qn("w:tab"), qn("w:br"), qn("w:cr")}:
            run.remove(child)


def set_run_text(run, text):
    clear_run_text(run)
    node = etree.Element(qn("w:t"))
    node.set(XML_SPACE, "preserve")
    node.text = text
    run.append(node)


def set_simple_text(paragraph, text):
    paragraph_runs = runs(paragraph)
    if not paragraph_runs:
        paragraph_runs = [etree.SubElement(paragraph, qn("w:r"))]
    for run in paragraph_runs:
        clear_run_text(run)
    set_run_text(paragraph_runs[0], text)


def make_simple(template, text):
    paragraph = deepcopy(template)
    set_simple_text(paragraph, text)
    return paragraph


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
    set_run_text(paragraph_runs[1], text)
    return paragraph


def make_labeled_bullet(template, label, text):
    paragraph = deepcopy(template)
    paragraph_runs = runs(paragraph)
    for run in paragraph_runs:
        clear_run_text(run)
    set_run_text(paragraph_runs[0], label)
    set_run_text(paragraph_runs[1], text)
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


def update_target_role(root):
    text_nodes = root.xpath("//w:t", namespaces=NS)
    replaced = 0
    for index, node in enumerate(text_nodes[:-1]):
        if node.text == "AI Agent开发工程师/Java后" and text_nodes[index + 1].text == "端工程师":
            node.text = "AI Agent / AI应用开发工程师"
            text_nodes[index + 1].text = ""
            replaced += 1
    if replaced != 2:
        raise RuntimeError(f"Expected two duplicated target-role slots, found {replaced}")


def transform(document_xml):
    root = etree.fromstring(document_xml)
    update_target_role(root)

    body = root.find("w:body", NS)
    paragraphs = direct_paragraphs(body)
    if len(paragraphs) != 87:
        raise RuntimeError(f"Unexpected reference paragraph count: {len(paragraphs)}")

    skill_heading = paragraphs[15]
    skill_line = paragraphs[16]
    blank_a = paragraphs[23]
    blank_b = paragraphs[24]
    skills = [
        make_skill_heading(skill_heading, "AI Agent 与大模型应用开发"),
        make_numbered_skill(skill_line, 1, "熟悉 Python、FastAPI、Pydantic，具备 Agent 应用服务化与接口集成能力。"),
        make_numbered_skill(skill_line, 2, "熟悉 LangGraph / LangChain，掌握 StateGraph、State、Node、Edge、Reducer，具备多 Agent Workflow 编排实践。"),
        make_numbered_skill(skill_line, 3, "熟悉 Tool Calling、Structured Output 与 MCP 工具接入，能够完成参数生成、调用及结果处理。"),
        make_numbered_skill(skill_line, 4, "了解 RAG、Embedding、向量检索、Agent Memory、Context Engineering、异常重试与 Fallback 等方案。"),
        make_numbered_skill(skill_line, 5, "熟练使用 AI Coding 工具辅助需求拆解、编码、重构与调试，并通过人工 Review、测试与边界检查保障代码质量。"),
        deepcopy(blank_a),
        make_skill_heading(skill_heading, "后端工程与业务落地"),
        make_numbered_skill(skill_line, 1, "熟练使用 Java，熟悉 Spring Boot、MyBatis、MySQL、Redis，具备独立搭建项目与接口开发能力。"),
        make_numbered_skill(skill_line, 2, "具备需求分析、领域建模、数据库设计、业务状态流、RESTful API 到上线维护的完整项目经验。"),
        make_numbered_skill(skill_line, 3, "能够处理权限、多角色协同、资源分配、状态一致性、异常场景与数据追溯，并完成第三方服务和硬件终端集成。"),
        make_numbered_skill(skill_line, 4, "熟悉 Linux、Git、前后端联调与服务器部署，具备线上问题排查和存量系统维护经验。"),
        deepcopy(blank_b),
    ]
    replace_range(body, paragraphs, 15, 27, skills)

    # Preserve the original project components and move the continuous section
    # break to the first (Agent) project's gray subheading.
    section_break = deepcopy(paragraphs[34])
    regular_blank = deepcopy(paragraphs[39])
    bullet_template = paragraphs[35]

    agent = [
        deepcopy(paragraphs[58]),
        deepcopy(paragraphs[59]),
        deepcopy(paragraphs[60]),
        make_simple(paragraphs[61], "Agent Workflow 与工程化落地："),
        section_break,
        make_simple(bullet_template, "基于 LangGraph StateGraph 编排景点、天气、酒店和规划 4 个 Agent，将独立检索任务拆分为并行分支，并通过 Join 节点汇聚结果；"),
        make_simple(bullet_template, "以 Typed State 管理请求、检索结果、规划结果和异常信息，通过 Reducer 处理并行节点的状态更新与错误传播；"),
        make_simple(bullet_template, "基于 MCP 与 langchain-mcp-adapters 接入高德地图 POI、天气等工具，使 Agent 按上下文完成 Tool Calling、参数生成和结果处理；"),
        make_simple(bullet_template, "使用 FastAPI + Pydantic 服务化封装工作流，并抽象 OpenAI Compatible 模型层，支持模型与服务地址切换；"),
        make_simple(bullet_template, "结合 Haversine 距离、最近邻策略和规则评分完成路线后处理，并通过 Vue3 实现行程展示与交互调整。"),
        deepcopy(paragraphs[67]),
    ]

    zhejiang = [
        deepcopy(paragraphs[40]),
        deepcopy(paragraphs[41]),
        make_simple(paragraphs[42], "业务建模与多端协同："),
        make_simple(bullet_template, "负责试剂、耗材、申领流转与审核模块的数据模型和业务流程设计，覆盖入库、申领、领用、归还等核心场景；"),
        make_simple(bullet_template, "构建多角色业务状态流，处理权限控制、状态一致性、异常分支与全流程追溯，支撑统计、审计和安全管控；"),
        make_simple(bullet_template, "面向 Android 一体机设计领用、归还和入库接口，与 RFID / 扫码现场流程联动，完成 Web、终端与后台接口协同。"),
        deepcopy(paragraphs[47]),
    ]

    ruitong = [
        deepcopy(paragraphs[48]),
        deepcopy(paragraphs[49]),
        deepcopy(paragraphs[50]),
        make_simple(paragraphs[51], "核心业务与系统集成："),
        make_simple(bullet_template, "参与用户、会员、映射管理和服务器资源分配等核心模块设计，负责数据模型、业务流程及后端接口开发；"),
        make_simple(bullet_template, "设计端口映射与服务器资源分配逻辑，并集成支付宝支付，处理订单创建、异步回调、会员权益更新与状态一致性；"),
        make_simple(bullet_template, "基于阿里云开放能力实现 DNS 解析自动增删与 OSS 文件存储，打通自定义域名和映射服务配置流程；"),
        make_simple(bullet_template, "完成部分运营后台、关键操作日志与业务追溯功能，并负责 Linux 部署及运行问题排查。"),
        deepcopy(paragraphs[57]),
    ]

    hanjiang = [
        deepcopy(paragraphs[31]),
        deepcopy(paragraphs[32]),
        make_simple(paragraphs[33], "业务流程与现场终端协同："),
        make_simple(bullet_template, "负责化学试剂管理模块后端开发，参与业务表结构与接口字段设计，支撑入库、领用、归还、盘库等全生命周期流程；"),
        make_simple(bullet_template, "实现试剂二维码动态生成与 Web 打印任务，对接打印设备完成标签打印和唯一标识管理；"),
        make_simple(bullet_template, "参与 Android 端人脸识别登录、接口联调与异常排查，保障 Web、后台和现场终端的数据协同。"),
        regular_blank,
    ]
    replace_range(body, paragraphs, 31, 67, agent + zhejiang + ruitong + hanjiang)

    # Keep the internship header layout but replace the role label only.
    internship_header_runs = runs(paragraphs[71])
    set_run_text(internship_header_runs[7], "  业务系统开发")

    internship_template = paragraphs[72]
    internship = [
        make_labeled_bullet(
            internship_template,
            "业务系统设计与工程落地：",
            "参与实验室管理、设备管理、考试系统等企业级项目，从需求分析、领域建模、业务流程设计到 API 实现和上线维护，具备将实际需求转化为可落地系统的完整经验。",
        ),
        make_labeled_bullet(
            internship_template,
            "业务建模与状态管理：",
            "根据实际场景设计领域对象、数据库结构和业务状态流，处理多角色流转、权限、数据一致性、追溯与异常分支。",
        ),
        make_labeled_bullet(
            internship_template,
            "系统集成与多端协同：",
            "负责 Web、Android 一体机、第三方硬件与后台服务的接口联调，实践支付宝、人脸识别、RFID / 扫码和打印设备接入。",
        ),
        make_labeled_bullet(
            internship_template,
            "工程交付与质量保障：",
            "参与存量系统升级、线上问题排查与 Linux 部署，重视日志、异常场景、接口边界和可维护性，保障系统稳定交付。",
        ),
    ]
    replace_range(body, paragraphs, 72, 75, internship)

    profiles = [
        make_simple(paragraphs[84], "计算机技术硕士，具备 1.5 年企业级业务系统开发经验，能够将需求转化为领域模型、状态流、服务接口与可落地系统。"),
        make_simple(paragraphs[84], "熟悉 Python、LangGraph、MCP、Tool Calling 与 FastAPI，能够完成 Agent Workflow 设计、外部工具集成及 AI 应用服务化落地。"),
        make_simple(paragraphs[84], "持续实践 AI-assisted Development，善于使用 AI Coding 工具提升需求拆解、编码与调试效率，并通过人工 Review、测试和边界场景验证保障交付质量。"),
    ]
    replace_range(body, paragraphs, 84, 86, profiles)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes")


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(REFERENCE, "r") as source:
        updated_xml = transform(source.read("word/document.xml"))
        with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as target:
            for info in source.infolist():
                data = updated_xml if info.filename == "word/document.xml" else source.read(info.filename)
                target.writestr(info, data)
    print(OUTPUT)


if __name__ == "__main__":
    main()
