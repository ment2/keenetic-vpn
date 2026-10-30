# Keenetic Xray v27: реестр архивирования и offline API
Дата: 2026-10-30

## Фактический статус
Подтверждено в Library `/Keenetic/Xray/sources/`:
- `xray-update-v23.py.readback-2026-10-30`
- `xray_openai_probe.py.readback-2026-10-30`
- `xray-safe-hourly.sh.readback-2026-10-30`
- `test-vpn-servers.py.readback-2026-10-30`
- `xray-watchdog.sh.readback-2026-10-30`
- `S99xray-watchdog.readback-2026-10-30`
- `S97xray.readback-2026-10-30`

В наличии также исторические файлы `setup_xray.library.py` и `update_xray_subscription.LEGACY-library.py`; они НЕ подтверждены как актуальные копии.

## Три незакрытых пункта
- `/opt/bin/xray_server_check.py`: задание `3939cf50-6de0-42f2-b10c-e42105e98a5a`, done/exit 0, source text прочитан; отдельный readback в Library **ещё не создан**.
- `/opt/bin/setup_xray.py`: задание `ecc2b4da-fbc3-4e46-806d-98f070621d7b`, done/exit 0, source text прочитан; отдельный readback в Library **ещё не создан**.
- `/opt/bin/update_xray_subscription.py`: задание `eeb3b549-8b87-4114-a603-789859eb1658`, done/exit 0, source text прочитан; отдельный readback в Library **ещё не создан**.

Не выдавать старые Library-файлы за новые снимки. Все readback — текстовые реконструкции, не доказанные побайтовые копии; SHA256 исходных файлов не получены.

## Изолированный API fixture
- `/Keenetic/Xray/patches/api-test-config.OFFLINE-2026-10-30.json`
- `/Keenetic/Xray/diagnostics/api-test-README-2026-10-30.md`
- Включает `HandlerService`/`RoutingService`, loopback API `127.0.0.1:18080`, synthetic SOCKS `127.0.0.1:18081`, blackhole outbound.
- Без реальных секретов, без `freedom`, без TPROXY, без рабочего порта.
- Только синтаксическая проверка JSON локально; проверка `xray run -test` не выполнена, так как локально нет подтверждённого совместимого бинарника.
- Ничего на роутере не запускалось и не менялось.

## API вывод
`ado` добавляет outbound из JSON; `rmo` удаляет по tag/JSON. `bo` задаёт фиксированный outboundTag для balancer, `bi` читает состояние. `adrules` без `-append` заменяет правила, `rmrules` удаляет по ruleTag. API в рабочем config отсутствует. Для первой активации требуется отдельно согласованная миграция, нулевые разрывы не гарантированы.