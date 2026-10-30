# Keenetic Xray v27: offline API test plan

Дата: 2026-10-30. Источник: результат существующего задания `0b3b65d2-03a5-4eec-a2e2-f7218f4d182d` (`done`, exit_code 0), справка установленного Xray 26.2.6 и документация Project X.

## Проверенные команды

| CLI | Синтаксис | Замечания |
|---|---|---|
| ado | `xray api ado -s 127.0.0.1:PORT c1.json` | Добавляет outbound, требует HandlerService |
| rmo | `xray api rmo -s 127.0.0.1:PORT tag` | Удаляет outbound; поведение текущих соединений НЕ подтверждено |
| bo | `xray api bo -s 127.0.0.1:PORT -b auto tag` | Override выбора балансировщика; RoutingService |
| bi | `xray api bi -s 127.0.0.1:PORT auto` | Чтение состояния балансировщика |
| adrules | `xray api adrules -s 127.0.0.1:PORT file.json` | По умолчанию ЗАМЕНЯЕТ routing rules; `-append` добавляет |
| rmrules | `xray api rmrules -s 127.0.0.1:PORT ruleTag` | Удаление по тегу; необходим контроль соответствия |
| run -test | `xray run -test -config file.json` | Проверка конфигурации без запуска сервиса |

По умолчанию API CLI использует `127.0.0.1:8080`, timeout 3 секунды. У действующего Xray API не настроен: `api_configured=False`, `api_services=[]`, `api_inbounds=[]`, `api_routing_rules=0`.

## Проект теста, НЕ выполнять на рабочем экземпляре

1. Создать локально вне роутера минимальную тестовую конфигурацию без реальных ключей и серверов, с `api: {tag:"api",listen:"127.0.0.1:PORT",services:["HandlerService","RoutingService"]}`; `PORT` выделять из свободного локального диапазона. Ни один тестовый inbound не должен использовать рабочие 10808 и 12345.
2. Проверить `xray run -test -config ...` на той же версии бинарника в отдельной среде. Проверить отсутствие `freedom` fallback, явный `blackhole` и отсутствие публичного API listener.
3. Запустить изолированный экземпляр только в тестовой среде. Проверить `lso`, `bi`, `ado` с фиктивным outbound, затем `bo`; убедиться, что `bi` отражает override. `adrules` не вызывать на живой конфигурации.
4. Снять измерения: старый TCP-поток, новые TCP-потоки, UDP-потоки и TPROXY; до и после override, затем при удалении только уже осушенного outbound. Не считать отсутствие разрыва доказанным до тестов.
5. Для миграции продакшена разработать отдельный план первого включения API: текущий процесс без API не умеет принимать hot-update. Требуется согласованное окно либо независимый постоянный ingress/conntrack-aware blue-green с проверенным drain. Никаких автоматических рестартов.
6. Сформировать план отката, проверки DNS/IPv6 и fail-closed на уровне firewall, контроль legacy watchdog, и журналирование без секретов.

## Выявленные риски

- `bo` закрепляет один конкретный outbound, а не произвольный набор пулов. Для pool-to-pool нужны безопасная смена balancer rules или слой управления выбором, что пока не подтверждено.
- При отсутствии подходящего routing match Xray может использовать первый outbound, поэтому порядок outbounds и catch-all blackhole критичны.
- Динамический `rmo` может повлиять на существующие TCP/UDP-сессии; сначала drain.
- Удаление override после restart и семантика сохранения API-изменений в config.json требуют проверки.
- Старый `S97xray` использует `killall xray`; watchdog способен его вызвать.

## Задача №1: архив

Проверено ранее: в `/Keenetic/Xray/sources/` есть `xray-update-v23.py.readback-2026-10-30`, `xray_openai_probe.py.readback-2026-10-30`, `xray-safe-hourly.sh.readback-2026-10-30`, `test-vpn-servers.py.readback-2026-10-30`, `S97xray.readback-2026-10-30`, `S99xray-watchdog.readback-2026-10-30`, `xray-watchdog.sh.readback-2026-10-30`. Не подтверждены актуальные сохранённые readback для `xray_server_check.py`, `setup_xray.py`, `update_xray_subscription.py`; все три уже были прочитаны существующими заданиями, новые чтения не требуются. Исторические library-версии нельзя выдавать за актуальные. Суффикс readback не означает побайтовую идентичность и не подтверждает SHA256.

## Границы

Только документация и read-only проверки. Рабочие процессы, конфигурации, cron, firewall, маршруты и kill-switch не менялись.

Справка: https://xtls.github.io/ru/config/api.html ; https://xtls.github.io/en/config/routing.html