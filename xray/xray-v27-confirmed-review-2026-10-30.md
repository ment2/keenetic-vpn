# Keenetic Xray v27: подтверждённый аудит watchdog
Дата: 2026-10-30

## Источники
Три существующие read_file задачи завершены done, exit_code=0, truncated=false:
- 5c44bf40-0740-40c2-b8ae-3250efb5aa6e: /opt/bin/xray-watchdog-v25.sh
- e5b46637-f36b-4ed9-a181-b435007ba863: /opt/etc/init.d/S99xray-watchdog
- bf9dc139-d991-439a-b649-9a785ca04725: /opt/bin/xray-watchdog.sh

## Подтверждённые факты
- v25 каждые 30 секунд вызывает `python3 /opt/bin/xray-control-v24.py status`, проверяет наличие TCP LISTEN `127.0.0.1:10808`, логирует изменения состояния OK/FAILED. Не отправляет сигналов и не рестартует Xray.
- startup S99xray-watchdog указывает на старый /opt/bin/xray-watchdog.sh и PIDFILE /opt/var/run/xray-watchdog.pid. start проверяет `kill -0`, stop вызывает `kill` по PID из файла без проверки идентичности процесса.
- Старый watchdog каждые 30 секунд проверяет TCP LISTEN 127.0.0.1:10808, а при отсутствии запускает `/opt/etc/init.d/S97xray restart`.
- Наличие LISTEN порта не доказывает SOCKS5 handshake, Telegram через VPN, OpenAI-qualified pool, TPROXY или fail-closed.
- Текущее runtime-состояние и правила маршрутизации этими тремя чтениями не подтверждены.

## Безопасный проект v27 (не активирован)
1. Read-only аудит /opt/bin/xray-control-v24.py, текущего config.json с исключением секретов, активных процессов, PID/start ticks, startup, cron, TPROXY ip rule/ip route/iptables и kill-switch. Не читать приватные ключи или токены.
2. Предварительные условия: Xray identity VERIFIED, проверка socks5 handshake и целевого маршрута без обхода провайдера; OpenAI-qualified теги и fallbackTag сверены с конфигом; TPROXY и fail-closed проверены без изменения правил.
3. Разделить наблюдение и управление: v27 по умолчанию status/plan; никаких сигналов, рестартов или изменений до отдельного утверждения точных операций.
4. План активации: сохранить версии, права и хэши startup/скриптов, защитить PID через cmdline и /proc start ticks, обеспечить единственного владельца watchdog, предусмотреть независимый ограниченный по времени rollback, проверять инварианты до/после.
5. Rollback должен восстанавливать только управление watchdog, не ослаблять kill-switch, не переключать на direct, не перезапускать Xray автоматически.
6. Остановка при любой непроверенной предпосылке; fail-closed важнее доступности.

## Не выполнено
Ни один сервис, cron, маршрут, kill-switch или файл роутера не изменялся. Переключение не производилось. В этом отчёте нет подтверждения runtime OpenAI/SOCKS5/TPROXY/fail-closed.