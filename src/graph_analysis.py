from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from typing import Any

from .graph_store import GraphStore
from .tools import BASE_PREFIXES

# 简繁汉字归一化映射（数据中常见的异体/简繁差异）
_CJK_NORMALIZE_MAP: dict[str, str] = {
    "征": "徵",  # 征 → 徵
    "徵": "徵",  # 徵 → 徵 (canonical)
    "历": "歷",  # 历 → 歷
    "门": "門",  # 门 → 門
    "为": "為",  # 为 → 為
    "云": "雲",  # 云 → 雲
    "习": "習",  # 习 → 習
    "书": "書",  # 书 → 書
    "业": "業",  # 业 → 業
    "东": "東",  # 东 → 東
    "乐": "樂",  # 乐 → 樂
    "乡": "鄉",  # 乡 → 鄉
    "买": "買",  # 买 → 買
    "争": "爭",  # 争 → 爭
    "事": "事",  # (keep)
    "云": "雲",  # 云 → 雲
    "亚": "亞",  # 亚 → 亞
    "产": "產",  # 产 → 產
    "亲": "親",  # 亲 → 親
    "人": "人",  # (keep)
    "仅": "僅",  # 仅 → 僅
    "他": "他",  # (keep)
    "会": "會",  # 会 → 會
    "传": "傳",  # 传 → 傳
    "体": "體",  # 体 → 體
    "何": "何",  # (keep)
    "作": "作",  # (keep)
    "值": "值",  # (keep)
    "关": "關",  # 关 → 關
    "兴": "興",  # 兴 → 興
    "养": "養",  # 养 → 養
    "内": "內",  # 内 → 內
    "写": "寫",  # 写 → 寫
    "刀": "刀",  # (keep)
    "制": "製",  # 制 → 製
    "发": "發",  # 发 → 發
    "号": "號",  # 号 → 號
    "合": "合",  # (keep)
    "向": "向",  # (keep)
    "四": "四",  # (keep)
    "国": "國",  # 国 → 國
    "场": "場",  # 场 → 場
    "在": "在",  # (keep)
    "地": "地",  # (keep)
    "型": "型",  # (keep)
    "备": "備",  # 备 → 備
    "复": "復",  # 复 → 復
    "多": "多",  # (keep)
    "大": "大",  # (keep)
    "头": "頭",  # 头 → 頭
    "好": "好",  # (keep)
    "学": "學",  # 学 → 學
    "实": "實",  # 实 → 實
    "对": "對",  # 对 → 對
    "导": "導",  # 导 → 導
    "将": "將",  # 将 → 將
    "层": "層",  # 层 → 層
    "展": "展",  # (keep)
    "工": "工",  # (keep)
    "市": "市",  # (keep)
    "师": "師",  # 师 → 師
    "常": "常",  # (keep)
    "干": "幹",  # 干 → 幹
    "平": "平",  # (keep)
    "年": "年",  # (keep)
    "广": "廣",  # 广 → 廣
    "开": "開",  # 开 → 開
    "异": "異",  # 异 → 異
    "张": "張",  # 张 → 張
    "当": "當",  # 当 → 當
    "录": "錄",  # 录 → 錄
    "形": "形",  # (keep)
    "得": "得",  # (keep)
    "微": "微",  # (keep)
    "心": "心",  # (keep)
    "总": "總",  # 总 → 總
    "您": "您",  # (keep)
    "成": "成",  # (keep)
    "我": "我",  # (keep)
    "或": "或",  # (keep)
    "房": "房",  # (keep)
    "所": "所",  # (keep)
    "打": "打",  # (keep)
    "执": "執",  # 执 → 執
    "找": "找",  # (keep)
    "技": "技",  # (keep)
    "报": "報",  # 报 → 報
    "拥": "擁",  # 拥 → 擁
    "持": "持",  # (keep)
    "指": "指",  # (keep)
    "挑": "挑",  # (keep)
    "据": "據",  # 据 → 據
    "数": "數",  # 数 → 數
    "文": "文",  # (keep)
    "斯": "斯",  # (keep)
    "新": "新",  # (keep)
    "方": "方",  # (keep)
    "无": "無",  # 无 → 無
    "日": "日",  # (keep)
    "时": "時",  # 时 → 時
    "明": "明",  # (keep)
    "是": "是",  # (keep)
    "普": "普",  # (keep)
    "最": "最",  # (keep)
    "有": "有",  # (keep)
    "服": "服",  # (keep)
    "本": "本",  # (keep)
    "条": "條",  # 条 → 條
    "来": "來",  # 来 → 來
    "极": "極",  # 极 → 極
    "析": "析",  # (keep)
    "查": "查",  # (keep)
    "样": "樣",  # 样 → 樣
    "根": "根",  # (keep)
    "案": "案",  # (keep)
    "梓": "梓",  # (keep)
    "植": "植",  # (keep)
    "模": "模",  # (keep)
    "次": "次",  # (keep)
    "正": "正",  # (keep)
    "比": "比",  # (keep)
    "民": "民",  # (keep)
    "气": "氣",  # 气 → 氣
    "求": "求",  # (keep)
    "汽": "汽",  # (keep)
    "没": "没",  # (keep)
    "法": "法",  # (keep)
    "派": "派",  # (keep)
    "流": "流",  # (keep)
    "测": "測",  # 测 → 測
    "海": "海",  # (keep)
    "消": "消",  # (keep)
    "深": "深",  # (keep)
    "清": "清",  # (keep)
    "游": "遊",  # 游 → 遊
    "源": "源",  # (keep)
    "满": "滿",  # 满 → 滿
    "火": "火",  # (keep)
    "点": "點",  # 点 → 點
    "爱": "愛",  # 爱 → 愛
    "版": "版",  # (keep)
    "物": "物",  # (keep)
    "特": "特",  # (keep)
    "状": "狀",  # 状 → 狀
    "猫": "貓",  # 猫 → 貓
    "环": "環",  # 环 → 環
    "现": "現",  # 现 → 現
    "生": "生",  # (keep)
    "用": "用",  # (keep)
    "电": "電",  # 电 → 電
    "男": "男",  # (keep)
    "画": "畫",  # 画 → 畫
    "界": "界",  # (keep)
    "留": "留",  # (keep)
    "目": "目",  # (keep)
    "相": "相",  # (keep)
    "看": "看",  # (keep)
    "真": "真",  # (keep)
    "知": "知",  # (keep)
    "确": "確",  # 确 → 確
    "示": "示",  # (keep)
    "社": "社",  # (keep)
    "科": "科",  # (keep)
    "租": "租",  # (keep)
    "移": "移",  # (keep)
    "程": "程",  # (keep)
    "空": "空",  # (keep)
    "立": "立",  # (keep)
    "第": "第",  # (keep)
    "等": "等",  # (keep)
    "简": "簡",  # 简 → 簡
    "类": "類",  # 类 → 類
    "系": "系",  # (keep)
    "级": "級",  # 级 → 級
    "组": "組",  # 组 → 組
    "织": "織",  # 织 → 織
    "结": "結",  # 结 → 結
    "统": "統",  # 统 → 統
    "继": "繼",  # 继 → 繼
    "续": "續",  # 续 → 續
    "编": "編",  # 编 → 編
    "网": "網",  # 网 → 網
    "置": "置",  # (keep)
    "美": "美",  # (keep)
    "考": "考",  # (keep)
    "者": "者",  # (keep)
    "聂": "聂",  # (keep)
    "联": "聯",  # 联 → 聯
    "聖": "聖",  # (keep)
    "股": "股",  # (keep)
    "能": "能",  # (keep)
    "脚": "腳",  # 脚 → 腳
    "脸": "臉",  # 脸 → 臉
    "自": "自",  # (keep)
    "航": "航",  # (keep)
    "艺": "藝",  # 艺 → 藝
    "节": "節",  # 节 → 節
    "范": "範",  # 范 → 範
    "荣": "榮",  # 荣 → 榮
    "获": "獲",  # 获 → 獲
    "营": "營",  # 营 → 營
    "落": "落",  # (keep)
    "董": "董",  # (keep)
    "蒋": "蒋",  # (keep)
    "薪": "薪",  # (keep)
    "行": "行",  # (keep)
    "表": "表",  # (keep)
    "被": "被",  # (keep)
    "装": "裝",  # 装 → 裝
    "规": "規",  # 规 → 規
    "视": "視",  # 视 → 視
    "角": "角",  # (keep)
    "解": "解",  # (keep)
    "言": "言",  # (keep)
    "設": "設",  # 设 → 設
    "証": "證",  # 证 → 證
    "評": "評",  # 评 → 評
    "試": "試",  # 试 → 試
    "話": "話",  # 话 → 話
    "語": "語",  # 语 → 語
    "說": "說",  # 说 → 說
    "請": "請",  # 请 → 請
    "論": "論",  # 论 → 論
    "謝": "謝",  # 谢 → 謝
    "證": "證",  # 證 → 證 (canonical)
    "識": "識",  # 识 → 識
    "豪": "豪",  # (keep)
    "质": "質",  # 质 → 質
    "资": "資",  # 资 → 資
    "起": "起",  # (keep)
    "路": "路",  # (keep)
    "车": "車",  # 车 → 車
    "转": "轉",  # 转 → 轉
    "载": "載",  # 载 → 載
    "输": "輸",  # 输 → 輸
    "辖": "辖",  # (keep)
    "运": "運",  # 运 → 運
    "近": "近",  # (keep)
    "返": "返",  # 返 → 返
    "还": "還",  # 还 → 還
    "进": "進",  # 进 → 進
    "连": "連",  # 连 → 連
    "送": "送",  # (keep)
    "适": "適",  # 适 → 適
    "选": "選",  # 选 → 選
    "通": "通",  # (keep)
    "造": "造",  # (keep)
    "達": "達",  # 达 → 達
    "還": "還",  # 還 → 還 (canonical)
    "那": "那",  # (keep)
    "部": "部",  # (keep)
    "郵": "郵",  # 邮 → 郵
    "配": "配",  # (keep)
    "重": "重",  # (keep)
    "钟": "鐘",  # 钟 → 鐘
    "键": "鍵",  # 键 → 鍵
    "长": "長",  # 长 → 長
    "问": "問",  # 问 → 問
    "间": "間",  # 间 → 間
    "阅": "閱",  # 阅 → 閱
    "队": "隊",  # 队 → 隊
    "防": "防",  # (keep)
    "际": "際",  # 际 → 際
    "限": "限",  # (keep)
    "除": "除",  # (keep)
    "隔": "隔",  # (keep)
    "集": "集",  # (keep)
    "需": "需",  # (keep)
    "青": "青",  # (keep)
    "面": "面",  # (keep)
    "项": "項",  # 项 → 項
    "顺": "順",  # 顺 → 順
    "预": "預",  # 预 → 預
    "领": "領",  # 领 → 領
    "题": "題",  # 题 → 題
    "风": "風",  # 风 → 風
    "飞": "飛",  # 飞 → 飛
    "食": "食",  # (keep)
    "首": "首",  # (keep)
    "香": "香",  # (keep)
    "驱": "驱",  # 驱 → 驅
    "驶": "駛",  # 驾 → 駕
    "验": "驗",  # 验 → 驗
    "高": "高",  # (keep)
    "魂": "魂",  # (keep)
    "鼎": "鼎",  # (keep)
    "鼻": "鼻",  # (keep)
    "龙": "龍",  # 龙 → 龍
}


