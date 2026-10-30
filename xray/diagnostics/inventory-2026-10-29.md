# Keenetic Xray: реестр исходников и изменений
Дата: 2026-10-29

## Подтверждено
- `/opt/bin/xray-update-v23.py`: условие допуска требует status ok, ip, country; observatory использует Google generate_204.
- `/opt/bin/xray_openai_probe.py`: отдельный временный Xray и SOCKS; HTTP 401 от OpenAI означает доступность.
- `/opt/bin/xray-safe-hourly.sh`: активный wrapper с остановкой/запуском Xray при обновлении и откатом.
- Найдены исходники `xray-control-v24.py`, `xray-control-v24-next.py`, `xray-identity-v24.py`, `xray-watchdog-switch-v26.py`; их чтение ожидается.
- Найдены различные скрипты `xray-watchdog-v25*`, `xray-v25-*`.

## Текущее состояние
- Cron: `*/15 * * * *` с flock и `/opt/bin/xray-safe-hourly.sh`.
- Резервная копия wrapper: `/opt/bin/xray-safe-hourly.sh.before-prod`.
- Резервная копия crontab: `/opt/etc/xray/crontab.before-v23`.
- Резервная копия v23: `/opt/bin/xray-update-v23.py.before-prod`.

## Правила архива
- `sources`: версии исходников, `patches`: согласованные изменения, `diagnostics`: результаты проверок.
- Снимки версионируются, не перезаписываются. SHA-256 указывается только после проверки реальных байтов.
- Не сохранять подписки, токены, пароли, ключи и конфигурации с секретами.
- Архив не синхронизируется с роутером автоматически; перед применением проверять актуальность.