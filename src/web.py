from __future__ import annotations

from flask import jsonify, render_template, request

from .config import AppConfig
from .service import AppService


def build_deliverable_status(config: AppConfig):
    return {
        "member_a": {
            "raw_text_dir": config.raw_text_dir.exists(),
            "clean_text_dir": config.clean_text_dir.exists(),
            "chapter_split_json": config.chapter_split_json.exists(),
            "person_passages_json": config.person_passages_json.exists(),
        },
        "member_b": {
            "entities_json": config.entities_json.exists(),
            "relations_json": config.relations_json.exists(),
            "extraction_prompts_md": config.extraction_prompts_md.exists(),
            "evaluation_samples_json": config.evaluation_samples_json.exists(),
        },
        "member_c": {
            "schema_ttl": config.schema_ttl.exists(),
            "core_ttl": config.core_ttl.exists(),
            "aligned_ttl": config.aligned_ttl.exists(),
            "alignment_rules_md": config.alignment_rules_md.exists(),
            "ontology_explanations_json": config.ontology_explanations_json.exists(),
        },
        "member_d": {
            "query_tools_py": (config.base_dir / "src" / "tools.py").exists(),
            "sparql_examples_md": config.sparql_examples_md.exists(),
            "frontend_html": (config.templates_dir / "index.html").exists(),
            "frontend_css": (config.static_dir / "styles.css").exists(),
            "demo_script_md": config.demo_script_md.exists(),
        },
    }


