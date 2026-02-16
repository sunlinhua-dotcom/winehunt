"""
实时汇率模块 — 接入免费 API，带缓存和兜底
数据源: open.er-api.com（免费，无需 API Key）
缓存策略: 每 6 小时刷新一次，避免频繁请求
兜底: API 不可用时使用硬编码汇率
"""
import asyncio
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ── 缓存配置 ──────────────────────────────
CACHE_TTL = 6 * 3600  # 6 小时缓存

_cached_rates: Optional[Dict[str, float]] = None
_cache_timestamp: float = 0

# ── 硬编码兜底汇率（2026-02 参考值）───────
FALLBACK_RATES = {
    'USD': 1.0,
    'EUR': 1.08,
    'GBP': 1.27,
    'HKD': 0.128,
    'CNY': 0.14,
    'AUD': 0.65,
    'NZD': 0.60,
    'CAD': 0.74,
    'JPY': 0.0067,
    'CHF': 1.12,
    'SGD': 0.75,
    'KRW': 0.00072,
    'SEK': 0.095,
    'DKK': 0.145,
    'NOK': 0.093,
}


async def _fetch_rates_from_api() -> Optional[Dict[str, float]]:
    """从免费 API 获取最新汇率（基准 USD）"""
    import httpx

    apis = [
        # 主 API: open.er-api.com（完全免费，无限次）
        "https://open.er-api.com/v6/latest/USD",
        # 备 API: cdn.jsdelivr.net 镜像（静态 JSON，每日更新）
        "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json",
    ]

    for api_url in apis:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(api_url)
                if resp.status_code != 200:
                    continue

                data = resp.json()

                # open.er-api.com 格式
                if 'rates' in data:
                    raw_rates = data['rates']
                    # 转换为 "每单位外币 = ? USD" 的格式
                    rates = {}
                    for currency, value in raw_rates.items():
                        if value and value > 0:
                            rates[currency.upper()] = 1.0 / value  # 倒数
                    rates['USD'] = 1.0
                    logger.info(f"✅ 实时汇率获取成功 (来源: open.er-api.com)")
                    return rates

                # fawazahmed0 格式
                elif 'usd' in data:
                    raw_rates = data['usd']
                    rates = {}
                    for currency, value in raw_rates.items():
                        if value and value > 0:
                            rates[currency.upper()] = 1.0 / value
                    rates['USD'] = 1.0
                    logger.info(f"✅ 实时汇率获取成功 (来源: fawazahmed0)")
                    return rates

        except Exception as e:
            logger.warning(f"汇率 API 请求失败 ({api_url[:40]}): {e}")
            continue

    return None


async def get_exchange_rates() -> Dict[str, float]:
    """
    获取汇率表（带 6 小时缓存）
    返回格式: {'USD': 1.0, 'EUR': 1.08, 'HKD': 0.128, ...}
    含义: 1 单位该货币 = ? 美元
    """
    global _cached_rates, _cache_timestamp

    now = time.time()

    # 缓存有效
    if _cached_rates and (now - _cache_timestamp) < CACHE_TTL:
        return _cached_rates

    # 尝试获取实时汇率
    rates = await _fetch_rates_from_api()
    if rates:
        _cached_rates = rates
        _cache_timestamp = now

        # 记录关键货币
        key_currencies = ['EUR', 'GBP', 'HKD', 'CNY', 'AUD', 'JPY', 'CHF']
        rate_info = ', '.join(f"{c}={rates.get(c, 0):.4f}" for c in key_currencies)
        logger.info(f"📊 关键汇率: {rate_info}")

        return rates

    # API 不可用，使用缓存或兜底
    if _cached_rates:
        logger.warning("⚠️ 汇率 API 不可用，使用上次缓存")
        return _cached_rates

    logger.warning("⚠️ 汇率 API 不可用，使用硬编码兜底")
    return FALLBACK_RATES


def get_cached_rate(currency: str) -> float:
    """同步获取已缓存的汇率（用于非 async 场景）"""
    rates = _cached_rates or FALLBACK_RATES
    return rates.get(currency.upper(), 1.0)


async def to_usd(price: float, currency: str) -> float:
    """将任意货币转换为美元"""
    rates = await get_exchange_rates()
    rate = rates.get(currency.upper(), 1.0)
    return price * rate


def to_usd_sync(price: float, currency: str) -> float:
    """同步版本的货币转换（使用缓存或兜底）"""
    return price * get_cached_rate(currency)
