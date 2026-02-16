"""
Wine-Searcher 爬虫模块 — 双引擎反反爬版
主引擎: curl_cffi (模拟真实浏览器 TLS/JA3 指纹)
备引擎: ScraperAPI 免费层 (5000 次/月)
"""
import asyncio
import random
import re
import os
import json
import logging
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── 配置 ──────────────────────────────────
BASE_URL = "https://www.wine-searcher.com"

# ScraperAPI 免费 key（环境变量覆盖）
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY", "")

# User-Agent 池
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

# TLS 指纹模拟的浏览器种类（仅使用 curl_cffi 确认支持的）
IMPERSONATES = [
    "chrome124",
    "chrome120",
    "chrome119",
    "chrome116",
    "chrome110",
    "chrome107",
    "chrome104",
    "chrome101",
    "chrome100",
    "chrome99",
    "safari15_5",
    "safari15_3",
]


# ── 引擎 1: curl_cffi（主引擎，带 session 预热）──────
async def _fetch_with_curl_cffi(url: str, max_retries: int = 3) -> Optional[str]:
    """
    使用 curl_cffi 模拟真实浏览器 TLS 指纹
    策略: 先访问主页获取 Cloudflare cookie → 再用同一 session 搜索
    """
    try:
        from curl_cffi.requests import AsyncSession
    except ImportError:
        logger.warning("curl_cffi 未安装，跳过此引擎")
        return None

    for attempt in range(max_retries):
        try:
            impersonate = random.choice(IMPERSONATES)
            ua = random.choice(USER_AGENTS)
            headers = {
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"macOS"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            }

            async with AsyncSession(impersonate=impersonate) as session:
                # Step 1: 预热 — 先访问主页拿 cookie（模拟真人先打开网站首页）
                warmup_headers = dict(headers)
                try:
                    warmup = await session.get(
                        BASE_URL,
                        headers=warmup_headers,
                        timeout=20,
                        allow_redirects=True,
                    )
                    logger.debug(f"预热状态: {warmup.status_code} ({impersonate})")
                    await asyncio.sleep(random.uniform(1.5, 4))
                except Exception as e:
                    logger.debug(f"预热失败 (继续尝试): {e}")

                # Step 2: 真正的搜索请求，带上 Referer 模拟站内浏览
                search_headers = dict(headers)
                search_headers["Referer"] = BASE_URL + "/"
                search_headers["Sec-Fetch-Site"] = "same-origin"

                resp = await session.get(
                    url,
                    headers=search_headers,
                    timeout=30,
                    allow_redirects=True,
                )

                if resp.status_code == 200:
                    logger.info(f"✅ curl_cffi 成功 ({impersonate}): {url[:80]}")
                    return resp.text
                elif resp.status_code == 403:
                    logger.warning(f"curl_cffi 403 (尝试 {attempt+1}/{max_retries}, {impersonate}): {url[:80]}")
                    await asyncio.sleep(random.uniform(5, 12))
                    continue
                else:
                    logger.warning(f"curl_cffi {resp.status_code}: {url[:80]}")
                    return None

        except Exception as e:
            logger.warning(f"curl_cffi 异常 (尝试 {attempt+1}): {e}")
            await asyncio.sleep(random.uniform(3, 6))
            continue

    return None


# ── 引擎 1: ScraperAPI（主引擎，代理 IP 绕过封锁）────
async def _fetch_with_scraper_api(url: str) -> Optional[str]:
    """
    使用 ScraperAPI 免费层（5000 次/月）
    通过代理 IP 绕过 Wine-Searcher 的 IP 封杀
    """
    if not SCRAPER_API_KEY:
        logger.debug("未配置 SCRAPER_API_KEY，跳过 ScraperAPI")
        return None

    import httpx
    api_url = "https://api.scraperapi.com"
    params = {
        "api_key": SCRAPER_API_KEY,
        "url": url,
        "render": "false",
    }

    for attempt in range(2):  # 最多重试 2 次
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.get(api_url, params=params)
                if resp.status_code == 200:
                    logger.info(f"✅ ScraperAPI 成功: {url[:80]}")
                    return resp.text
                elif resp.status_code in (500, 502, 503):
                    logger.warning(f"ScraperAPI {resp.status_code} 重试 ({attempt+1}/2): {url[:80]}")
                    await asyncio.sleep(random.uniform(3, 6))
                    continue
                else:
                    logger.warning(f"ScraperAPI {resp.status_code}: {url[:80]}")
                    return None
        except Exception as e:
            logger.warning(f"ScraperAPI 异常 ({attempt+1}/2): {e}")
            await asyncio.sleep(random.uniform(2, 4))
            continue

    return None


