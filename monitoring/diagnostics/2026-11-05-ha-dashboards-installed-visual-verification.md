# Home Assistant dashboards installed: owner screenshot verification (2026-11-05)

## Evidence and scope
Owner supplied screenshots of **two separate, already-installed Home Assistant dashboards** in the mobile UI on 2026-11-05 at approximately 21:13–21:15 local clock. This supersedes the older historical note that the Lovelace dashboard YAML was only prepared, not installed. These are direct visual evidence of cards and live-looking sensor values/history in HA; they do not by themselves prove exact entity registry IDs, backend source revision, continuous availability or future boot persistence.

### 1. HA Agent Monitor / Мониторинг системы
The first screenshot (same conversation) shows a dedicated **HA Agent Monitor** section in the existing “Мониторинг системы” dashboard:
- Состояние агента: **RUNNING**
- Подключение Cloudflare: **Подключено**
- Количество опросов: **13**
- Последний опрос: **28 секунд назад**
- Авария: **OK**
- History graph visibly includes previous `BLOCKED`, `Отключено`, `Проблема` segments. These are past events, not the current agent status.

Separate terminal evidence confirms the safe-preflight-recovery monitor candidate was installed and subsequently reached `POLLS=8`, `HA_AGENT_IDLE`, `PENDING_JOURNAL=False`. Policy revision 3 permits diagnostic, exec, read_file, write_file inside the HA SSH add-on. This does not establish HA OS host-root access.

### 2. Keenetic VPN Monitoring / VPN и OpenAI
Four owner screenshots show **the VPN и OpenAI dashboard is already installed in the HA UI**, with rendered cards:
- `Сводка по VPN`, `Доступность OpenAI через каждый узел`, `Состояние VLESS`
- `История статусов VLESS · 24 ч` and `· 7 дней`
- `Длительность полной VLESS-пробы` and `Полная длительность VLESS-пробы · 24 ч`
- Existing YAML source: `monitoring/homeassistant/keenetic_vpn_dashboard.yaml`. These screenshots corroborate its cards and content, without proving exact live dashboard source SHA.

**VLESS HTTP summary at screenshot time: 6/7 OK, 1 failed, 0 missing.**
- vpn01: ok, DE, egress 78.17.178.91, full probe 2633 ms.
- vpn02: ok, NL, egress 140.225.199.96, full probe 2711 ms; historical failed interval visible in 24h graph.
- vpn04: ok, DE, egress 78.17.178.113, full probe 2804 ms.
- vpn05: ok, DE, egress 78.17.178.113, full probe 3100 ms.
- vpn06: failed, country/egress unknown, full probe 4123 ms; many recurring short failures/successes visible in 24h and 7d history.
- vpn07: ok, RU, egress 95.129.234.51, full probe 1224 ms.
- vpn09: ok, US, egress 152.53.242.98, full probe 2986 ms.

**OpenAI per-node reachability is separate from generic VLESS HTTP.** Visible current-cycle screenshots show vpn01, vpn02, vpn04, vpn05, vpn09 reachable; vpn06 and vpn07 `network_error`. Screenshot examples: vpn05 checked 2026-11-05T18:00:21.297300+00:00, 3916 ms; vpn06 18:00:26.593537+00:00, 5268 ms; vpn07 18:00:38.701863+00:00, 12067 ms; vpn09 18:00:42.741008+00:00, 4012 ms. This is one observed snapshot, not a lasting diagnosis.

The dashboard correctly distinguishes general VLESS status, OpenAI reachability and full end-to-end test duration (not RTT). These results **do not identify real user session routing or traffic volume attributable to a specific VPN**. The dashboard's charts and values demonstrate HA entity updates/history at screenshot time. Do not treat old history bars as current failures.

## Updated project status
- **Both HA Agent Monitor and Keenetic VPN Monitoring dashboards are ALREADY INSTALLED AND VISIBLY WORKING in HA** as of the supplied screenshots. Do not instruct owner to re-import YAML, recreate sensors or repeat basic deployment diagnostics.
- 7 VPN nodes appear; the 28 general VLESS + 21 OpenAI + 12 interface sensor architecture remains documented in historical integration notes. Screenshots directly demonstrate only displayed cards/entities, not an exhaustive registry count or the interface cards.
- Open HA investigation items: vpn06 intermittent generic VLESS failure; vpn06 and vpn07 OpenAI `network_error`; vpn02 earlier generic failure period; improve chart legibility on iPhone only if desired. Investigate with existing telemetry and historical notes before demanding Termius commands.
- Do not alter production Xray, VPN pool, firewall, routes or cron merely because monitoring reports failures.
- HA Agent Monitor and VPN dashboard are distinct independent monitoring displays. Avoid confusing their installation or state.

## Earlier sources
- `monitoring/homeassistant/keenetic_vpn_dashboard.yaml`
- `monitoring/README.md` (the “not installed” statement is now superseded)
- `monitoring/diagnostics/2026-11-04-monitor-writefile-lockfix-and-ha-dashboard.md`
- `ment2/keenetic-control`, `feature/homeassistant-admin-agent-20261104`, HA incident diagnostics and safe-preflight rollout notes.
