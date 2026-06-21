from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch


OUTPUT_PATH = Path(r"D:\cxdownload\kg agent\kg_agent_app\docs\ppt_fixed_tools_table.png")
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")


ROWS = [
    ("get_person_labels", "person_name", "查询人物候选实体，用于先确认用户问的是谁"),
    ("get_courtesy_name", "person_name", "查询人物的“字”"),
    ("get_art_name", "person_name", "查询人物的“号”"),
    ("get_courtesy_and_art_name", "person_name", "同时查询人物的“字”和“号”"),
    ("get_birth_death", "person_name", "查询人物生卒年、基础时间信息"),
    ("get_teacher_relations", "person_name", "查询师承关系"),
    ("get_family_relations", "person_name", "查询亲属关系，如父子等"),
    ("get_social_relations", "person_name", "查询交游关系"),
    ("get_school_membership", "person_name", "查询人物所属流派"),
    ("get_school_founder", "school_name", "查询某流派的开创者"),
    ("get_pair_relations", "person_a, person_b", "查询两个人物之间的直接关系"),
    ("get_related_people", "person_name", "查询人物关联网络，用于关系图展示"),
    ("get_classmates", "person_name", "查询同门、师兄弟关系"),
    ("run_raw_sparql", "sparql", "执行高级 SPARQL 查询，处理固定工具覆盖不了的问题"),
]


def main() -> None:
    font_manager.fontManager.addfont(str(FONT_PATH))
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
    plt.rcParams["axes.unicode_minus"] = False

    palette = {
        "page": "#f5efe2",
        "panel": "#fbf6ec",
        "header": "#e4d3b5",
        "stripe_a": "#f8f1e5",
        "stripe_b": "#f1e6d4",
        "border": "#b8a58a",
        "title": "#5f4836",
        "tool": "#7a4e2f",
        "param": "#8c6a3c",
        "body": "#5c5148",
        "caption": "#7b6a58",
        "shadow": "#d8c7aa",
    }

    fig_h = 0.48 * (len(ROWS) + 3)
    fig, ax = plt.subplots(figsize=(16, fig_h), dpi=220)
    fig.patch.set_facecolor(palette["page"])
    ax.set_facecolor(palette["page"])
    ax.axis("off")

    shadow = FancyBboxPatch(
        (0.017, 0.045),
        0.966,
        0.90,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        transform=ax.transAxes,
        facecolor=palette["shadow"],
        edgecolor="none",
        alpha=0.18,
        zorder=-3,
    )
    panel = FancyBboxPatch(
        (0.012, 0.05),
        0.966,
        0.90,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        transform=ax.transAxes,
        facecolor=palette["panel"],
        edgecolor=palette["border"],
        linewidth=1.15,
        zorder=-2,
    )
    ax.add_patch(shadow)
    ax.add_patch(panel)

    table = ax.table(
        cellText=[list(row) for row in ROWS],
        colLabels=["工具名称", "参数", "作用说明"],
        bbox=[0.03, 0.11, 0.94, 0.72],
        cellLoc="left",
        colLoc="left",
        colWidths=[0.30, 0.18, 0.52],
    )

    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.75)

    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor(palette["border"])
        cell.set_linewidth(0.7)
        if r == 0:
            cell.set_facecolor(palette["header"])
            cell.set_text_props(color=palette["title"], weight="bold")
        else:
            cell.set_facecolor(palette["stripe_a"] if r % 2 else palette["stripe_b"])
            if c == 0:
                cell.set_text_props(color=palette["tool"], weight="bold")
            elif c == 1:
                cell.set_text_props(color=palette["param"])
            else:
                cell.set_text_props(color=palette["body"])

    ax.text(
        0.5,
        0.91,
        "固定查询工具表",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=21,
        color=palette["title"],
        weight="bold",
    )

    ax.text(
        0.5,
        0.055,
        "使用 @tool 封装固定查询函数，并在 LangGraph 中通过 ToolNode 调度执行。",
        transform=ax.transAxes,
        ha="center",
        va="center",
        color=palette["caption"],
        fontsize=11,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(rect=[0.015, 0.02, 0.985, 0.98])
    fig.savefig(OUTPUT_PATH, facecolor=fig.get_facecolor(), bbox_inches="tight")


if __name__ == "__main__":
    main()