def _normalize_name(name: str) -> str:
    """将名字中的简体字映射为繁体，用于跨简繁匹配。"""
    result: list[str] = []
    for ch in name:
        result.append(_CJK_NORMALIZE_MAP.get(ch, ch))
    return "".join(result)


PERSON_RELATION_TYPES = {
    "hasTeacher": "师承",
    "hasFriend": "交游",
    "fatherOf": "亲属",
}

SCHOOL_RELATION_TYPES = {
    "belongsToSchool": "所属流派",
    "foundsSchool": "开创流派",
}

RELATION_COLOR_MAP = {
    "师承": "#7a2412",
    "亲属": "#8f5d16",
    "交游": "#2c596a",
    "所属流派": "#7d6a2d",
    "开创流派": "#5d4f97",
}

MAIN_RELATION_LABELS = {"师承", "交游", "亲属", "所属流派", "开创流派"}
RELATION_PRIORITY = {
    "师承": 5,
    "亲属": 4,
    "交游": 3,
    "开创流派": 2,
    "所属流派": 1,
}
DEFAULT_PREVIEW_NODES = 54
DEFAULT_PREVIEW_EDGES = 88
EXPANDED_PREVIEW_NODES = 120
EXPANDED_PREVIEW_EDGES = 180


@dataclass(frozen=True)
class RelationEdge:
    source: str
    target: str
    relation_type: str
    relation_label: str
    source_type: str
    target_type: str


