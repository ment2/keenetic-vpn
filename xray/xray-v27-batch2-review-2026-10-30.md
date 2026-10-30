# Keenetic Xray v27 — вторая партия read-only

Дата: 2026-10-30. Цель: бесшовное обновление VPN-пулов. Никаких изменений на роутере.

## Проверенные задания
- f0c71a65-5b8d-4830-8f6b-a507a80e8e68: done, exit_code 0, config.pending.json (redacted).
- b8194218-213b-4450-80d5-6292179622c9: done, exit_code 0, xray-identity-v24.py.
- 0782de07-28b6-44bb-9a99-c3878b92fccf: done, exit_code 0, test-vpn-servers.py.
- 44326dde-ac39-4225-be2e-5471ff1bb945: done, exit_code 0, xray-watchdog.sh.
- 803ca834-6acf-4d90-9eda-518775f3f16a: done, exit_code 1, operation_failed for config-server-test.json. Existence is unknown.

## Подтверждённые особенности
- config.pending.json: VLESS outbounds vpn01, vpn02, vpn04, vpn05, vpn07, vpn09; blocked blackhole; SOCKS 127.0.0.1:10808, TPROXY :12345; balancer auto, leastPing, selector vpn, fallbackTag vpn01; observatory probe Google generate_204 every 60s. Это не OpenAI qualification.
- xray-identity-v24.py: строго проверяет командную строку основного процесса и PID/start_ticks, не меняет состояние.
- test-vpn-servers.py: читает текущий config.json, создаёт SOCKS inbounds на 11000+номер тега, маршрутизирует их к соответствующим VLESS; пишет /opt/etc/xray/config-server-test.json и chmod 0600. НЕ запускать как read-only.
- xray-watchdog.sh: каждые 30с проверяет SOCKS LISTEN и при отсутствии вызывает S97xray restart; последний использует killall xray. Риск для blue-green.

## Выводы
- Существующий pending конфиг не является подтверждённым рабочим новым пулом.
- Для бесшовного обновления требуется разобраться с источником подписки, формированием pending, критериями OpenAI-qualified и точкой переключения, исключив killall/restart.
- Секреты и адреса VPN-серверов в отчёт не включены.
- Не менялись Xray, cron, firewall, маршруты, kill-switch, файлы и сервисы на роутере.