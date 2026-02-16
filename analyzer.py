"""
捡漏分析引擎
核心逻辑：计算利润率、评估机会质量、发现捡漏
"""
import logging
from wine_list import (
    PREMIUM_WINES, calculate_profit_rate, calculate_total_cost,
    get_shipping_cost, DEFAULT_PROFIT_THRESHOLD
)

logger = logging.getLogger(__name__)


def analyze_opportunity(wine_info: dict, wine_config: dict, profit_threshold: float = None) -> dict | None:
    """
    分析一条酒的价格数据，判断是否为捡漏机会

    参数:
      wine_info: 从爬虫获取的数据 {wine_name, global_lowest, hk_avg_price_usd, ...}
      wine_config: 保值酒配置 {name, region, category}
      profit_threshold: 利润阈值（百分比）

    返回:
      捡漏机会 dict 或 None（不满足条件）
    """
    if profit_threshold is None:
        profit_threshold = DEFAULT_PROFIT_THRESHOLD

    if not wine_info.get("found") or not wine_info.get("global_lowest"):
        return None

    global_lowest = wine_info["global_lowest"]
    buy_price = global_lowest["price_usd"]
    hk_avg = wine_info.get("hk_avg_price_usd")

    if not hk_avg or hk_avg <= 0 or buy_price <= 0:
        return None

    # 合理性校验：单瓶酒价格应在 $10-$20000 范围内
    if buy_price < 10 or buy_price > 20000:
        logger.warning(f"⚠️ 买入价异常 ({wine_config['name']}): {buy_price:.2f} USD，跳过")
        return None
    if hk_avg < 10 or hk_avg > 50000:
        logger.warning(f"⚠️ 港卖价异常 ({wine_config['name']}): {hk_avg:.2f} USD，跳过")
        return None

    # 港卖价不应超过买入价 10 倍（极端异常）
    if hk_avg > buy_price * 10:
        logger.warning(
            f"⚠️ 价差异常 ({wine_config['name']}): 买{buy_price:.0f} USD 卖{hk_avg:.0f} USD，跳过"
        )
        return None

    region = wine_config.get("region", "default")
    profit_rate = calculate_profit_rate(buy_price, hk_avg, region, is_case=True)

    # 利润率上限 500%，超过视为数据错误
    if profit_rate > 500:
        logger.warning(f"⚠️ 利润率异常 ({wine_config['name']}): {profit_rate:.1f}%，跳过")
        return None

    if profit_rate < profit_threshold:
        return None

    total_cost = calculate_total_cost(buy_price, region, is_case=True)

    # 机会评分 (1-10)
    score = _calculate_score(profit_rate, buy_price, hk_avg, wine_config)

    opportunity = {
        "wine_name": wine_config["name"],
        "vintage": wine_info.get("vintage", ""),
        "region": region,
        "category": wine_config.get("category", ""),
        "buy_price": round(buy_price, 2),
        "buy_currency": global_lowest.get("currency", "USD"),
        "buy_merchant": global_lowest.get("merchant", ""),
        "buy_country": global_lowest.get("country", ""),
        "buy_url": global_lowest.get("url", ""),
        "sell_price_hk": round(hk_avg, 2),
        "total_cost": round(total_cost, 2),
        "profit_rate": round(profit_rate, 1),
        "score": str(score),
        "data_source": "wine-searcher",
        "shipping_cost": get_shipping_cost(region, is_case=True),
    }

    logger.info(
        f"🍷 发现捡漏: {wine_config['name']} | "
        f"买入: {buy_price:.0f} USD | 卖出: {hk_avg:.0f} USD | "
        f"利润率: {profit_rate:.1f}% | 评分: {score}/10"
    )

    return opportunity


def _calculate_score(profit_rate: float, buy_price: float,
                     sell_price: float, wine_config: dict) -> int:
    """
    计算机会评分 (1-10)
    考虑因素：利润率、类别权重、价格合理性
    """
    score = 0

    # 利润率评分 (最高 4 分)
    if profit_rate >= 50:
        score += 4
    elif profit_rate >= 30:
        score += 3
    elif profit_rate >= 20:
        score += 2
    elif profit_rate >= 15:
        score += 1

    # 类别权重 (最高 3 分)
    category = wine_config.get("category", "")
    if "一级庄" in category or "顶级" in category:
        score += 3
    elif "超二级" in category or "右岸" in category:
        score += 2
    elif "名庄" in category or "硬通货" in category:
        score += 2
    else:
        score += 1

    # 价格区间合理性 (最高 2 分)
    if 50 <= buy_price <= 5000:
        score += 2  # 适合炒酒的价格区间
    elif buy_price < 50:
        score += 0  # 太便宜可能不保值
    else:
        score += 1  # 太贵风险大

    # 额外加分：差价绝对值大
    if (sell_price - buy_price) > 100:
        score += 1

    return min(score, 10)


def batch_analyze(wine_results: list, profit_threshold: float = None) -> list:
    """
    批量分析多款酒，返回符合条件的捡漏机会列表
    """
    opportunities = []

    for wine_config in PREMIUM_WINES:
        wine_name = wine_config["name"]
        wine_info = next((w for w in wine_results if w.get("wine_name") == wine_name), None)

        if not wine_info:
            continue

        opp = analyze_opportunity(wine_info, wine_config, profit_threshold)
        if opp:
            opportunities.append(opp)

    # 按利润率降序排序
    opportunities.sort(key=lambda x: x["profit_rate"], reverse=True)
    return opportunities