# ── 引擎 3: httpx 基础请求（最后备用）────────────
async def _fetch_with_httpx(url: str) -> Optional[str]:
    """最基础的 httpx 请求"""
    try:
        import httpx
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                logger.info(f"✅ httpx 成功: {url[:80]}")
                return resp.text
            logger.warning(f"httpx {resp.status_code}: {url[:80]}")
            return None
    except Exception as e:
        logger.warning(f"httpx 异常: {e}")
        return None


# ── 统一请求函数（瀑布式降级）───────────────────
async def _smart_fetch(url: str) -> Optional[str]:
    """
    依次尝试三个引擎，直到成功：
    1. ScraperAPI（免费代理，绕过 IP 封锁，最可靠）
    2. curl_cffi（TLS 指纹伪装，IP 未封时可用）
    3. httpx（基础请求，兜底）
    """
    # 引擎 1: ScraperAPI（优先，绕过 IP 封锁）
    html = await _fetch_with_scraper_api(url)
    if html:
        return html

    # 引擎 2: curl_cffi（IP 未封时有效）
    html = await _fetch_with_curl_cffi(url, max_retries=1)
    if html:
        return html

    # 引擎 3: httpx（兜底）
    html = await _fetch_with_httpx(url)
    if html:
        return html

    logger.error(f"❌ 所有引擎均失败: {url[:80]}")
    return None


# ── 随机延迟 ─────────────────────────────
async def _random_delay(min_sec: float = 3, max_sec: float = 8):
    """模拟人类浏览间隔"""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


# ── 价格解析 ─────────────────────────────
def _parse_price(price_text: str) -> Optional[float]:
    if not price_text:
        return None
    cleaned = re.sub(r'[^\d.,]', '', price_text.strip())
    if ',' in cleaned and '.' in cleaned:
        if cleaned.index(',') > cleaned.index('.'):
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        parts = cleaned.split(',')
        if len(parts[-1]) == 2:
            cleaned = cleaned.replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    try:
        return float(cleaned)
    except ValueError:
        return None


def _detect_currency(price_text: str) -> str:
    if '$' in price_text or 'USD' in price_text:
        return 'USD'
    elif '€' in price_text or 'EUR' in price_text:
        return 'EUR'
    elif '£' in price_text or 'GBP' in price_text:
        return 'GBP'
    elif 'HK$' in price_text or 'HKD' in price_text:
        return 'HKD'
    elif '¥' in price_text or 'CNY' in price_text:
        return 'CNY'
    return 'USD'


EXCHANGE_RATES = {
    'USD': 1.0, 'EUR': 1.08, 'GBP': 1.27,
    'HKD': 0.128, 'CNY': 0.14, 'AUD': 0.65,
    'JPY': 0.0067, 'CHF': 1.12,
}


def _to_usd(price: float, currency: str) -> float:
    return price * EXCHANGE_RATES.get(currency, 1.0)


# ── 页面解析 ─────────────────────────────
def _parse_wine_page(html: str) -> list:
    """解析 Wine-Searcher 搜索结果页"""
    results = []
    soup = BeautifulSoup(html, 'html.parser')

    # 方法1: 优先尝试多种 CSS 选择器（Wine-Searcher 页面结构可能变化）
    selectors = [
        '.card__offer', '.offer-row', '.result-row', '[data-offer]',
        'tr.offer', '.search-result-item',
        '.wine-card', '.listing-row', '.price-listing',
        'div[class*="offer"]', 'div[class*="listing"]',
        'tr[class*="offer"]', 'tr[class*="result"]',
    ]
    offer_cards = []
    for sel in selectors:
        offer_cards = soup.select(sel)
        if offer_cards:
            logger.debug(f"HTML 解析命中选择器: {sel} ({len(offer_cards)} 条)")
            break

    for card in offer_cards[:20]:
        try:
            merchant_el = card.select_one('.merchant-name, .offer-merchant, a[data-merchant]')
            merchant = merchant_el.get_text(strip=True) if merchant_el else "未知商家"

            # 🛑 过滤 1: 排除拍卖和整箱
            card_text = card.get_text().lower()
            if any(kw in card_text for kw in ['auction', 'bid ', 'lot of', 'case of', 'set of']):
                continue
            if 'auction' in merchant.lower():
                continue

            price_el = card.select_one('.offer-price, .price, [data-price]')
            if not price_el:
                continue
            price_text = price_el.get_text(strip=True)
            price = _parse_price(price_text)
            
            # 🛑 过滤 2: 排除价格过低（可能是配件或误报）
            if not price or price < 20:
                continue

            currency = _detect_currency(price_text)

            country_el = card.select_one('.country, .offer-country, [data-country]')
            country = country_el.get_text(strip=True) if country_el else ""

            # 优先获取 wine-searcher.com 的链接（具体 listing），而非酒商主页
            link = ""
            for a_tag in card.select('a[href]'):
                href = a_tag.get('href', '')
                if 'wine-searcher.com' in href or href.startswith('/find') or href.startswith('/merchant'):
                    link = href
                    break
            if link and not link.startswith('http'):
                link = BASE_URL + link

            results.append({
                "merchant": merchant,
                "price": price,
                "price_usd": _to_usd(price, currency),
                "currency": currency,
                "country": country,
                "url": link,
            })
        except Exception as e:
            logger.debug(f"解析 offer 失败: {e}")

    # 方法2: JSON-LD
    if not results:
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'offers' in data:
                    offers = data['offers']
                    if isinstance(offers, list):
                        for offer in offers[:20]:
                            # 🛑 JSON-LD 过滤
                            desc = (offer.get('description') or '').lower()
                            seller = (offer.get('seller', {}).get('name') or '').lower()
                            if any(kw in desc or kw in seller for kw in ['auction', 'bid', 'lot of']):
                                continue

                            price = offer.get('price')
                            if price and float(price) > 20:
                                curr = offer.get('priceCurrency', 'USD')
                                results.append({
                                    "merchant": offer.get('seller', {}).get('name', '未知'),
                                    "price": float(price),
                                    "price_usd": _to_usd(float(price), curr),
                                    "currency": curr,
                                    "country": "",
                                    "url": offer.get('url', ''),
                                })
            except Exception:
                continue

    # 方法3: 简单价格提取（fallback）— 严格限制范围
    if not results:
        # 尝试从页面中直接提取价格数字
        price_patterns = soup.find_all(string=re.compile(r'\$[\d,]+\.?\d*'))
        for pt in price_patterns[:5]:
            price = _parse_price(pt)
            # 严格限制：单瓶葡萄酒价格通常在 $20-$15000 之间
            if price and 20 < price < 15000:
                results.append({
                    "merchant": "Wine-Searcher",
                    "price": price,
                    "price_usd": price,
                    "currency": "USD",
                    "country": "",
                    "url": "",
                })

    return results


