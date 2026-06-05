from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(default="", description="Natural-language user question")


class SparqlRequest(BaseModel):
    sparql: str = Field(default="", description="Raw SPARQL query")


class QueryResult(BaseModel):
    mode: str
    answer: str
    sparql: str | None = None
    rows: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
