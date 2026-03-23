# UI Spec — Phone UI (Life Reflex Arc)

## Screen Map (server phase -> screen)
- CREATED -> Created (Victim Monitoring / Alerting)
- DISPATCHED -> Dispatch (role-specific join)
- CPR -> Cpr
- AED_PICKED -> RunnerPicked (Runner delivery)
- AED_DELIVERED -> Convergence
- HANDOVER -> Handover

> Note: Role-based join is controlled by server role status (PRIME/RUNNER/GUIDE). UI must render from IncidentState only.

---

## Global Tokens (approx from screenshots)
- Phone frame: 320x640 dp canvas, corner radius 36dp, inner radius 28dp
- Top status bar: 14:00 left, 5G 100% right, 10sp
- Primary text: 24–32sp, bold
- Secondary text: 12–14sp
- Button height: 52–56dp, radius 14–16dp
- Card radius: 16–20dp
- Colors:
  - Black: #0A0A0A
  - Dark navy: #0F172A
  - Slate: #1F2937
  - Red: #DC2626
  - Blue: #2563EB
  - Green: #16A34A
  - Yellow: #F59E0B
  - Gray text: #94A3B8

## Animations
- Live indicator: pulse (alpha 0.4→1.0, duration 1200ms, infinite, easeInOut)
- Button press: scale 1.0→0.96 on press
- Alert countdown ring: sweep progress 1.0→0.0 with 1s ticks
- Screen transitions: fade+slide (AnimatedVisibility: enter fadeIn(200) + slideInVert(20), exit fadeOut(200))

---

## Created Screen (Victim)
### Monitoring
- Layout: black background, centered ECG bar graph
- Top-left: “HEALTH GUARD” 10sp, green heartbeat icon right
- Center: bars (red), BPM 86 (56sp), “监测中...”
- Bottom: dark button “异常确认”
- Logs panel bottom (LazyColumn)

### Alerting
- Layout: black background
- Center: circular countdown ring (red/gray), big number
- Text: “SOS ALERT” red
- Body: “检测到异常倒地 / 即将自动呼叫急救”
- Button: “我没事（取消）”

---

## Dispatch Screen
- Background: red header block, rounded bottom
- Header chips: “一级危急(SCA)” + incidentId
- Title: 附近有人 心脏骤停
- Subtitle: 距离您 150 米 • 购物中心中庭
- Golden Rescue Time card: dark card, 3:30 yellow
- Buttons row: left ghost “无法前往”, right red “立即响应”
- Logs panel bottom

---

## Cpr Screen
- Background: black
- Title: “CPR METRONOME” 10sp
- Center: green circular dial, 100 BPM
- Footer: two buttons “开始CPR” (red dot) and “呼叫替补” (icon)
- Logs panel bottom

---

## RunnerPicked Screen
- Header: blue block with lightning, “AED 紧急配送”
- Target tag: “目标：二楼服务台 AED箱”
- Map card with dotted path and AED tag
- Status card: “STATUS / 正在前往取件” or “正在赶回患者位置”, ETA 30s
- Primary button: “到达 AED 位置” or “到达患者位置”
- Logs panel bottom

---

## Convergence Screen
- Background: dark
- Center: large green circle, “50m”, “Closing In”
- Text: “AED 即将到达”
- Button: “AED 已送达”
- Logs panel bottom

---

## Handover Screen
- Background: white
- Top: green success icon + “任务归档”
- Card: NFC 一碰传 (dashed border)
- Stats list: 总耗时/协同人数/AED使用
- Logs panel bottom
