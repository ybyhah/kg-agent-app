import json
import re

f = open('data/intermediate/entities.json', 'r', encoding='utf-8')
data = json.load(f)
f.close()

entities = data.get('entities', [])
total = len(entities)
print('读取到', total, '个实体')
print()

# 年号 → 朝代 映射（完整版本）
era_to_dynasty = {}

# 明朝年号
ming_eras = ['洪武', '建文', '永乐', '洪熙', '宣德', '正统', '景泰', '天顺',
             '成化', '弘治', '正德', '嘉靖', '隆庆', '万历', '泰昌', '天启', '崇祯']
for era in ming_eras:
    era_to_dynasty[era] = '明'

# 清朝年号
qing_eras = ['天命', '天聪', '崇德', '顺治', '康熙', '雍正', '乾隆', '嘉庆',
             '道光', '咸丰', '同治', '光绪', '宣统']
for era in qing_eras:
    era_to_dynasty[era] = '清'

# 宋朝年号
song_eras = ['建隆', '乾德', '开宝', '太平兴国', '雍熙', '端拱', '淳化', '至道',
             '咸平', '景德', '大中祥符', '天禧', '乾兴', '天圣', '明道', '景祐',
             '宝元', '康定', '庆历', '皇祐', '至和', '嘉祐', '治平', '熙宁',
             '元丰', '元祐', '绍圣', '元符', '建中靖国', '崇宁', '大观', '政和',
             '重和', '宣和', '靖康', '建炎', '绍兴', '隆兴', '乾道', '淳熙',
             '绍熙', '庆元', '嘉泰', '开禧', '嘉定', '宝庆', '绍定', '端平',
             '嘉熙', '淳祐', '宝祐', '开庆', '景定', '咸淳', '德祐', '景炎', '祥兴']
for era in song_eras:
    era_to_dynasty[era] = '宋'

# 唐朝年号
tang_eras = ['武德', '贞观', '永徽', '显庆', '龙朔', '麟德', '乾封', '总章',
             '咸亨', '上元', '仪凤', '调露', '永隆', '开耀', '永淳', '弘道',
             '嗣圣', '文明', '光宅', '垂拱', '永昌', '载初', '天授', '如意',
             '长寿', '延载', '证圣', '神功', '圣历', '久视', '大足', '长安',
             '神龙', '景龙', '唐隆', '景云', '太极', '延和', '先天', '开元',
             '天宝', '至德', '乾元', '宝应', '广德', '永泰', '大历', '建中',
             '兴元', '贞元', '永贞', '元和', '长庆', '宝历', '太和', '开成',
             '会昌', '大中', '咸通', '乾符', '广明', '中和', '光启', '文德',
             '龙纪', '大顺', '景福', '乾宁', '光化', '天复', '天祐']
for era in tang_eras:
    era_to_dynasty[era] = '唐'

# 元朝年号
yuan_eras = ['中统', '至元', '元贞', '大德', '至大', '皇庆', '延祐', '至治',
             '泰定', '致和', '天历', '至顺', '元统', '至正']
for era in yuan_eras:
    era_to_dynasty[era] = '元'

# 汉朝年号
han_eras = ['建武', '中元', '永平', '建初', '元和', '章和', '永元', '元兴',
            '延平', '永初', '元初', '永宁', '建光', '延光', '永建', '阳嘉',
            '永和', '汉安', '建康', '永嘉', '本初', '建和', '和平', '元嘉',
            '永兴', '永寿', '延熹', '永康', '建宁', '熹平', '光和', '中平',
            '初平', '兴平', '建安']
for era in han_eras:
    era_to_dynasty[era] = '汉'

# 科举 / 头衔 关键字（按优先级）
title_keywords_high = [
    '进士', '举人', '状元', '榜眼', '探花', '翰林', '贡生', '监生',
    '秀才', '生员', '廪生', '庠生', '明经', '孝廉',
]
title_keywords_mid = [
    '编修', '检讨', '庶吉士', '大学士', '协办大学士',
    '尚书', '侍郎', '郎中', '员外郎', '主事',
    '知府', '知县', '知州', '总督', '巡抚',
    '御史', '给事中', '詹事',
    '太傅', '太保', '太师', '少师', '少傅', '少保',
    '布政使', '按察使', '都指挥使',
    '将军', '总兵', '参将', '游击', '都尉',
    '刺史', '司马', '司空', '司徒', '司业',
    '丞相', '宰相', '相国',
    '国公', '侯', '伯', '公', '爵',
]
title_keywords_low = [
    '大夫', '寺丞', '主簿', '典史', '巡检', '县丞', '主簿', '吏目',
    '教授', '学正', '教谕', '训导', '博士',
    '中书', '通判', '推官', '经历', '知事',
]

