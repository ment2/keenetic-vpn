# Keenetic Xray v27 — результат третьей read-only диагностики
Дата: 2026-10-30

## Исходное задание
- ID: `9e44b556-59ac-4ae3-b2f0-c76a534e0ec2`
- Операция: `exec`, только чтение.
- Статус: `done`.
- Exit code: `124`.
- Вывод: `output_limit_reached`.
- Задание повторно не отправлялось. Новых задач на роутер не создавалось.

## Интерпретация
Вывод диагностической команды превысил установленный лимит; данных IPv4/IPv6 `ip rule`, таблиц маршрутизации, nftables, iptables и SOCKS listener не получено. Код 124 относится к диагностическому заданию и сам по себе не доказывает неисправность Xray. Не следует объявлять PASS/FAIL для TPROXY kernel routing и fail-closed.

## Сопоставление с ранее подтверждённой структурой конфигурации
- SOCKS inbound: `local-socks`, `socks`, `127.0.0.1:10808`.
- TPROXY inbound: `tproxy-in`, `dokodemo-door`, `0.0.0.0:12345`, `sockopt.tproxy=tproxy`.
- VLESS outbounds: `vpn01`, `vpn02`, `vpn04`, `vpn05`, `vpn06`, `vpn07`, `vpn09`.
- Outbound `blocked`: `blackhole`.
- Routing for SOCKS/TPROXY: balancer `auto`.
- Balancer selector: `['vpn']`; fallbackTag: `vpn01`.
- Нет подтверждения фактической OpenAI-квалификации каждого outbound, реального SOCKS5 Telegram через VPN, kernel policy routing, отсутствия утечек и fail-closed.

## Предложение следующего этапа (не запускалось)
После отдельного согласования — небольшие, ограниченные по объёму read-only команды: отдельно `ip -4 rule show`, `ip -6 rule show`, выборочные маршруты таблиц TPROXY; краткие агрегированные счётчики/названия цепочек nftables и iptables без полного ruleset; `netstat -lnt` с фильтром по SOCKS/TPROXY. Не выводить секреты, адреса VPN-серверов или полные дампы правил. Любое отсутствие сведений трактовать как UNKNOWN, не как PASS.

## Инварианты
Не менялись Xray, cron, маршруты, kill-switch, файлы роутера; перезапусков не выполнялось. Миграция watchdog не активирована.