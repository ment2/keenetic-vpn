# Keenetic Xray: проверенный staging и план безопасного переключения

Дата: 2026-10-30. Проект: Keenetic Ultra KN-1810, Entware, Xray, Telegram через SOCKS5, Cloudflare Worker v5 / Keenetic Mobile.

## Проверенный статус
- Рабочий Xray: PID 10821, процесс `/opt/sbin/xray run -config /opt/etc/xray/config.json`.
- SHA-256 рабочего `/opt/etc/xray/config.json`: `66d074f32fffbf4a251576c8297714e9647174546e9e73e5bf27cf2768efe6d7`, одинаковый до и после staging.
- SOCKS5 `127.0.0.1:10808`: LISTEN.
- Cron сохранён: `*/15 * * * * /opt/bin/flock -n /opt/tmp/xray-update.lock /opt/bin/xray-safe-hourly.sh >> /opt/var/log/xray-update.log 2>&1`.
- Обновлённый wrapper `/opt/bin/xray-safe-hourly.sh`: shebang `#!/opt/bin/sh`, права 700, SHA-256 `890c242609c1146f5ba6087a1f973fc4a707c82491c0892b96bd60aac261deb5`. Резервная копия `/opt/bin/xray-safe-hourly.sh.pre-entware-shell-20261030`.
- Wrapper выполняет генерацию и проверку кандидата, но только сохраняет `/opt/etc/xray/config.pending.json`; не заменяет рабочий config.json и не перезапускает Xray.
- Результат staging: exit code 0; `config.pending.json` создан, 6615 байт, права 600; `xray run -test` exit 0.
- Кандидатов подписки 12: 7 ALLOWED, 5 UNVERIFIED/ошибка API. В staging: `vpn01`, `vpn02`, `vpn04`, `vpn05`, `vpn06`, `vpn07`, `vpn09`. Balancer `auto`, selector `vpn`, fallbackTag `vpn01` (в проверенном пуле).
- Генератор `/opt/bin/xray-update-v23.py` вызывает `check_openai(outbound)` для каждого кандидата и добавляет в `allowed` только `api_status == 'reachable'`. При пустом пуле не генерирует применяемую конфигурацию. OpenAI probe использует временный Xray и SOCKS5, успешный тест API — HTTP 401 на `/v1/models`.
- Логи показывают `STAGED_ONLY ... NOT applied, no restart`; старое `SUCCESS: OpenAI VPN pool active` от прежнего сломанного wrapper не является подтверждением применения.
- Xray предупреждает о deprecated VLESS без Flow, gRPC, WebSocket ALPN, `host` в headers; кандидат проходит синтаксический тест.

## Инварианты безопасности
1. Не вызывать `killall xray`, `S97xray stop/restart`, не перезапускать действующий Xray без отдельного разрешения.
2. Не менять cron, маршруты, TPROXY, kill-switch, правила fail-closed.
3. Не допускать прямого обхода провайдера для Telegram: Telegram использует SOCKS5 `127.0.0.1:10808`.
4. В пул и fallback допускаются только индивидуально проверенные для OpenAI VPN-серверы.
5. До проверки механизма безопасного переключения сохранять режим staging-only.

## Следующая фаза
- Изучить имеющиеся `/opt/bin/xray-control-v24-next.py`, watchdog v25/v26 и текущую конфигурацию на предмет динамического Xray API, совместимости и отката. Пока API в текущем рабочем процессе не подтверждён как доступный.
- Разработать план контролируемого переключения с резервным процессом, отдельными портами и тестами; избегать конфликтов TPROXY/SOCKS, сохранять fail-closed и предусмотреть откат.
- Выполнять только read-only диагностику и dry-run до отдельного разрешения на сетевое переключение.
- После проверки добавить результаты в `/Keenetic/Xray/diagnostics/` и финальные исходники в `/Keenetic/Xray/sources/`.

## Задания проверки
- `82347548-49b0-4578-97ac-23dd7f9b3e97`: staging DONE, exit 0.
- `03927629-cd64-4941-8e1e-9538c8c50b0a`: аудит OpenAI, fallback, PID, SHA, SOCKS5 DONE, exit 0.
- `ce28a762-330a-44be-9a02-3217b340ac23`: чтение существующего control v24-next, ожидается результат на момент записи.