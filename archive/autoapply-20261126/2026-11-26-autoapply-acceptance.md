# Keenetic Xray — восстановление autoapply, 26.11.2026

Статус: первый штатный цикл SUCCESS. Это восстановление autoapply с перерывом соединений, не v30.

## Production
- Скрипт `/opt/bin/xray-safe-hourly.sh`, root:root, 0700, 3150 байт.
- SHA256: `c63c0f171cda5b5f3150731e0706784b66977b256d737856edfcce15fba223c8`.
- Архивная копия `xray-safe-hourly-20261126.sh`: SHA256 совпадает, sh -n успешен.
- Cron (без изменений): `*/15 * * * * /opt/bin/flock -n /opt/tmp/xray-update.lock /opt/bin/xray-safe-hourly.sh >> /opt/var/log/xray-update.log 2>&1`
- Updater `/opt/bin/xray-update-v23.py`; service `/opt/etc/init.d/S97xray`.
- Резерв исходного скрипта `/opt/bin/xray-safe-hourly.sh.before-autoapply-20261126`, SHA256 `890c242609c1146f5ba6087a1f973fc4a707c82491c0892b96bd60aac261deb5`.
- Резерв конфигурации `/opt/etc/xray/config.lastgood.autoapply.json`, 7067 байт, mtime 10.11 20:32, 0600.

## Приёмка (МСК)
- 17:16:09 STAGED_ONLY; 17:31:11 PENDING_UNCHANGED.
- 17:36 установка, job dfa6a2f3-0014-4a88-8861-7a96d422bff7, exit 0.
- Проверка после установки db49fb02-1daf-4dd2-ae94-3869c2708ded: SHA совпал, PID 760, активный config 7067 байт, pending 5104 байт.
- 17:45 штатный cron; 17:46:15 APPLY: restarting Xray with new pool.
- 17:46:24 SUCCESS: new pool active; internet and OpenAI verified.
- 17:47:08 независимая проверка a8e89f88-937a-45e5-9398-94ee64e75d05, exit 0: PID 5793, config.json 5104 байт, mtime 26.11 17:46, pending отсутствует, резерв присутствует. Отката в этом цикле не было.
- Предыдущая диагностика: 7 активных, 5 подготовленных VLESS; число после применения отдельно не пересчитано.
- Журнал содержит бинарные данные: для чтения маркеров использован grep -a.

## Ограничения
Проверки через SOCKS5 127.0.0.1:10808: Google HTTP204 и OpenAI HTTP401 без ключа. Это проверка достижимости, не авторизованного API. TPROXY/UDP отдельно не проверены. Перерыв TCP/UDP и возможный прямой WAN при обновлении разрешены владельцем; no-leak и бесшовность не доказаны. Откат предусмотрен, но не испытан на production. Конкуренция watchdog допустима; побайтовое сравнение может реагировать на порядок JSON. При отключении питания/SIGKILL откат не гарантирован; ошибка записи журнала при set -e может помешать rollback. Один успешный цикл не доказывает долговременную стабильность. Cron, firewall, маршруты, watchdog не изменялись. Принудительный restart при приёмке не выполнялся. GitHub Actions не использовались при восстановлении. Не объединять с v30. Секреты и содержимое VPN-конфигураций не архивируются.
