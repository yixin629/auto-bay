# AutoBay API 接口文档

Base URL: `http://localhost:8000/api/v1`

认证方式：Bearer Token（除了 register 和 login 外所有接口都需要）

```
Authorization: Bearer <access_token>
```

---

## 1. Auth 认证模块

### POST /auth/register — 用户注册
```json
// Request
{ "email": "user@example.com", "password": "password123", "full_name": "张三" }

// Response 201
{ "id": "uuid", "email": "user@example.com", "full_name": "张三", "role": "owner", "is_active": true }
```

### POST /auth/login — 用户登录
```json
// Request
{ "email": "user@example.com", "password": "password123" }

// Response 200
{ "access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer" }
```

### GET /auth/me — 获取当前用户
```json
// Response 200
{ "id": "uuid", "email": "user@example.com", "full_name": "张三", "role": "owner", "is_active": true }
```

---

## 2. Products 产品模块

### POST /products/ — 创建产品
```json
// Request
{
  "sku": "PHONE-CASE-001",
  "title": "Premium Silicone Phone Case iPhone 15",
  "description": "High quality silicone case...",
  "category": "Phone Accessories",
  "brand": "AutoBay",
  "sourcing_mode": "alibaba_1688",     // alibaba_1688|alibaba_intl|domestic_agency|dropship|own_inventory
  "sourcing_config": { "supplier_url": "https://detail.1688.com/offer/xxx.html", "moq": 50 },
  "base_cost": 15.00,
  "base_cost_currency": "CNY",
  "images": [{ "url": "https://...", "position": 0, "alt_text": "Front view" }],
  "attributes": { "color": "Black", "material": "Silicone" },
  "weight_grams": 50,
  "country_of_origin": "CN",
  "hs_code": "3926909090"
}

// Response 201
{ "id": "uuid", "sku": "PHONE-CASE-001", "status": "draft", ... }
```

### GET /products/ — 产品列表
Query 参数：`offset=0`, `limit=50`, `status=active|draft|archived`

```json
// Response 200
{ "items": [{ "id": "uuid", "sku": "...", "title": "...", ... }], "total": 42 }
```

### GET /products/{product_id} — 产品详情
### PATCH /products/{product_id} — 更新产品（部分更新）
### DELETE /products/{product_id} — 删除产品（204 No Content）

---

## 3. Listings 平台 Listing 模块

### POST /listings/ — 创建 Listing
```json
// Request
{
  "product_id": "product-uuid",
  "platform_connection_id": "connection-uuid",
  "title": "eBay-specific title override",    // 可选，不填用产品标题
  "price": 49.99,
  "currency": "AUD",
  "pricing_strategy": "cost_plus",            // fixed|cost_plus|competitor_match|ai_dynamic
  "pricing_config": { "margin_pct": 0.30, "shipping_estimate": 5.00 }
}
```

### GET /listings/ — Listing 列表
Query 参数：`product_id`, `platform`, `status`, `offset`, `limit`

### GET /listings/{listing_id} — Listing 详情
### PATCH /listings/{listing_id} — 更新 Listing
### DELETE /listings/{listing_id} — 删除 Listing

---

## 4. Orders 订单模块

### POST /orders/ — 创建订单（手动或同步创建）
```json
{
  "platform_connection_id": "connection-uuid",
  "external_order_id": "eBay-12345",
  "customer_name": "John Smith",
  "customer_email": "john@example.com",
  "shipping_address": { "street1": "123 Main St", "city": "Sydney", "state": "NSW", "zip": "2000", "country": "AU" },
  "currency": "AUD",
  "line_items": [
    { "title": "Phone Case", "sku": "PHONE-CASE-001", "quantity": 2, "unit_price": 49.99 }
  ]
}
```

### GET /orders/ — 订单列表
Query 参数：`status`, `platform`, `offset`, `limit`

### GET /orders/{order_id} — 订单详情（含 line_items + shipments）
### PATCH /orders/{order_id} — 更新订单状态
```json
{ "status": "shipped", "tracking_number": "AU123456", "carrier": "Australia Post" }
```

---

## 5. Inventory 库存模块

### POST /inventory/locations — 创建仓库
```json
{ "name": "深圳仓库", "country": "CN", "location_type": "own_warehouse" }
```

### GET /inventory/locations — 仓库列表
### GET /inventory/products/{product_id} — 查询产品库存（按仓库）
### POST /inventory/adjust — 调整库存
```json
{
  "product_id": "uuid",
  "location_id": "uuid",
  "quantity_change": 100,      // 正数=入库，负数=出库
  "movement_type": "purchase", // purchase|sale|adjustment|return_stock|transfer
  "notes": "首批到货 100 件"
}
```

---

## 6. Pricing 定价模块

### POST /pricing/calculate — 计算建议价格
```json
// Request
{
  "base_cost": 15.00,
  "cost_currency": "CNY",
  "target_currency": "AUD",
  "margin_pct": 0.30,
  "platform": "ebay",
  "shipping_estimate": 5.00
}

// Response 200
{
  "suggested_price": 12.86,
  "exchange_rate": 0.22,
  "cost_in_target": 3.30,
  "estimated_profit": 4.56,
  "margin_pct": 0.30
}
```

---

## 7. Customer Service 客服模块

### GET /customer-service/messages — 消息列表
Query 参数：`requires_human=true|false`, `offset`, `limit`

### POST /customer-service/messages/{message_id}/approve — 审批 AI 草稿并发送
```json
{ "response_text": "可选：编辑后的回复内容（不填则用 AI 草稿）" }
```

---

## 8. Marketing 营销模块

### POST /marketing/campaigns — 创建营销活动
```json
{ "name": "Summer Sale eBay", "campaign_type": "ebay_promoted", "budget_daily": 50.00 }
```

campaign_type 枚举：`ebay_promoted|amazon_ppc|google_ads|facebook_ads|tiktok_ads|social_post`

### GET /marketing/campaigns — 活动列表
### POST /marketing/campaigns/{campaign_id}/generate — AI 生成广告内容
```json
{
  "product_title": "Premium Phone Case",
  "product_description": "Silicone protective case...",
  "target_audience": "tech enthusiasts"
}

// Response
{
  "ad_copy": { "headlines": ["...", "..."], "descriptions": ["..."] },
  "keywords": ["phone case", "iPhone 15 case", ...]
}
```

---

## 错误响应格式

```json
// 400
{ "detail": "Bad request: specific error message" }

// 401
{ "detail": "Not authenticated" }

// 404
{ "detail": "Product not found" }

// 409
{ "detail": "Product with SKU 'xxx' already exists" }

// 422 (Validation Error)
{ "detail": [{ "loc": ["body", "sku"], "msg": "Field required", "type": "missing" }] }
```