# 谥号关键字（常见）
shi_keywords = ['文正', '文忠', '文襄', '文敏', '文清', '文恪', '文恭', '文端',
                '文达', '文懿', '文和', '文安', '文穆', '文简', '文勤', '文肃',
                '文毅', '文宪', '文庄', '文裕', '文义', '文靖', '文穆', '文宁',
                '武毅', '武勇', '武襄', '武烈', '武壮', '武愍', '武敬', '武节',
                '忠武', '忠烈', '忠毅', '忠敏', '忠简', '忠肃', '忠敬', '忠愍',
                '节愍', '烈愍', '庄烈', '贞愍', '恭毅', '恭简', '恭敏', '恭惠',
                '襄毅', '襄敏', '襄简', '襄勤', '襄烈', '端毅', '端简', '端敏',
                '文贞', '文定', '文洁', '文洁', '文靖', '文节', '文僖', '文慎',
                '献', '文', '武', '成', '康', '穆', '昭', '孝', '景', '桓',
                '威', '勇', '敏', '惠', '襄', '烈', '毅', '刚', '简', '肃',
                '恭', '敬', '庄', '安', '定', '戴', '思', '哀', '伤', '殇',
                '幽', '灵', '炀', '厉', '剌', '丑', '缪', '虚', '声', '声']


