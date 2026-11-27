"""Pure HA card/config plans. Never calls HA or saves a dashboard."""
import copy
from mixed_rc2_integration import METRICS, SHADOW_EID, PROD_EID, encoded, sha

TEMPLATE = '''{% set eid = '__ENTITY__' %}
{% set ts = as_timestamp(now()) %}
{% set age = ts - (state_attr(eid,'checked_at') | int(0)) %}
{% set sub = state_attr(eid,'subscription_at') %}
{% set rows = state_attr(eid,'rows') or [] %}
{% macro status(o) -%}
{{ o.status if o.status == 'unsupported' or (o.at is not none and 0 <= ts-o.at <= 1800) else ('missing' if o.at is none else 'stale') }}
{%- endmacro %}
{% macro ms(o) -%}{{ o.ms ~ ' мс' if o.ms is not none and o.at is not none and 0 <= ts-o.at <= 1800 else '—' }}{%- endmacro %}
{% macro label(s) -%}{{ {'ok':'🟢 OK','unsupported':'⚪ не поддержан','not_confirmed':'⚪ не подтверждён','missing':'⚪ нет данных','unknown':'⚪ неизвестно','stale':'⚪ устарело','timeout':'🔴 тайм-аут','network_error':'🔴 сбой сети','http_error':'🔴 HTTP','ip_mismatch':'🔴 IP не совпали','unverified_time':'⚪ разные моменты','geo_unavailable':'⚪ нет геоданных','invalid_response':'🔴 ошибка ответа'}.get(s,'⚪ неизвестно') }}{%- endmacro %}
{% if states(eid) != 'ok' or not 0 <= age <= 150 or sub is none or not 0 <= ts-sub <= 1800 %}
⚪ **Нет актуальной подписки / сводки**
{% else %}
{% set n = namespace(active=0,vpn=0,net=0,ai=0,geo=0,vless=0,hy=0) %}
{% for r in rows %}
{% if r.active == true %}{% set n.active = n.active+1 %}{% endif %}
{% if status(r.vpn) == 'ok' %}{% set n.vpn = n.vpn+1 %}{% endif %}
{% if status(r.internet) == 'ok' %}{% set n.net = n.net+1 %}{% endif %}
{% if status(r.openai) == 'ok' %}{% set n.ai = n.ai+1 %}{% endif %}
{% if status(r.geo) == 'ok' %}{% set n.geo = n.geo+1 %}{% endif %}
{% if r.protocol == 'vless' %}{% set n.vless = n.vless+1 %}{% elif r.protocol == 'hysteria2' %}{% set n.hy = n.hy+1 %}{% endif %}
{% endfor %}
**Подключений: {{ rows|count }} · VLESS {{ n.vless }} · Hysteria2 {{ n.hy }} · в пуле {{ n.active if state_attr(eid,'active_unmatched') is not none else '?' }}**

Проверено: {{ state_attr(eid,'probe_complete') }}/{{ rows|count }} · VPN {{ n.vpn }} · Интернет {{ n.net }} · OpenAI {{ n.ai }} · Гео {{ n.geo }}.

Подписка: {{ as_local(as_datetime(sub)).strftime('%d.%m %H:%M:%S') }} · Сводка: {{ as_local(as_datetime(state_attr(eid,'checked_at'))).strftime('%H:%M:%S') }}.
{% if ts-sub > 1000 %}⚠️ Подписка не обновилась в ожидаемый срок.{% endif %}
{% if state_attr(eid,'active_unmatched') is none or state_attr(eid,'pending_unmatched') is none or state_attr(eid,'active_unmatched') or state_attr(eid,'pending_unmatched') %}⚠️ Состав пула неизвестен или не совпадает с подпиской.{% endif %}

| Сервер | VPN | Интернет | AI | GEO / допуск |
| :--- | :--- | :--- | :--- | :--- |
{% for r in rows -%}
| {{ '◆' if r.active == true else '◇' if r.active == false else '?' }} {{ r.tag }} | {{ label(status(r.vpn)) }} | {{ label(status(r.internet)) }} | {{ label(status(r.openai)) }} | {{ (r.geo.country or '—') if status(r.geo) == 'ok' else '—' }} / {{ r.geo_policy if status(r.geo) == 'ok' and status(r.exit_ip_probe) == 'ok' else 'UNVERIFIED' }} |
{% endfor %}
◆ в пуле · ◇ вне пула · ? неизвестно. Допуск информационный, не переключает VPN.

{% for r in rows %}
**{{ r.tag }} · {{ 'Hysteria2' if r.protocol == 'hysteria2' else 'VLESS' }}** · {{ r.support }}  
{% if r.support == 'unsupported' %}Причина: {{ {'unsupported_option':'неизвестный параметр','ech_unverified':'ECH не проверен','duplicate_option':'дубли параметров','tls_policy':'нарушение TLS-политики','invalid_uri':'неподдерживаемая URI'}.get(r.get('support_reason'),'не уточнена') }}.  {% endif %}
Вход: `{{ '[' ~ r.host ~ ']' if ':' in r.host else r.host }}:{{ r.port if r.port is not none else '—' }}`  
Выход: {{ r.exit_ip if r.exit_ip and status(r.exit_ip_probe) == 'ok' else '—' }} · {{ r.geo.city or '—' if status(r.geo) == 'ok' else '—' }}  
VPN: {{ label(status(r.vpn)) }} · Сеть: {{ label(status(r.internet)) }} / {{ ms(r.internet) }} · AI: {{ label(status(r.openai)) }} / {{ ms(r.openai) }}  
IP: {{ label(status(r.exit_ip_probe)) }} / {{ ms(r.exit_ip_probe) }} · GEO: {{ label(status(r.geo)) }} / {{ ms(r.geo) }}  
Допуск: {{ r.geo_policy if status(r.geo) == 'ok' and status(r.exit_ip_probe) == 'ok' else 'UNVERIFIED' }} · {{ 'кандидат по проверкам' if r.eligible and status(r.internet) == 'ok' and status(r.openai) == 'ok' and status(r.geo) == 'ok' and status(r.exit_ip_probe) == 'ok' else 'не допущен по проверкам' }}
{% if r.active_config_matches == false or r.pending_config_matches == false %}⚠️ Настройки пула отличаются.{% endif %}
{% if r.last_geo and r.last_geo.at is not none and 0 <= ts-r.last_geo.at <= 86400 %}Последняя известная (не текущая): {{ r.last_geo.country or '—' }} {{ r.last_geo.city or '—' }} · {{ r.last_geo.ip }}.{% endif %}

---
{% endfor %}
*Время HTTP-пробы, не ICMP ping. OpenAI — ожидаемый HTTP 401 без авторизации, Интернет — HTTP 204. Геофильтр использует выходной, не входной IP.*
{% endif %}'''