# ── 公开 API ─────────────────────────────
async def search_wine_prices(wine_name: str, country_filter: str = None) -> list:
    """搜索酒价"""
    search_query = wine_name.replace(' ', '+')
    url = f"{BASE_URL}/find/{search_query}/1/a"
    if country_filter:
        url += f"?Xcountry={country_filter}"

    await _random_delay(2, 5)
    html = await _smart_fetch(url)

    if not html:
        return []

    results = _parse_wine_page(html)

    # 如果是香港页面，强制将未标注 HKD 的 $ 价格视为 HKD
    if country_filter and 'hong' in country_filter.lower():
        for r in results:
            if r['currency'] == 'USD':
                # Wine-Searcher 香港页面默认显示 HKD，即使符号是 $
                r['currency'] = 'HKD'
                r['price_usd'] = _to_usd(r['price'], 'HKD')
                logger.debug(f"香港页面货币修正: ${r['price']:.0f} HKD -> ${r['price_usd']:.2f} USD")

    return results


async def get_global_lowest_price(wine_name: str) -> Optional[dict]:
    """获取全球最低价"""
    results = await search_wine_prices(wine_name)
    if not results:
        return None
    results.sort(key=lambda x: x["price_usd"])
    return results[0]


async def get_hk_average_price(wine_name: str) -> Optional[float]:
    """获取香港市场均价（含异常值过滤）"""
    results = await search_wine_prices(wine_name, country_filter="hong+kong")
    if not results:
        return None

    usd_prices = [r["price_usd"] for r in results if r["price_usd"] > 0]
    if not usd_prices:
        return None

    # 异常值过滤：去掉偏离中位数 5 倍以上的值
    usd_prices.sort()
    median = usd_prices[len(usd_prices) // 2]
    filtered = [p for p in usd_prices if p < median * 5 and p > median * 0.2]
    if not filtered:
        filtered = usd_prices  # 过滤失败则回退

    avg = sum(filtered) / len(filtered)
    logger.info(f"香港均价 ({wine_name}): ${avg:.2f} USD (样本 {len(filtered)} 条, 中位 ${median:.2f})")
    return avg


async def search_wine_basic(wine_name: str) -> dict:
    """搜索一款酒基本信息"""
    global_lowest = await get_global_lowest_price(wine_name)
    if not global_lowest:
        return {"wine_name": wine_name, "found": False}

    # 构建 Wine-Searcher 搜索结果页 URL 作为统一直达链接
    search_query = wine_name.replace(' ', '+')
    ws_search_url = f"{BASE_URL}/find/{search_query}/1/a"

    # 如果爬到的 url 是酒商主页（非 wine-searcher），替换为搜索页
    if global_lowest.get("url") and 'wine-searcher.com' not in global_lowest["url"]:
        global_lowest["url"] = ws_search_url
    elif not global_lowest.get("url"):
        global_lowest["url"] = ws_search_url

    await _random_delay(3, 6)

    hk_avg = await get_hk_average_price(wine_name)

    return {
        "wine_name": wine_name,
        "found": True,
        "global_lowest": global_lowest,
        "hk_avg_price_usd": hk_avg,
    }
