# Keenetic Xray v27: ограниченная read-only диагностика

Дата: 2026-10-30. Статус: DRAFT, ожидает отдельного согласования. Ни одна команда из этого документа не выполнялась.

## Основание
Задание 9e44b556-59ac-4ae3-b2f0-c76a534e0ec2: done, exit_code=124, output=output_limit_reached. Нет пригодного вывода сетевых правил. Ранее подтверждены настройки Xray: SOCKS5 127.0.0.1:10808, TPROXY 0.0.0.0:12345, семь VLESS VPN, balancer auto selector ['vpn'], fallbackTag vpn01, blackhole blocked. Не подтверждены runtime fail-closed и Telegram VPN egress.

## Команда 1: IPv4/IPv6 policy rules
```sh
printf '%s\n' '=== IPv4 RULES ==='
ip -4 rule show 2>&1 | head -n 35
printf '%s\n' '=== IPv6 RULES ==='
ip -6 rule show 2>&1 | head -n 35
```

## Команда 2: TPROXY routes
```sh
printf '%s\n' '=== IPv4 TABLES ==='
ip -4 route show table all 2>&1 |
  grep -E '(^| )local |default|dev lo|table ' |
  head -n 45

printf '%s\n' '=== IPv6 TABLES ==='
ip -6 route show table all 2>&1 |
  grep -E '(^| )local |default|dev lo|table ' |
  head -n 35
```

## Команда 3: firewall and kill-switch indicators
```sh
printf '%s\n' '=== IPTABLES MANGLE ==='
iptables -t mangle -S 2>&1 |
  grep -Ei 'TPROXY|MARK|PREROUTING|XRAY|12345|10808|RETURN|ACCEPT|DROP|REJECT' |
  head -n 55

printf '%s\n' '=== IPTABLES FILTER ==='
iptables -t filter -S 2>&1 |
  grep -Ei 'FORWARD|OUTPUT|DROP|REJECT|XRAY|VPN' |
  head -n 45

printf '%s\n' '=== NFT SUMMARY ==='
if command -v nft >/dev/null 2>&1; then
  nft list tables 2>&1 | head -n 25
else
  echo 'nft unavailable'
fi
```

## Команда 4: local listeners
```sh
printf '%s\n' '=== TCP LISTENERS ==='
netstat -lnt 2>&1 |
  grep -E '127\.0\.0\.1:10808|:12345' |
  head -n 15

printf '%s\n' '=== UDP LISTENERS ==='
netstat -lnu 2>&1 |
  grep -E ':12345|:10808' |
  head -n 15
```

## Ограничения и правила выполнения
- Нужна отдельная явная санкция на эти точные четыре команды перед exec. Выполнять строго последовательно, с проверкой результата каждой асинхронной задачи, без повторного enqueue.
- `head` ограничивает количество строк, а не длину каждой строки; максимальный размер вывода не гарантирован. Pipe exit status может скрыть ошибку `ip`, `iptables`, `grep` или `nft`; читать текст ошибок и отсутствие совпадений не считать PASS.
- Фильтры могут скрыть значимые правила; вывод iptables не включает nft chains. `nft list tables` не доказывает содержимое nft chains.
- Просмотр правил не доказывает fail-closed при отказе VPN, фактический SOCKS5 handshake, Telegram VPN egress или принадлежность VPN к OpenAI-qualified pool.
- Никаких изменений Xray, cron, firewall, маршрутов, kill-switch, файлов или watchdog. Любое UNKNOWN блокирует активацию v27.