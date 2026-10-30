# Keenetic Xray: журнал v27–v29
Дата: 2026-10-30. Лаборатория v29 ещё не запускалась.

## Ограничения
Не менять production Xray, cron, firewall, маршруты, kill-switch. Не раскрывать VPN-секреты. Асинхронные задания не дублировать.

## v27: BO лаборатория и очистка
- `4c229d1f-7c93-4906-9d79-d8ab43c712b9`: exit_code=0; CONFIG_VALIDATION_SUCCESS; BO lab-vpn-a EXIT 0; OLD_BEFORE A; BO lab-vpn-b EXIT 0; NEW_AFTER B; OLD_AFTER OLD_STILL_ALIVE; BO_TEST_COMPLETE. Локальные синтетические outbounds, не реальные VPN.
- `2748597a-540e-444f-aa8b-81e0e03d78ee`: exit_code=0; LAB_DIRECTORY_ABSENT, NO_LAB_LISTENERS; production PID 13546; SHA256 `66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7`.

## v28: read-only аудит production
- `0e53b54d-c8d7-43fb-bc26-53ec10b5f037`: done, exit_code=0.
- Xray 26.2.6, linux/mipsle; PID 13546.
- `/opt/etc/xray/config.json` SHA256 `66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7`; MATCHES_V27=True.
- Balancer `auto`, selector `vpn`, strategy `leastPing`, fallbackTag присутствует (значение не выводилось).
- Outbounds: vpn01, vpn02, vpn04, vpn05, vpn06, vpn07, vpn09 (VLESS); blocked (blackhole).
- Inbounds: local-socks (SOCKS, loopback, 10808); tproxy-in (dokodemo-door, 12345).
- API отсутствует: ENABLED=False, TAG=None, SERVICES=[].
- Routing: local-socks/tproxy-in -> balancer auto; следующее правило -> blocked.
- Вывод: BO в production пока недоступен без отдельного изменения конфигурации; совместимость с leastPing/fallback ещё не доказана.

## v29: подготовка лаборатории
- План: balancer `auto`, `leastPing`, selector `vpn`, fallback `lab-fallback`, семь синтетических freedom-outbound, SOCKS 18091, API 18090; BO vpn01 -> A, vpn02 -> B, сохранение старого TCP.
- Тест НЕ проверяет реальный автоматический выбор leastPing или срабатывание fallback.
- Файл на роутере `/opt/tmp/xray-v29-lab.sh`.
- Задание `9e5cffa5-e1eb-4415-b210-ac9e65361d9d`: done, exit_code=0, written=true, SHA256 `3ffd0cf5e79ec8df2f0f7aa82c014e2f245488edb582805a69d8e49cf0832d2b`, backup_created=false.
- Скрипт НЕ запускался. Команда `/opt/bin/sh /opt/tmp/xray-v29-lab.sh` требует отдельного разрешения. Скрипт создаёт временные файлы/процессы и не является read-only.

## Следующие шаги
1. С отдельного разрешения проверить занятость портов 18090, 18091, 18111, 18112, 18114, 18115, 18116, 18117, 18119, 18120 и независимо сверить SHA256 скрипта.
2. С отдельного разрешения однократно запустить лабораторию, дождаться результата.
3. Проверить cleanup, production PID и SHA256, внести результаты в журнал.