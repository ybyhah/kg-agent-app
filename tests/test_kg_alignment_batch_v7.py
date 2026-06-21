from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
import urllib.error
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
ALIGN_ENTITIES_PATH = REPO_ROOT / "scripts" / "kg_alignment" / "align_entities.py"
BATCH_V7_PATH = REPO_ROOT / "scripts" / "kg_alignment" / "batch_align_v7.py"
FORMAL_BACKFILL_PATH = REPO_ROOT / "scripts" / "kg_alignment" / "formal_backfill_curated.py"
RANKED_BACKFILL_PATH = REPO_ROOT / "scripts" / "kg_alignment" / "ranked_backfill.py"
GATED_BATCH_PATH = REPO_ROOT / "scripts" / "kg_alignment" / "full_batch_gated.py"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_module(module_name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class FakeHttpResponse:
    def __init__(self, body: str, url: str = "https://example.test") -> None:
        self._body = body.encode("utf-8")
        self.status = 200
        self._url = url

    def read(self) -> bytes:
        return self._body

    def geturl(self) -> str:
        return self._url

    def __enter__(self) -> "FakeHttpResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def build_cbdb_detail_payload(
    *,
    person_id: str,
    name: str,
    courtesy_name: str = "",
    art_name: str = "",
    birth_year: str = "",
    death_year: str = "",
    dynasty: str = "",
    birth_place: str = "",
    ctext_pages: str = "",
) -> str:
    aliases = []
    if courtesy_name:
        aliases.append({"AliasType": "字", "AliasTypeId": "4", "AliasName": courtesy_name})
    if art_name:
        aliases.append({"AliasType": "室名、別號", "AliasTypeId": "5", "AliasName": art_name})

    addresses = []
    if birth_place:
        addresses.append(
            {
                "AddrTypeId": "1",
                "AddrType": "籍貫(基本地址)",
                "AddrId": "4594",
                "AddrName": birth_place,
                "MoveCount": "1",
                "FirstYear": "",
                "LastYear": "",
                "Source": "明人傳記資料索引",
                "Pages": "0187",
                "Notes": f"{birth_place}人",
            }
        )

    sources = []
    if ctext_pages:
        sources.append(
            {
                "Source": "中國哲學書電子化計劃 (ctext)",
                "SourceId": "66734",
                "Pages": ctext_pages,
                "Notes": "",
                "UrlApi": "https://ctext.org/datawiki.pl?if=en&res=",
                "UrlApiCoda": "",
            }
        )

    payload = {
        "Package": {
            "PersonAuthority": {
                "PersonInfo": {
                    "Person": {
                        "BasicInfo": {
                            "PersonId": person_id,
                            "EngName": "",
                            "ChName": name,
                            "IndexYear": birth_year,
                            "IndexAddrId": "4594",
                            "IndexAddr": birth_place,
                            "Gender": "0",
                            "YearBirth": birth_year,
                            "DynastyBirth": "未詳",
                            "DynastyBirthId": "0",
                            "EraBirth": "未詳",
                            "EraBirthId": "0",
                            "EraYearBirth": "",
                            "YearDeath": death_year,
                            "DynastyDeath": "未詳",
                            "DynastyDeathId": "0",
                            "EraDeath": "未詳",
                            "EraDeathId": "0",
                            "EraYearDeath": "",
                            "YearsLived": "",
                            "YearsLivedApprox": "",
                            "Dynasty": dynasty,
                            "DynastyId": "19",
                            "JunWang": "【未詳】",
                            "JunWangId": "0",
                            "Source": "",
                            "SourcePages": "",
                            "Notes": "",
                        },
                        "PersonAliases": {"Alias": aliases},
                        "PersonAddresses": {"Address": addresses},
                        "PersonSources": {"Source": sources},
                    }
                }
            }
        }
    }
    return json.dumps(payload, ensure_ascii=False)


