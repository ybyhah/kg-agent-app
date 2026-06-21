from __future__ import annotations

import json
from typing import Callable

from langchain_core.tools import tool

from .tools import QueryTools, ToolResult


def _serialize_tool_result(result: ToolResult) -> str:
    return json.dumps(
        {
            "name": result.name,
            "sparql": result.sparql,
            "rows": result.rows,
            "note": result.note,
        },
        ensure_ascii=False,
    )


def build_langchain_tools(query_tools: QueryTools) -> list[Callable]:
    @tool
    def get_person_labels(person_name: str) -> str:
        """查询人物候选实体。参数 person_name，人物姓名、字、号或别名。返回 JSON 字符串，包含 name、sparql、rows、note。"""
        return _serialize_tool_result(query_tools.get_person_labels(person_name))

    @tool
    def get_courtesy_name(person_name: str) -> str:
        """查询人物的字。参数 person_name，人物姓名。返回 JSON 字符串，包含 name、sparql、rows、note。"""
        return _serialize_tool_result(query_tools.get_courtesy_name(person_name))

    @tool
    def get_art_name(person_name: str) -> str:
        """查询人物的号。参数 person_name，人物姓名。返回 JSON 字符串，包含 name、sparql、rows、note。"""
        return _serialize_tool_result(query_tools.get_art_name(person_name))

    @tool
    def get_courtesy_and_art_name(person_name: str) -> str:
        """同时查询人物的字和号。参数 person_name，人物姓名。返回 JSON 字符串，包含 name、sparql、rows、note。"""
        return _serialize_tool_result(query_tools.get_courtesy_and_art_name(person_name))

    @tool
    def get_birth_death(person_name: str) -> str:
        """查询人物生卒信息。参数 person_name，人物姓名。返回 JSON 字符串，包含 name、sparql、rows、note。"""
        return _serialize_tool_result(query_tools.get_birth_death(person_name))

    @tool
    def get_teacher_relations(person_name: str) -> str:
        """查询人物师承关系。参数 person_name，人物姓名。返回 JSON 字符串，包含 name、sparql、rows、note。"""
        return _serialize_tool_result(query_tools.get_teacher_relations(person_name))

    @tool
    def get_family_relations(person_name: str) -> str:
        """查询人物亲属关系。参数 person_name，人物姓名。返回 JSON 字符串，包含 name、sparql、rows、note。"""
        return _serialize_tool_result(query_tools.get_family_relations(person_name))

    @tool
    def get_social_relations(person_name: str) -> str:
        """查询人物交游关系。参数 person_name，人物姓名。返回 JSON 字符串，包含 name、sparql、rows、note。"""
        return _serialize_tool_result(query_tools.get_social_relations(person_name))

    @tool
    def get_school_membership(person_name: str) -> str:
        """查询人物所属流派。参数 person_name，人物姓名。返回 JSON 字符串，包含 name、sparql、rows、note。"""
        return _serialize_tool_result(query_tools.get_school_membership(person_name))

    @tool
    def get_school_founder(school_name: str) -> str:
        """查询流派开创者。参数 school_name，流派名称。返回 JSON 字符串，包含 name、sparql、rows、note。"""
        return _serialize_tool_result(query_tools.get_school_founder(school_name))

    @tool
    def get_school_representatives(school_name: str) -> str:
        """查询流派代表人物、成员与开创者。参数 school_name，流派名称。返回 JSON 字符串，包含 name、sparql、rows、note。"""
        return _serialize_tool_result(query_tools.get_school_representatives(school_name))

    @tool
    def get_pair_relations(person_a: str, person_b: str) -> str:
        """查询两个人物之间的直接关系。参数 person_a、person_b。返回 JSON 字符串，包含 name、sparql、rows、note。"""
        return _serialize_tool_result(query_tools.get_pair_relations(person_a, person_b))

    @tool
    def get_related_people(person_name: str) -> str:
        """查询人物关联网络。参数 person_name，人物姓名。返回 JSON 字符串，包含 name、sparql、rows、note。"""
        return _serialize_tool_result(query_tools.get_related_people(person_name))

    @tool
    def get_classmates(person_name: str) -> str:
        """查询人物同门、师兄弟关系。参数 person_name，人物姓名。返回 JSON 字符串，包含 name、sparql、rows、note。"""
        return _serialize_tool_result(query_tools.get_classmates(person_name))

    return [
        get_person_labels,
        get_courtesy_name,
        get_art_name,
        get_courtesy_and_art_name,
        get_birth_death,
        get_teacher_relations,
        get_family_relations,
        get_social_relations,
        get_school_membership,
        get_school_founder,
        get_school_representatives,
        get_pair_relations,
        get_related_people,
        get_classmates,
    ]
