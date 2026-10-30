# Keenetic Xray v27: API capability review
Дата: 2026-10-30

## Достоверная диагностика
Задание `8265a0dd-c314-40dc-b440-53a5c5eac256`: `done`, exit code 0.
Бинарник Xray 26.2.6 (go1.26.1, linux/mipsle). `xray help api` показывает:
- `ado`, `rmo`, `lso` — add/remove/list outbound
- `adi`, `rmi`, `lsi` — add/remove/list inbound
- `adrules`, `rmrules`, `lsrules` — add/remove/list routing rules
- `bo`, `bi` — balancer override/info
- `stats`, `statsquery`, `statssys` — статистика

Текущий рабочий `config.json`:
- `api_configured=False`
- `api_services=[]`
- `api_inbounds=[]`
- `api_routing_rules=0`

Python `grpc` отсутствует, но CLI `xray api` доступен.

## Следствие
CLI-команды сами по себе не создают API endpoint в уже запущенном процессе. Нужна одноразовая подготовка конфигурации с API, а её активация через обычный restart сейчас недопустима: init-скрипт использует `killall xray`. Нулевой разрыв текущих TCP/UDP сессий при таком переходе не гарантируется.

## Предлагаемая безопасная архитектура
1. **Фаза 0 (read-only):** проверить конкретные аргументы `xray help api ado/rmo/bo/bi/adrules`, а также возможности `run -test` для будущего API config. Проверить, что API bind ограничен loopback и доступен только локальному контроллеру.
2. **Фаза 1 (offline):** построить отдельный тестовый config с локальным API inbound, `HandlerService` и `RoutingService` при поддержке сборкой; не использовать живые SOCKS/TProxy порты. Тестировать в изолированной среде/на отдельном порту. Не вводить `freedom` fallback.
3. **Фаза 2 (одноразовая миграция):** отдельный план перехода на API-enabled процесс с управляемым drain, rollback и измерением реальных разрывов. Это не zero-downtime по умолчанию. Требует отдельного согласования, так как затрагивает живой Xray.
4. **Фаза 3 (обычные обновления):** добавить проверенные новые outbounds; переключить выбор новых потоков (через balancer override/правила); держать старые outbounds до подтверждённого drain; удалять после завершения существующих сессий. Проверить, сохраняет ли Xray активные потоки при `rmo` и изменении routing.
5. **Fail-closed:** независимый сетевой запрет прямого выхода, тесты TCP и UDP/TProxy, контроль DNS и kill-switch. Не считать доступность OpenAI по одному HTTP 401 вечной гарантией.

## Риски
- `bo` может быть недостаточно для атомарной смены множества outbounds; нужны проверки.
- Неизвестна точная семантика удаления outbound для существующих потоков.
- Текущие `vpnNN` теги зависят от порядка подписки; нужен стабильный ID.
- Старый watchdog способен вызвать restart и killall, его нельзя оставлять неучтённым при миграции.
- На данный момент изменения рабочего роутера не проводились.

## Архив
Снимки `readback` в `/Keenetic/Xray/sources/` — восстановленный текст, не побайтовые копии с SHA256. Текущий `xray-update-v23.py` успешно прочитан и сохранён как readback. Снимки `xray_server_check.py`, `setup_xray.py`, `update_xray_subscription.py` были прочитаны, но отдельные актуальные readback-копии ещё не подтверждены в библиотеке.