class KgAlignmentBatchV7Tests(unittest.TestCase):
    def test_ranked_backfill_selects_top_seed_entities_by_richness(self) -> None:
        ranked_backfill = load_module("test_ranked_backfill", RANKED_BACKFILL_PATH)

        entities = [
            {
                "type": "人物",
                "name": "甲",
                "id": "甲_e1",
                "source_text": "甲，字子明。",
            },
            {
                "type": "人物",
                "name": "乙",
                "id": "乙_e1",
                "source_text": "乙，字伯和，号南山，杭州人，明人。",
            },
            {
                "type": "人物",
                "name": "丙",
                "id": "丙_e1",
                "source_text": "丙",
            },
            {
                "type": "人物",
                "name": "乙",
                "id": "乙_e2",
                "source_text": "乙",
            },
            {
                "type": "人物",
                "name": "外部",
                "id": "外部_e1",
                "source_text": "外部，字不入选。",
            },
        ]

        with mock.patch.object(
            ranked_backfill,
            "KNOWN_CBDB_MAP",
            {"甲": {"cbdb_id": "1"}, "乙": {"cbdb_id": "2"}, "丙": {"cbdb_id": "3"}},
        ):
            selected = ranked_backfill.select_top_seed_entities(entities, limit=2)

        self.assertEqual([entity["name"] for entity in selected], ["乙", "甲"])
        self.assertEqual(selected[0]["id"], "乙_e1")
        self.assertEqual(selected[1]["id"], "甲_e1")

    def test_ranked_backfill_bridges_seed_names_to_local_aliases(self) -> None:
        ranked_backfill = load_module("test_ranked_backfill_alias_bridge", RANKED_BACKFILL_PATH)

        entities = [
            {
                "type": "人物",
                "name": "文征明",
                "id": "文征明_e1",
                "source_text": "文征明，字征仲，号衡山，长洲人。",
            },
            {
                "type": "人物",
                "name": "达受",
                "id": "达受_e1",
                "source_text": "达受，僧人。",
            },
        ]

        with mock.patch.object(
            ranked_backfill,
            "KNOWN_CBDB_MAP",
            {"文徵明": {"cbdb_id": "1"}, "释达受": {"cbdb_id": "2"}},
        ):
            selected = ranked_backfill.select_top_seed_entities(entities, limit=10)

        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]["name"], "文征明")
        self.assertEqual(selected[0]["alignment_seed_name"], "文徵明")
        self.assertEqual(selected[1]["name"], "达受")
        self.assertEqual(selected[1]["alignment_seed_name"], "释达受")

    def test_full_batch_gated_writes_only_high_threshold_and_reports_low_threshold(self) -> None:
        align_entities = load_module("test_align_entities_gate", ALIGN_ENTITIES_PATH)
        gated_batch = load_module("test_full_batch_gated", GATED_BATCH_PATH)

        entities_payload = {
            "entities": [
                {
                    "type": "人物",
                    "name": "高分人物",
                    "id": "高分人物_e1",
                    "source_text": "高分人物，字子高，号清泉，杭州人，明人。",
                },
                {
                    "type": "人物",
                    "name": "低分人物",
                    "id": "低分人物_e1",
                    "source_text": "低分人物，字小低。",
                },
            ]
        }

        def fake_get_or_build_candidates(name, person_info, skip_external=False):
            return [{"cbdb_id": f"id-{name}", "name": name, "seed_match": name == "高分人物"}]

        def fake_disambiguate(candidates, local_name, local_info):
            score = 0.92 if local_name == "高分人物" else 0.58
            candidate = align_entities.AlignmentCandidate(
                source_id=local_info.get("id", local_name),
                source_name=local_name,
                external_id=f"id-{local_name}",
                external_name=local_name,
                courtesy_name="",
                art_name="",
                birth_year="",
                death_year="",
                dynasty="",
                birth_place="",
                match_score=score,
                match_method="gated_test",
                alignment_status="aligned",
            )
            return candidate, ["mock_rule"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            entities_path = tmp / "entities.json"
            aligned_path = tmp / "aligned.ttl"
            report_path = tmp / "gated_report.json"
            entities_path.write_text(json.dumps(entities_payload, ensure_ascii=False), encoding="utf-8")
            aligned_path.write_text("@prefix kg: <http://example.org/kg/> .\n", encoding="utf-8")

            with mock.patch.object(gated_batch, "ENTITIES_JSON", entities_path), \
                 mock.patch.object(gated_batch, "ALIGNED_TTL", aligned_path), \
                 mock.patch.object(gated_batch, "REPORT_PATH", report_path), \
                 mock.patch.object(gated_batch, "WRITE_THRESHOLD", 0.85), \
                 mock.patch.object(gated_batch, "REPORT_ONLY_THRESHOLD", 0.5), \
                 mock.patch.object(gated_batch, "get_or_build_candidates", side_effect=fake_get_or_build_candidates), \
                 mock.patch.object(gated_batch, "disambiguate", side_effect=fake_disambiguate):
                summary = gated_batch.run_full_batch_gated()

            ttl_text = aligned_path.read_text(encoding="utf-8")
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["written"], 1)
        self.assertEqual(summary["report_only"], 1)
        self.assertEqual(summary["skipped"], 0)
        self.assertIn('kg:高分人物_e1  kg:cbdbId  "id-高分人物" .', ttl_text)
        self.assertNotIn("低分人物_e1", ttl_text)
        self.assertEqual(len(report["written_records"]), 1)
        self.assertEqual(len(report["report_only_records"]), 1)
        self.assertEqual(report["report_only_records"][0]["name"], "低分人物")

    def test_write_alignment_block_can_replace_existing_subject_block(self) -> None:
        align_entities = load_module("test_align_entities_upsert", ALIGN_ENTITIES_PATH)

        old_block = """# old block
kg:文彭_e1  owl:sameAs  <http://cbdb.fas.harvard.edu/person/11111> .
kg:文彭_e1
    kg:cbdbId  "11111" ;
    kg:name  "文彭" ;
    kg:alignmentStatus  "aligned_with_external" .

kg:其他_e1  owl:sameAs  <http://cbdb.fas.harvard.edu/person/22222> .
kg:其他_e1  kg:cbdbId  "22222" .
"""

        candidate = align_entities.AlignmentCandidate(
            source_id="文彭_e1",
            source_name="文彭",
            external_id="34677",
            external_name="文彭",
            courtesy_name="寿承",
            art_name="三桥",
            birth_year="1498",
            death_year="1573",
            dynasty="明",
            birth_place="长洲",
            match_score=0.95,
            match_method="formal_backfill",
            alignment_status="aligned",
        )
        candidate.ctext_id = "326035"
        candidate.ctext_url = "https://ctext.org/datawiki.pl?if=en&res=326035"

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / "aligned.ttl"
            tmp_path.write_text(old_block, encoding="utf-8")
            ttl = align_entities.write_alignment_block(
                ttl_path=tmp_path,
                person_name="文彭",
                source_entity_id="文彭_e1",
                candidate=candidate,
                replace_existing=True,
                dry_run=False,
            )
            saved = tmp_path.read_text(encoding="utf-8")

        self.assertIn('kg:文彭_e1  kg:cbdbId  "34677" .', saved)
        self.assertNotIn('kg:文彭_e1  kg:cbdbId  "11111" .', saved)
        self.assertEqual(saved.count("kg:文彭_e1  owl:sameAs"), 1)
        self.assertIn('kg:其他_e1  kg:cbdbId  "22222" .', saved)
        self.assertIn(ttl.strip(), saved)

    def test_formal_backfill_curated_targets_uses_best_entity_and_writes_real_ids(self) -> None:
        align_entities = load_module("test_align_entities_formal", ALIGN_ENTITIES_PATH)
        formal_backfill = load_module("test_formal_backfill_curated", FORMAL_BACKFILL_PATH)

        entities_payload = {
            "entities": [
                {
                    "type": "人物",
                    "name": "文彭",
                    "id": "文彭_e1",
                    "source_text": "文彭，字寿承，号三桥，待诏伯子，官南京国博。",
                },
                {
                    "type": "人物",
                    "name": "文彭",
                    "id": "文彭_e2",
                    "source_text": "文彭",
                },
                {
                    "type": "人物",
                    "name": "何震",
                    "id": "何震_e1",
                    "source_text": "何震，字主臣，号雪渔，一号长卿，婺源人。",
                },
            ]
        }

        def fake_get_or_build_candidates(name, person_info, skip_external=False):
            if name == "文彭":
                return [
                    {
                        "cbdb_id": "34677",
                        "name": "文彭",
                        "courtesy_name": "寿承",
                        "art_name": "三桥",
                        "birth_year": "1498",
                        "death_year": "1573",
                        "dynasty": "明",
                        "birth_place": "长洲",
                        "ctext_id": "326035",
                        "ctext_url": "https://ctext.org/datawiki.pl?if=en&res=326035",
                        "source": "CBDB_API",
                        "seed_match": True,
                    }
                ]
            return [
                {
                    "cbdb_id": "42095",
                    "name": "何震",
                    "courtesy_name": "主臣",
                    "art_name": "雪渔",
                    "birth_year": "1522",
                    "death_year": "1604",
                    "dynasty": "明",
                    "birth_place": "婺源",
                    "ctext_id": "",
                    "ctext_url": "",
                    "source": "CBDB_API",
                    "seed_match": True,
                }
            ]

        def fake_disambiguate(candidates, local_name, local_info):
            raw = candidates[0]
            candidate = align_entities.AlignmentCandidate(
                source_id=local_info.get("id", local_name),
                source_name=local_name,
                external_id=raw["cbdb_id"],
                external_name=raw["name"],
                courtesy_name=raw.get("courtesy_name", ""),
                art_name=raw.get("art_name", ""),
                birth_year=raw.get("birth_year", ""),
                death_year=raw.get("death_year", ""),
                dynasty=raw.get("dynasty", ""),
                birth_place=raw.get("birth_place", ""),
                match_score=0.88,
                match_method="formal_backfill",
                alignment_status="aligned",
            )
            candidate.ctext_id = raw.get("ctext_id", "")
            candidate.ctext_url = raw.get("ctext_url", "")
            return candidate, ["seed"]

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            entities_path = tmp / "entities.json"
            aligned_path = tmp / "aligned.ttl"
            report_path = tmp / "formal_report.json"
            entities_path.write_text(json.dumps(entities_payload, ensure_ascii=False), encoding="utf-8")
            aligned_path.write_text("@prefix kg: <http://example.org/kg/> .\n", encoding="utf-8")

            with mock.patch.object(formal_backfill, "ENTITIES_JSON", entities_path), \
                 mock.patch.object(formal_backfill, "ALIGNED_TTL", aligned_path), \
                 mock.patch.object(formal_backfill, "REPORT_PATH", report_path), \
                 mock.patch.object(formal_backfill, "CURATED_TARGET_NAMES", ["文彭", "何震"]), \
                 mock.patch.object(formal_backfill, "get_or_build_candidates", side_effect=fake_get_or_build_candidates), \
                 mock.patch.object(formal_backfill, "disambiguate", side_effect=fake_disambiguate):
                summary = formal_backfill.run_formal_backfill()

            ttl_text = aligned_path.read_text(encoding="utf-8")
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["selected_targets"], 2)
        self.assertEqual(summary["written"], 2)
        self.assertEqual(summary["with_cbdb"], 2)
        self.assertEqual(summary["with_ctext"], 1)
        self.assertIn('kg:文彭_e1  kg:cbdbId  "34677" .', ttl_text)
        self.assertNotIn("kg:文彭_e2", ttl_text)
        self.assertIn('kg:何震_e1  kg:cbdbId  "42095" .', ttl_text)
        self.assertEqual(report["written"], 2)
        self.assertEqual(report["records"][0]["name"], "文彭")

    def test_search_ctext_by_name_falls_back_to_cbdb_linked_ctext_source(self) -> None:
        align_entities = load_module("test_align_entities_ctext", ALIGN_ENTITIES_PATH)

        with mock.patch.object(
            align_entities.urllib.request,
            "urlopen",
            side_effect=urllib.error.HTTPError(
                url="https://ctext.org/plugins/apisearch?query=%E6%96%87%E5%BD%AD",
                code=404,
                msg="Not Found",
                hdrs=None,
                fp=None,
            ),
        ), mock.patch.object(
            align_entities,
            "search_cbdb_by_name",
            return_value=[
                {
                    "cbdb_id": "34677",
                    "name": "文彭",
                    "ctext_id": "326035",
                    "ctext_url": "https://ctext.org/datawiki.pl?if=en&res=326035",
                    "dynasty": "明",
                    "birth_place": "長洲",
                }
            ],
        ):
            candidates = align_entities.search_ctext_by_name("文彭")

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["name"], "文彭")
        self.assertEqual(candidates[0]["cbdb_id"], "326035")
        self.assertEqual(candidates[0]["ctext_url"], "https://ctext.org/datawiki.pl?if=en&res=326035")
        self.assertEqual(candidates[0]["source"], "CTEXT_FALLBACK")

    def test_known_map_seed_match_promotes_curated_candidate_to_aligned(self) -> None:
        align_entities = load_module("test_align_entities_seed", ALIGN_ENTITIES_PATH)

        known_name = next(iter(align_entities.KNOWN_CBDB_MAP))
        known = align_entities.KNOWN_CBDB_MAP[known_name]

        candidates = [
            {
                "cbdb_id": known["cbdb_id"],
                "name": known_name,
                "courtesy_name": "",
                "art_name": "",
                "birth_year": "",
                "death_year": "",
                "dynasty": "",
                "birth_place": "",
                "seed_match": True,
            }
        ]

        best_candidate, rules = align_entities.disambiguate(candidates, known_name, {})

        self.assertIsNotNone(best_candidate)
        self.assertEqual(best_candidate.alignment_status, "aligned")
        self.assertGreaterEqual(best_candidate.match_score, 0.5)
        self.assertTrue(any("KNOWN_MAP" in rule for rule in rules))

    def test_search_cbdb_by_name_uses_json_detail_enrichment_and_ctext_source(self) -> None:
        align_entities = load_module("test_align_entities_search", ALIGN_ENTITIES_PATH)

        search_html = """
        <html>
        <head><title>CBDB 人物資料庫 - 34677</title></head>
        <body>
        <script>
        var searchResultsData = [{"id": 34677, "label": "文彭"}];
        </script>
        </body>
        </html>
        """
        detail_json = build_cbdb_detail_payload(
            person_id="34677",
            name="文彭",
            courtesy_name="壽承",
            art_name="三橋",
            birth_year="1498",
            death_year="1573",
            dynasty="明",
            birth_place="長洲",
            ctext_pages="326035",
        )

        def fake_urlopen(req, timeout=0):
            url = req.full_url
            if "mode=exact" in url:
                return FakeHttpResponse(search_html, url)
            if "id=34677" in url and "o=json" in url:
                return FakeHttpResponse(detail_json, url)
            raise AssertionError(f"Unexpected URL: {url}")

        with mock.patch.object(align_entities.urllib.request, "urlopen", side_effect=fake_urlopen):
            candidates = align_entities.search_cbdb_by_name("文彭")

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate["cbdb_id"], "34677")
        self.assertEqual(candidate["name"], "文彭")
        self.assertEqual(candidate["courtesy_name"], "壽承")
        self.assertEqual(candidate["art_name"], "三橋")
        self.assertEqual(candidate["birth_year"], "1498")
        self.assertEqual(candidate["death_year"], "1573")
        self.assertEqual(candidate["dynasty"], "明")
        self.assertEqual(candidate["birth_place"], "長洲")
        self.assertEqual(candidate["ctext_id"], "326035")
        self.assertEqual(candidate["ctext_url"], "https://ctext.org/datawiki.pl?if=en&res=326035")

    def test_append_to_aligned_ttl_writes_kg_prefix_and_external_ids(self) -> None:
        align_entities = load_module("test_align_entities_append", ALIGN_ENTITIES_PATH)

        candidate = align_entities.AlignmentCandidate(
            source_id="e1",
            source_name="文彭",
            external_id="34677",
            external_name="文彭",
            courtesy_name="壽承",
            art_name="三橋",
            birth_year="1498",
            death_year="1573",
            dynasty="明",
            birth_place="長洲",
            match_score=0.92,
            match_method="cbdb_json",
            alignment_status="aligned",
        )
        candidate.ctext_id = "326035"
        candidate.ctext_url = "https://ctext.org/datawiki.pl?if=en&res=326035"

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / "aligned.ttl"
            with mock.patch.object(align_entities, "ALIGNED_TTL", tmp_path):
                ttl = align_entities.append_to_aligned_ttl("文彭", "文彭_e1", candidate, dry_run=False)
                saved = tmp_path.read_text(encoding="utf-8")

        self.assertIn("kg:文彭_e1", ttl)
        self.assertIn("owl:sameAs", ttl)
        self.assertIn('kg:cbdbId  "34677"', ttl)
        self.assertIn('kg:ctextId  "326035"', ttl)
        self.assertIn("https://ctext.org/datawiki.pl?if=en&res=326035", ttl)
        self.assertIn(saved, "\n" + ttl + "\n")

    def test_run_batch_alignment_writes_enriched_external_ids(self) -> None:
        align_entities = load_module("test_align_entities_for_batch", ALIGN_ENTITIES_PATH)
        batch_v7 = load_module("test_batch_align_v7", BATCH_V7_PATH)

        entities_payload = {
            "entities": [
                {
                    "name": "待消歧人物",
                    "source_text": "待消歧人物，字伯明，号松泉，浙江杭州人，明人。",
                }
            ]
        }

        candidate_dict = {
            "cbdb_id": "45678",
            "name": "待消歧人物",
            "courtesy_name": "伯明",
            "art_name": "松泉",
            "birth_year": "1540",
            "death_year": "1600",
            "dynasty": "明",
            "birth_place": "浙江杭州",
            "ctext_id": "998877",
            "ctext_url": "https://ctext.org/datawiki.pl?if=en&res=998877",
            "source": "CBDB_API",
        }

        def fake_llm_disambiguation(person_name, local_info, candidates, api_key="", **kwargs):
            self.assertEqual(person_name, "待消歧人物")
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].external_id, "45678")
            candidates[0].llm_score = 88
            candidates[0].llm_reason = "字、号、籍贯、朝代一致"
            candidates[0].alignment_status = "aligned"
            candidates[0].ctext_id = "998877"
            candidates[0].ctext_url = "https://ctext.org/datawiki.pl?if=en&res=998877"
            return candidates

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            entities_path = tmp / "entities.json"
            aligned_path = tmp / "aligned.ttl"
            report_path = tmp / "alignment_report.txt"
            entities_path.write_text(json.dumps(entities_payload, ensure_ascii=False), encoding="utf-8")

            def fake_append_to_aligned_ttl(person_name, source_entity_id, candidate, dry_run=False):
                ttl = (
                    f'kg:{person_name} owl:sameAs <http://cbdb.fas.harvard.edu/person/{candidate.external_id}> .\n'
                    f'kg:{person_name} kg:cbdbId "{candidate.external_id}" .\n'
                    f'kg:{person_name} kg:ctextId "{candidate.ctext_id}" .\n'
                    f'kg:{person_name} rdfs:seeAlso <{candidate.ctext_url}> .\n'
                    f'kg:{person_name} kg:alignmentMethod "{candidate.match_method}" .\n'
                )
                with aligned_path.open("a", encoding="utf-8") as fh:
                    fh.write(ttl)
                return ttl

            with mock.patch.object(batch_v7, "ENTITIES_JSON", entities_path), \
                 mock.patch.object(batch_v7, "ALIGNED_TTL", aligned_path), \
                 mock.patch.object(batch_v7, "REPORT_PATH", report_path), \
                 mock.patch.object(batch_v7, "LLM_API_KEY", "fake-key"), \
                 mock.patch.object(batch_v7, "RULE_HIGH_THRESHOLD", 0.8), \
                 mock.patch.object(batch_v7, "RULE_LLM_THRESHOLD", 0.15), \
                 mock.patch.object(batch_v7, "MAX_LLM_CALLS", 10), \
                 mock.patch.object(batch_v7, "get_or_build_candidates", return_value=[candidate_dict]), \
                 mock.patch.object(batch_v7, "disambiguate", return_value=(
                     align_entities.AlignmentCandidate(
                         source_id="local",
                         source_name="待消歧人物",
                         external_id="45678",
                         external_name="待消歧人物",
                         courtesy_name="伯明",
                         art_name="松泉",
                         birth_year="1540",
                         death_year="1600",
                         dynasty="明",
                         birth_place="浙江杭州",
                         match_score=0.25,
                         match_method="rule_based",
                         alignment_status="partial",
                     ),
                     ["姓名完全匹配 +0.3"],
                 )), \
                 mock.patch.object(batch_v7, "append_to_aligned_ttl", side_effect=fake_append_to_aligned_ttl), \
                 mock.patch.object(batch_v7, "llm_disambiguation", side_effect=fake_llm_disambiguation):
                summary = batch_v7.run_batch_alignment()

            ttl_text = aligned_path.read_text(encoding="utf-8")
            report_text = report_path.read_text(encoding="utf-8")

        self.assertEqual(summary["aligned_rule"], 0)
        self.assertEqual(summary["aligned_llm"], 1)
        self.assertEqual(summary["llm_calls"], 1)
        self.assertIn("owl:sameAs", ttl_text)
        self.assertIn("45678", ttl_text)
        self.assertIn("998877", ttl_text)
        self.assertIn("LLM 辅助对齐: 1", report_text)


if __name__ == "__main__":
    unittest.main()
