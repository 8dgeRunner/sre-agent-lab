# Design System — SRE Agent 靶场

## Product Context

- **What this is:** 给 SRE、平台工程师和技术负责人使用的故障诊断练习与 Agent 评测平台。
- **Who it's for:** 同事、领导、评测参与者和平台管理员。
- **Space/industry:** SRE、混沌工程、AIOps。
- **Project type:** 内部工具 / 诊断工作台。

## Aesthetic Direction

- **Direction:** Industrial / Utilitarian。
- **Decoration level:** Minimal；把视觉重点留给告警、证据和评分。
- **Mood:** 像一块可靠的值班控制台：克制、清晰、带一点现场感。
- **Layout:** 案例侧栏 + 主工作区，流程按“任务—证据—诊断—评分”推进。

## Typography

- **Display / Body:** IBM Plex Sans — 可读、工程感强，适合中英文混排。
- **Data / Code:** JetBrains Mono — 用于 Run ID、证据 ID 和数值。
- **Loading:** Google Fonts CDN；网络不可用时回退到系统无衬线字体。

## Color

- **Approach:** Restrained。
- **Primary ink:** `#18201D` — 文字、导航和主要结构。
- **Accent:** `#D84B2A` — 开始演练、提交和关键动作。
- **Surface:** `#FFFEF9` — 卡片和工作区。
- **Canvas:** `#F5F4EE` — 页面背景。
- **Semantic:** success `#26734D`，warning `#9B6515`，error `#A42C20`，info `#1E5D88`。

## Spacing and Layout

- **Base unit:** 4px。
- **Density:** Comfortable；让证据文本和评分足够易读。
- **Grid:** 桌面两列（案例 270px + 主区），移动端单列。
- **Max content width:** 1180px。
- **Border radius:** 6px controls, 8px cards, 10px panels, 9999px status pills。

## Motion

- **Approach:** Minimal-functional。
- **Behavior:** 只使用按钮状态、步骤切换和 loading 状态，不使用干扰诊断的装饰动画。

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-08-18 | 首版网页登录工作台 | 让同事和领导无需手动操作 Bearer Token 即可体验完整流程 |