class GraphAnalysisService:
    def __init__(self, graph_store: GraphStore):
        self.graph_store = graph_store
        self._relation_edges_cache: list[RelationEdge] | None = None
        self._person_detail_cache: dict[str, dict[str, Any]] = {}

    def build_overview(self) -> dict[str, Any]:
        edges = self._load_relation_edges()
        people_graph = self._build_people_graph(edges)
        centrality = self._build_centrality_analysis(people_graph)
        communities = self._build_community_analysis(edges)
        school_evolution = self._build_school_evolution(edges, centrality["degree_map"])
        node_counts = self._build_node_counts(edges)
        return {
            "summary": {
                "nodeCount": node_counts["node_count"],
                "edgeCount": len(edges),
                "personCount": node_counts["person_count"],
                "schoolCount": node_counts["school_count"],
            },
            "centrality": {
                "topDegree": centrality["top_degree"],
                "topBetweenness": centrality["top_betweenness"],
            },
            "communities": communities,
            "schoolEvolution": school_evolution,
        }

    def find_shortest_path(self, source_name: str, target_name: str) -> dict[str, Any]:
        if not source_name.strip() or not target_name.strip():
            return {
                "ok": False,
                "error": "起点和终点不能为空。",
            }

        edges = self._load_relation_edges()
        adjacency = self._build_path_adjacency(edges)
        all_person_names = {edge.source for edge in edges} | {edge.target for edge in edges}
        source = self._resolve_graph_name(source_name, adjacency, all_person_names)
        target = self._resolve_graph_name(target_name, adjacency, all_person_names)
        if source is None or target is None:
            return {
                "ok": False,
                "error": "未在当前人物关系图中找到对应人物。",
            }

        if source == target:
            return {
                "ok": True,
                "source": source,
                "target": target,
                "distance": 0,
                "nodes": [source],
                "steps": [],
            }

        queue: deque[str] = deque([source])
        visited = {source}
        previous: dict[str, tuple[str, str]] = {}

        while queue:
            current = queue.popleft()
            for neighbor, relation_label in adjacency.get(current, []):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                previous[neighbor] = (current, relation_label)
                if neighbor == target:
                    queue.clear()
                    break
                queue.append(neighbor)

        if target not in previous:
            return {
                "ok": False,
                "source": source,
                "target": target,
                "error": "当前图中未找到两人之间的可达路径。",
            }

        path_nodes = [target]
        path_steps: list[dict[str, str]] = []
        cursor = target
        while cursor != source:
            parent, relation_label = previous[cursor]
            path_steps.append(
                {
                    "source": parent,
                    "target": cursor,
                    "relation": relation_label,
                }
            )
            path_nodes.append(parent)
            cursor = parent
        path_nodes.reverse()
        path_steps.reverse()

        return {
            "ok": True,
            "source": source,
            "target": target,
            "distance": len(path_steps),
            "nodes": path_nodes,
            "steps": path_steps,
        }

    def get_exploration_graph(
        self,
        *,
        center: str = "",
        hop: int = 1,
        relation_types: list[str] | None = None,
        full_view: bool = False,
    ) -> dict[str, Any]:
        edges = self._load_relation_edges()
        normalized_types = {item.strip() for item in (relation_types or []) if item.strip()}
        if not normalized_types:
            normalized_types = set(MAIN_RELATION_LABELS)
        edges = [edge for edge in edges if edge.relation_label in normalized_types]

        if center.strip():
            return self._build_center_graph(edges, center=center.strip(), hop=max(1, min(hop, 2)))
        return self._build_full_graph(edges, expanded=full_view)

    def get_person_detail(self, person_name: str) -> dict[str, Any]:
        resolved = self._resolve_person_detail_name(person_name)
        if not resolved:
            return {
                "ok": False,
                "error": "未找到对应人物。",
            }
        if resolved in self._person_detail_cache:
            return self._person_detail_cache[resolved]

        edges = self._load_relation_edges()

        courtesy_names: set[str] = set()
        art_names: set[str] = set()
        schools: set[str] = set()
        node_types: set[str] = set()
        relations: list[dict[str, str]] = []

        for edge in edges:
            if edge.source == resolved:
                node_types.add(edge.source_type)
                if edge.relation_type == "hasCourtesyName":
                    courtesy_names.add(edge.target)
                elif edge.relation_type == "hasArtName":
                    art_names.add(edge.target)
                elif edge.relation_type == "belongsToSchool":
                    schools.add(edge.target)
                elif edge.relation_type not in {"hasCourtesyName", "hasArtName"}:
                    relations.append({
                        "relatedLabel": edge.target,
                        "relationLabel": edge.relation_label,
                        "direction": "outgoing",
                    })
            elif edge.target == resolved:
                node_types.add(edge.target_type)
                if edge.relation_type not in {"hasCourtesyName", "hasArtName"}:
                    relations.append({
                        "relatedLabel": edge.source,
                        "relationLabel": edge.relation_label,
                        "direction": "incoming",
                    })

        # Deduplicate relations
        seen_relations: set[tuple[str, str, str]] = set()
        unique_relations: list[dict[str, str]] = []
        for rel in relations:
            key = (rel["relatedLabel"], rel["relationLabel"], rel["direction"])
            if key not in seen_relations:
                seen_relations.add(key)
                unique_relations.append(rel)

        # Derive entity type URI
        entity_type_map = {"Person": "yrz:Person", "School": "yrz:School", "Place": "yrz:Place"}
        entity_type = ""
        for raw_type in node_types:
            mapped = entity_type_map.get(raw_type, "")
            if mapped:
                entity_type = mapped
                break

        profile = {
            "name": resolved,
            "courtesyNames": sorted(courtesy_names),
            "artNames": sorted(art_names),
            "birthYears": [],
            "deathYears": [],
            "schools": sorted(schools),
            "entityType": entity_type,
        }
        result = {
            "ok": True,
            "profile": profile,
            "relations": unique_relations,
        }
        self._person_detail_cache[resolved] = result
        return result

    def _load_relation_edges(self) -> list[RelationEdge]:
        if self._relation_edges_cache is not None:
            return self._relation_edges_cache
        rows = self.graph_store.query(
            f"""
            {BASE_PREFIXES}
            SELECT DISTINCT
              ?sourceLabel ?targetLabel ?relationType ?relationTypeLabel ?sourceClass ?targetClass
            WHERE {{
              ?relationFact rdf:type yrz:Relation ;
                            yrz:relationType ?relationType ;
                            yrz:sourceEntity ?source ;
                            yrz:targetEntity ?target .
              OPTIONAL {{ ?source rdfs:label ?sourceLabelRaw . }}
              OPTIONAL {{ ?target rdfs:label ?targetLabelRaw . }}
              OPTIONAL {{ ?relationType rdfs:label ?relationTypeLabel . }}
              OPTIONAL {{ ?source rdf:type ?sourceClass . }}
              OPTIONAL {{ ?target rdf:type ?targetClass . }}
              BIND(COALESCE(?sourceLabelRaw, STR(?source)) AS ?sourceLabel)
              BIND(COALESCE(?targetLabelRaw, STR(?target)) AS ?targetLabel)
            }}
            """
        )

        edges: list[RelationEdge] = []
        seen: set[tuple[str, str, str]] = set()
        for row in rows:
            relation_type = self._local_name(row.get("relationType", ""))
            fallback_label = PERSON_RELATION_TYPES.get(relation_type, SCHOOL_RELATION_TYPES.get(relation_type, relation_type))
            relation_label = self._normalize_relation_label(str(row.get("relationTypeLabel") or fallback_label).strip())
            source = self._display_label(row.get("sourceLabel", ""))
            target = self._display_label(row.get("targetLabel", ""))
            if not source or not target or not relation_type:
                continue
            if source == target:
                continue
            edge_key = (source, target, relation_label or relation_type)
            if edge_key in seen:
                continue
            seen.add(edge_key)
            edges.append(
                RelationEdge(
                    source=source,
                    target=target,
                    relation_type=relation_type,
                    relation_label=relation_label,
                    source_type=self._local_name(row.get("sourceClass", "")),
                    target_type=self._local_name(row.get("targetClass", "")),
                )
            )
        self._relation_edges_cache = edges
        return edges

    def _build_people_graph(self, edges: list[RelationEdge]) -> dict[str, set[str]]:
        graph: dict[str, set[str]] = defaultdict(set)
        for edge in edges:
            if edge.relation_type not in PERSON_RELATION_TYPES:
                continue
            graph[edge.source].add(edge.target)
            graph[edge.target].add(edge.source)
        return graph

    def _build_centrality_analysis(self, graph: dict[str, set[str]]) -> dict[str, Any]:
        nodes = sorted(graph.keys())
        if not nodes:
            return {
                "degree_map": {},
                "top_degree": [],
                "top_betweenness": [],
            }

        n = len(nodes)
        degree_map = {
            node: round((len(graph[node]) / (n - 1)) if n > 1 else 0.0, 4)
            for node in nodes
        }
        betweenness_map = self._betweenness_centrality(graph)

        top_degree = [
            {"name": name, "score": score, "degree": len(graph[name])}
            for name, score in sorted(degree_map.items(), key=lambda item: (-item[1], item[0]))[:8]
        ]
        top_betweenness = [
            {"name": name, "score": score}
            for name, score in sorted(betweenness_map.items(), key=lambda item: (-item[1], item[0]))[:8]
        ]
        return {
            "degree_map": degree_map,
            "top_degree": top_degree,
            "top_betweenness": top_betweenness,
        }

    def _betweenness_centrality(self, graph: dict[str, set[str]]) -> dict[str, float]:
        nodes = list(graph.keys())
        betweenness = {node: 0.0 for node in nodes}

        for source in nodes:
            stack: list[str] = []
            predecessors: dict[str, list[str]] = {node: [] for node in nodes}
            sigma = dict.fromkeys(nodes, 0.0)
            sigma[source] = 1.0
            distance = dict.fromkeys(nodes, -1)
            distance[source] = 0
            queue: deque[str] = deque([source])

            while queue:
                vertex = queue.popleft()
                stack.append(vertex)
                for neighbor in graph[vertex]:
                    if distance[neighbor] < 0:
                        queue.append(neighbor)
                        distance[neighbor] = distance[vertex] + 1
                    if distance[neighbor] == distance[vertex] + 1:
                        sigma[neighbor] += sigma[vertex]
                        predecessors[neighbor].append(vertex)

            dependency = dict.fromkeys(nodes, 0.0)
            while stack:
                vertex = stack.pop()
                for predecessor in predecessors[vertex]:
                    if sigma[vertex] == 0:
                        continue
                    dependency[predecessor] += (
                        sigma[predecessor] / sigma[vertex]
                    ) * (1.0 + dependency[vertex])
                if vertex != source:
                    betweenness[vertex] += dependency[vertex]

        node_count = len(nodes)
        if node_count > 2:
            scale = 2 / ((node_count - 1) * (node_count - 2))
            for node in betweenness:
                betweenness[node] = round(betweenness[node] * scale, 4)
        else:
            for node in betweenness:
                betweenness[node] = 0.0
        return betweenness

    def _build_community_analysis(self, edges: list[RelationEdge]) -> list[dict[str, Any]]:
        graph: dict[str, set[str]] = defaultdict(set)
        relation_counter: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
        for edge in edges:
            if edge.relation_type not in {"hasTeacher", "hasFriend"}:
                continue
            graph[edge.source].add(edge.target)
            graph[edge.target].add(edge.source)
            key = tuple(sorted((edge.source, edge.target)))
            relation_counter[key][edge.relation_label] += 1

        communities: list[dict[str, Any]] = []
        visited: set[str] = set()
        community_id = 1
        for node in sorted(graph.keys()):
            if node in visited:
                continue
            queue: deque[str] = deque([node])
            visited.add(node)
            members: list[str] = []
            relation_types: Counter[str] = Counter()
            while queue:
                current = queue.popleft()
                members.append(current)
                for neighbor in graph[current]:
                    key = tuple(sorted((current, neighbor)))
                    relation_types.update(relation_counter.get(key, Counter()))
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            communities.append(
                {
                    "id": f"C{community_id}",
                    "size": len(members),
                    "members": sorted(members),
                    "dominantRelations": [
                        {"relation": relation, "count": count}
                        for relation, count in relation_types.most_common(3)
                    ],
                }
            )
            community_id += 1

        communities.sort(key=lambda item: (-item["size"], item["id"]))
        return communities[:8]

    def _build_school_evolution(
        self,
        edges: list[RelationEdge],
        degree_map: dict[str, float],
    ) -> list[dict[str, Any]]:
        school_members: dict[str, set[str]] = defaultdict(set)
        school_founders: dict[str, set[str]] = defaultdict(set)
        person_schools: dict[str, set[str]] = defaultdict(set)

        for edge in edges:
            if edge.relation_type == "belongsToSchool":
                school_members[edge.target].add(edge.source)
                person_schools[edge.source].add(edge.target)
            elif edge.relation_type == "foundsSchool":
                school_founders[edge.target].add(edge.source)
                person_schools[edge.source].add(edge.target)

        school_links: dict[tuple[str, str], int] = defaultdict(int)
        for edge in edges:
            if edge.relation_type not in PERSON_RELATION_TYPES:
                continue
            source_schools = person_schools.get(edge.source, set())
            target_schools = person_schools.get(edge.target, set())
            for source_school in source_schools:
                for target_school in target_schools:
                    if source_school == target_school:
                        continue
                    key = tuple(sorted((source_school, target_school)))
                    school_links[key] += 1

        school_rows: list[dict[str, Any]] = []
        all_schools = sorted(set(school_members.keys()) | set(school_founders.keys()))
        for school in all_schools:
            members = sorted(school_members.get(school, set()))
            founders = sorted(school_founders.get(school, set()))
            representative_figures = [
                {"name": name, "degreeCentrality": degree_map.get(name, 0.0)}
                for name in sorted(
                    members,
                    key=lambda item: (-degree_map.get(item, 0.0), item),
                )[:5]
            ]
            linked_schools = []
            for (school_a, school_b), count in school_links.items():
                if school not in {school_a, school_b}:
                    continue
                linked_schools.append(
                    {
                        "school": school_b if school_a == school else school_a,
                        "linkCount": count,
                    }
                )
            linked_schools.sort(key=lambda item: (-item["linkCount"], item["school"]))

            school_rows.append(
                {
                    "school": school,
                    "founders": founders,
                    "memberCount": len(members),
                    "representativeFigures": representative_figures,
                    "linkedSchools": linked_schools[:5],
                }
            )

        school_rows.sort(key=lambda item: (-item["memberCount"], item["school"]))
        return school_rows

    def _build_node_counts(self, edges: list[RelationEdge]) -> dict[str, int]:
        people: set[str] = set()
        schools: set[str] = set()
        all_nodes: set[str] = set()
        for edge in edges:
            all_nodes.add(edge.source)
            all_nodes.add(edge.target)
            if edge.relation_type in PERSON_RELATION_TYPES:
                people.add(edge.source)
                people.add(edge.target)
            if edge.relation_type == "belongsToSchool":
                people.add(edge.source)
                schools.add(edge.target)
            if edge.relation_type == "foundsSchool":
                people.add(edge.source)
                schools.add(edge.target)
        return {
            "node_count": len(all_nodes),
            "person_count": len(people),
            "school_count": len(schools),
        }

    def _build_path_adjacency(self, edges: list[RelationEdge]) -> dict[str, list[tuple[str, str]]]:
        adjacency: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for edge in edges:
            if edge.relation_type not in PERSON_RELATION_TYPES:
                continue
            adjacency[edge.source].append((edge.target, edge.relation_label))
            adjacency[edge.target].append((edge.source, edge.relation_label))
        return adjacency

    def _build_full_graph(self, edges: list[RelationEdge], *, expanded: bool = False) -> dict[str, Any]:
        preview_edges = self._select_preview_edges(
            edges,
            max_nodes=EXPANDED_PREVIEW_NODES if expanded else DEFAULT_PREVIEW_NODES,
            max_edges=EXPANDED_PREVIEW_EDGES if expanded else DEFAULT_PREVIEW_EDGES,
        )
        nodes = self._nodes_from_edges(preview_edges)
        centrality_map = self._build_people_centrality_map(edges)
        communities = self._community_lookup(edges)
        graph_nodes = [self._graph_node_dict(node, centrality_map, communities) for node in sorted(nodes, key=lambda item: item["label"])]
        graph_edges = [self._graph_edge_dict(edge) for edge in preview_edges]
        total_counts = self._build_node_counts(edges)
        return {
            "ok": True,
            "nodes": graph_nodes,
            "edges": graph_edges,
            "meta": {
                "mode": "full" if expanded else "preview",
                "center": "",
                "hop": 0,
                "nodeCount": len(graph_nodes),
                "edgeCount": len(graph_edges),
                "totalNodeCount": total_counts["node_count"],
                "totalPersonCount": total_counts["person_count"],
                "totalSchoolCount": total_counts["school_count"],
                "totalEdgeCount": len(edges),
                "isSubset": len(graph_nodes) < total_counts["node_count"] or len(graph_edges) < len(edges),
                "relationTypes": sorted({edge["relationLabel"] for edge in graph_edges}),
                "note": (
                    "当前展示精选子图预览，优先保留高连接度人物、关键流派与主要关系。"
                    if not expanded
                    else "当前展示扩展视图，为了保证前端流畅度仍保留了子图采样。"
                ),
            },
        }

    def _build_center_graph(self, edges: list[RelationEdge], *, center: str, hop: int) -> dict[str, Any]:
        adjacency: dict[str, list[RelationEdge]] = defaultdict(list)
        all_people_names: set[str] = set()
        for edge in edges:
            adjacency[edge.source].append(edge)
            adjacency[edge.target].append(edge)
            if edge.source_type == "Person":
                all_people_names.add(edge.source)
            if edge.target_type == "Person":
                all_people_names.add(edge.target)

        resolved_center = self._resolve_graph_name(center, adjacency, all_people_names)
        if not resolved_center:
            return {
                "ok": False,
                "error": "未找到该人物，无法展开关系网络。",
            }

        visited = {resolved_center}
        queue: deque[tuple[str, int]] = deque([(resolved_center, 0)])
        selected_edges: dict[tuple[str, str, str], RelationEdge] = {}

        while queue:
            current, depth = queue.popleft()
            if depth >= hop:
                continue
            for edge in adjacency.get(current, []):
                edge_key = (edge.source, edge.target, edge.relation_label)
                selected_edges[edge_key] = edge
                next_nodes = [edge.source, edge.target]
                for node in next_nodes:
                    if node not in visited:
                        visited.add(node)
                        queue.append((node, depth + 1))

        chosen_edges = list(selected_edges.values())
        nodes = self._nodes_from_edges(chosen_edges)
        centrality_map = self._build_people_centrality_map(edges)
        communities = self._community_lookup(edges)
        graph_nodes = [self._graph_node_dict(node, centrality_map, communities, center=resolved_center) for node in sorted(nodes, key=lambda item: item["label"])]
        graph_edges = [self._graph_edge_dict(edge, center=resolved_center) for edge in chosen_edges]
        return {
            "ok": True,
            "nodes": graph_nodes,
            "edges": graph_edges,
            "meta": {
                "mode": "center",
                "center": resolved_center,
                "hop": hop,
                "nodeCount": len(graph_nodes),
                "edgeCount": len(graph_edges),
                "relationTypes": sorted({edge["relationLabel"] for edge in graph_edges}),
            },
        }

    def _build_people_centrality_map(self, edges: list[RelationEdge]) -> dict[str, float]:
        people_graph = self._build_people_graph(edges)
        return self._build_centrality_analysis(people_graph)["degree_map"]

    def _community_lookup(self, edges: list[RelationEdge]) -> dict[str, str]:
        communities = self._build_community_analysis(edges)
        lookup: dict[str, str] = {}
        for community in communities:
            for member in community.get("members", []):
                lookup[member] = community["id"]
        return lookup

    def _nodes_from_edges(self, edges: list[RelationEdge]) -> list[dict[str, str]]:
        node_map: dict[str, dict[str, str]] = {}
        for edge in edges:
            node_map.setdefault(edge.source, {"id": edge.source, "label": edge.source, "type": self._node_kind(edge.source_type)})
            node_map.setdefault(edge.target, {"id": edge.target, "label": edge.target, "type": self._node_kind(edge.target_type)})
        return list(node_map.values())

    def _graph_node_dict(
        self,
        node: dict[str, str],
        centrality_map: dict[str, float],
        communities: dict[str, str],
        center: str = "",
    ) -> dict[str, Any]:
        degree_score = centrality_map.get(node["label"], 0.0)
        base_size = 18 if node["type"] == "school" else 20
        size = round(base_size + degree_score * 30 + (8 if node["label"] == center else 0), 2)
        entity_type_map = {
            "person": "yrz:Person",
            "school": "yrz:School",
            "place": "yrz:Place",
            "unknown": "",
        }
        return {
            "id": node["id"],
            "label": node["label"],
            "type": node["type"],
            "entityType": entity_type_map.get(node["type"], ""),
            "size": size,
            "isCenter": node["label"] == center,
            "degreeCentrality": degree_score,
            "community": communities.get(node["label"], ""),
        }

    def _graph_edge_dict(self, edge: RelationEdge, center: str = "") -> dict[str, Any]:
        edge_class_map = {
            "hasTeacher": "edge-class-teacher",
            "fatherOf": "edge-class-family",
            "hasFriend": "edge-class-social",
            "belongsToSchool": "edge-class-school",
            "foundsSchool": "edge-class-school",
        }
        return {
            "id": f"{edge.source}::{edge.target}::{edge.relation_label}",
            "source": edge.source,
            "target": edge.target,
            "relationType": edge.relation_type,
            "relationLabel": edge.relation_label,
            "color": RELATION_COLOR_MAP.get(edge.relation_label, "#6f6458"),
            "width": 2.6 if edge.source == center or edge.target == center else 1.9,
            "isCenterEdge": edge.source == center or edge.target == center,
            "edgeClass": edge_class_map.get(edge.relation_type, ""),
            "ontology": {
                "relationType": edge.relation_type,
                "domain": self._node_kind(edge.source_type).capitalize(),
                "range": self._node_kind(edge.target_type).capitalize(),
                "sourceType": edge.source_type,
                "targetType": edge.target_type,
            },
        }

    def _select_preview_edges(
        self,
        edges: list[RelationEdge],
        *,
        max_nodes: int,
        max_edges: int,
    ) -> list[RelationEdge]:
        if len(edges) <= max_edges:
            return edges

        adjacency: dict[str, list[RelationEdge]] = defaultdict(list)
        node_degree: Counter[str] = Counter()
        school_degree: Counter[str] = Counter()
        for edge in edges:
            adjacency[edge.source].append(edge)
            adjacency[edge.target].append(edge)
            node_degree[edge.source] += 1
            node_degree[edge.target] += 1
            if edge.source_type == "School":
                school_degree[edge.source] += 1
            if edge.target_type == "School":
                school_degree[edge.target] += 1

        people_graph = self._build_people_graph(edges)
        degree_map = self._build_centrality_analysis(people_graph)["degree_map"]
        seed_names = [name for name, _score in sorted(degree_map.items(), key=lambda item: (-item[1], item[0]))[:6]]
        seed_names.extend(
            name for name, _count in sorted(school_degree.items(), key=lambda item: (-item[1], item[0]))[:3]
        )
        if not seed_names:
            seed_names.extend(name for name, _count in node_degree.most_common(6))

        chosen_edges: dict[tuple[str, str, str], RelationEdge] = {}
        chosen_nodes: set[str] = set()
        queue: deque[str] = deque(dict.fromkeys(seed_names))
        visited_nodes: set[str] = set()

        def edge_sort_key(item: RelationEdge) -> tuple[int, int, str, str]:
            peer = item.target if item.source in visited_nodes else item.source
            return (
                RELATION_PRIORITY.get(item.relation_label, 0),
                node_degree.get(peer, 0),
                item.source,
                item.target,
            )

        while queue and len(chosen_edges) < max_edges and len(chosen_nodes) < max_nodes:
            node = queue.popleft()
            if node in visited_nodes:
                continue
            visited_nodes.add(node)
            for edge in sorted(adjacency.get(node, []), key=edge_sort_key, reverse=True):
                edge_key = (edge.source, edge.target, edge.relation_label)
                if edge_key in chosen_edges:
                    continue
                prospective_nodes = chosen_nodes | {edge.source, edge.target}
                if len(prospective_nodes) > max_nodes:
                    continue
                chosen_edges[edge_key] = edge
                chosen_nodes = prospective_nodes
                if len(chosen_edges) >= max_edges:
                    break
                for next_node in (edge.source, edge.target):
                    if next_node not in visited_nodes:
                        queue.append(next_node)

        if len(chosen_edges) < max_edges:
            remaining_edges = sorted(
                edges,
                key=lambda edge: (
                    RELATION_PRIORITY.get(edge.relation_label, 0),
                    node_degree.get(edge.source, 0) + node_degree.get(edge.target, 0),
                    edge.source,
                    edge.target,
                ),
                reverse=True,
            )
            for edge in remaining_edges:
                edge_key = (edge.source, edge.target, edge.relation_label)
                if edge_key in chosen_edges:
                    continue
                prospective_nodes = chosen_nodes | {edge.source, edge.target}
                if len(prospective_nodes) > max_nodes:
                    continue
                chosen_edges[edge_key] = edge
                chosen_nodes = prospective_nodes
                if len(chosen_edges) >= max_edges:
                    break

        return list(chosen_edges.values())

    def _node_kind(self, raw_type: str) -> str:
        if raw_type == "School":
            return "school"
        if raw_type == "Person":
            return "person"
        if raw_type == "Place":
            return "place"
        return "unknown"

    def _resolve_person_name(
        self,
        raw_name: str,
        adjacency: dict[str, list[tuple[str, str]]],
    ) -> str | None:
        target = raw_name.strip()
        normalized_target = _normalize_name(target)
        for name in adjacency:
            if _normalize_name(name) == normalized_target:
                return name
        candidates = [name for name in adjacency if normalized_target in _normalize_name(name) or _normalize_name(name) in normalized_target]
        return sorted(candidates, key=len)[0] if candidates else None

    def _resolve_graph_name(
        self,
        raw_name: str,
        adjacency: dict,
        person_names: set[str],
    ) -> str | None:
        target = raw_name.strip()
        normalized_target = _normalize_name(target)
        all_candidates = set(adjacency.keys()) | person_names
        for name in all_candidates:
            if _normalize_name(name) == normalized_target:
                return name
        candidates = [name for name in all_candidates if normalized_target in _normalize_name(name) or _normalize_name(name) in normalized_target]
        return sorted(candidates, key=len)[0] if candidates else None

    def _resolve_person_detail_name(self, person_name: str) -> str | None:
        edges = self._load_relation_edges()
        candidates = sorted({edge.source for edge in edges} | {edge.target for edge in edges})
        target = person_name.strip()
        normalized_target = _normalize_name(target)
        for name in candidates:
            if _normalize_name(name) == normalized_target:
                return name
        fuzzy = [name for name in candidates if normalized_target in _normalize_name(name) or _normalize_name(name) in normalized_target]
        return sorted(fuzzy, key=len)[0] if fuzzy else None

    def _normalize_relation_label(self, label: str) -> str:
        if not label:
            return ""
        normalized = label.replace("父子", "亲属").replace("父亲", "亲属")
        normalized = normalized.replace("开创", "开创流派")
        if normalized in {"belongsToSchool", "所属印派"}:
            return "所属流派"
        if normalized in {"foundsSchool"}:
            return "开创流派"
        if normalized in {"hasTeacher"}:
            return "师承"
        if normalized in {"hasFriend"}:
            return "交游"
        if normalized in {"fatherOf"}:
            return "亲属"
        return normalized

    def _display_label(self, raw_value: Any) -> str:
        text = str(raw_value or "").strip()
        if not text:
            return ""
        if text.startswith("http://") or text.startswith("https://"):
            local = self._local_name(text)
            parts = [part for part in local.split("_") if part]
            for part in reversed(parts):
                if part.startswith("e") and part[1:].isdigit():
                    continue
                if part.isdigit():
                    continue
                return part
            return local
        return text

    def _escape_literal(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _local_name(self, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if "#" in text:
            return text.rsplit("#", 1)[-1]
        if "/" in text:
            return text.rsplit("/", 1)[-1]
        return text