def overview(shadow=True):
    eid='sensor.keenetic_dynamic_vpn_rc2_mixed_shadow' if shadow else 'sensor.keenetic_dynamic_vpn_rc2'
    return {'type':'markdown','title':'VPN · смешанный RC2'+(' · тест' if shadow else ''),'content':TEMPLATE.replace('__ENTITY__',eid)}


def graphs(rows, states, shadow=True, legend=True):
    prefix=SHADOW_EID if shadow else PROD_EID
    by={}
    for s in states:
        eid=s.get('entity_id','');a=s.get('attributes',{})
        if not eid.startswith(prefix):continue
        key=(a.get('node_id'),a.get('metric'))
        if key[0] and key[1]:
            if key in by:raise ValueError('duplicate metric identity')
            by[key]=eid
    if not rows or len({r['id'] for r in rows})!=len(rows):raise ValueError('invalid rows')
    if not all((r['id'],m) in by for r in rows for m in METRICS):raise ValueError('history registration incomplete')
    order=sorted(rows,key=lambda r:(0 if r['tag'].startswith('vpn') else 1,int(r['tag'][3:] if r['tag'].startswith('vpn') else r['tag'][2:])))
    def ent(r,m,name=None):return {'entity':by[(r['id'],m)],'name':name or r['tag']}
    def graph(title,hours,entities):return {'type':'history-graph','title':title,'hours_to_show':hours,'entities':entities}
    individual=[graph(r['tag']+' · время HTTP-пробы, мс · 6 ч',6,[ent(r,'internet_ms','Интернет'),ent(r,'openai_ms','OpenAI')]) for r in order]
    labels={'vpn':'VPN','internet':'Интернет','openai':'OpenAI','geo':'Геолокация','internet_ms':'Интернет, время пробы','openai_ms':'OpenAI, время пробы'}
    history=[]
    for m in METRICS:
        g=graph(labels[m]+' · 24 ч',24,[ent(r,m) for r in order])
        history.append({'type':'custom:rc2-history-legend','metric':m,'graph':g} if legend and m in ('vpn','internet','openai','geo') else g)
    return individual,history


def view(rows, states, shadow=True, legend=True):
    individual,historical=graphs(rows,states,shadow,legend)
    return {'title':'VPN RC2 mixed'+(' shadow' if shadow else ''),'path':'rc2-mixed-shadow' if shadow else 'vpn-openai','cards':[overview(shadow),*individual,*historical]}


def plan_dashboard(old, target_path, desired_view, expected):
    """Pure CAS change plan. No HA requests; keep all other views/resources."""
    if sha(encoded(old))!=expected:raise ValueError('dashboard changed')
    result=copy.deepcopy(old);matches=[i for i,v in enumerate(result['views']) if v.get('path')==target_path]
    if len(matches)!=1:raise ValueError('target view ambiguous or absent')
    if desired_view.get('path')!=target_path:raise ValueError('target path mismatch')
    # Keep view-level settings and title; replace only cards in the accepted view.
    result['views'][matches[0]]['cards']=copy.deepcopy(desired_view['cards'])
    return {'before':old,'after':result,'before_sha':expected,'after_sha':sha(encoded(result))}


def rollback_dashboard(actual,plan):
    if sha(encoded(actual))!=plan['after_sha'] or sha(encoded(plan['before']))!=plan['before_sha']:raise ValueError('dashboard rollback CAS failed')
    return copy.deepcopy(plan['before'])