def build_ui_text():
    return {
        "title": "印人传知识图谱智能体",
        "eyebrow": "Seal Lineage Knowledge Agent",
        "hero_title": "印人传知识图谱智能体",
        "hero_script": "古籍抽取 · 图谱建模 · 智能问答",
        "hero_quote": "让人物传记、关系规则与结构化图谱在同一幅知识长卷中并置呈现，让查询、追踪与分析拥有清晰的来路。",
        "hero_intro": (
            "这是一个围绕《印人传》构建的知识图谱智能体。"
            "首页集中展示我们如何把古籍文本整理为人物记录，如何通过人工规则与 AI 协同完成抽取、"
            "RDF/Turtle 建模、实体对齐与 LangGraph 问答，再把结果落到关系网络与图结构分析中。"
        ),
        "hero_primary": "开始查询",
        "hero_secondary": "进入图谱查询",
        "nav_home": "概览",
        "nav_qa": "智能问答",
        "nav_sparql": "图谱查询",
        "nav_network": "关系网络",
        "nav_analysis": "图结构分析",
        "hero_cards": [
            {
                "title": "人工规则骨架",
                "text": "抽取 Schema、数据清洗、关系分类与消歧规则先行，保证知识图谱不是黑盒生成。",
            },
            {
                "title": "图谱问答链路",
                "text": "固定工具、few-shot SPARQL 与 fallback 组成 LangGraph 工作流，让自然语言问题落到可执行查询。",
            },
            {
                "title": "可视化分析面板",
                "text": "关系网络图、本体解释与图结构分析联动展示，让人物、流派与关系脉络被直接看见。",
            },
        ],
        "qa_kicker": "自然语言问答",
        "qa_title": "智能问答",
        "qa_badge": "本地图谱优先",
        "qa_placeholder": "例如：文彭的号是什么？",
        "qa_button": "查询",
        "qa_examples": [
            {
                "question": "文彭的字和号是什么？",
                "route": "tool",
                "description": "测试固定工具：get_courtesy_and_art_name",
            },
            {
                "question": "吴门印派代表人物有哪些？",
                "route": "generated_sparql",
                "description": "测试生成式 SPARQL：流派代表人物复杂查询",
            },
            {
                "question": "比较文彭与丁敬的篆刻理论差异。",
                "route": "fallback",
                "description": "测试开放式问题直接进入 fallback，由大模型生成谨慎回答",
            },
        ],
        "qa_result_hint": "系统会优先依据本地知识图谱返回结果。",
        "qa_waiting": "请输入问题并开始查询。",
        "qa_history_title": "历史查询",
        "qa_history_empty": "这里会保留本次会话中的问题记录。",
        "qa_chat_intro": "你好，这里会优先根据本地知识图谱回答问题，并同步展示对应的查询链路。",
        "qa_examples_title": "示例问题",
        "qa_examples_hint": "保留 3 条可演示链路：固定工具、生成式 SPARQL、失败后 fallback。",
        "qa_notes_label": "链路说明",
        "qa_answer_label": "图谱回答",
        "qa_user_label": "当前问题",
        "qa_trace_title": "查询轨迹",
        "qa_trace_hint": "右侧保留本次问答的链路、SPARQL 与结果表。",
        "qa_input_hint": "按 Enter 发送问题",
        "qa_clear_history": "清空记录",
        "runtime_status_label": "模型状态",
        "runtime_reference_label": "参考模式",
        "runtime_reference_on": "已开启",
        "runtime_reference_off": "已关闭",
        "runtime_llm_disabled": "当前未启用大模型链路",
        "runtime_llm_enabled": "问答增强已启用",
        "reference_toggle_on": "开启参考模式",
        "reference_toggle_off": "关闭参考模式",
        "graph_conclusion_label": "图谱结论",
        "model_reference_label": "模型参考说明",
        "notes_label": "补充说明",
        "route_label": "当前链路",
        "route_stage_label": "执行阶段",
        "sparql_label": "SPARQL",
        "rows_label": "结果表",
        "query_descriptions": {
            "tool": "当前回答由 function calling 触发固定工具，并由模型基于工具结果组织。",
            "generated_sparql": "当前回答由生成式 SPARQL 查询链路返回。",
            "tool_error": "固定工具未稳定命中，系统已转入后续图谱链路。",
            "fallback": "工具链与 SPARQL 链均未稳定返回结果，系统进入谨慎说明。",
            "empty": "等待查询。",
        },
        "graph_kicker": "结构化探索",
        "graph_title": "图谱查询台",
        "graph_badge": "SPARQL",
        "graph_intro": "适合需要直接查看结构化三元组查询结果时使用。",
        "graph_button": "执行查询",
        "graph_result_title": "查询结果",
        "graph_result_hint": "在下方查看返回表格与执行信息。",
        "graph_waiting": "请输入 SPARQL 后执行查询。",
        "network_kicker": "关系可视化",
        "network_title": "人物关系网络",
        "network_badge": "Network",
        "network_intro": "支持全量人物图谱浏览、中心人物扩展、关系类型筛选、节点详情查看，以及与图结构分析结果联动高亮。",
        "network_from_qa": "从问答结果生成",
        "network_from_sparql": "从图谱结果生成",
        "network_load_full": "加载全量图谱",
        "network_expand_person": "按人物扩展",
        "network_center_placeholder": "输入人物名，如：文彭",
        "network_hop_one": "一跳",
        "network_hop_two": "两跳",
        "network_filter_label": "关系筛选",
        "network_empty": "当前还没有可用于构图的关系数据，请先查询人物关系或流派信息。",
        "network_too_small": "当前结果过少，暂时无法形成可读的关系网络。",
        "network_canvas_title": "网络预览",
        "network_meta_title": "图数据摘要",
        "network_format_title": "节点与边数据",
        "network_format_hint": "此处展示前端当前使用的关系网络数据结构。",
        "network_detail_title": "节点详情",
        "network_detail_empty": "点击图中的人物或流派节点后，在这里查看详情。",
        "network_relation_teacher": "师承",
        "network_relation_family": "亲属",
        "network_relation_social": "交游",
        "network_relation_school": "所属流派",
        "network_relation_founder": "开创流派",
        "analysis_kicker": "图结构分析",
        "analysis_title": "图谱分析面板",
        "analysis_badge": "Bonus",
        "analysis_intro": "基于当前本地图谱中的人物关系与流派关系，展示中心性分析、社区发现、路径分析与流派演变线索。",
        "analysis_refresh": "刷新分析",
        "analysis_path_button": "分析路径",
        "analysis_path_placeholder_a": "起点人物，例如：文徵明",
        "analysis_path_placeholder_b": "终点人物，例如：文彭",
        "analysis_waiting": "点击刷新后载入图结构分析结果。",
        "tool_mode": "固定工具",
        "fallback_mode": "fallback",
        "empty_mode": "等待查询",
        "generated_mode": "生成式 SPARQL",
        "tool_error_mode": "继续检索",
        "result_empty": "暂无结果。",
        "result_error": "请求失败，请稍后重试。",
    }


