# Keenetic Xray v27: подтверждённые результаты маршрутизации

Дата: 2026-10-30. Только read-only диагностика.

## Задание № 2
Job ID: `f67e9049-fb6f-4276-90e5-cb43387c4056`.
Status: `done`; exit_code: `0`.

### IPv4
- Table 100: `local default dev lo table 100 scope host`. Соответствует маршруту локальной доставки для маркированного TPROXY трафика.
- Table 16391: `default via 192.168.0.1 dev apclii0 table 16391 src 192.168.0.135 metric 1000`.
- Main: `default via 192.168.0.1 dev apclii0 metric 1000`.
- Из предыдущей проверки policy rules: priority 20000 `fwmark 0x40000000/0x40000000 lookup 100`; priority 10 `fwmark 0xffffa00 lookup main`; priority 1164 `from 192.168.0.135 lookup 16391`.

### IPv6
- В выборочном выводе присутствуют `unreachable default` и локальные маршруты; IPv6 policy rules ранее содержали только `local` и `main`.
- Динамическая защита от IPv6-утечек не подтверждена.

### Интерпретация и ограничения
- Table 100 и fwmark совместимы с TPROXY, но необходима проверка назначения маркировки в firewall.
- Наличие прямых IPv4 default routes не доказывает утечку, но требует проверки kill-switch и исключений.
- Вывод ограничен grep/head; это не исчерпывающий аудит маршрутов.
- Fail-closed: UNKNOWN; VPN egress Telegram: UNKNOWN; OpenAI-qualified pool: UNKNOWN.

## Задание № 3
Job ID: `1a28086b-200c-4013-9d93-d0ebdd9c9336`.
Последняя проверка: `queued`. Не повторять постановку. Команда из согласованного плана: iptables mangle/filter и nft tables summary, только чтение.

## Ограничения
Команда № 4 ещё не отправлена. Xray, cron, маршруты, firewall и kill-switch не изменялись.