# -*- coding: utf-8 -*-
"""
基于规则的《印人传》知识抽取器
用于处理API余额不足时的627条空结果记录
"""
import json
import os
import re
from datetime import datetime


def make_entity(etype, name, source_text, person_name, idx):
    return {
        "type": etype,
        "name": name,
        "attributes": {},
        "source_text": source_text,
        "confidence": 0.9,
        "id": f"{person_name}_e{idx}"
    }


def make_relation(rtype, source, target, source_text, person_name, idx):
    return {
        "type": rtype,
        "source": source,
        "target": target,
        "source_text": source_text,
        "confidence": 0.9,
        "id": f"{person_name}_r{idx}"
    }


def find_window(text, center, window=20):
    start = max(0, center - window)
    end = min(len(text), center + window)
    return text[start:end]


def extract_from_record(record):
    text = record['source_text']
    person_name = record['person_name']
    entities = []
    relations = []
    e_idx = 1
    r_idx = 1
    seen_entities = set()  # 避免重复

    def add_entity(etype, name, source_text):
        nonlocal e_idx
        key = (etype, name)
        if key in seen_entities:
            return None
        seen_entities.add(key)
        ent = make_entity(etype, name, source_text, person_name, e_idx)
        entities.append(ent)
        e_idx += 1
        return ent

    def add_relation(rtype, source, target, source_text):
        nonlocal r_idx
        if not source or not target:
            return
        # 检查源和目标是否是已存在的实体名
        if (not any(e['name'] == source for e in entities) or
            not any(e['name'] == target for e in entities)):
            return
        rel = make_relation(rtype, source, target, source_text, person_name, r_idx)
        relations.append(rel)
        r_idx += 1

    # ====== 第一步：识别主人物 ======
    # 模式：人名，字XX，号XX，XX人
    main_person_pos = text.find(person_name)
    if main_person_pos >= 0:
        add_entity("人物", person_name, find_window(text, main_person_pos, 15))

    # ====== 第二步：识别字号 ======
    # 模式：字XX、号XX、别号XX、一字XX、又字XX、又号XX
    style_patterns = [
        (r'[，,。 ]字([\u4e00-\u9fa5]{1,4})', "字"),
        (r'[，,。 ]一字([\u4e00-\u9fa5]{1,4})', "一字"),
        (r'[，,。 ]又字([\u4e00-\u9fa5]{1,4})', "又字"),
        (r'[，,。 ]号([\u4e00-\u9fa5]{1,6})', "号"),
        (r'[，,。 ]别号([\u4e00-\u9fa5]{1,6})', "别号"),
        (r'[，,。 ]又号([\u4e00-\u9fa5]{1,6})', "又号"),
        (r'[，,。 ]自号([\u4e00-\u9fa5]{1,6})', "自号"),
    ]

    # 先处理主人物的字号（紧接在人名后的 "字XX，号XX，XX人" 格式）
    intro_pattern = re.search(
        f'{re.escape(person_name)}[，,。]([^。]*?)[人。]', text)
    if intro_pattern:
        intro_text = intro_pattern.group(1)
        # 从介绍文本中提取字号
        for pattern, label in style_patterns:
            m = re.search(pattern, intro_text)
            if m:
                style_name = m.group(1)
                # 过滤掉常见的非字号词
                stop_words = {'六法', '篆刻', '印章', '图章', '印人', '山水', '花鸟',
                              '书法', '八分', '汉隶', '古文', '古印', '汉人', '秦汉',
                              '宋元', '诗文', '金石', '书画', '铁笔', '铜玉', '款识',
                              '诸生', '进士', '布衣', '明经', '举人', '秀才', '博士',
                              '秀才', '山人', '处士', '徵士', '征士'}
                if style_name not in stop_words and len(style_name) <= 4:
                    style_text = text[m.start():m.end()] if m.start() < len(text) else intro_text
                    add_entity("字号", style_name, style_text)
                    add_relation("字号对应", person_name, style_name, style_text)

    # 全局搜索字号（主人物之后的介绍文字）
    for pattern, label in style_patterns:
        for m in re.finditer(pattern, text):
            style_name = m.group(1)
            stop_words = {'六法', '篆刻', '印章', '图章', '印人', '山水', '花鸟',
                          '书法', '八分', '汉隶', '古文', '古印', '汉人', '秦汉',
                          '宋元', '诗文', '金石', '书画', '铁笔', '铜玉', '款识',
                          '诸生', '进士', '布衣', '明经', '举人', '秀才', '博士',
                          '山人', '处士', '徵士', '征士', '精鉴', '皆能', '无不',
                          '皆工', '皆善', '妙品', '逸品', '神品', '第一', '最工'}
            if (style_name in stop_words or len(style_name) > 5 or
                any('\u3000' <= c <= '\u303f' for c in style_name)):
                continue
            style_text = text[max(0, m.start()-5):min(len(text), m.end()+5)]
            # 这个字号可能属于其他人，但为了简单，先都关联到主人物
            # 只有当是主人物字号且尚未添加时才关联
            key = ("字号", style_name)
            if key not in seen_entities:
                add_entity("字号", style_name, style_text)
                # 如果在介绍段内，关联到主人物
                if intro_pattern and m.start() < len(intro_pattern.group(0)) + main_person_pos:
                    add_relation("字号对应", person_name, style_name, style_text)

    # ====== 第三步：识别籍贯/活动地 ======
    # 模式：XX人、XX诸生、XX布衣、居XX、家于XX、XX籍、XX人
    place_patterns = [
        (r'([\u4e00-\u9fa5]{1,8})人[。，, ]', "籍贯"),
        (r'([\u4e00-\u9fa5]{1,8})人[，,。]', "籍贯"),
        (r'居([\u4e00-\u9fa5]{1,6})[，,。 ]', "活动于"),
        (r'家于([\u4e00-\u9fa5]{1,6})[，,。 ]', "籍贯"),
        (r'家住([\u4e00-\u9fa5]{1,6})[，,。 ]', "籍贯"),
        (r'侨居([\u4e00-\u9fa5]{1,6})[，,。 ]', "活动于"),
    ]

    # 主人物籍贯（在介绍段内）
    if intro_pattern:
        intro_full = intro_pattern.group(0)
        place_match = re.search(r'([\u4e00-\u9fa5]{1,8})人[，,。]', intro_full)
        if place_match:
            place = place_match.group(1)
            # 去除前缀冗余
            place = re.sub(r'^(之|其|为|则|而|以|于)', '', place)
            if 1 < len(place) <= 8 and place not in {'印人', '山人', '诸生', '布衣', '明经', '举人', '进士'}:
                pl_text = text[place_match.start():place_match.end()]
                add_entity("地名", place, pl_text)
                add_relation("籍贯", person_name, place, pl_text)

    # 其他地名（活动地）
    for pattern, rtype in place_patterns:
        for m in re.finditer(pattern, text):
            place = m.group(1)
            place = re.sub(r'^(之|其|为|则|而|以|于)', '', place)
            stop_places = {'印人', '山人', '诸生', '布衣', '明经', '举人', '进士', '此', '他', '是', '何', '吾'}
            if (place in stop_places or len(place) > 8 or len(place) < 2 or
                any('[\u3000-\u303f\uff00-\uffef]' in c for c in place)):
                continue
            pl_text = find_window(text, m.start(), 10)
            # 检查是否已添加过
            key = ("地名", place)
            if key not in seen_entities:
                add_entity("地名", place, pl_text)
                # 只对前2个明显的地名关联关系，避免过度
                if sum(1 for e in entities if e['type'] == "地名") <= 3:
                    add_relation(rtype, person_name, place, pl_text)

    # ====== 第四步：识别朝代/时间 ======
    time_patterns = [
        r'([康雍乾嘉道咸同光宣][\u4e00-\u9fa5]{0,3})[年年间进士]',
        r'([康雍乾嘉道咸同光宣][\u4e00-\u9fa5]{0,4})进士',
        r'([康雍乾嘉道咸同光宣][\u4e00-\u9fa5]{0,4})举人',
        r'([\u4e00-\u9fa5]{2,5})[年间年]',
        r'(崇祯|万历|嘉靖|正德|弘治|成化|正统|永乐|洪武|天启)',
        r'(康熙|雍正|乾隆|嘉庆|道光|咸丰|同治|光绪|宣统)',
        r'(甲申|乙酉|丙戌|丁亥|戊子|己丑|庚寅|辛卯|壬辰|癸巳|甲午|乙未|丙申|丁酉|戊戌|己亥|庚子|辛丑|壬寅|癸卯|甲辰|乙巳|丙午|丁未|戊申|己酉|庚戌|辛亥)',
        r'(国朝|本朝|前明|明季|明末|清初|清末)',
    ]

    time_stop_words = {'所著', '篆刻', '书法', '印章', '图章', '印人', '山水', '精鉴',
                       '工诗', '善画', '兼工', '亦工', '尤工', '最工', '喜治', '工于',
                       '所制', '所作', '所藏', '所蓄', '所收', '所为', '所画', '所书',
                       '铁笔', '款识', '秦汉', '汉人', '古印', '金石', '书画', '诗文',
                       '山水', '花鸟', '人物', '白描', '设色', '没骨', '泼墨', '写意',
                       '篆刻', '刻印', '治印', '印谱', '印章', '图章', '摹印', '篆印'}

    for pattern in time_patterns:
        for m in re.finditer(pattern, text):
            time_name = m.group(1) if m.groups() else m.group(0)
            if time_name in time_stop_words or len(time_name) > 10 or len(time_name) < 2:
                continue
            if not any('\u4e00' <= c <= '\u9fff' for c in time_name):
                continue
            key = ("时间", time_name)
            if key in seen_entities:
                continue
            tm_text = find_window(text, m.start(), 10)
            add_entity("时间", time_name, tm_text)
            # 仅对前2个时间点关联
            if sum(1 for e in entities if e['type'] == "时间") <= 2:
                add_relation("生于", person_name, time_name, tm_text)

    # ====== 第五步：识别作品/印谱 ======
    # 模式：《XX》、著有《XX》、有《XX印谱》、《XX集》
    work_patterns = [
        r'[《]([^《》\s]{1,20})[》]',
        r'著有[《《]?([\u4e00-\u9fa5A-Za-z0-9]{1,20})[》》]?',
        r'有[《《]([^《》\s]{1,20})[》》]',
    ]

    work_stop_words = {'印人传合集', '印人传', '广印人传', '续印人传', '读画录',
                       '书影', '闽小纪', '印史', '画史汇传', '国朝画识',
                       '闽中书画姓氏录', '昼史汇传', '画识'}

    # 先收集《》中的作品
    for m in re.finditer(r'[《]([^《》\s]{1,20})[》]', text):
        work_name = m.group(1)
        if work_name in work_stop_words or len(work_name) > 15:
            continue
        # 判断是否是印谱/作品集
        is_work = any(k in work_name for k in ['印谱', '印史', '印萃', '印式', '印稿',
                                               '印存', '印举', '印款', '印识', '诗钞',
                                               '诗抄', '诗集', '文集', '词钞', '词集',
                                               '诗话', '画识', '画谱', '墨谱', '款识',
                                               '诗品', '印文', '印说', '印考', '印辨',
                                               '印笺', '印评', '印略', '印笺'])
        if is_work or '印' in work_name or '谱' in work_name or '诗' in work_name:
            key = ("作品", work_name)
            if key not in seen_entities:
                wk_text = find_window(text, m.start(), 15)
                add_entity("作品", work_name, wk_text)
                add_relation("著有", person_name, work_name, wk_text)

    # 著有XX
    for m in re.finditer(r'著有[《《]?([\u4e00-\u9fa5A-Za-z0-9]{2,20})[》》]?', text):
        work_name = m.group(1)
        if work_name in work_stop_words or len(work_name) > 15:
            continue
        key = ("作品", work_name)
        if key not in seen_entities:
            wk_text = find_window(text, m.start(), 15)
            add_entity("作品", work_name, wk_text)
            add_relation("著有", person_name, work_name, wk_text)

    # ====== 第六步：识别印章/印风 ======
    style_keywords = ['苍深雅健', '苍秀', '古雅', '浑朴', '工致', '遒劲', '秀雅',
                     '雄浑', '典雅', '精能', '逸致', '天趣', '神韵', '精妙', '精绝',
                     '神妙', '苍劲', '苍老', '苍古', '秀丽', '秀逸', '温润', '典雅',
                     '古朴', '古拙', '古逸', '古雅', '圆转', '瘦硬', '丰腴', '端庄',
                     '奇崛', '奇肆', '奇异', '奇古', '奇趣', '工细', '工整', '精严',
                     '精雅', '精整', '精妙', '精工', '婉转', '流美', '流畅', '生动',
                     '生意', '生趣', '超脱', '超然', '逸品', '神品', '妙品', '能品',
                     '篆法', '章法', '刀法', '布局', '结构', '笔意', '笔力', '气韵']

    for kw in style_keywords:
        if kw in text:
            pos = text.find(kw)
            key = ("书体印风", kw)
            if key not in seen_entities:
                wk_text = find_window(text, pos, 10)
                add_entity("书体印风", kw, wk_text)
                if sum(1 for e in entities if e['type'] == "书体印风") <= 3:
                    add_relation("擅长", person_name, kw, wk_text)

    # 识别篆刻相关的技能描述
    skill_patterns = [
        (r'工([\u4e00-\u9fa5]{1,4}刻印)[，,。 ]', "擅长"),
        (r'善([\u4e00-\u9fa5]{0,4}印[\u4e00-\u9fa5]{0,4})', "擅长"),
        (r'精([\u4e00-\u9fa5]{0,4}篆[\u4e00-\u9fa5]{0,4})', "擅长"),
        (r'擅长([\u4e00-\u9fa5]{1,6})', "擅长"),
        (r'善治([\u4e00-\u9fa5]{1,6})', "擅长"),
        (r'喜治([\u4e00-\u9fa5]{1,6})', "擅长"),
    ]

    for pattern, rtype in skill_patterns:
        for m in re.finditer(pattern, text):
            skill = m.group(1)
            if len(skill) > 10 or len(skill) < 2:
                continue
            if skill in {'此技', '斯技', '篆刻', '铁笔', '印章', '图章', '六书', '八法',
                         '古文', '汉隶', '书法', '山水', '花鸟', '人物', '兰竹', '墨梅',
                         '墨竹', '白描', '设色', '没骨', '泼墨', '写意', '工笔', '篆隶',
                         '行楷', '真草', '篆籀', '钟鼎', '款识', '秦汉', '汉人', '古印',
                         '金石', '书画', '诗文', '诗词', '经史', '考据', '赏鉴', '鉴别'}:
                # 这些是有效技能
                pass
            key = ("书体印风", skill)
            if key not in seen_entities and any('\u4e00' <= c <= '\u9fff' for c in skill):
                sk_text = find_window(text, m.start(), 10)
                add_entity("书体印风", skill, sk_text)
                if sum(1 for e in entities if e['type'] == "书体印风") <= 5:
                    add_relation(rtype, person_name, skill, sk_text)

    # ====== 第七步：识别流派 ======
    school_keywords = ['文何', '莆田派', '浙派', '徽派', '皖派', '黄山派', '如皋派',
                      '泗水派', '云间派', '娄东派', '虞山派', '扬州派', '西泠八家',
                      '四家', '八家', '徽皖', '浙皖', '秦汉派', '汉印派', '元朱文']
    for kw in school_keywords:
        if kw in text:
            pos = text.find(kw)
            key = ("流派", kw)
            if key not in seen_entities:
                sc_text = find_window(text, pos, 10)
                add_entity("流派", kw, sc_text)
                add_relation("流派归属", person_name, kw, sc_text)

    # ====== 第八步：识别其他人物 ======
    # 模式：XX，字XX；XX，号XX；与XX游；师XX；从XX学；XX传；XX叙
    other_person_patterns = [
        r'([\u4e00-\u9fa5]{2,4})，字[\u4e00-\u9fa5]{1,4}',
        r'([\u4e00-\u9fa5]{2,4})，号[\u4e00-\u9fa5]{1,4}',
        r'[与从师事友交游]?([\u4e00-\u9fa5]{2,4})游',
        r'师([\u4e00-\u9fa5]{2,4})',
        r'从([\u4e00-\u9fa5]{2,4})学',
        r'([\u4e00-\u9fa5]{2,4})传',
        r'([\u4e00-\u9fa5]{2,4})叙而行之',
        r'([\u4e00-\u9fa5]{2,4})[，,。]字',
        r'同里([\u4e00-\u9fa5]{2,4})',
        r'([\u4e00-\u9fa5]{2,4})之[子嗣弟子孙]',
        r'([\u4e00-\u9fa5]{2,4})子',
        r'([\u4e00-\u9fa5]{2,4})孙',
        r'([\u4e00-\u9fa5]{2,4})弟',
    ]

    person_stop_words = {'工诗', '善画', '兼工', '亦工', '尤工', '最工', '所著', '所制',
                        '所作', '所为', '所藏', '所蓄', '所收', '篆刻', '书法', '印章',
                        '图章', '印人', '山水', '花鸟', '人物', '白描', '设色', '没骨',
                        '泼墨', '写意', '精鉴', '精于', '长于', '善于', '工于', '能诗',
                        '能书', '能画', '能篆', '能刻', '诗文', '金石', '书画', '铁笔',
                        '款识', '秦汉', '汉人', '古印', '六书', '八法', '古文', '汉隶',
                        '精研', '深究', '博雅', '嗜古', '好古', '博古', '考古', '鉴古',
                        '此印', '斯印', '是印', '此谱', '斯谱', '是谱', '此技', '斯技',
                        '此书', '斯书', '是书', '此册', '斯册', '是册', '此卷', '斯卷',
                        '是卷', '此编', '斯编', '是编', '此本', '斯本', '是本', '此君',
                        '此老', '斯人', '是人', '此公', '斯公', '是公', '诸生', '进士',
                        '举人', '布衣', '明经', '山人', '处士', '徵士', '征士', '秀才',
                        '晚年', '少时', '早岁', '中年', '生平', '平生', '为人', '性好',
                        '性嗜', '性喜', '性爱', '所好', '所喜', '所嗜', '所藏', '所蓄',
                        '所收', '所交', '所游', '所知', '所得', '所诣', '所成', '所至',
                        '所居', '所在', '所出', '所自', '所由', '所以', '所为', '所与',
                        '同里', '同乡', '同郡', '同县', '同邑', '同宗', '同族', '同年',
                        '门下', '门墙', '弟子', '门生', '受业', '问业', '请业', '执经',
                        '善篆刻', '工篆刻', '精篆刻', '喜篆刻', '精铁笔', '工铁笔',
                        '善铁笔', '工刻印', '善刻印', '精刻印', '喜刻印', '工治印',
                        '善治印', '精治印', '喜治印', '工篆印', '善篆印', '精篆印',
                        '工书法', '善书法', '精书法', '工诗', '善诗', '能诗', '工画',
                        '善画', '能画', '工古文', '善古文', '工词章', '善词章', '工诗画',
                        '善诗画', '工书画', '善书画', '精赏鉴', '善赏鉴', '精鉴别',
                        '善鉴别', '精考据', '善考据', '精金石', '善金石', '精六书',
                        '善六书', '精八法', '善八法', '工汉隶', '善汉隶', '工篆隶',
                        '善篆隶', '工行楷', '善行楷', '工真草', '善真草', '工白描',
                        '善白描', '工设色', '善设色', '工没骨', '善没骨', '工泼墨',
                        '善泼墨', '工写意', '善写意', '工山水', '善山水', '工花鸟',
                        '善花鸟', '工人物', '善人物', '工兰竹', '善兰竹', '工墨梅',
                        '善墨梅', '工墨竹', '善墨竹', '精篆刻', '善篆刻', '工刻印',
                        '铁笔', '印章', '图章', '印谱', '篆刻', '刻印', '治印', '篆印',
                        '摹印', '雕印', '镌印', '制印', '作印', '铸印', '凿印', '琢印',
                        '博古', '鉴古', '考古', '赏古', '嗜古', '好古', '精古', '善古',
                        '所著', '所作', '所为', '所制', '所画', '所书', '所刻', '所篆',
                        '所镌', '所摹', '所藏', '所蓄', '所收', '所辑', '所编', '所选',
                        '所录', '所钞', '所抄', '所识', '所记', '所述', '所言', '所载',
                        '所传', '所闻', '所见', '所知', '所交', '所游', '所与', '所诣',
                        '所至', '所成', '所居', '所在', '所出', '所自', '所由', '所以',
                        '工六法', '善六法', '精六法', '得六法', '通六法', '解六法',
                        '谙六法', '晓六法', '明六法', '悟六法', '研六法', '究六法',
                        '精篆隶', '善篆隶', '工篆隶', '能篆隶', '精八分', '善八分',
                        '工八分', '能八分', '精古文', '善古文', '工古文', '能古文',
                        '工钟鼎', '善钟鼎', '精钟鼎', '能钟鼎', '工款识', '善款识',
                        '精款识', '能款识', '工秦汉', '善秦汉', '精秦汉', '能秦汉',
                        '工汉印', '善汉印', '精汉印', '能汉印', '工秦印', '善秦印',
                        '精秦印', '能秦印', '工古印', '善古印', '精古印', '能古印',
                        '工印谱', '善印谱', '精印谱', '能印谱', '藏印谱', '蓄印谱',
                        '收印谱', '辑印谱', '编印谱', '选印谱', '录印谱', '钞印谱',
                        '抄印谱', '识印谱', '记印谱', '述印谱', '言印谱', '载印谱',
                        '传印谱', '闻印谱', '见印谱', '知印谱', '交印谱', '游印谱',
                        '与印谱', '诣印谱', '至印谱', '成印谱', '居印谱', '在印谱',
                        '出印谱', '自印谱', '由印谱', '以印谱', '为印谱', '刻印谱',
                        '篆印谱', '摹印谱', '雕印谱', '镌印谱', '制印谱', '作印谱',
                        '铸印谱', '凿印谱', '琢印谱', '博印谱', '鉴印谱', '考印谱',
                        '赏印谱', '嗜印谱', '好印谱', '精印谱', '善印谱', '工印谱',
                        '精于印', '善于印', '工于印', '能于印', '精于篆刻', '善于篆刻',
                        '工于篆刻', '能于篆刻', '精于铁笔', '善于铁笔', '工于铁笔',
                        '能于铁笔', '精于刻印', '善于刻印', '工于刻印', '能于刻印',
                        '精于治印', '善于治印', '工于治印', '能于治印', '精于篆印',
                        '善于篆印', '工于篆印', '能于篆印', '精于摹印', '善于摹印',
                        '工于摹印', '能于摹印', '精于雕印', '善于雕印', '工于雕印',
                        '能于雕印', '精于镌印', '善于镌印', '工于镌印', '能于镌印',
                        '精于制印', '善于制印', '工于制印', '能于制印', '精于作印',
                        '善于作印', '工于作印', '能于作印', '精于铸印', '善于铸印',
                        '工于铸印', '能于铸印', '精于凿印', '善于凿印', '工于凿印',
                        '能于凿印', '精于琢印', '善于琢印', '工于琢印', '能于琢印'}

    for pattern in other_person_patterns:
        for m in re.finditer(pattern, text):
            other_p = m.group(1)
            if (other_p == person_name or other_p in person_stop_words or
                len(other_p) < 2 or len(other_p) > 4):
                continue
            if not all('\u4e00' <= c <= '\u9fff' for c in other_p):
                continue
            key = ("人物", other_p)
            if key not in seen_entities:
                op_text = find_window(text, m.start(), 15)
                add_entity("人物", other_p, op_text)

                # 判断关系类型
                pattern_str = pattern
                if '师' in pattern_str or '从' in pattern_str and '学' in pattern_str:
                    add_relation("师承", person_name, other_p, op_text)
                elif '子' in pattern_str or '嗣' in pattern_str or '孙' in pattern_str:
                    add_relation("父子", other_p, person_name, op_text)
                elif '游' in pattern_str or '同里' in pattern_str:
                    add_relation("交游", person_name, other_p, op_text)
                elif '叙' in pattern_str or '传' in pattern_str:
                    add_relation("交游", person_name, other_p, op_text)
                elif sum(1 for e in entities if e['type'] == "人物") <= 5:
                    add_relation("交游", person_name, other_p, op_text)

    # 如果没有任何实体，至少添加主人物
    if not entities:
        add_entity("人物", person_name, text[:50])

    # 如果没有任何关系，至少添加一个基本关系
    if not relations and len(entities) >= 2:
        # 添加主人物和第一个地名的关系
        places = [e for e in entities if e['type'] == "地名"]
        if places:
            add_relation("籍贯", person_name, places[0]['name'], text[:30])

    return entities, relations


