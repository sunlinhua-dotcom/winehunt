# 🍷 Wine Deal Hunter — 开发日志

## 2026-02-16 阶段一：项目初始化与核心开发

### 需求确认

- 确认三层免费数据源策略：Bordeaux Index API → Wine-Searcher 爬虫 → Wine-Searcher 试用 API
- 确认利润计算公式、运费模型、保险费率
- 确认硬通货酒清单：50+ 款全球保值型葡萄酒

### 后端开发

创建 7 个核心模块：

1. `wine_list.py` — 50+ 硬通货清单 + 运费模型 + 利润计算
2. `database.py` — SQLite 数据库（4 张表 + CRUD）
3. `scraper.py` — Wine-Searcher 爬虫（反爬 + 价格解析 + 汇率转换）
4. `analyzer.py` — 捡漏分析引擎（利润率 + 评分算法）
5. `notifier.py` — Telegram 推送（机会通知 + 每日摘要）
6. `scanner.py` — 定时扫描调度（全量/单酒）
7. `main.py` — FastAPI 主应用（15+ REST API + 定时任务 + 前端服务）

### 前端开发

创建 3 个前端文件（嵌入 FastAPI 静态服务）：

1. `index.html` — 6 页面结构（Dashboard/捡漏/搜索/监控/清单/日志）
2. `style.css` — 高端暗色主题 + Glassmorphism + 响应式
3. `app.js` — SPA 导航 + API 调用 + 实时状态更新

### 验证结果

- ✅ 后端依赖安装成功
- ✅ 应用启动正常（<http://localhost:8080）>
- ✅ Dashboard 页面加载正确
- ✅ 硬通货清单展示正确（50+ 酒款按分类）
- ✅ 手动搜索页面功能正常
- ✅ 监控酒单页面功能正常
- ✅ 侧边导航流畅切换

## 2026-02-16 阶段二：UI/UX 全面重构

### 需求

- 从"AI 生成感"转向葡萄酒行业专业交易工具美学
- 酒红 + 暗金配色系统
- SVG 图标替代全部 emoji
- 移动端底部固定导航
- 实时扫描进度面板

### 修改文件

1. `style.css` — 酒红暗金配色 + Cormorant Garamond 字体 + 44px 触控 + 移动端适配
2. `index.html` — 全部 SVG 图标 + ARIA 无障碍 + 扫描状态面板
3. `app.js` — 扫描进度轮询 + API 格式适配 + 导航联动
4. `scanner.py` — 新增 `_scan_progress` 实时进度追踪
5. `main.py` — `/api/scan/status` 增强返回完整进度数据

### 验证结果

- ✅ 酒红+金色配色系统正确呈现
- ✅ SVG 图标全面替代 emoji
- ✅ 移动端 375px 底部导航正常显示
- ✅ 桌面端侧边栏导航功能正常
- ✅ 硬通货清单按产区分类展示
- ✅ 搜索页简洁专注
- ✅ 后端 API 数据格式兼容

## 2026-02-16 阶段三：搜索功能 Bug 修复

### 问题

- 搜索任何酒名都返回空/失败
- 用户反馈「一款酒都搜索不到」

### 根因分析

1. **HTTP 方法不匹配**：前端 `searchWine()` 用 GET + URLSearchParams 发请求，后端 `/api/search` 定义为 POST + JSON body → 405 Method Not Allowed
2. **返回字段不匹配**：前端期望 `data.global_lowest` / `data.hk_average`（扁平），后端返回嵌套结构 `data.global_lowest.price_usd` / `data.hk_avg_price`
3. **酒品类展示正常**：`wine_list.py` 有 50 款酒 (8 个分类)，`/api/wines` 接口正常返回

### 修复内容

1. `app.js` — searchWine() 改为 POST + JSON body，修复字段映射，增强搜索结果渲染
2. `main.py` — /api/search 返回扁平化结构，统一字段名，移除扫描锁阻塞
3. `scraper.py` — 重写为三引擎瀑布降级架构：
   - **ScraperAPI**（主引擎）：免费代理 IP 绕过 IP 封锁，5000 次/月
   - **curl_cffi**（备用）：模拟 Chrome/Safari TLS 指纹
   - **httpx**（兜底）：基础 HTTP 请求
