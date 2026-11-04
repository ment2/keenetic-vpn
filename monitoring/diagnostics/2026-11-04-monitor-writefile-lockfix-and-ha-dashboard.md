# VPN Monitoring: восстановление записи и панель Home Assistant
Дата: 2026-11-04
Репозиторий: ment2/keenetic-vpn
Ветка: feature/vpn-monitoring-home-assistant-20261104

## Подтверждённый инцидент установки
- Источник обновления: monitoring/openai_health_collector_loop.py, Git blob SHA 326ecbfb905377cbef740c72829d53a163bc2704.
- Первая попытка прямого скачивания из raw.githubusercontent.com: HTTP 404 (приватный репозиторий); целевой файл не заменён.
- Предварительная резервная копия через os.link() создала жёсткую ссылку. Оба пути имели inode 4237 и два имени; SHA256 695978d642a360248fc0ab3706cc389830448acdaef9ded0c4f0f0a556aa3718.
- Agent agent_safety.py защищает read_file/write_file: для существующего целевого файла требует st_nlink == 1; исключения намеренно редактируются до operation_failed. Именно этим объяснились оба отказа read_file и один отказ write_file.
- Исправление: независимая копия вместо hardlink. Job 6c3a4628-ae08-4003-a838-4a21bf977ade: BACKUP_SPLIT_OK, оба SHA256 прежние, nlink=1.
- После исправления read_file: job 10ab6ff0-e216-4822-8ac9-11a7f291b37e, done exit 0.
- Единственная повторная запись через Keenetic Mobile: job 8ba8067b-f4dd-4c8a-825c-11e6d29e4a31, done exit 0, written=true, backup_created=true, SHA256 a5e4d80dbc9709ad2cece194f2a4b07891022fa2489ec9ab56d81d3617b27236.
- Полный read-only контроль: job 2fff4aff-d534-4398-bb9a-6f3459475698, VERIFICATION_OK: оригинал 5565 байт inode 4257, Git blob совпадает; отдельная предварительная копия 5288 байт inode 4254; оба nlink=1, AST_OK.
- Тест блокировки в отдельном временном каталоге: job d01a1f17-0421-429d-aaa6-45859bf09ba0, exit 0: LOCK_CONTENTION_TEST_OK OPENAI_CYCLE_SKIPPED lock_busy; NO_XRAY_NO_MQTT_TEST_OK.
- Все операции: без изменения production Xray, firewall, маршрутов и cron.

## Данные мониторинга
- Семь текущих тегов: vpn01, vpn02, vpn04, vpn05, vpn06, vpn07, vpn09.
- Последние прочитанные 3 раунда OpenAI: пять reachable; vpn06 и vpn07 network_error. Проверено 2026-11-04, показатели могут измениться.
- Сбор OpenAI каждые 15 минут, MQTT discovery создаёт три поля на узел: status, checked_at, test_duration_ms (21 датчик).
- Ранее установлены 28 датчиков общей VLESS-пробы, 4 на узел, и 12 интерфейсных датчиков. Общая HTTP-проба не заменяет проверку OpenAI.
- Нет доказанного per-outbound учёта трафика; интерфейсные счётчики нельзя выдавать за трафик конкретного VPN.

## Панель Lovelace
- Исходник: monitoring/homeassistant/keenetic_vpn_dashboard.yaml.
- Используются только встроенные карточки Home Assistant (markdown, entities, history-graph).
- Точные ранее подтверждённые VLESS entity_id из keenetic_vpn_dashboard.yaml.
- Для новых OpenAI сенсоров ID ещё не прочитаны из реестра HA; шаблон ищет датчики по именам discovery. Если имя было переименовано, панель покажет «нет датчика», а не выдуманный успешный статус.
- По текущей сессии нет подключённого Home Assistant Control API. Создание YAML в GitHub НЕ означает, что панель уже импортирована в Home Assistant.
- До окончательной приёмки необходимо открыть HA dashboard UI, вставить YAML (полная конфигурация, а не одиночная карточка), сверить реальные entity_id и подтвердить рендер/историю.
- Home Assistant 192.168.0.169:8123 по ранее подтверждённой LAN доступности.

## Безопасность
- Без секретов, ключей, подписок, UUID или паролей в репозитории.
- Никаких попыток VPN cutover, auto-pool apply или изменений S97/S98/S99/watchdog.
