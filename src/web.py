from __future__ import annotations

from flask import jsonify, render_template, request

from .config import AppConfig
from .service import AppService


def build_ui_text():
    return {
        "title": "\u5370\u4eba\u4f20\u77e5\u8bc6\u95ee\u7b54\u7cfb\u7edf",
        "eyebrow": "\u77e5\u8bc6\u56fe\u8c31\u5927\u4f5c\u4e1a / KG Agent",
        "hero_title": "\u5370\u4eba\u4f20\u77e5\u8bc6\u95ee\u7b54\u7cfb\u7edf",
        "hero_intro": (
            "\u9762\u5411\u300a\u5370\u4eba\u4f20\u300b\u6784\u5efa\u7684\u77e5\u8bc6\u56fe\u8c31\u95ee\u7b54\u539f\u578b\u3002"
            "\u5f53\u524d\u9875\u9762\u5df2\u7ecf\u9884\u7559\u666e\u901a\u95ee\u7b54\u3001\u9ad8\u7ea7 SPARQL\u3001"
            "\u56fe\u8c31\u63a5\u5165\u72b6\u6001\u548c\u53ef\u89c6\u5316\u6269\u5c55\u5165\u53e3\uff0c"
            "\u9002\u5408\u6210\u5458 D \u6301\u7eed\u6574\u5408\u6210\u5458 B \u7684\u62bd\u53d6\u7ed3\u679c\u4e0e\u6210\u5458 C \u7684 Turtle \u56fe\u8c31\u3002"
        ),
        "start_query": "\u5f00\u59cb\u67e5\u8be2",
        "health": "\u67e5\u770b\u5065\u5eb7\u72b6\u6001",
        "ttl_title": "\u56fe\u8c31\u63a5\u5165\u72b6\u6001",
        "ttl_online": "\u5df2\u63a5\u5165",
        "ttl_offline": "\u672a\u63a5\u5165",
        "demo_title": "\u63a8\u8350\u6f14\u793a\u987a\u5e8f",
        "demo_steps": [
            "\u5148\u5c55\u793a\u666e\u901a\u95ee\u7b54",
            "\u518d\u5c55\u793a\u56fa\u5b9a\u5de5\u5177\u67e5\u8be2",
            "\u6700\u540e\u5c55\u793a\u9ad8\u7ea7 SPARQL",
        ],
        "qa_kicker": "\u81ea\u7136\u8bed\u8a00\u67e5\u8be2",
        "qa_title": "\u666e\u901a\u95ee\u7b54",
        "qa_badge": "\u5de5\u4f5c\u6d41\u5165\u53e3",
        "qa_placeholder": "\u4f8b\u5982\uff1a\u6587\u5f6d\u662f\u8c01\uff1f",
        "qa_button": "\u67e5\u8be2",
        "qa_examples": [
            "\u6587\u5f6d\u662f\u8c01\uff1f",
            "\u6587\u5f6d\u7684\u5b57\u662f\u4ec0\u4e48\uff1f",
            "\u6587\u5fb5\u660e\u4e0e\u6587\u5f6d\u662f\u4ec0\u4e48\u5173\u7cfb\uff1f",
            "\u8c01\u5f00\u521b\u4e86\u5434\u95e8\u5370\u6d3e\uff1f",
        ],
        "qa_result_title": "\u95ee\u7b54\u7ed3\u679c",
        "qa_result_hint": "\u5f53\u524d\u4e3a\u8c03\u8bd5\u8f93\u51fa\uff0c\u540e\u7eed\u53ef\u6539\u6210\u5361\u7247\u5f0f\u5c55\u793a",
        "qa_waiting": "\u7b49\u5f85\u67e5\u8be2...",
        "member_kicker": "\u6210\u5458 D \u63d0\u524d\u51c6\u5907",
        "member_title": "\u6574\u5408\u91cd\u70b9",
        "member_todos": [
            "\u5148\u548c\u6210\u5458 C \u5b9a\u6b7b\u547d\u540d\u7a7a\u95f4\u3001\u7c7b\u540d\u548c\u5c5e\u6027\u540d\u3002",
            "\u4f18\u5148\u628a\u5b57\u3001\u53f7\u3001\u751f\u5352\u5e74\u3001\u5e08\u627f\u3001\u4eb2\u5c5e\u3001\u4ea4\u6e38\u3001\u6d41\u6d3e\u505a\u6210\u56fa\u5b9a\u5de5\u5177\u3002",
            "\u4e3a\u6bcf\u7c7b\u9ad8\u9891\u95ee\u9898\u51c6\u5907 SPARQL \u6a21\u677f\uff0c\u4e0d\u8981\u4e00\u5f00\u59cb\u5168\u9760\u6a21\u578b\u751f\u6210\u3002",
            "\u628a\u666e\u901a\u95ee\u7b54\u4e0e\u9ad8\u7ea7 SPARQL \u9875\u9762\u63d0\u524d\u8dd1\u901a\uff0c\u540e\u7eed\u53ea\u66ff\u6362\u6570\u636e\u6e90\u3002",
            "\u4eba\u7269\u5173\u7cfb\u7f51\u7edc\u53ef\u89c6\u5316\u653e\u5230\u4e3b\u94fe\u8def\u7a33\u5b9a\u540e\u518d\u63a5\u5165\u3002",
        ],
        "sparql_kicker": "\u7ed3\u6784\u5316\u67e5\u8be2",
        "sparql_title": "\u9ad8\u7ea7 SPARQL",
        "sparql_badge": "\u9002\u5408\u6f14\u793a\u8bfe\u7a0b\u6280\u672f\u70b9",
        "sparql_button": "\u6267\u884c SPARQL",
        "sparql_result_title": "SPARQL \u8fd4\u56de\u7ed3\u679c",
        "sparql_result_hint": "\u9002\u5408\u8bfe\u5802\u73b0\u573a\u5c55\u793a",
        "sparql_waiting": "\u7b49\u5f85\u6267\u884c...",
        "showcase_kicker": "\u793a\u4f8b\u65b9\u5411",
        "showcase_title": "\u5efa\u8bae\u5c55\u793a\u95ee\u9898",
        "showcases": [
            "\u4eba\u7269\u57fa\u7840\u4fe1\u606f\uff1a\u67d0\u4eba\u7684\u5b57\u3001\u53f7\u3001\u751f\u5352\u5e74",
            "\u4eba\u7269\u5173\u7cfb\uff1a\u7236\u5b50\u3001\u5e08\u627f\u3001\u4ea4\u6e38",
            "\u6d41\u6d3e\u95ee\u9898\uff1a\u67d0\u4eba\u5c5e\u4e8e\u4ec0\u4e48\u6d41\u6d3e\uff0c\u8c01\u5f00\u521b\u4e86\u67d0\u6d41\u6d3e",
            "\u590d\u6742\u67e5\u8be2\uff1a\u67d0\u4eba\u7269\u7684\u5173\u8054\u4eba\u7269\u6216\u8def\u5f84\u67e5\u8be2",
            "\u9ad8\u7ea7\u67e5\u8be2\uff1a\u76f4\u63a5\u6267\u884c SPARQL \u5c55\u793a\u56fe\u8c31\u7ed3\u6784",
        ],
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
        result = service.answer_question(question)
        return jsonify(result.model_dump())

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
