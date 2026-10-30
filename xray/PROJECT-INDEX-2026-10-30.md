# Keenetic / Xray v27: реестр проекта
Дата: 2026-10-30. Статус: исследование и проектирование, НЕ внедрено.

## Цель
Обновлять серверные пулы из VPN-подписки без перезапуска основного Xray, без потери существующих соединений и без выхода в обход VPN через провайдера. Гарантия отсутствия разрыва TCP/UDP пока НЕ доказана.

## Текущая система (подтверждено чтением роутера)
- `/opt/bin/xray-update-v23.py`: загрузка HTTPS-подписки, VLESS parsing через `setup_xray.create_outbound`, `xray_server_check.probe`, `xray_openai_probe.check`, допуск только при OpenAI reachable, проверка Xray `run -test`.
- `/opt/bin/xray_openai_probe.py`: временный изолированный Xray/SOCKS; HTTP 401 от `https://api.openai.com/v1/models` считается достижимостью.
- `/opt/bin/xray-safe-hourly.sh`: staging-only, пишет `/opt/etc/xray/config.pending.json`, не перезапускает Xray.
- `/opt/bin/setup_xray.py`: преобразователь VLESS URI; его standalone `main` ПИШЕТ `config.json` и создаёт `direct` outbound, поэтому запускать standalone нельзя.
- `/opt/bin/update_xray_subscription.py`: старый updater; `--apply` изменяет `config.json`, не использовать в v27.
- `/opt/bin/test-vpn-servers.py`: создаёт тестовый конфиг на диске; не запускать как read-only.
- `/opt/bin/xray-control-v24.py`, `/opt/bin/xray-identity-v24.py`: только проверки процессов.
- `/opt/bin/xray-watchdog-v25.sh`: только наблюдение.
- `/opt/bin/xray-watchdog.sh`: при отсутствии SOCKS вызывает `S97xray restart`.
- `/opt/etc/init.d/S97xray`: restart через `killall xray` (опасно для blue-green).
- `/opt/etc/init.d/S99xray-watchdog`: всё ещё указывает на старый watchdog.
- `/opt/bin/xray-watchdog-switch-v26.py`: safety-gate, activation NOT_IMPLEMENTED.
- `/opt/etc/xray/config.pending.json`: кандидат с VLESS и `leastPing`, Google probe; **не публиковать полный конфиг с пользовательскими идентификаторами/секретами**.

## Проверенные задания
Партия 1: d290b026, 9da27fcb, 47e7b90b, 1fb911ca, 4c4c43dd — все done, exit 0.
Партия 2: f0c71a65, b8194218, 0782de07, 44326dde — done exit 0; 803ca834 — done exit 1 operation_failed.
Партия 3: e438cf68, 82b6337c, e550fc0f, 0ced0f24, aeef051e — все done, exit 0.
См. подробные отчёты `xray-v27-batch*-*.md` и `xray-v27-seamless-pool-switch-design-2026-10-30.md`.

## Файлы библиотеки
- `sources/`: ранее архивированные версии v23–v26, а также `setup_xray.library.py`, `xray-safe-hourly.LEGACY-library.sh`, `update_xray_subscription.LEGACY-library.py`.
- **LEGACY-library означает старую версию из библиотеки, НЕ подтверждённый снимок текущего роутера.**
- `diagnostics/`: staging status, inventory, switch review.
- `patches/`: исторический draft patch, НЕ применять без сверки.
- Корень `/Keenetic/Xray/`: архитектура v27, отчёты партий, проверки сети и план.

## Отсутствующие подтверждённые исходники в папке проекта
Нужны именно актуальные безопасно очищенные снимки роутера:
`xray-update-v23.py`, `xray_openai_probe.py`, `xray_server_check.py`, `xray-safe-hourly.sh`, `setup_xray.py`,
`update_xray_subscription.py`, `test-vpn-servers.py`, `xray-watchdog.sh`,
`S97xray`, `S99xray-watchdog`.
Не переносить подписку `subscription.url`, приватные ключи, токены, `config.json`, `config.pending.json` целиком. Для конфигов архивировать только редактированные структурные сводки и SHA-256, если проверен на реальных байтах.

## Следующий этап
1. Безопасно получить отсутствующий `xray_server_check.py` и проверить установленный Xray API, возможность AddOutbound/RemoveOutbound без рестарта.
2. Выбрать горячую смену outbound или blue-green с управлением TCP/UDP flow stickiness и drain.
3. Устойчивые идентификаторы серверов; повторная проверка OpenAI перед активацией; fail-closed; rollback.
4. Создать кандидат, тестировать отдельно. После успешного внедрения сохранить именно финальные файлы с SHA-256 и инструкцией отката.

## Безопасность
В ходе документирования работающие Xray, cron, маршруты, firewall и kill-switch не менялись. 