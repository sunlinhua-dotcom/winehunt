"""
Telegram 通知模块
推送捡漏机会到 Telegram
"""
import os
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


def _get_config():
    """获取 Telegram 配置"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    return token, chat_id


from exchange_rates import get_cached_rate

def format_opportunity_message(opp: dict) -> str:
    """格式化捡漏机会消息 (RMB版)"""
    emoji_map = {
        "波尔多一级庄": "🏰",
        "波尔多超二级庄": "🏠",
        "波尔多右岸": "🍇",
        "勃艮第顶级": "🌟",
        "意大利名庄": "🇮🇹",
        "新世界硬通货": "🌍",
        "香槟名庄": "🍾",
        "罗纳河谷": "🏔️",
    }

    category = opp.get("category", "")
    emoji = emoji_map.get(category, "🍷")

    profit_emoji = "🔥" if opp.get("profit_rate", 0) >= 30 else "💰"

    # 汇率转换
    cny_rate_val = get_cached_rate('CNY') # 1 CNY = ? USD
    usd_to_cny = 1.0 / cny_rate_val if cny_rate_val > 0 else 7.2
    
    def to_rmb(usd):
        return usd * usd_to_cny

    msg = f"""
{emoji} *{opp['wine_name']}*
{f"年份: {opp['vintage']}" if opp.get('vintage') else ""}
━━━━━━━━━━━━━━━━━━━━
{profit_emoji} *利润率: {opp['profit_rate']:.1f}%*
📊 评分: {opp.get('score', 'N/A')}/10

💴 买入价: ¥{to_rmb(opp['buy_price']):.0f}
🏪 商家: {opp.get('buy_merchant', 'N/A')}
🌐 来源地: {opp.get('buy_country', 'N/A')}

🇭🇰 香港参考: ¥{to_rmb(opp.get('sell_price_hk', 0)):.0f}
📦 全入成本: ¥{to_rmb(opp.get('total_cost', 0)):.0f}
🚢 运费: ¥{to_rmb(opp.get('shipping_cost', 0)):.0f}/瓶

📂 分类: {category}
━━━━━━━━━━━━━━━━━━━━
"""

    if opp.get("buy_url"):
        msg += f"🔗 [查看详情]({opp['buy_url']})\n"

    return msg.strip()


def format_daily_summary(opportunities: list, stats: dict) -> str:
    """格式化每日摘要"""
    msg = f"""
📊 *Wine 捡漏日报*
━━━━━━━━━━━━━━━━━
🔍 扫描次数: {stats.get('total_scans', 0)}
💰 今日发现: {stats.get('today_opportunities', 0)} 条机会
🏆 最高利润: {stats.get('max_profit_rate', 0):.1f}%
⏰ 最后扫描: {stats.get('last_scan', 'N/A')}
━━━━━━━━━━━━━━━━━

"""

    if opportunities:
        msg += "*🔥 今日 Top 5 机会:*\n\n"
        for i, opp in enumerate(opportunities[:5], 1):
            msg += f"{i}. *{opp['wine_name']}*\n"
            msg += f"   利润率: {opp['profit_rate']:.1f}% | ${opp['buy_price']:.0f} → ${opp.get('sell_price_hk', 0):.0f}\n\n"
    else:
        msg += "_暂无符合条件的捡漏机会_\n"

    return msg.strip()


async def send_telegram_message(text: str, parse_mode: str = "Markdown") -> bool:
    """发送 Telegram 消息"""
    token, chat_id = _get_config()

    if not token or not chat_id:
        logger.warning("Telegram 配置缺失，跳过通知")
        return False

    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                logger.info("Telegram 通知发送成功")
                return True
            else:
                logger.error(f"Telegram 发送失败: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Telegram 发送异常: {e}")
        return False


async def notify_opportunity(opp: dict) -> bool:
    """通知一条捡漏机会"""
    msg = format_opportunity_message(opp)
    return await send_telegram_message(msg)


async def notify_daily_summary(opportunities: list, stats: dict) -> bool:
    """发送每日摘要"""
    msg = format_daily_summary(opportunities, stats)
    return await send_telegram_message(msg)
