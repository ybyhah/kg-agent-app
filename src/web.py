from __future__ import annotations

from flask import jsonify, render_template, request

from .config import AppConfig
from .service import AppService


def build_ui_text():
    return {
        "title": "印人传知识问答系统",
        "eyebrow": "知识图谱大作业 / KG Agent",
        "hero_title": "印人传知识问答系统",
        "hero_intro": (
            "面向《印人传》构建的知识图谱问答原型。"
            "当前页面已经预留普通问答、高级 SPARQL、图谱接入状态和可视化扩展入口，"
            "适合成员 D 持续整合成员 B 的抽取结果与成员 C 的 Turtle 图谱。"
        ),
        "start_query": "开始查询",
        "health": "查看健康状态",
        "ttl_title": "图谱接入状态",
        "ttl_online": "已接入",
        "ttl_offline": "未接入",
        "demo_title": "推荐演示顺序",
        "demo_steps": [
            "先展示普通问答",
            "再展示固定工具查询",
            "最后展示高级 SPARQL",
        ],
        "qa_kicker": "自然语言查询",
        "qa_title": "普通问答",
        "qa_badge": "工作流入口",
        "qa_placeholder": "例如：文彭是谁？",
        "qa_button": "查询",
        "qa_examples": [
            "文彭是谁？",
            "文彭的字是什么？",
            "文彭的号是什么？",
            "文彭的生卒年是什么？",
            "文徵明与文彭是什么关系？",
            "文彭的师承是？",
            "谁开创了吴门印派？",
        ],
        "qa_result_title": "问答结果",
        "qa_result_hint": "展示回答、备注、SPARQL 和结果行",
        "qa_waiting": "请输入问题后开始查询。",
        "member_kicker": "成员 D 提前准备",
        "member_title": "整合重点",
        "member_todos": [
            "先和成员 C 定死命名空间、类名和属性名。",
            "优先把字、号、生卒年、师承、亲属、交游、流派做成固定工具。",
            "为每类高频问题准备 SPARQL 模板，不要一开始全靠模型生成。",
            "把普通问答与高级 SPARQL 页面提前跑通，后续只替换数据源。",
            "人物关系网络可视化放到主链路稳定后再接入。",
        ],
        "sparql_kicker": "结构化查询",
        "sparql_title": "高级 SPARQL",
        "sparql_badge": "适合演示课程技术点",
        "sparql_button": "执行 SPARQL",
        "sparql_result_title": "SPARQL 返回结果",
        "sparql_result_hint": "适合课堂现场展示",
        "sparql_waiting": "请输入 SPARQL 后执行。",
        "showcase_kicker": "示例方向",
        "showcase_title": "建议展示问题",
        "showcases": [
            "人物基础信息：某人的字、号、生卒年",
            "人物关系：父子、师承、交游",
            "流派问题：某人属于什么流派，谁开创了某流派",
            "复杂查询：某人物的关联人物或路径查询",
            "高级查询：直接执行 SPARQL 展示图谱结构",
        ],
        "answer_label": "回答",
        "notes_label": "说明",
        "sparql_label": "SPARQL",
        "rows_label": "结果行",
        "tool_mode": "工具查询",
        "fallback_mode": "回退回答",
        "empty_mode": "空输入",
        "generated_mode": "生成式 SPARQL",
        "tool_error_mode": "工具查询未完成",
        "result_empty": "暂时没有结果行。",
        "result_error": "请求失败，请稍后重试。",
    }


def register_routes(app, config: AppConfig):
    service = AppService(config)
    ui = build_ui_text()

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            ui=ui,
            ttl_status={
                "schema": config.schema_ttl.exists(),
                "core": config.core_ttl.exists(),
                "aligned": config.aligned_ttl.exists(),
            },
        )

    @app.post("/api/query")
    def query():
        payload = request.get_json(silent=True) or {}
        question = str(payload.get("question", "")).strip()
        try:
            result = service.answer_question(question)
            return jsonify(result.model_dump())
        except Exception as exc:
            return (
                jsonify(
                    {
                        "mode": "fallback",
                        "answer": "查询流程执行失败。",
                        "sparql": None,
                        "rows": [],
                        "notes": [str(exc)],
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
            }
        )
