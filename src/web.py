from __future__ import annotations

from flask import jsonify, render_template, request

from .config import AppConfig
from .service import AppService


def register_routes(app, config: AppConfig):
    service = AppService(config)

    @app.get("/")
    def index():
        return render_template(
            "index.html",
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
