# Xray v27: реестр комплектности архива (2026-10-30)

## Завершено
Пять существующих read_file заданий завершились `done`, `exit_code=0`:
- `ad3d2dce-b87a-4ab6-80df-2923a1e43754`: `/opt/bin/xray_server_check.py`
- `f84fa056-6bdb-4c4b-aa43-c8614398480c`: `/opt/bin/test-vpn-servers.py`
- `d33ad5a6-9654-4785-b098-82decbbcd35b`: `/opt/bin/xray-watchdog.sh`
- `7f8719cc-5ed8-4807-88a0-dfbc5c6a729f`: `/opt/etc/init.d/S97xray`
- `db5cd2e3-2087-46ed-a840-99a821d23c33`: `/opt/etc/init.d/S99xray-watchdog`

В `sources/` добавлены четыре файла с суффиксом `.readback-2026-10-30`: `S97xray`, `S99xray-watchdog`, `xray-watchdog.sh`, `test-vpn-servers.py`. Это текстовые реконструкции из ответа read_file, **не побайтовые выгрузки**, не подтверждены SHA256 с роутера.

## Недостающие снимки
`xray_server_check.py` успешно прочитан, но отдельная копия исходника в `sources/` пока не сохранена. Также отсутствуют архивные копии актуальных `xray-update-v23.py`, `xray_openai_probe.py`, `xray-safe-hourly.sh`, `setup_xray.py`, `update_xray_subscription.py`. Ранее существовавшие файлы с суффиксом `LEGACY-library` являются историческими версиями, не доказанными текущими.

## Важные факты
- `xray_server_check.py` запускает временный Xray для каждого outbound и проверяет `https://ipwho.is/` через выделенный SOCKS. Результат включает IP и country_code. `main` может выполнять активные проверки, поэтому только читать.
- Старый watchdog вызывает `S97xray restart`; тот использует `killall xray`. Риск для blue-green.
- `test-vpn-servers.py` при запуске записывает `config-server-test.json`.
- Все файлы роутера, cron, firewall, маршруты и службы оставлены без изменений.
- Доступный MCP `read_file` маскирует секреты и запрещает чтение отдельных credential/private key файлов; даже с разрешением пользователя этот механизм не предоставляет необработанный экспорт.

## Статус
Архив **частично пополнен**, полная комплектность не подтверждена. Не выдавать копии readback за идентичные оригиналам без сверки хешей.