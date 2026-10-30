# Keenetic Xray v27 — контроль комплектности архива

Дата: 2026-10-30. Библиотека: `/Keenetic/Xray/`.

## Уже находится в библиотеке
- Проектные отчёты v27 (партии 1–3), архитектура, диагностические материалы и исторические исходники v23–v26.
- Исторические копии `setup_xray.library.py`, `xray-safe-hourly.LEGACY-library.sh`, `update_xray_subscription.LEGACY-library.py` (не считать текущими копиями роутера).

## Актуальные исходники, ранее прочитанные через Keenetic Mobile, но пока не перенесённые в отдельные файлы `sources/`
`xray-update-v23.py`, `xray_openai_probe.py`, `xray-safe-hourly.sh`, `setup_xray.py`, `update_xray_subscription.py`, `xray-control-v24.py`, `xray-identity-v24.py`, `xray-watchdog-v25.sh`, `xray-watchdog-switch-v26.py`.

## Новые задания (не повторять)
- `ad3d2dce-b87a-4ab6-80df-2923a1e43754` — `/opt/bin/xray_server_check.py`: queued.
- `f84fa056-6bdb-4c4b-aa43-c8614398480c` — `/opt/bin/test-vpn-servers.py`: queued.
- `d33ad5a6-9654-4785-b098-82decbbcd35b` — `/opt/bin/xray-watchdog.sh`: queued.
- `7f8719cc-5ed8-4807-88a0-dfbc5c6a729f` — `/opt/etc/init.d/S97xray`: queued.
- `db5cd2e3-2087-46ed-a840-99a821d23c33` — `/opt/etc/init.d/S99xray-watchdog`: running.

## Ограничение доступа
Keenetic Mobile `read_file` выполняет серверное редактирование чувствительных значений и запрещает файлы учётных данных, сессий и приватных ключей. Поэтому точные необработанные байты конфигураций с секретами недоступны через текущий инструмент. Не выдавать redacted за полный оригинал. Пользователь разрешил полный архив, но инструмент технически не обеспечивает его получение.

## Безопасность
Только read_file. Никаких изменений сервисов, маршрутов, cron, kill-switch, Xray.