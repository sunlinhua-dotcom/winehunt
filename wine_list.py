"""
保值酒知识库 — 硬通货清单
包含全球公认的保值型葡萄酒，用于定时扫描和捡漏发现
"""

# 保值酒清单：每条包含 name（搜索关键词）、region（产区）、category（分类）
# ══════════════════════════════════════════
# 核心扫描清单 — 20 款高流通性硬通货（节省 API 额度）
# 标准: 国际拍卖/二手市场最活跃、价格透明度最高
# ══════════════════════════════════════════
PREMIUM_WINES = [
    # ── 波尔多一级庄（5 款，必扫）──
    {"name": "Chateau Lafite Rothschild", "region": "Bordeaux", "category": "波尔多一级庄"},
    {"name": "Chateau Latour", "region": "Bordeaux", "category": "波尔多一级庄"},
    {"name": "Chateau Mouton Rothschild", "region": "Bordeaux", "category": "波尔多一级庄"},
    {"name": "Chateau Margaux", "region": "Bordeaux", "category": "波尔多一级庄"},
    {"name": "Chateau Haut-Brion", "region": "Bordeaux", "category": "波尔多一级庄"},

    # ── 波尔多右岸顶级（3 款）──
    {"name": "Petrus", "region": "Bordeaux", "category": "波尔多右岸"},
    {"name": "Chateau Cheval Blanc", "region": "Bordeaux", "category": "波尔多右岸"},
    {"name": "Chateau Angelus", "region": "Bordeaux", "category": "波尔多右岸"},

    # ── 勃艮第顶级（3 款）──
    {"name": "Domaine de la Romanee-Conti", "region": "Burgundy", "category": "勃艮第顶级"},
    {"name": "Domaine Leroy", "region": "Burgundy", "category": "勃艮第顶级"},
    {"name": "Domaine Armand Rousseau", "region": "Burgundy", "category": "勃艮第顶级"},

    # ── 意大利名庄（3 款）──
    {"name": "Sassicaia", "region": "Italy", "category": "意大利名庄"},
    {"name": "Ornellaia", "region": "Italy", "category": "意大利名庄"},
    {"name": "Masseto", "region": "Italy", "category": "意大利名庄"},

    # ── 新世界硬通货（3 款）──
    {"name": "Penfolds Grange", "region": "Australia", "category": "新世界硬通货"},
    {"name": "Opus One", "region": "USA", "category": "新世界硬通货"},
    {"name": "Screaming Eagle", "region": "USA", "category": "新世界硬通货"},

    # ── 香槟（2 款）──
    {"name": "Dom Perignon", "region": "Champagne", "category": "香槟名庄"},
    {"name": "Louis Roederer Cristal", "region": "Champagne", "category": "香槟名庄"},

    # ── 罗纳河谷（1 款）──
    {"name": "Guigal La Mouline", "region": "Rhone", "category": "罗纳河谷"},
]

