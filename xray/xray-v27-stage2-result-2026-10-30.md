# Keenetic Xray v27 — этап 2, подтверждённые результаты

Дата: 2026-10-30

## Источник
Задание `01a0ba28-cacf-47ac-8bf5-87faeab32621`: `done`, `exit_code=0`. Вторая согласованная команда читала структуру `/opt/etc/xray/config.json`, не изменяя её.

## Конфигурация
- SOCKS inbound: `local-socks`, `socks`, `127.0.0.1:10808`.
- TPROXY inbound: `tproxy-in`, `dokodemo-door`, `0.0.0.0:12345`, `sockopt.tproxy=tproxy`.
- VLESS outbounds: `vpn01`, `vpn02`, `vpn04`, `vpn05`, `vpn06`, `vpn07`, `vpn09`.
- `blocked`: `blackhole`.
- Routing rule: `inboundTag=['local-socks','tproxy-in']` -> `balancerTag=auto`.
- Routing rule: `outboundTag=blocked` (условия правила не были выведены, поэтому нельзя установить, какие потоки блокируются).
- Balancer `auto`: `selector=['vpn']`, `fallbackTag=vpn01`.
- В выведенном списке outbound отсутствуют `freedom` и `direct`.

## Выводы и ограничения
Структура указывает на VPN-направление трафика SOCKS/TPROXY и VPN fallback, но не доказывает актуальную OpenAI-квалификацию всех VPN, фактическую доступность Telegram через SOCKS, применённые kernel rules или fail-closed при сбое. `selector=['vpn']` не является отдельным списком проверенных OpenAI-серверов. Требуется сверка источника квалификации и дополнительных проверок без вмешательства в работающий Xray.

## Следующее задание
`9e44b556-59ac-4ae3-b2f0-c76a534e0ec2`: третья ранее согласованная read-only команда для `ip rule`, IPv4/IPv6 route, nftables/iptables и SOCKS listener. На момент составления отчёта статус `queued`; не отправлять повторно.

## Безопасность
Не выполнялись перезапуск Xray, изменения cron, маршрутов, kill-switch или файлов на роутере. Новые изменения не санкционированы.