def extract_enhanced(source_text, person_name):
    info = {
        '字': '', '号': '', '籍贯': '', '朝代': '',
        '生年': '', '卒年': '', '谥号': '', '科举': '', '官职': ''
    }
    if not source_text:
        return info

    st = source_text.strip()

    # ============ 1. 提取 字 ============
    patterns_zi = [
        r'字[\s，,；;。:：]*([\u4e00-\u9fa5]{1,6})',
        r'字曰[\s，,]*([\u4e00-\u9fa5]{1,6})',
        r'又字[\s，,]*([\u4e00-\u9fa5]{1,6})',
        r'初字[\s，,]*([\u4e00-\u9fa5]{1,6})',
    ]
    for p in patterns_zi:
        m = re.search(p, st)
        if m:
            zi = m.group(1).strip()
            if zi and len(zi) >= 1 and zi not in ['某', '氏', '人', '号', '年']:
                info['字'] = zi
                break

    # ============ 2. 提取 号 ============
    patterns_hao = [
        r'号[\s，,；;。:：]*([\u4e00-\u9fa5]{1,10})',
        r'别号[\s，,]*([\u4e00-\u9fa5]{1,10})',
        r'又号[\s，,]*([\u4e00-\u9fa5]{1,10})',
        r'自号[\s，,]*([\u4e00-\u9fa5]{1,10})',
        r'晚号[\s，,]*([\u4e00-\u9fa5]{1,10})',
    ]
    for p in patterns_hao:
        m = re.search(p, st)
        if m:
            hao = m.group(1).strip()
            if hao and len(hao) >= 1 and hao not in ['某', '氏', '人', '字']:
                info['号'] = hao
                break

    # ============ 3. 提取 籍贯 ============
    patterns_place = [
        r'([\u4e00-\u9fa5]{2,8})人',
        r'([\u4e00-\u9fa5]{2,8})籍',
        r'籍([\u4e00-\u9fa5]{2,8})',
        r'籍贯[\s：:，,]*([\u4e00-\u9fa5]{2,10})',
        r'世居[\s：:，,]*([\u4e00-\u9fa5]{2,10})',
        r'居[\s：:，,]*([\u4e00-\u9fa5]{2,10})',
        r'家于[\s：:，,]*([\u4e00-\u9fa5]{2,10})',
    ]
    invalid_places = ['字号', '字', '号', '其', '此', '进士', '举', '以', '而',
                       '所', '者', '之', '为', '亦', '乃', '则', '曰', '某', '氏',
                       '人', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
                       '明', '清', '宋', '唐', '元', '汉', '万', '千', '百']
    for p in patterns_place:
        m = re.search(p, st)
        if m:
            place = m.group(1).strip()
            if len(place) >= 2 and place not in invalid_places:
                info['籍贯'] = place
                break

    # ============ 4. 提取 朝代 ============

    # 4a. 直接匹配朝代名
    dynasty_kw = [
        ('明', r'明[\s，,。；;朝年代国]'),
        ('清', r'清[\s，,。；;朝年代国]'),
        ('宋', r'宋[\s，,。；;朝年代国]'),
        ('元', r'元[\s，,。；;朝年代国]'),
        ('唐', r'唐[\s，,。；;朝年代国]'),
        ('汉', r'汉[\s，,。；;朝年代国]'),
        ('民国', r'民[国國]'),
        ('五代', r'五代'),
        ('晋', r'晋[\s，,。；;朝年代国]'),
        ('三国', r'三国'),
        ('隋', r'隋[\s，,。；;朝年代国]'),
        ('辽', r'辽[\s，,。；;朝年代国]'),
        ('金', r'金[\s，,。；;朝年代国]'),
        ('西夏', r'西夏'),
        ('南北朝', r'南北朝'),
    ]
    for dname, pattern in dynasty_kw:
        if re.search(pattern, st):
            info['朝代'] = dname
            break

    # 4b. 通过年号（按长度从长到短匹配，避免短词误匹）
    if not info['朝代']:
        eras_sorted = sorted(era_to_dynasty.keys(), key=lambda x: -len(x))
        for era in eras_sorted:
            if era in st:
                info['朝代'] = era_to_dynasty[era]
                break

    # 4c. 通过公元年份推断朝代
    if not info['朝代']:
        # 匹配 4 位数字年份（公元）
        year_ms = re.findall(r'(\d{3,4})', st)
        for y_str in year_ms:
            try:
                y = int(y_str)
                if 1368 <= y <= 1644:
                    info['朝代'] = '明'
                    break
                elif 1644 <= y <= 1911:
                    info['朝代'] = '清'
                    break
                elif 1912 <= y <= 1949:
                    info['朝代'] = '民国'
                    break
                elif 618 <= y <= 907:
                    info['朝代'] = '唐'
                    break
                elif 960 <= y <= 1279:
                    info['朝代'] = '宋'
                    break
                elif 202 <= y <= 220:
                    info['朝代'] = '汉'
                    break
                elif 1271 <= y <= 1368:
                    info['朝代'] = '元'
                    break
            except:
                pass

    # 4d. "明末" "清初" 等复合词
    if not info['朝代']:
        m = re.search(r'(明清|明末|清初|清末|宋代|唐代|元代|汉代|晋代|隋末|晚唐|北宋|南宋|三国|先明|前明)', st)
        if m:
            kw = m.group(1)
            if '明' in kw: info['朝代'] = '明'
            elif '清' in kw: info['朝代'] = '清'
            elif '宋' in kw: info['朝代'] = '宋'
            elif '唐' in kw: info['朝代'] = '唐'
            elif '元' in kw: info['朝代'] = '元'
            elif '汉' in kw: info['朝代'] = '汉'
            elif '晋' in kw: info['朝代'] = '晋'
            elif '三国' in kw: info['朝代'] = '三国'

    # ============ 5. 提取 生卒年 ============

    # 5a. 格式：XXXX年-YYYY年 / XXXX—YYYY / XXXX到YYYY
    m = re.search(r'(\d{3,4})[\s年年\-—～~至到\-]*(\d{2,4})[\s年]?', st)
    if m:
        birth = m.group(1)
        death_raw = m.group(2)
        if len(death_raw) == 2:
            death = birth[:2] + death_raw
        else:
            death = death_raw
        # 验证合理年份范围
        try:
            b_int = int(birth)
            d_int = int(death)
            if 500 <= b_int <= 2000 and 500 <= d_int <= 2000 and b_int < d_int:
                info['生年'] = birth
                info['卒年'] = death
        except:
            pass

    # 5b. 格式：生于XXXX年 / 生万历X年 / 生XXXX
    if not info['生年']:
        b_patterns = [
            r'(?:生于|生年|生于公元|生)[\s于公元年年月日第年元]*(\d{3,4})',
            r'(?:生于|生年)[\s于]*([\u4e00-\u9fa5]{2,4})[朝元]*?(\d{1,4})',
        ]
        for bp in b_patterns:
            bm = re.search(bp, st)
            if bm:
                info['生年'] = bm.group(1)
                break

    # 5c. 格式：卒于XXXX年 / 卒XXXX / 万历XX年卒 / 享年XX
    if not info['卒年']:
        d_patterns = [
            r'(?:卒于|卒年|去世|殁|逝世|卒|死)[\s于公元年月日第年]*(\d{3,4})',
        ]
        for dp in d_patterns:
            dm = re.search(dp, st)
            if dm:
                info['卒年'] = dm.group(1)
                break

    # 5d. 享年 / 享年XX岁 也提供一定信息
    if not info['卒年']:
        xiangnian_m = re.search(r'(?:享年|年|卒年|寿)(\d{2,3})', st)
        if xiangnian_m:
            # 只记录寿命，不强行推断生卒年
            # 但可作为辅助信息
            pass

    # ============ 6. 提取 谥号 ============
    if not info['谥号']:
        # 格式：谥XX / 谥号XX / 谥曰XX
        shi_m = re.search(r'谥[\s曰:：,，]*([\u4e00-\u9fa5]{1,6})', st)
        if shi_m:
            info['谥号'] = shi_m.group(1).strip()
        else:
            shi_m2 = re.search(r'谥号[\s曰:：,，]*([\u4e00-\u9fa5]{1,8})', st)
            if shi_m2:
                info['谥号'] = shi_m2.group(1).strip()
            else:
                # 直接搜常见谥号词
                for shi in shi_keywords:
                    if shi in st and len(shi) >= 2:
                        info['谥号'] = shi
                        break

    # ============ 7. 提取 科举 / 官职 ============
    for kw in title_keywords_high:
        if kw in st:
            info['科举'] = kw
            break

    for kw in title_keywords_mid:
        if kw in st:
            info['官职'] = kw
            break
    if not info['官职']:
        for kw in title_keywords_low:
            if kw in st:
                info['官职'] = kw
                break

    return info