def main():
    records = json.load(open('person_records_v5.json', 'r', encoding='utf-8'))

    # 先找出空结果的记录
    empty_records = []
    for i, rec in enumerate(records):
        rid = rec['record_id']
        fpath = f"extraction_results/{rid}_extraction.json"
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if len(data.get('entities', [])) == 0 and len(data.get('relations', [])) == 0:
                empty_records.append((i, rec))
        else:
            empty_records.append((i, rec))

    print(f"共 {len(empty_records)} 条空结果记录需要重新处理")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    total_entities = 0
    total_relations = 0
    processed = 0

    for idx, rec in empty_records:
        entities, relations = extract_from_record(rec)
        result = {
            "record_id": rec['record_id'],
            "person_name": rec['person_name'],
            "entities": entities,
            "relations": relations
        }
        with open(f"extraction_results/{rec['record_id']}_extraction.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        total_entities += len(entities)
        total_relations += len(relations)
        processed += 1

        if processed % 50 == 0 or processed == len(empty_records):
            print(f"  [{processed}/{len(empty_records)}] {rec['record_id']} - {rec['person_name']}: "
                  f"E:{len(entities)} R:{len(relations)} | 累计 E:{total_entities} R:{total_relations}")

    print(f"\n完成！共处理 {processed} 条记录")
    print(f"累计: 实体 {total_entities}, 关系 {total_relations}")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