def register_routes(app, config: AppConfig):
    # 使用预加载的服务单例
    service = app.config.get("APP_SERVICE")
    if service is None:
        # 如果没有预加载，创建新实例
        service = AppService(config)

    ui = build_ui_text()

    @app.get("/")
    def index():
        initial_network_graph = {
            "ok": True,
            "nodes": [],
            "edges": [],
            "meta": {
                "mode": "",
                "center": "",
                "hop": 0,
                "nodeCount": 0,
                "edgeCount": 0,
                "relationTypes": [],
                "note": "关系网络改为页面渲染后再异步加载，避免首页首屏阻塞。",
            },
        }
        return render_template(
            "index.html",
            ui=ui,
            runtime_status=service.get_runtime_status(),
            initial_network_graph=initial_network_graph,
        )

    @app.post("/api/query")
    def query():
        payload = request.get_json(silent=True) or {}
        question = str(payload.get("question", "")).strip()
        try:
            result = service.answer_question(question)
            return jsonify(result.model_dump())
        except Exception as exc:
            import traceback
            error_detail = str(exc)
            # 检查是否是API认证错误
            if "401" in error_detail or "Incorrect API key" in error_detail:
                error_detail = f"API密钥验证失败：{error_detail}\n请检查 .env 文件中的 DEEPSEEK_API_KEY 是否正确。"
            return (
                jsonify(
                    {
                        "mode": "fallback",
                        "answer": "查询流程执行失败。",
                        "sparql": None,
                        "rows": [],
                        "notes": [error_detail, traceback.format_exc()],
                        "route_label": "fallback",
                        "route_stage": "请求处理异常",
                    }
                ),
                500,
            )

    @app.post("/api/sparql")
    def sparql():
        payload = request.get_json(silent=True) or {}
        sparql_text = str(payload.get("sparql", "")).strip()
        if not sparql_text:
            return jsonify({"ok": False, "error": "SPARQL 不能为空。"}), 400

        try:
            result = service.run_sparql(sparql_text)
            return jsonify(
                {
                    "ok": True,
                    "sparql": result.sparql,
                    "rows": result.rows,
                    "note": result.note,
                }
            )
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.get("/api/graph-analysis")
    def graph_analysis():
        try:
            return jsonify({"ok": True, "data": service.get_graph_analysis()})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.get("/api/graph-explore")
    def graph_explore():
        center = str(request.args.get("center", "")).strip()
        hop = request.args.get("hop", default=1, type=int) or 1
        full_view = str(request.args.get("full_view", "")).strip().lower() in {"1", "true", "yes", "on"}
        relation_types = request.args.getlist("relation_type")
        try:
            return jsonify(
                {
                    "ok": True,
                    "data": service.get_graph_exploration(
                        center=center,
                        hop=hop,
                        relation_types=relation_types,
                        full_view=full_view,
                    ),
                }
            )
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.get("/api/person-detail")
    def person_detail():
        person_name = str(request.args.get("name", "")).strip()
        if not person_name:
            return jsonify({"ok": False, "error": "人物名不能为空。"}), 400
        try:
            return jsonify(service.get_person_detail(person_name))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.get("/api/runtime-status")
    def runtime_status():
        return jsonify({"ok": True, "data": service.get_runtime_status()})

    @app.post("/api/reference-mode")
    def reference_mode():
        payload = request.get_json(silent=True) or {}
        enabled = bool(payload.get("enabled", False))
        try:
            return jsonify({"ok": True, "data": service.set_reference_mode(enabled)})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.post("/api/graph-path")
    def graph_path():
        payload = request.get_json(silent=True) or {}
        source_name = str(payload.get("source_name", "")).strip()
        target_name = str(payload.get("target_name", "")).strip()
        try:
            result = service.find_person_path(source_name, target_name)
            return jsonify(result)
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.get("/api/tools")
    def tools():
        return jsonify(
            {
                "ok": True,
                "course_overview": service.get_course_overview(),
                "tools": service.list_tools(),
            }
        )

    @app.get("/api/health")
    def health():
        return jsonify(
            {
                "ok": True,
                "ttl_files": {
                    "schema": config.schema_ttl.exists(),
                    "core": config.core_ttl.exists(),
                    "aligned": config.aligned_ttl.exists(),
                },
                "ontology_explanations": config.ontology_explanations_json.exists(),
                "deliverables": build_deliverable_status(config),
            }
        )
