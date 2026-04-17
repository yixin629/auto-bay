# AutoBay Celery 后台任务说明

## 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────────┐
│ Celery Beat │────>│    Redis     │────>│   Celery Workers        │
│  (调度器)    │     │  (消息队列)  │     │                         │
│             │     │             │     │  Queue: default (通用)    │
│ 4 个定时任务 │     │  3 个 DB:    │     │  Queue: sync   (同步)    │
│             │     │  /1 broker  │     │  Queue: ai     (AI任务)  │
│             │     │  /2 results │     │                         │
└─────────────┘     └─────────────┘     └─────────────────────────┘
```

---

## 定时任务列表

| 任务 | 频率 | 队列 | 文件 |
|------|------|------|------|
| sync_all_orders | 每 5 分钟 | sync | `tasks/sync_orders.py` |
| sync_all_inventory | 每 15 分钟 | sync | `tasks/sync_inventory.py` |
| fetch_rates | 每 24 小时 | default | `tasks/update_exchange_rates.py` |
| recalculate_all_prices | 每 1 小时 | default | `tasks/update_pricing.py` |

---

## 任务详情

### 1. sync_all_orders — 订单同步

**频率**：每 5 分钟

**逻辑**：
1. 查询所有 `is_active=True` 的 PlatformConnection
2. 对每个 connection，通过 ConnectorRegistry 获取对应的 Connector
3. 调用 `connector.fetch_orders(since=last_synced_at)`
4. 对比 `external_order_id` 去重
5. 新订单插入 `orders` + `order_line_items` 表
6. 更新 `platform_connection.last_synced_at`

**重试策略**：最多 2 次重试，间隔 60 秒

**错误处理**：单个平台失败不影响其他平台，记录日志后继续

### 2. sync_all_inventory — 库存同步

**频率**：每 15 分钟

**逻辑**：
1. 查询所有 `status=active` 且 `external_listing_id IS NOT NULL` 的 Listing
2. 对每个 listing，查询其 product 在所有仓库的库存
3. 计算 `available = sum(on_hand - reserved)`
4. 调用 `connector.update_stock(external_listing_id, available)`
5. 更新 `listing.last_synced_at`

**重试策略**：最多 2 次重试，间隔 120 秒

### 3. fetch_rates — 汇率更新

**频率**：每天一次（UTC 00:00）

**逻辑**：
1. 调用 exchangerate.host API 获取 CNY 对 AUD/USD/GBP/EUR 汇率
2. 每个汇率对插入一条新记录到 `exchange_rates` 表
3. 查询时取最新一条（按 `fetched_at` 降序）

**回退**：API 不可用时使用硬编码的近似汇率

### 4. recalculate_all_prices — 价格重算

**频率**：每小时

**逻辑**：
1. 查询所有 `pricing_strategy != 'fixed'` 且 `status=active` 的 Listing
2. 对每个 listing：
   - 获取产品成本 + 汇率
   - 根据策略计算新价格（cost_plus / competitor_match / ai_dynamic）
   - 如果价格变化 > $0.01，更新 listing.price
   - 记录到 `price_history` 表
   - 如果有 external_listing_id，推送新价格到平台

---

## 启动命令

```bash
# 启动 Worker（处理所有队列）
celery -A app.workers.celery_app worker -l info -Q default,sync,ai

# 启动 Beat（定时调度器）
celery -A app.workers.celery_app beat -l info

# 生产环境建议：按队列隔离 Worker
celery -A app.workers.celery_app worker -l info -Q sync -c 4        # 高并发同步
celery -A app.workers.celery_app worker -l info -Q ai -c 2          # AI 任务（昂贵）
celery -A app.workers.celery_app worker -l info -Q default -c 4     # 通用任务
```

---

## 配置说明 (`celery_app.py`)

```python
celery_app.conf.update(
    task_serializer="json",        # JSON 序列化
    task_track_started=True,       # 追踪任务开始时间
    task_acks_late=True,           # 任务完成后再确认（防丢失）
    worker_prefetch_multiplier=1,  # 每次只取一个任务（公平调度）
    task_routes={                  # 路由规则
        "app.workers.tasks.sync_*": {"queue": "sync"},
        "app.workers.tasks.ai_*": {"queue": "ai"},
        "app.workers.tasks.*": {"queue": "default"},
    },
)
```

---

## 监控

```bash
# 安装 Flower（Celery 可视化监控）
pip install flower

# 启动 Flower
celery -A app.workers.celery_app flower --port=5555

# 访问 http://localhost:5555
```
