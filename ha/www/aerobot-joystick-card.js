/* Carte Lovelace "Aerobot joystick" : manette virtuelle sans dependance.
 * Ressource : /local/aerobot-joystick-card.js (type: module)
 * Config :
 *   type: custom:aerobot-joystick-card
 *   service: esphome.aerobot_drive_xy     # action ESPHome "drive_xy"
 *   manual_service: esphome.aerobot_manual_mode
 *   rate_ms: 100
 * Le firmware coupe les moteurs tout seul si plus aucune commande n'arrive (~400 ms).
 */
class AerobotJoystickCard extends HTMLElement {
  setConfig(config) {
    this._config = Object.assign(
      { service: "esphome.aerobot_drive_xy", manual_service: "esphome.aerobot_manual_mode", rate_ms: 100, title: "Manette Aérobot" },
      config
    );
    this._x = 0;
    this._y = 0;
    this._timer = null;
    if (this._root) return;
    this._root = this.attachShadow({ mode: "open" });
    this._root.innerHTML = `
      <style>
        ha-card { padding: 12px; text-align: center; }
        .pad { position: relative; width: 220px; height: 220px; margin: 8px auto; border-radius: 50%;
               background: var(--secondary-background-color, #eee); touch-action: none; user-select: none; }
        .knob { position: absolute; width: 70px; height: 70px; border-radius: 50%; left: 75px; top: 75px;
                background: var(--primary-color, #03a9f4); opacity: .85; }
        .hint { font-size: 12px; color: var(--secondary-text-color); }
        button { margin: 4px; padding: 6px 12px; }
      </style>
      <ha-card header="${this._config.title}">
        <div class="pad"><div class="knob"></div></div>
        <div class="hint">Maintiens et glisse. Relâcher = arrêt.</div>
        <button id="on">Mode manuel</button><button id="off">Quitter</button>
      </ha-card>`;
    const pad = this._root.querySelector(".pad");
    const knob = this._root.querySelector(".knob");
    const R = 110, K = 35;
    const move = (ev) => {
      const r = pad.getBoundingClientRect();
      let dx = ev.clientX - (r.left + R);
      let dy = ev.clientY - (r.top + R);
      const max = R - K;
      const d = Math.hypot(dx, dy);
      if (d > max) { dx = (dx / d) * max; dy = (dy / d) * max; }
      knob.style.left = R - K + dx + "px";
      knob.style.top = R - K + dy + "px";
      this._x = dx / max;      // droite positif
      this._y = -dy / max;     // haut positif = avancer
    };
    const start = (ev) => {
      pad.setPointerCapture(ev.pointerId);
      move(ev);
      this._send();
      this._timer = setInterval(() => this._send(), this._config.rate_ms);
    };
    const end = () => {
      clearInterval(this._timer);
      this._timer = null;
      this._x = 0; this._y = 0;
      knob.style.left = R - K + "px";
      knob.style.top = R - K + "px";
      this._send();           // arret explicite
    };
    pad.addEventListener("pointerdown", start);
    pad.addEventListener("pointermove", (ev) => { if (this._timer) move(ev); });
    pad.addEventListener("pointerup", end);
    pad.addEventListener("pointercancel", end);
    this._root.getElementById("on").addEventListener("click", () => this._call(this._config.manual_service, { enable: true }));
    this._root.getElementById("off").addEventListener("click", () => this._call(this._config.manual_service, { enable: false }));
  }

  set hass(hass) { this._hass = hass; }

  _call(svc, data) {
    if (!this._hass) return;
    const [domain, name] = svc.split(".");
    this._hass.callService(domain, name, data);
  }

  _send() {
    // x = virage (droite positif) ; le firmware attend turn > 0 = gauche
    this._call(this._config.service, { forward: +this._y.toFixed(2), turn: +(-this._x).toFixed(2) });
  }

  getCardSize() { return 5; }
}
customElements.define("aerobot-joystick-card", AerobotJoystickCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "aerobot-joystick-card", name: "Aérobot joystick", description: "Manette virtuelle pour Aérobot" });
