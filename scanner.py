"""
定时扫描模块
每30分钟自动扫描保值酒清单，发现捡漏机会
"""
import asyncio
import logging
from datetime import datetime
from wine_list import PREMIUM_WINES
from scraper import search_wine_basic
from analyzer import analyze_opportunity
from database import save_opportunity, save_scan_log, save_price_history, get_stats, get_opportunities
from notifier import notify_opportunity, notify_daily_summary

logger = logging.getLogger(__name__)

# 扫描状态
_scan_running = False
_last_scan_result = None
_scan_progress = {
    "status": "idle",
    "total": 0,
    "scanned": 0,
    "found": 0,
    "errors": 0,
    "current_wine": "",
}


def is_scanning() -> bool:
    return _scan_running


def get_scan_progress() -> dict:
    return dict(_scan_progress)


def get_last_scan_result():
    return _last_scan_result


async def run_full_scan(profit_threshold: float = 15, notify: bool = True) -> dict:
    """
    执行一次完整扫描
    遍历保值酒清单 → 爬取价格 → 分析利润 → 保存+通知
    """
    global _scan_running, _last_scan_result

    if _scan_running:
        logger.warning("扫描已在进行中，跳过本次")
        return {"status": "skipped", "reason": "scan_in_progress"}

    _scan_running = True
    started_at = datetime.now()
    wines_scanned = 0
    opportunities_found = 0
    errors = []
    found_opportunities = []
    total = len(PREMIUM_WINES)

    _scan_progress.update({
        "status": "running",
        "total": total,
        "scanned": 0,
        "found": 0,
        "errors": 0,
        "current_wine": "",
    })

    logger.info(f"🔍 开始扫描 {total} 款保值酒...")

    try:
        for wine_config in PREMIUM_WINES:
            wine_name = wine_config["name"]
            _scan_progress["current_wine"] = wine_name

            try:
                # 1. 爬取价格数据
                wine_info = await search_wine_basic(wine_name)
                wines_scanned += 1
                _scan_progress["scanned"] = wines_scanned

                if not wine_info.get("found"):
                    logger.debug(f"未找到数据: {wine_name}")
                    continue

                # 2. 保存价格历史
                if wine_info.get("global_lowest"):
                    gl = wine_info["global_lowest"]
                    await save_price_history(
                        wine_name=wine_name,
                        vintage="",
                        price=gl["price_usd"],
                        currency="USD",
                        source="wine-searcher",
                        merchant=gl.get("merchant", ""),
                        country=gl.get("country", "")
                    )

                # 3. 分析是否为捡漏机会
                opp = analyze_opportunity(wine_info, wine_config, profit_threshold)
                if opp:
                    # 确保 buy_url 指向 Wine-Searcher 搜索页
                    buy_url = opp.get("buy_url", "")
                    if not buy_url or ('wine-searcher.com' not in buy_url):
                        ws_query = wine_name.replace(' ', '+')
                        opp["buy_url"] = f"https://www.wine-searcher.com/find/{ws_query}/1/a"

                    # 保存到数据库
                    opp_id = await save_opportunity(opp)
                    opp["id"] = opp_id
                    found_opportunities.append(opp)
                    opportunities_found += 1
                    _scan_progress["found"] = opportunities_found

                    # 发送 Telegram 通知
                    if notify:
                        await notify_opportunity(opp)

            except Exception as e:
                error_msg = f"{wine_name}: {str(e)}"
                errors.append(error_msg)
                _scan_progress["errors"] = len(errors)
                logger.error(f"扫描异常: {error_msg}")
                continue

        # 保存扫描日志
        duration = (datetime.now() - started_at).total_seconds()
        await save_scan_log({
            "scan_type": "full",
            "wines_scanned": wines_scanned,
            "opportunities_found": opportunities_found,
            "errors": "; ".join(errors) if errors else None,
            "started_at": started_at.isoformat(),
            "duration_seconds": duration,
        })

        result = {
            "status": "completed",
            "wines_scanned": wines_scanned,
            "opportunities_found": opportunities_found,
            "errors_count": len(errors),
            "duration_seconds": round(duration, 1),
            "opportunities": found_opportunities,
        }

        _last_scan_result = result
        logger.info(
            f"✅ 扫描完成: {wines_scanned} 款酒, "
            f"发现 {opportunities_found} 条机会, "
            f"耗时 {duration:.1f}s"
        )

        return result

    finally:
        _scan_running = False
        _scan_progress["status"] = "completed" if not errors else "completed_with_errors"
        _scan_progress["current_wine"] = ""


async def run_single_scan(wine_name: str, region: str = "default",
                          category: str = "", profit_threshold: float = 15) -> dict:
    """
    扫描单款酒（手动搜索用）
    """
    wine_config = {
        "name": wine_name,
        "region": region,
        "category": category,
    }

    wine_info = await search_wine_basic(wine_name)

    if not wine_info.get("found"):
        return {"wine_name": wine_name, "found": False, "opportunity": None}

    opp = analyze_opportunity(wine_info, wine_config, profit_threshold)

    return {
        "wine_name": wine_name,
        "found": True,
        "global_lowest": wine_info.get("global_lowest"),
        "hk_avg_price": wine_info.get("hk_avg_price_usd"),
        "opportunity": opp,
    }