# 增强的消歧规则
def enhanced_score(info):
    score = 0
    reasons = []
    if info['字']:
        score += 0.3
        reasons.append('字')
    if info['号']:
        score += 0.2
        reasons.append('号')
    if info['籍贯']:
        score += 0.15
        reasons.append('籍贯')
    if info['朝代']:
        score += 0.15
        reasons.append('朝代')
    if info['生年']:
        score += 0.15
        reasons.append('生年')
    if info['卒年']:
        score += 0.1
        reasons.append('卒年')
    if info['谥号']:
        score += 0.1
        reasons.append('谥号')
    if info['科举']:
        score += 0.1
        reasons.append('科举')
    if info['官职']:
        score += 0.1
        reasons.append('官职')
    return score, reasons


# ============ 统计 ============
aligned = 0
pending = 0
insufficient_data = 0
has_courtesy = 0
has_art = 0
has_place = 0
has_dynasty = 0
has_birth = 0
has_death = 0
has_shi = 0
has_keju = 0
has_guan = 0
aligned_list = []

for e in entities:
    name = e.get('name', '')
    source_text = e.get('source_text', '') or ''
    info = extract_enhanced(source_text, name)

    has_c = bool(info['字'])
    has_a = bool(info['号'])
    has_p = bool(info['籍贯'])
    has_dy = bool(info['朝代'])
    has_b = bool(info['生年'])
    has_de = bool(info['卒年'])
    has_sh = bool(info['谥号'])
    has_ke = bool(info['科举'])
    has_gu = bool(info['官职'])

    if has_c or has_a or has_p or has_dy or has_b or has_de or has_sh or has_ke or has_gu:
        score, reasons = enhanced_score(info)
        if score >= 0.15:
            aligned += 1
            aligned_list.append(name)
        else:
            pending += 1
    else:
        insufficient_data += 1

    if has_c: has_courtesy += 1
    if has_a: has_art += 1
    if has_p: has_place += 1
    if has_dy: has_dynasty += 1
    if has_b: has_birth += 1
    if has_de: has_death += 1
    if has_sh: has_shi += 1
    if has_ke: has_keju += 1
    if has_gu: has_guan += 1


# ============ 输出 ============
print('=' * 60)
print('消歧对齐结果分析（超级增强版）')
print('=' * 60)
print()
col1 = 45
col2 = 12
col3 = 12
def fmt(a, b, c):
    return str(a).ljust(col1) + str(b).ljust(col2) + str(c).ljust(col3)

print(fmt('aligned (已对齐)', aligned, str(round(aligned/total*100, 1)) + '%'))
print(fmt('pending (待对齐，有属性未查询)', pending, str(round(pending/total*100, 1)) + '%'))
print(fmt('insufficient_data (数据不足)', insufficient_data, str(round(insufficient_data/total*100, 1)) + '%'))
print(fmt('总计', total, '100%'))
print()
print('=' * 60)
print('属性统计')
print('=' * 60)
print()
print('有字号的实体数:'.ljust(22), str(has_courtesy))
print('有号的实体数:'.ljust(22), str(has_art))
print('有籍贯的实体数:'.ljust(22), str(has_place))
print('有朝代的实体数:'.ljust(22), str(has_dynasty))
print('有生年的实体数:'.ljust(22), str(has_birth))
print('有卒年的实体数:'.ljust(22), str(has_death))
print('有谥号的实体数:'.ljust(22), str(has_shi))
print('有科举的实体数:'.ljust(22), str(has_keju))
print('有官职的实体数:'.ljust(22), str(has_guan))
print()
print('=' * 60)
print('示例实体（aligned）')
print('=' * 60)
for name in aligned_list[:20]:
    print('  ', name)
