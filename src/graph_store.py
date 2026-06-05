from __future__ import annotations

from pathlib import Path


class GraphStore:
    def __init__(self, ttl_files: list[Path]):
        self.ttl_files = ttl_files
        self._graph = None
        self._rdflib_error = None

    def is_ready(self) -> bool:
        return any(path.exists() for path in self.ttl_files)

    def load(self):
        if self._graph is not None:
            return self._graph

        try:
            from rdflib import Graph
        except ImportError as exc:
            self._rdflib_error = exc
            raise RuntimeError(
                "rdflib is not installed. Install dependencies from requirements.txt first."
            ) from exc

        graph = Graph()
        loaded = 0
        for ttl_path in self.ttl_files:
            if ttl_path.exists():
                graph.parse(ttl_path, format="turtle")
                loaded += 1

        if loaded == 0:
            raise FileNotFoundError(
                "No Turtle files were found. Put schema.ttl/core.ttl/aligned.ttl into data/kg/."
            )

        self._graph = graph
        return self._graph

    def query(self, sparql: str) -> list[dict[str, str]]:
        graph = self.load()
        result = graph.query(sparql)
        rows: list[dict[str, str]] = []
        for row in result:
            row_dict: dict[str, str] = {}
            for key in row.labels.keys():
                value = row[key]
                row_dict[str(key)] = "" if value is None else str(value)
            rows.append(row_dict)
        return rows
