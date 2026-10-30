# Keenetic Xray v27: policy rules, подтверждённый результат

Дата: 2026-10-30. Режим: только чтение.

## Команда 1
Задание `1efb922d-df56-4e32-b183-70c379fe6509`: `done`, `exit_code=0`.

```text
=== IPv4 RULES ===
0: from all lookup local
10: from all fwmark 0xffffa00 lookup main
1164: from 192.168.0.135 lookup 16391
20000: from all fwmark 0x40000000/0x40000000 lookup 100
32766: from all lookup main
32767: from all lookup default
=== IPv6 RULES ===
0: from all lookup local
32766: from all lookup main
```

## Анализ
- Метка `0x40000000/0x40000000` направляет IPv4 в таблицу 100; это совместимо с TPROXY, но таблица 100 и фактическая установка метки ещё не проверены.
- Правило `fwmark 0xffffa00 lookup main` имеет более высокий приоритет; назначение и охват метки не установлены.
- Правило источника `192.168.0.135 lookup 16391` требует анализа таблицы 16391.
- В IPv6 нет отдельного policy rule для TPROXY; отсутствие утечек IPv6 не доказано.
- Данные показывают конфигурацию правил в момент проверки, но не подтверждают fail-closed.

## Команда 2
Полный текст сверён с `/Keenetic/Xray/xray-v27-bounded-readonly-plan-2026-10-30.md`.
Задание `f67e9049-fb6f-4276-90e5-cb43387c4056`: `queued` при первой проверке результата. Не повторять отправку. Команды 3 и 4 ещё не отправлялись.

## Инварианты
Никаких изменений Xray, cron, маршрутов, firewall, kill-switch и файлов роутера не выполнялось.