# ══════════════════════════════════════════
# 完整备选清单 — 全部 50 款（供手动搜索或未来扩展）
# ══════════════════════════════════════════
EXTENDED_WINES = [
    # ── 波尔多超级二级庄 ──
    {"name": "Chateau Leoville Las Cases", "region": "Bordeaux", "category": "波尔多超二级庄"},
    {"name": "Chateau Cos d'Estournel", "region": "Bordeaux", "category": "波尔多超二级庄"},
    {"name": "Chateau Ducru-Beaucaillou", "region": "Bordeaux", "category": "波尔多超二级庄"},
    {"name": "Chateau Palmer", "region": "Bordeaux", "category": "波尔多超二级庄"},
    {"name": "Chateau Pichon Longueville Comtesse de Lalande", "region": "Bordeaux", "category": "波尔多超二级庄"},
    {"name": "Chateau Lynch-Bages", "region": "Bordeaux", "category": "波尔多超二级庄"},
    {"name": "Chateau Pontet-Canet", "region": "Bordeaux", "category": "波尔多超二级庄"},

    # ── 波尔多右岸补充 ──
    {"name": "Chateau Ausone", "region": "Bordeaux", "category": "波尔多右岸"},
    {"name": "Le Pin", "region": "Bordeaux", "category": "波尔多右岸"},
    {"name": "Chateau Pavie", "region": "Bordeaux", "category": "波尔多右岸"},

    # ── 勃艮第补充 ──
    {"name": "Domaine Comte Georges de Vogue", "region": "Burgundy", "category": "勃艮第顶级"},
    {"name": "Domaine Georges Roumier", "region": "Burgundy", "category": "勃艮第顶级"},
    {"name": "Domaine Coche-Dury", "region": "Burgundy", "category": "勃艮第顶级"},
    {"name": "Domaine Leflaive", "region": "Burgundy", "category": "勃艮第顶级"},

    # ── 意大利补充 ──
    {"name": "Tignanello", "region": "Italy", "category": "意大利名庄"},
    {"name": "Solaia", "region": "Italy", "category": "意大利名庄"},
    {"name": "Gaja Barbaresco", "region": "Italy", "category": "意大利名庄"},
    {"name": "Giacomo Conterno Barolo Monfortino", "region": "Italy", "category": "意大利名庄"},

    # ── 新世界补充 ──
    {"name": "Penfolds Bin 389", "region": "Australia", "category": "新世界硬通货"},
    {"name": "Penfolds Bin 407", "region": "Australia", "category": "新世界硬通货"},
    {"name": "Harlan Estate", "region": "USA", "category": "新世界硬通货"},
    {"name": "Almaviva", "region": "Chile", "category": "新世界硬通货"},
    {"name": "Vega Sicilia Unico", "region": "Spain", "category": "新世界硬通货"},

    # ── 香槟补充 ──
    {"name": "Krug Grande Cuvee", "region": "Champagne", "category": "香槟名庄"},
    {"name": "Salon Le Mesnil", "region": "Champagne", "category": "香槟名庄"},
    {"name": "Bollinger La Grande Annee", "region": "Champagne", "category": "香槟名庄"},

    # ── 罗纳河谷补充 ──
    {"name": "Guigal La Landonne", "region": "Rhone", "category": "罗纳河谷"},
    {"name": "Guigal La Turque", "region": "Rhone", "category": "罗纳河谷"},
    {"name": "Chateau Rayas", "region": "Rhone", "category": "罗纳河谷"},
    {"name": "Chapoutier Ermitage Le Pavillon", "region": "Rhone", "category": "罗纳河谷"},
]

# 供前端「硬通货清单」页面展示的完整列表
ALL_WINES = PREMIUM_WINES + EXTENDED_WINES

# 运费模型（美元/瓶）
SHIPPING_COSTS = {
    "Bordeaux": {"per_bottle_case": 7, "per_bottle_single": 12},
    "Burgundy": {"per_bottle_case": 7, "per_bottle_single": 12},
    "Rhone": {"per_bottle_case": 7, "per_bottle_single": 12},
    "Italy": {"per_bottle_case": 7, "per_bottle_single": 12},
    "Champagne": {"per_bottle_case": 7, "per_bottle_single": 12},
    "USA": {"per_bottle_case": 20, "per_bottle_single": 25},
    "Australia": {"per_bottle_case": 20, "per_bottle_single": 25},
    "Chile": {"per_bottle_case": 18, "per_bottle_single": 23},
    "Spain": {"per_bottle_case": 7, "per_bottle_single": 12},
    "default": {"per_bottle_case": 15, "per_bottle_single": 20},
}

# 保险费率
INSURANCE_RATE = 0.025  # 2.5%

# 利润阈值
DEFAULT_PROFIT_THRESHOLD = 15  # 15%


def get_shipping_cost(region: str, is_case: bool = True) -> float:
    """获取运费"""
    costs = SHIPPING_COSTS.get(region, SHIPPING_COSTS["default"])
    return costs["per_bottle_case"] if is_case else costs["per_bottle_single"]


def calculate_total_cost(buy_price: float, region: str, is_case: bool = True) -> float:
    """计算全入成本 = 购买价 + 运费 + 保险"""
    shipping = get_shipping_cost(region, is_case)
    insurance = buy_price * INSURANCE_RATE
    return buy_price + shipping + insurance


def calculate_profit_rate(buy_price: float, sell_price: float, region: str, is_case: bool = True) -> float:
    """计算利润率"""
    total_cost = calculate_total_cost(buy_price, region, is_case)
    if total_cost <= 0:
        return 0
    return ((sell_price - total_cost) / total_cost) * 100
