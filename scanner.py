"""
定时扫描模块
自动扫描保值酒清单，发现捡漏机会
优化策略：
  - 单请求合并：全球+HK 数据一次请求搞定
  - 自适应缓存：连续无机会的酒 TTL 从 24h→48h→72h 递增
  - curl_cffi 优先：免费引擎优先，ScraperAPI 仅作后备
"""
import asyncio
import logging
import random
from datetime import datetime, timedelta
from wine_list import ALL_WINES
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

# ── 自适应缓存：连续无机会次数越多，TTL 越长 ──
_scan_cache: dict = {}
# key=wine_name, value={"time": datetime, "had_opportunity": bool, "miss_streak": int}

# 自适应 TTL：连续无机会 0-1 次→24h, 2 次→48h, 3+ 次→72h
def _get_cache_ttl(miss_streak: int) -> timedelta:
    if miss_streak <= 1:
        return timedelta(hours=24)
    elif miss_streak == 2:
        return timedelta(hours=48)
    else:
        return timedelta(hours=72)


def _should_skip_wine(wine_name: str) -> bool:
    """智能判断是否跳过某款酒"""
    if wine_name not in _scan_cache:
        return False
    cache = _scan_cache[wine_name]
    # 有机会的始终重扫
    if cache.get("had_opportunity"):
        return False
    # 根据连续无机会次数决定 TTL
    ttl = _get_cache_ttl(cache.get("miss_streak", 0))
    if datetime.now() - cache["time"] < ttl:
        return True
    return False


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
    智能缓存: 24h 内无机会的酒款自动跳过
    """
    global _scan_running, _last_scan_result

    if _scan_running:
        logger.warning("扫描已在进行中，跳过本次")
        return {"status": "skipped", "reason": "scan_in_progress"}

    # 预热汇率缓存
    try:
        from exchange_rates import get_exchange_rates
        await get_exchange_rates()
    except Exception:
        pass

    _scan_running = True
    started_at = datetime.now()
    wines_scanned = 0
    opportunities_found = 0
    skipped = 0
    errors = []
    found_opportunities = []

    # 随机打乱顺序，避免每次扫描模式相同触发反爬
    wines_to_scan = list(ALL_WINES)
    random.shuffle(wines_to_scan)
    total = len(wines_to_scan)

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
        for wine_config in wines_to_scan:
            wine_name = wine_config["name"]
            _scan_progress["current_wine"] = wine_name

            # ── 智能缓存检查 ──
            if _should_skip_wine(wine_name):
                skipped += 1
                _scan_progress["scanned"] = wines_scanned + skipped
                logger.debug(f"⏭️ 跳过 (24h缓存): {wine_name}")
                continue

            try:
                # 1. 爬取价格数据
                wine_info = await search_wine_basic(wine_name)
                wines_scanned += 1
                _scan_progress["scanned"] = wines_scanned + skipped

                if not wine_info.get("found"):
                    # 记录缓存：没找到数据，增加连续无机会计数
                    prev = _scan_cache.get(wine_name, {})
                    _scan_cache[wine_name] = {
                        "time": datetime.now(),
                        "had_opportunity": False,
                        "miss_streak": prev.get("miss_streak", 0) + 1
                    }
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

                    # 记录缓存：有机会，重置连续无机会计数
                    _scan_cache[wine_name] = {
                        "time": datetime.now(),
                        "had_opportunity": True,
                        "miss_streak": 0
                    }

                    # 发送 Telegram 通知
                    if notify:
                        await notify_opportunity(opp)
                else:
                    # 记录缓存：无机会，增加连续无机会计数
                    prev = _scan_cache.get(wine_name, {})
                    _scan_cache[wine_name] = {
                        "time": datetime.now(),
                        "had_opportunity": False,
                        "miss_streak": prev.get("miss_streak", 0) + 1
                    }

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
            "wines_skipped": skipped,
            "opportunities_found": opportunities_found,
            "errors_count": len(errors),
            "duration_seconds": round(duration, 1),
            "opportunities": found_opportunities,
        }

        _last_scan_result = result
        logger.info(
            f"✅ 扫描完成: {wines_scanned} 款酒 (跳过 {skipped} 款), "
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
    扫描单款酒（手动搜索用，不受缓存限制）
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