4. `.env` — 新增配置文件存放 ScraperAPI Key 和扫描间隔

### 验证结果

- ✅ ScraperAPI 成功绕过 Wine-Searcher 403 封锁
- ✅ Dom Perignon 搜索返回完整数据（全球最低价 $89.05，香港均价 $1046.46，利润率 884.7%）
- ✅ 搜索结果包含酒商名称、运费、查看链接
- ✅ 硬通货清单显示 50 款酒 / 8 个分类 正常

### 后续优化

- 修复竞标价格（Auction/Bid）被误认为零售价的问题（过滤 Auction/Bid 关键词，排除 <$20 异常低价）

## 2026-02-16 阶段四：全面代码审查与 Bug 修复

### 问题

- 用户反馈数据完全不真实：Chateau Haut-Brion 港卖 $35,657,308，利润率 858万%
- 买入/卖出价格显示 $0（字段名不匹配）
- 缺少购买链接

### 修复内容（共 11 个 Bug）

**前端 (app.js)**:

1. 修正字段映射 (`source_price` → `buy_price`)
2. 新增「直达链接」按钮

**爬虫 (scraper.py)**:
3. 香港页面 HKD 被误认 USD → 强制货币识别修正
4. fallback 方法3 抓到乱数据 → 收紧价格范围 $20-$15000
5. 香港均价无异常值过滤 → 增加中位数 5x 过滤
6. HTML 选择器覆盖不足 → 扩展 12 种选择器 + 调试日志

**分析器 (analyzer.py)**:
7. 无合理性校验 → 增加价格范围 $10-$20000、10x 比值上限、500% 利润率上限

**数据库 (database.py)**:
8. INSERT 无去重导致重复记录堆积 → 改为 UPSERT（同酒名只保留最新）
9. 日志缺少 duration 格式化字段 → 增加 `duration`/`scanned`/`found`/`scan_time`

**主应用 (main.py)**:
10. 手动搜索 API 绕过 analyzer 校验 → 复用 analyzer 结果 + 利润率上限兜底
11. 启动时不清理历史脏数据 → 自动 DELETE profit_rate > 500% 的记录

## 2026-02-16 阶段五：实时汇率 + API 消耗优化

### 问题

- ScraperAPI 免费额度 5020/5000 已超限，下次重置 2026-03-16
- 硬编码汇率 EUR=1.08 实际为 1.19（偏差 9.9%），CHF=1.12 实际为 1.30（偏差 **16.2%**）
- 50 款酒 × 2 次/酒 × 12 次/天 = 1200 次/天，5 天耗尽

### 修复内容

1. **新建 `exchange_rates.py`** — 实时汇率模块
   - 双 API 源: open.er-api.com（主） + fawazahmed0（备），完全免费无 Key
   - 6 小时缓存避免频繁请求
   - 硬编码兜底确保断网可用
   - 支持 15 种货币

2. **修改 `scraper.py`** — 对接实时汇率替代硬编码 EXCHANGE_RATES

3. **精简 `wine_list.py`** — 50→20 款核心酒 + 30 款备选
   - `PREMIUM_WINES` (20款) 用于定时扫描
   - `EXTENDED_WINES` (30款) 用于手动搜索
   - `ALL_WINES` (50款) 用于前端展示

4. **重写 `scanner.py`** — 智能缓存
   - 24h 内已扫且无机会的酒款自动跳过
   - 有机会的酒款始终重扫（追踪价格变化）
   - 每次扫描前预热汇率缓存

5. **修改 `main.py`** — 启动时预热实时汇率缓存

6. **更新 `.env`** — 新 ScraperAPI Key + 间隔从 2h→8h

### API 消耗对比

| 指标 | 优化前 | 优化后 | 降幅 |
|------|--------|--------|------|
| 酒款数 | 50 | 20 | -60% |
| 扫描间隔 | 2h | 8h | -75% |
| 每日调用 | 1200 次 | 120 次 | **-90%** |
| 额度可维持 | ~4 天 | **42 天** | +10x |
