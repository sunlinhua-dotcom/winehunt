"""
Wine-Searcher 捡漏应用 — FastAPI 后端
"""
import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入项目模块
from database import (
    init_db, get_opportunities, get_opportunity_by_id,
    get_scan_logs, get_price_history, get_stats,
    add_to_watchlist, get_watchlist, remove_from_watchlist
)
from scanner import run_full_scan, run_single_scan, is_scanning, get_scan_progress
from wine_list import PREMIUM_WINES, ALL_WINES

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 定时任务相关
_scheduler_task = None


async def scheduled_scan():
    """定时扫描任务"""
    interval = int(os.getenv("SCAN_INTERVAL_MINUTES", "480"))
    threshold = float(os.getenv("PROFIT_THRESHOLD", "15"))

    while True:
        try:
            logger.info(f"⏰ 定时扫描触发（每 {interval} 分钟）")
            await run_full_scan(profit_threshold=threshold, notify=True)
        except Exception as e:
            logger.error(f"定时扫描异常: {e}")

        await asyncio.sleep(interval * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _scheduler_task

    # 启动时初始化数据库
    await init_db()
    logger.info("✅ 数据库初始化完成")

    # 预热实时汇率缓存
    try:
        from exchange_rates import get_exchange_rates
        rates = await get_exchange_rates()
        logger.info(f"✅ 实时汇率预热完成 (EUR={rates.get('EUR', 0):.4f}, HKD={rates.get('HKD', 0):.4f})")
    except Exception as e:
        logger.warning(f"汇率预热失败（将使用兜底汇率）: {e}")

    # 清理历史脏数据（利润率异常或价格为零的记录）
    try:
        from database import get_db
        db = await get_db()
        await db.execute("DELETE FROM opportunities WHERE profit_rate > 500 OR buy_price <= 0 OR sell_price_hk <= 0")
        await db.commit()
        await db.close()
        logger.info("✅ 已清理异常数据")
    except Exception as e:
        logger.warning(f"清理脏数据时出错: {e}")

    # 启动定时扫描
    _scheduler_task = asyncio.create_task(scheduled_scan())
    logger.info("✅ 定时扫描任务已启动")

    yield

    # 关闭时取消定时任务
    if _scheduler_task:
        _scheduler_task.cancel()
        logger.info("⏹️ 定时扫描任务已停止")


# 创建 FastAPI 应用
app = FastAPI(
    title="🍷 Wine Deal Hunter",
    description="Wine-Searcher 捡漏助手 — 专业炒酒人的利润发现引擎",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ===== Pydantic 模型 =====
class SearchRequest(BaseModel):
    wine_name: str
    region: str = "default"
    category: str = ""
    profit_threshold: float = 15


class WatchlistItem(BaseModel):
    wine_name: str
    region: Optional[str] = None
    target_price: Optional[float] = None
    notes: Optional[str] = None


# ===== API 路由 =====

@app.get("/")
async def root():
    """返回前端页面"""
    html_path = os.path.join(static_dir, "index.html")
    return FileResponse(html_path)


@app.get("/api/stats")
async def api_stats():
    """获取总览统计数据"""
    stats = await get_stats()
    stats["scanning"] = is_scanning()
    stats["premium_wines_count"] = len(ALL_WINES)

    # 获取实时汇率 (USD -> CNY)
    try:
        from exchange_rates import get_exchange_rates
        rates = await get_exchange_rates()
        # rates['CNY'] 是 1 CNY = ? USD，所以 USD->CNY 是其倒数
        cny_rate_val = rates.get('CNY', 0.14)
        usd_to_cny = 1.0 / cny_rate_val if cny_rate_val > 0 else 7.14
    except Exception:
        usd_to_cny = 7.14  # 兜底汇率
    stats["usd_to_cny"] = round(usd_to_cny, 2)

    return stats


@app.get("/api/opportunities")
async def api_opportunities(
    limit: int = Query(50, ge=1, le=200),
    min_profit: float = Query(0, ge=0),
    status: str = Query("active")
):
    """获取捡漏机会列表"""
    opps = await get_opportunities(limit=limit, status=status, min_profit=min_profit)
    return {"total": len(opps), "opportunities": opps}


@app.get("/api/opportunities/{opp_id}")
async def api_opportunity_detail(opp_id: int):
    """获取单条机会详情"""
    opp = await get_opportunity_by_id(opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="机会不存在")
    return opp


@app.post("/api/search")
async def api_search(req: SearchRequest):
    """手动搜索一款酒（复用 analyzer 校验逻辑）"""

    result = await run_single_scan(
        wine_name=req.wine_name,
        region=req.region,
        category=req.category,
        profit_threshold=req.profit_threshold
    )

    gl = result.get("global_lowest") or {}
    opp = result.get("opportunity")  # analyzer 已校验过的结果

    # 如果 analyzer 通过校验且返回了 opportunity，直接使用其数据
    if opp:
        return {
            "wine_name": opp.get("wine_name", req.wine_name),
            "found": True,
            "global_lowest": opp.get("buy_price", 0),
            "hk_average": opp.get("sell_price_hk", 0),
            "total_cost": opp.get("total_cost", 0),
            "profit_rate": opp.get("profit_rate", 0),
            "source_region": opp.get("buy_country", ""),
            "source_merchant": opp.get("buy_merchant", ""),
            "shipping_cost": opp.get("shipping_cost", 0),
            "buy_url": opp.get("buy_url", ""),
        }

    # analyzer 未通过校验（数据异常或利润率不达标），返回原始数据供参考
    buy_price = gl.get("price_usd", 0) if isinstance(gl, dict) else 0
    hk_price = result.get("hk_avg_price") or 0

    from wine_list import calculate_total_cost, get_shipping_cost
    region = req.region or "default"
    total_cost = calculate_total_cost(buy_price, region) if buy_price else 0
    profit_rate = ((hk_price - total_cost) / total_cost * 100) if total_cost and hk_price else 0
    # 再次校验合理性上限
    if profit_rate > 500:
        profit_rate = 0  # 标记为异常

    return {
        "wine_name": result.get("wine_name", req.wine_name),
        "found": result.get("found", False),
        "global_lowest": buy_price,
        "hk_average": hk_price if isinstance(hk_price, (int, float)) else 0,
        "total_cost": total_cost,
        "profit_rate": round(profit_rate, 2),
        "source_region": gl.get("country", "") if isinstance(gl, dict) else "",
        "source_merchant": gl.get("merchant", "") if isinstance(gl, dict) else "",
        "shipping_cost": get_shipping_cost(region),
        "buy_url": gl.get("url", "") if isinstance(gl, dict) else "",
    }


@app.post("/api/scan")
async def api_trigger_scan(background_tasks: BackgroundTasks):
    """手动触发一次全量扫描"""
    if is_scanning():
        raise HTTPException(status_code=429, detail="扫描已在进行中")

    threshold = float(os.getenv("PROFIT_THRESHOLD", "15"))
    background_tasks.add_task(run_full_scan, profit_threshold=threshold, notify=True)
    return {"status": "started", "message": "扫描已在后台启动", "total": len(ALL_WINES)}


@app.get("/api/scan/status")
async def api_scan_status():
    """获取扫描状态"""
    progress = get_scan_progress()
    return {
        "scanning": is_scanning(),
        "status": progress.get("status", "idle"),
        "total": progress.get("total", 0),
        "scanned": progress.get("scanned", 0),
        "found": progress.get("found", 0),
        "errors": progress.get("errors", 0),
        "current_wine": progress.get("current_wine", ""),
    }


@app.get("/api/logs")
async def api_scan_logs(limit: int = Query(20, ge=1, le=100)):
    """获取扫描日志"""
    logs = await get_scan_logs(limit=limit)
    return {"total": len(logs), "logs": logs}


@app.get("/api/price-history/{wine_name}")
async def api_price_history(wine_name: str, limit: int = Query(100, ge=1, le=500)):
    """获取价格历史"""
    history = await get_price_history(wine_name, limit=limit)
    return {"wine_name": wine_name, "total": len(history), "history": history}


@app.get("/api/wines")
async def api_wines():
    """获取保值酒清单（展示全部 50 款，含核心 + 备选）"""
    # 按分类分组
    categories = {}
    for wine in ALL_WINES:
        cat = wine.get("category", "其他")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(wine)
    return {"total": len(ALL_WINES), "categories": categories}


# ===== 监控酒单 =====

@app.get("/api/watchlist")
async def api_get_watchlist():
    """获取监控酒单"""
    items = await get_watchlist()
    return {"total": len(items), "watchlist": items}


@app.post("/api/watchlist")
async def api_add_watchlist(item: WatchlistItem):
    """添加到监控酒单"""
    item_id = await add_to_watchlist(
        wine_name=item.wine_name,
        region=item.region,
        target_price=item.target_price,
        notes=item.notes
    )
    return {"id": item_id, "status": "added"}


@app.delete("/api/watchlist/{item_id}")
async def api_remove_watchlist(item_id: int):
    """移除监控酒单"""
    await remove_from_watchlist(item_id)
    return {"status": "removed"}



@app.get("/api/admin/reset")
async def admin_reset_db():
    """【紧急修复】手动触发数据库重置，清理旧的错误数据"""
    try:
        from database import get_db
        db = await get_db()
        await db.execute("DELETE FROM opportunities")
        await db.execute("DELETE FROM price_history")
        await db.execute("DELETE FROM scan_logs")
        await db.commit()
        await db.close()
        
        # 清除内存缓存
        try:
            from scanner import _scan_cache
            _scan_cache.clear()
        except (ImportError, AttributeError):
            pass
            
        logger.warning("⚠️ 数据库已通过 /api/admin/reset 手动清空")
        return {"status": "ok", "message": "数据库已清空，请点击'立即扫描'重新采集数据"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", os.getenv("BACKEND_PORT", "8080")))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
