/* RC2 native history graph wrapper, Home Assistant frontend 20261028.6.
 * The native graph remains responsible for history, tooltips and colors.
 * This legend reads only colors already rendered by the native timeline.
 * No external libraries, requests, services or sensor modifications.
 */
const TITLES = {
  ok: "Успешно", not_confirmed: "VPN не подтверждён",
  network_error: "Ошибка соединения", timeout: "Тайм-аут",
  http_error: "Неожиданный HTTP-ответ", invalid_response: "Некорректный ответ",
  geo_unavailable: "Геолокация недоступна", ip_mismatch: "IP не совпадает",
  stale: "Данные устарели", missing: "Нет измерения",
  unknown: "Неизвестно", unavailable: "Недоступно"
};
const NOTES = {
  vpn: "Успешно — есть подтверждение работы туннеля; это не членство в активном пуле.",
  internet: "Успешно — HTTP 204 от контрольного адреса.",
  openai: "Успешно — ожидаемый HTTP 401 от API OpenAI, не проверка сайта ChatGPT.",
  geo: "Успешно — получены географические данные; это не решение о допуске в пул."
};
const ORDER = Object.keys(TITLES);
const LABEL_OK = {vpn:"VPN подтверждён", internet:"Интернет доступен (204)", openai:"API доступен (401)", geo:"Геолокация определена"};
function findTimelines(root) {
  const found=[], seen=new Set(), queue=[root];
  while(queue.length && seen.size<2500) {
    const n=queue.shift();
    if(!n || seen.has(n)) continue;
    seen.add(n);
    if(n.localName==="state-history-chart-timeline") found.push(n);
    if(n.shadowRoot) queue.push(n.shadowRoot);
    if(n.children) queue.push(...n.children);
  }
  return found;
}
function legendRows(timelines) {
  const rows=new Map();
  for(const timeline of timelines) {
    const rawByLabel=new Map();
    for(const entity of timeline.data||[]) {
      for(const s of entity.data||[]) {
        const label=String(s.state_localize??s.state??"");
        if(!rawByLabel.has(label)) rawByLabel.set(label,new Set());
        rawByLabel.get(label).add(s.state);
      }
    }
    const series=timeline.shadowRoot?.querySelector("ha-chart-base")?.data;
    if(!Array.isArray(series)) continue;
    for(const dataset of series) {
      for(const segment of dataset.data||[]) {
        const v=segment.value;
        if(!Array.isArray(v)||v.length<5) continue;
        const color=segment.itemStyle?.color||v[4];
        if(typeof color!=="string"||!color||!CSS.supports("color",color)) continue;
        const label=String(v[3]??"");
        const raws=rawByLabel.get(label);
        const state=raws?.size===1?String([...raws][0]):label;
        if(!state) continue;
        rows.set(state+"\u0000"+color,{state,color,label});
      }
    }
  }
  return [...rows.values()].sort((a,b)=>{
    const rank=x=>ORDER.includes(x)?ORDER.indexOf(x):ORDER.length;
    return rank(a.state)-rank(b.state)||a.state.localeCompare(b.state)||a.color.localeCompare(b.color);
  });
}
class RC2HistoryLegend extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:"open"});
    const css=document.createElement("style");
    css.textContent=`
      :host{display:block}
      .wrap{display:flex;flex-direction:column;gap:6px}
      .legend{padding:10px 14px;box-sizing:border-box;font-size:13px;line-height:1.45}
      .items{display:flex;gap:6px 12px;flex-wrap:wrap}
      .item{display:inline-flex;align-items:center;gap:6px}
      .swatch{width:12px;height:12px;border-radius:2px;box-sizing:border-box;border:1px solid rgba(128,128,128,.25);flex:none}
      .note{color:var(--secondary-text-color);font-size:12px;margin-top:5px}
      .fallback{color:var(--secondary-text-color)}
      strong{font-weight:600;display:block;margin-bottom:4px}
    `;
    this.wrap=document.createElement("div"); this.wrap.className="wrap";
    this.legend=document.createElement("ha-card"); this.legend.className="legend";
    this.head=document.createElement("strong"); this.head.textContent="Легенда · 24 ч";
    this.items=document.createElement("div"); this.items.className="items";
    this.note=document.createElement("div"); this.note.className="note";
    this.legend.append(this.head,this.items,this.note);
    this.graphHost=document.createElement("div");
    this.wrap.append(this.legend,this.graphHost);
    this.shadowRoot.append(css,this.wrap);
    this._signature=null; this._generation=0;
  }
  setConfig(config) {
    if(!config?.graph||config.graph.type!=="history-graph"||
       config.graph.hours_to_show!==24||!Object.hasOwn(NOTES,config.metric))
      throw Error("RC2 legend requires a 24-hour native history graph and metric");
    this._metric=config.metric;
    this._signature=null;
    this.graphHost.replaceChildren();
    this._graph=null;
    const generation=++this._generation;
    this.note.textContent=NOTES[this._metric]+" Пустой участок — нет отображённой истории.";
    this._refresh();
    window.loadCardHelpers().then(helpers=>{
      if(generation!==this._generation) return;
      const card=helpers.createCardElement(config.graph);
      this._graph=card;
      if(this._hass) card.hass=this._hass;
      this.graphHost.replaceChildren(card);
      this._refresh();
    }).catch(()=>{
      if(generation===this._generation) {
        this.graphHost.textContent="Не удалось загрузить штатный график. Обновите страницу.";
      }
    });
  }
  set hass(value) {
    this._hass=value;
    if(this._graph) this._graph.hass=value;
  }
  get hass(){return this._hass}
  getCardSize(){return (this._graph?.getCardSize?.()||6)+1}
  connectedCallback(){
    if(!this._timer) this._timer=setInterval(()=>this._refresh(),2000);
    this._refresh();
  }
  disconnectedCallback(){
    if(this._timer) clearInterval(this._timer);
    this._timer=null;
  }
  _refresh(){
    const rows=legendRows(findTimelines(this.graphHost));
    const signature=JSON.stringify(rows);
    if(signature===this._signature) return;
    this._signature=signature;
    this.items.replaceChildren();
    if(!rows.length){
      const empty=document.createElement("span");empty.className="fallback";
      empty.textContent="Цвета появятся после загрузки истории.";
      this.items.append(empty);return;
    }
    for(const r of rows){
      const item=document.createElement("span");item.className="item";
      const swatch=document.createElement("span");swatch.className="swatch";
      swatch.style.backgroundColor=r.color;swatch.setAttribute("aria-hidden","true");
      const label=document.createElement("span");
      label.textContent=r.state==="ok"?LABEL_OK[this._metric]:(Object.hasOwn(TITLES,r.state)?TITLES[r.state]:(r.label||r.state));
      label.title=r.state;
      item.append(swatch,label);this.items.append(item);
    }
  }
}
if(!customElements.get("rc2-history-legend"))
  customElements.define("rc2-history-legend",RC2HistoryLegend);
