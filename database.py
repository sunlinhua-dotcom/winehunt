"""
数据库模块 — SQLite（轻量免配置）
管理酒款、捡漏机会、扫描日志
"""
import aiosqlite
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 优先从环境变量读取 DB_PATH，方便本地调试和 Zeabur 持久化挂载
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "wine_deals.db"))
logger.info(f"DB_PATH: {DB_PATH}")


async def get_db():
    """获取数据库连接"""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    """初始化数据库表"""
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wine_name TEXT NOT NULL,
                vintage TEXT,
                region TEXT,
                category TEXT,
                buy_price REAL NOT NULL,
                buy_currency TEXT DEFAULT 'USD',
                buy_merchant TEXT,
                buy_country TEXT,
                buy_url TEXT,
                sell_price_hk REAL,
                total_cost REAL,
                profit_rate REAL,
                score TEXT,
                data_source TEXT DEFAULT 'wine-searcher',
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notified INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS scan_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_type TEXT,
                wines_scanned INTEGER DEFAULT 0,
                opportunities_found INTEGER DEFAULT 0,
                errors TEXT,
                started_at TIMESTAMP,
                finished_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_seconds REAL
            );

            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wine_name TEXT NOT NULL,
                region TEXT,
                target_price REAL,
                notes TEXT,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wine_name TEXT NOT NULL,
                vintage TEXT,
                price REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                source TEXT,
                merchant TEXT,
                country TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_opp_profit ON opportunities(profit_rate DESC);
            CREATE INDEX IF NOT EXISTS idx_opp_status ON opportunities(status);
            CREATE INDEX IF NOT EXISTS idx_opp_created ON opportunities(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_price_wine ON price_history(wine_name);
        """)
        await db.commit()
    finally:
        await db.close()


async def save_opportunity(opp: dict) -> int:
    """保存一条捡漏机会（同酒名去重：更新已有记录或新增）"""
    db = await get_db()
    try:
        # 先查是否已有同酒名的 active 记录
        cursor = await db.execute(
            "SELECT id FROM opportunities WHERE wine_name = ? AND status = 'active'",
            (opp["wine_name"],)
        )
        existing = await cursor.fetchone()

        if existing:
            # 更新已有记录
            await db.execute(
                """UPDATE opportunities SET
                    buy_price=?, buy_currency=?, buy_merchant=?, buy_country=?,
                    buy_url=?, sell_price_hk=?, total_cost=?, profit_rate=?,
                    score=?, data_source=?, created_at=CURRENT_TIMESTAMP
                WHERE id=?""",
                (
                    opp["buy_price"], opp.get("buy_currency", "USD"),
                    opp.get("buy_merchant"), opp.get("buy_country"), opp.get("buy_url"),
                    opp.get("sell_price_hk"), opp.get("total_cost"),
                    opp.get("profit_rate"), opp.get("score"),
                    opp.get("data_source", "wine-searcher"), existing["id"]
                )
            )
            await db.commit()
            return existing["id"]
        else:
            # 新增记录
            cursor = await db.execute(
                """INSERT INTO opportunities
                (wine_name, vintage, region, category, buy_price, buy_currency,
                 buy_merchant, buy_country, buy_url, sell_price_hk, total_cost,
                 profit_rate, score, data_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    opp["wine_name"], opp.get("vintage"), opp.get("region"),
                    opp.get("category"), opp["buy_price"], opp.get("buy_currency", "USD"),
                    opp.get("buy_merchant"), opp.get("buy_country"), opp.get("buy_url"),
                    opp.get("sell_price_hk"), opp.get("total_cost"),
                    opp.get("profit_rate"), opp.get("score"), opp.get("data_source", "wine-searcher")
                )
            )
            await db.commit()
            return cursor.lastrowid
    finally:
        await db.close()


async def get_opportunities(limit: int = 50, status: str = "active", min_profit: float = 0):
    """获取捡漏机会列表"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT * FROM opportunities
            WHERE status = ? AND profit_rate >= ?
            ORDER BY profit_rate DESC
            LIMIT ?""",
            (status, min_profit, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_opportunity_by_id(opp_id: int):
    """获取单条机会详情"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM opportunities WHERE id = ?", (opp_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def save_scan_log(log: dict) -> int:
    """保存扫描日志"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO scan_logs
            (scan_type, wines_scanned, opportunities_found, errors, started_at, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                log.get("scan_type"), log.get("wines_scanned", 0),
                log.get("opportunities_found", 0), log.get("errors"),
                log.get("started_at"), log.get("duration_seconds")
            )
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_scan_logs(limit: int = 20):
    """获取扫描日志"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM scan_logs ORDER BY finished_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        logs = []
        for row in rows:
            d = dict(row)
            # 格式化耗时供前端显示
            secs = d.get("duration_seconds")
            if secs and secs > 0:
                mins = int(secs // 60)
                remaining = int(secs % 60)
                d["duration"] = f"{mins}m {remaining}s" if mins else f"{remaining}s"
            else:
                d["duration"] = "—"
            # 兼容前端字段名
            d["scanned"] = d.get("wines_scanned", 0)
            d["found"] = d.get("opportunities_found", 0)
            d["scan_time"] = d.get("finished_at")
            logs.append(d)
        return logs
    finally:
        await db.close()


async def save_price_history(wine_name: str, vintage: str, price: float,
                             currency: str, source: str, merchant: str, country: str):
    """保存价格历史"""
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO price_history
            (wine_name, vintage, price, currency, source, merchant, country)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (wine_name, vintage, price, currency, source, merchant, country)
        )
        await db.commit()
    finally:
        await db.close()


async def get_price_history(wine_name: str, limit: int = 100):
    """获取某款酒的价格历史"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT * FROM price_history
            WHERE wine_name LIKE ?
            ORDER BY recorded_at DESC LIMIT ?""",
            (f"%{wine_name}%", limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


# 监控酒单操作
async def add_to_watchlist(wine_name: str, region: str = None,
                           target_price: float = None, notes: str = None) -> int:
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO watchlist (wine_name, region, target_price, notes) VALUES (?, ?, ?, ?)",
            (wine_name, region, target_price, notes)
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_watchlist():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM watchlist WHERE active = 1 ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def remove_from_watchlist(item_id: int):
    db = await get_db()
    try:
        await db.execute("UPDATE watchlist SET active = 0 WHERE id = ?", (item_id,))
        await db.commit()
    finally:
        await db.close()


async def get_stats():
    """获取统计数据"""
    db = await get_db()
    try:
        stats = {}
        # 今日机会数
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM opportunities WHERE date(created_at) = date('now') AND status = 'active'"
        )
        row = await cursor.fetchone()
        stats["today_opportunities"] = row["cnt"] if row else 0

        # 总机会数
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM opportunities WHERE status = 'active'")
        row = await cursor.fetchone()
        stats["total_opportunities"] = row["cnt"] if row else 0

        # 最高利润率
        cursor = await db.execute(
            "SELECT MAX(profit_rate) as max_profit FROM opportunities WHERE status = 'active'"
        )
        row = await cursor.fetchone()
        stats["max_profit_rate"] = round(row["max_profit"], 1) if row and row["max_profit"] else 0

        # 最近扫描时间
        cursor = await db.execute("SELECT finished_at FROM scan_logs ORDER BY finished_at DESC LIMIT 1")
        row = await cursor.fetchone()
        stats["last_scan"] = row["finished_at"] if row else None

        # 扫描总次数
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM scan_logs")
        row = await cursor.fetchone()
        stats["total_scans"] = row["cnt"] if row else 0

        return stats
    finally:
        await db.close()
