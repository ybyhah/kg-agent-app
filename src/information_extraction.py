from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field


class ExtractionEntity(BaseModel):
    name: str = Field(description="实体名称")
    category: str = Field(description="实体类别，如 PERSON、BOOK、LOCATION、ORG、TIME")
    evidence: str = Field(default="", description="支持该实体的原文片段")


class ExtractionAttribute(BaseModel):
    subject: str = Field(description="属性归属主体")
    attribute: str = Field(description="属性名称")
    value: str = Field(description="属性值")
    evidence: str = Field(default="", description="支持该属性的原文片段")


class ExtractionRelation(BaseModel):
    source: str = Field(description="关系起点实体")
    relation: str = Field(description="关系名称")
    target: str = Field(description="关系终点实体")
    evidence: str = Field(default="", description="支持该关系的原文片段")


class ExtractionPayload(BaseModel):
    entities: list[ExtractionEntity] = Field(default_factory=list)
    attributes: list[ExtractionAttribute] = Field(default_factory=list)
    relations: list[ExtractionRelation] = Field(default_factory=list)


@dataclass(frozen=True)
class PersonRecord:
    record_id: str
    person_name: str
    source_text: str
    text_length: int


@dataclass(frozen=True)
class ExtractedRecord:
    record_id: str
    person_name: str
    source_text: str
    text_length: int
    entities: list[dict[str, str]]
    attributes: list[dict[str, str]]
    relations: list[dict[str, str]]


class LlmClient(Protocol):
    def invoke(self, prompt: str) -> str:
        ...


class JsonExtractionParser:
    _fence_pattern = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)

    def parse(self, raw_text: str) -> ExtractionPayload:
        content = raw_text.strip()
        match = self._fence_pattern.search(content)
        if match:
            content = match.group(1).strip()
        data = json.loads(content)
        return ExtractionPayload.model_validate(data)


class PersonRecordExtractor:
    def __init__(self, client: LlmClient, parser: JsonExtractionParser | None = None):
        self.client = client
        self.parser = parser or JsonExtractionParser()

    def extract_record(self, record: PersonRecord) -> ExtractedRecord:
        prompt = self._build_prompt(record)
        raw_response = self.client.invoke(prompt)
        payload = self.parser.parse(raw_response)
        return ExtractedRecord(
            record_id=record.record_id,
            person_name=record.person_name,
            source_text=record.source_text,
            text_length=record.text_length,
            entities=[item.model_dump() for item in payload.entities],
            attributes=[item.model_dump() for item in payload.attributes],
            relations=[item.model_dump() for item in payload.relations],
        )

    def _build_prompt(self, record: PersonRecord) -> str:
        return f"""
你是古籍信息抽取助手。请阅读下面的人物记录，并完成三类抽取：
1. NER：抽取文本中出现的实体。
2. 属性抽取：抽取人物属性，如字、号、籍贯、身份、官职、技艺、著作、评价等。
3. 关系抽取：抽取人物与人物、人物与作品、人物与地点、人物与身份之间的关系。

要求：
- 只根据原文输出，不要编造。
- 输出必须是 JSON 对象，且只能包含 entities、attributes、relations 三个顶级字段。
- entities 中每项字段：name, category, evidence
- attributes 中每项字段：subject, attribute, value, evidence
- relations 中每项字段：source, relation, target, evidence
- 如果某类没有结果，返回空数组。

记录编号：{record.record_id}
人物名：{record.person_name}
原文：
{record.source_text}
""".strip()


def load_person_records(input_path: Path) -> list[PersonRecord]:
    with input_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    records: list[PersonRecord] = []
    for item in payload:
        records.append(
            PersonRecord(
                record_id=str(item["record_id"]),
                person_name=str(item["person_name"]),
                source_text=str(item["source_text"]),
                text_length=int(item["text_length"]),
            )
        )
    return records


def extract_records_to_file(
    input_path: Path,
    output_path: Path,
    extractor: PersonRecordExtractor,
    limit: int | None = None,
) -> list[dict[str, object]]:
    records = load_person_records(input_path)
    if limit is not None:
        records = records[:limit]

    results: list[dict[str, object]] = []
    for record in records:
        extracted = extractor.extract_record(record)
        results.append(asdict(extracted))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return results
