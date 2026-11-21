#!/usr/bin/env python3
"""Genere les plans electriques d'Aerobot.

  hardware/schema_electrique.svg  schema electrique (symboles), avec schemdraw
  hardware/plan_perfboard.svg     plan de cablage de la perfboard 50 x 40 mm, vue de dessus

Usage (depuis la racine du depot) :
    pip install schemdraw
    python tools/schemas.py

Les positions des composants sur la perfboard sont celles de hardware/enclosure.scad
(variables esp, mpu, mini, capa) et de TUTORIEL.md, section 7.5.
"""
import html
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_SCHEMA = ROOT / "hardware" / "schema_electrique.svg"
OUT_PLAN = ROOT / "hardware" / "plan_perfboard.svg"

# couleurs des fils (identiques sur les deux plans et dans le boitier 3D)
C = {
    "vpwr": "#d23a2a",   # rouge   : Vpwr ~16 V
    "gnd": "#1b1b1b",    # noir    : masse
    "txd": "#2ea44f",    # vert    : TXD du robot -> RX de l'ESP
    "rxd": "#d4a017",    # jaune   : TX de l'ESP -> RXD du robot
    "brc": "#f08a24",    # orange  : BRC
    "v5": "#c2185b",     # rose    : 5 V
    "v33": "#7b3fbf",    # violet  : 3,3 V
    "sda": "#1f6fd1",    # bleu    : SDA
    "scl": "#17a2b8",    # cyan    : SCL
    "io7": "#0f766e",    # vert fonce : RX de l'ESP apres le diviseur (~3,3 V)
    "io10": "#8d6e63",   # brun    : GPIO10 -> R3
    "base": "#6b7280",   # gris    : R3 -> base de Q1
}


# ----------------------------------------------------------------------------- schema
def schema():
    import schemdraw
    import schemdraw.elements as elm

    schemdraw.config(fontsize=11, bgcolor="white", lw=1.6, font="sans-serif")
    d = schemdraw.Drawing(show=False)
    G = "#444444"

    def ic(pins, size, at, title):
        e = d.add(elm.Ic(pins=[elm.IcPin(**p_) for p_ in pins], size=size).at(at).anchor("center"))
        d.add(elm.Label().at((at[0], at[1] + size[1] / 2 + 0.45)).label(title, fontsize=12))
        return e

    # J1 : port serie du Roomba (mini-DIN 7). Ordre de haut en bas : 1, 2, 3, 4, 5, 6, 7.
    j1 = ic([dict(name=n, pin=str(k), side="right", slot=f"{8 - k}/7", anchorname=f"p{k}")
             for k, n in [(1, "Vpwr"), (2, "Vpwr"), (3, "RXD"), (4, "TXD 5 V"), (5, "BRC"), (6, "GND"), (7, "GND")]],
            (3.0, 9.6), (0, 0), "J1  port série du Roomba (mini-DIN 7)")
    u1 = ic([dict(name="IN+", side="left", slot="2/2", anchorname="inp"), dict(name="IN−", side="left", slot="1/2", anchorname="inn"),
             dict(name="OUT+", side="right", slot="2/2", anchorname="outp"), dict(name="OUT−", side="right", slot="1/2", anchorname="outn")],
            (3.2, 2.4), (7.0, 8.4), "U1  Mini360 (réglé à 5,0 V)")
    u2 = ic([dict(name="5V", side="left", slot="7/7", anchorname="v5"),
             dict(name="GND", side="left", slot="6/7", anchorname="gnda"),
             dict(name="GPIO6 (TX)", side="left", slot="5/7", anchorname="tx"),
             dict(name="GPIO7 (RX)", side="left", slot="4/7", anchorname="rx"),
             dict(name="GPIO10", side="left", slot="2/7", anchorname="io10"),
             dict(name="3V3", side="right", slot="7/7", anchorname="v33"),
             dict(name="GPIO4 (SDA)", side="right", slot="6/7", anchorname="sda"),
             dict(name="GPIO3 (SCL)", side="right", slot="5/7", anchorname="scl"),
             dict(name="GND", side="right", slot="4/7", anchorname="gndb")],
            (6.4, 9.6), (22.0, 0), "U2  ESP32-C3 SuperMini")
    u3 = ic([dict(name="VCC", side="left", slot="7/7", anchorname="vcc"), dict(name="SDA", side="left", slot="6/7", anchorname="sda"),
             dict(name="SCL", side="left", slot="5/7", anchorname="scl"), dict(name="GND", side="left", slot="4/7", anchorname="gnd")],
            (3.2, 9.6), (33.0, 0), "U3  MPU6050 (GY-521)")

    # --- alimentation
    d.add(elm.Wire("-|").at(j1.p1).to(u1.inp).color(C["vpwr"]))
    d.add(elm.Line().at(u1.inn).left(0.6).color(G)); d.add(elm.Ground())
    d.add(elm.Line().at(u1.outn).right(0.6).color(G)); d.add(elm.Ground())
    xc = 12.0
    d.add(elm.Line().at(u1.outp).to((xc, u1.outp[1])).color(C["v5"]))
    d.add(elm.Dot().color(C["v5"]))
    d.add(elm.Wire("-|").at((xc, u1.outp[1])).to((17.4, u2.v5[1])).color(C["v5"]))
    d.add(elm.Line().at((17.4, u2.v5[1])).to(u2.v5).color(C["v5"]))
    d.add(elm.Capacitor(polar=True).at((xc, u1.outp[1])).down(2.6).label("C1  470-1000 µF 16 V\n(au plus près de l'ESP)", loc="bottom", ofst=0.3))
    d.add(elm.Ground())
    d.add(elm.Line().at(u2.gnda).left(0.8).color(G)); d.add(elm.Ground())

    # --- RXD du robot <- GPIO6 (direct)
    d.add(elm.Line().at(u2.tx).to(j1.p3).color(C["rxd"]))
    # --- TXD du robot -> R1 -> noeud -> GPIO7 ; noeud -> R2 -> masse
    d.add(elm.Resistor().at(j1.p4).right(5.5).label("R1  4,7-5,1 kΩ", loc="top").color(C["txd"]))
    node = d.add(elm.Dot().color(C["io7"]))
    d.add(elm.Line().at(node.end).to(u2.rx).color(C["io7"]))
    d.add(elm.Resistor().at(node.end).down(3.0).label("R2  10 kΩ", loc="bottom", ofst=0.2).color(C["io7"]))
    d.add(elm.Ground())

    # --- BRC : transistor NPN, base pilotee par GPIO10 a travers R3
    q1 = d.add(elm.BjtNpn(circle=True).right().at((3.4, -6.6)).anchor("base").label("Q1\nBC547\n2N2222", loc="right", ofst=0.15))
    d.add(elm.Wire("|-").at(q1.collector).to(j1.p5).color(C["brc"]))
    d.add(elm.Ground().at(q1.emitter))
    yb = -9.4
    d.add(elm.Line().at(q1.base).left(1.0).color(C["base"]))
    d.add(elm.Line().down(abs(yb - q1.base[1])).color(C["base"]))
    d.add(elm.Resistor().right(5.0).label("R3  1 kΩ", loc="bottom").color(C["base"]))
    d.add(elm.Line().to((17.6, yb)).color(C["io10"]))
    d.add(elm.Line().to((17.6, u2.io10[1])).color(C["io10"]))
    d.add(elm.Line().to(u2.io10).color(C["io10"]))

    # --- masse du port : broche 6 seulement
    d.add(elm.Line().at(j1.p6).right(0.8).color(G)); d.add(elm.Ground())
    d.add(elm.Label().at(j1.p2).label("non relié", loc="right", ofst=0.2, color="#888888", fontsize=9))
    d.add(elm.Label().at(j1.p7).label("non relié", loc="right", ofst=0.2, color="#888888", fontsize=9))

    # --- MPU6050 : liaisons droites (broches alignees)
    d.add(elm.Line().at(u2.v33).to(u3.vcc).color(C["v33"]))
    d.add(elm.Line().at(u2.sda).to(u3.sda).color(C["sda"]))
    d.add(elm.Line().at(u2.scl).to(u3.scl).color(C["scl"]))
    d.add(elm.Line().at(u2.gndb).to(u3.gnd).color(G))
    d.add(elm.Dot().at(((u2.gndb[0] + u3.gnd[0]) / 2, u2.gndb[1])).color(G))
    d.add(elm.Ground().at(((u2.gndb[0] + u3.gnd[0]) / 2, u2.gndb[1])))

    # --- notes
    d.add(elm.Label().at((-1.6, -11.4)).label(
        "Pendant les tests : ESP alimenté par l'USB, J1.1 (Vpwr) NON relié. Vpwr se branche en dernier, après la mesure de courant (TUTORIEL, étape 9).",
        halign="left", fontsize=10))
    d.add(elm.Label().at((-1.6, -12.2)).label(
        "R1/R2 : 5 V × 10/(5+10) ≈ 3,3 V sur GPIO7.   GPIO10 = 1 → Q1 conduit → BRC à 0 V (réveil).   Brochage de J1 déduit de la spec : 3/4 et 5/7 à confirmer au multimètre.",
        halign="left", fontsize=10, color="#555555"))
    return d


# ----------------------------------------------------------------------------- plan perfboard
# coordonnees de plaque en mm : x de 0 (cote USB) a 50, y de 0 (cote bouton CLEAN) a 40 (cote port)
P = 2.54
BOARD_W, BOARD_H = 50, 40
ESP = (0.5, 6, 22.52, 18)
MPU = (27, 6, 21, 16)
MINI = (6, 27, 17, 11)
CAPA = (27, 26, 12, 8)

# reseaux : (numero, cle couleur, nom, pastilles)
NETS = [
    (1, "vpwr", "Vpwr ~16 V", ["J2_1", "U1_IN+"]),
    (2, "gnd", "Masse", ["J2_6", "U1_IN-", "U1_OUT-", "C1-", "E_GND", "M_GND", "R2a", "Q1_E"]),
    (3, "v5", "5 V", ["U1_OUT+", "C1+", "E_5V"]),
    (4, "v33", "3,3 V", ["E_3V3", "M_VCC"]),
    (5, "sda", "SDA", ["E_IO4", "M_SDA"]),
    (6, "scl", "SCL", ["E_IO3", "M_SCL"]),
    (7, "txd", "TXD du robot (5 V)", ["J2_4", "R1a"]),
    (8, "io7", "RX de l'ESP (≈3,3 V)", ["R1b", "R2b", "E_IO7"]),
    (9, "rxd", "RXD du robot", ["E_IO6", "J2_3"]),
    (10, "brc", "BRC", ["J2_5", "Q1_C"]),
    (11, "io10", "Commande BRC", ["E_IO10", "R3a"]),
    (12, "base", "Base de Q1", ["R3b", "Q1_B"]),
]
LABELS = {"J2_1": "fiche 1", "J2_6": "fiche 6", "J2_4": "fiche 4", "J2_3": "fiche 3", "J2_5": "fiche 5",
          "U1_IN+": "Mini360 IN+", "U1_IN-": "Mini360 IN−", "U1_OUT+": "Mini360 OUT+", "U1_OUT-": "Mini360 OUT−",
          "C1+": "C1 +", "C1-": "C1 −", "E_GND": "ESP GND", "E_5V": "ESP 5V", "E_3V3": "ESP 3V3", "E_IO4": "ESP IO4",
          "E_IO3": "ESP IO3", "E_IO7": "ESP IO7", "E_IO6": "ESP IO6", "E_IO10": "ESP IO10",
          "M_GND": "MPU GND", "M_VCC": "MPU VCC", "M_SDA": "MPU SDA", "M_SCL": "MPU SCL",
          "R1a": "R1 g.", "R1b": "R1 d.", "R2a": "R2 g.", "R2b": "R2 d.", "R3a": "R3 g.", "R3b": "R3 d.",
          "Q1_E": "Q1 E", "Q1_B": "Q1 B", "Q1_C": "Q1 C"}


def plan():
    pins = {}
    power = ["5V", "GND", "3V3", "IO4", "IO3", "IO2", "IO1", "IO0"]
    gpio = ["IO5", "IO6", "IO7", "IO8", "IO9", "IO10", "IO20", "IO21"]
    x0 = ESP[0] + 2.0
    for i, n in enumerate(power):
        pins["E_" + n] = (x0 + i * P, ESP[1] + 1.4)
    for i, n in enumerate(gpio):
        pins["E_" + n] = (x0 + i * P, ESP[1] + ESP[3] - 1.4)
    mpu_names = ["VCC", "GND", "SCL", "SDA", "XDA", "XCL", "AD0", "INT"]
    for i, n in enumerate(mpu_names):
        pins["M_" + n] = (MPU[0] + 1.8 + i * P, MPU[1] + 1.4)
    pins.update({"U1_IN+": (MINI[0] + 1.3, MINI[1] + MINI[3] - 1.3), "U1_IN-": (MINI[0] + 1.3, MINI[1] + 1.3),
                 "U1_OUT+": (MINI[0] + MINI[2] - 1.3, MINI[1] + MINI[3] - 1.3), "U1_OUT-": (MINI[0] + MINI[2] - 1.3, MINI[1] + 1.3)})
    pins.update({"C1+": (CAPA[0] - 1.0, CAPA[1] + CAPA[3] / 2), "C1-": (CAPA[0] + CAPA[2] + 0.4, CAPA[1] - 0.9)})
    res = [("R1", 25.6, "4,7-5,1 k"), ("R2", 28.8, "10 k"), ("R3", 32.0, "1 k")]
    for n, y, _ in res:
        pins[n + "a"], pins[n + "b"] = (42.0, y), (48.9, y)
    pins.update({"Q1_E": (39.2, 36.0), "Q1_B": (41.74, 36.0), "Q1_C": (44.28, 36.0)})
    for i, k in enumerate(["J2_1", "J2_6", "J2_4", "J2_3", "J2_5"]):
        pins[k] = (25.0 + i * P, 38.6)

    net_of = {}
    for num, col, name, pads in NETS:
        for pd in pads:
            net_of[pd] = (num, col)

    S, M, TOP = 14, 36, 70
    LEG = 360
    WPX, HPX = BOARD_W * S + 2 * M + LEG, BOARD_H * S + TOP + 60

    def X(x): return M + x * S
    def Y(y): return TOP + (BOARD_H - y) * S

    e = html.escape
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WPX}" height="{HPX}" viewBox="0 0 {WPX} {HPX}" '
         f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
         f'<rect width="{WPX}" height="{HPX}" fill="#ffffff"/>',
         f'<text x="{M}" y="26" font-size="18" font-weight="700" fill="#1f2328">Perfboard 50 × 40 mm : implantation et câblage</text>',
         f'<text x="{M}" y="46" font-size="12" fill="#59636e">Vue de dessus, côté composants. Relie entre elles les pastilles qui portent le même numéro (même couleur).</text>']
    o.append(f'<text x="{X(BOARD_W/2)}" y="{Y(BOARD_H)-8}" font-size="12" font-weight="600" fill="#1f2328" text-anchor="middle">↑ côté port série (fiche mini-DIN)</text>')
    o.append(f'<text x="{X(BOARD_W/2)}" y="{Y(0)+20}" font-size="12" fill="#59636e" text-anchor="middle">↓ côté bouton CLEAN</text>')
    o.append(f'<rect x="{X(0)}" y="{Y(BOARD_H)}" width="{BOARD_W*S}" height="{BOARD_H*S}" rx="6" fill="#2f7d4a" stroke="#1d5532" stroke-width="2"/>')
    for i in range(20):
        for j in range(16):
            o.append(f'<circle cx="{X(0.9 + i*P):.1f}" cy="{Y(0.9 + j*P):.1f}" r="2.6" fill="#c9a24c" opacity=".45"/>')
    for x, y in [(2.5, 2.5), (47.5, 2.5), (2.5, 37.5), (47.5, 37.5)]:
        o.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="{2.5*S}" fill="#2f7d4a" stroke="#ffffff" stroke-dasharray="4 3" opacity=".9"/>')
        o.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="{1.1*S}" fill="#ffffff" stroke="#777"/>')

    def module(r, fill, label, sub=""):
        x, y, w, h = r
        o.append(f'<rect x="{X(x)}" y="{Y(y+h)}" width="{w*S}" height="{h*S}" rx="4" fill="{fill}" stroke="#0b0b0b" stroke-width="1.2"/>')
        o.append(f'<text x="{X(x+w/2)}" y="{Y(y+h/2)+1}" font-size="14" font-weight="700" fill="#ffffff" text-anchor="middle">{e(label)}</text>')
        if sub:
            o.append(f'<text x="{X(x+w/2)}" y="{Y(y+h/2)+18}" font-size="11" fill="#dfe3e8" text-anchor="middle">{e(sub)}</text>')

    module(ESP, "#1a1e2e", "ESP32-C3 SuperMini", "USB-C vers la fente du boîtier")
    o.append(f'<rect x="{X(-0.6)}" y="{Y(19.5)}" width="{7.4*S}" height="{9*S}" rx="3" fill="#b9bdc2" stroke="#555"/>')
    o.append(f'<text x="{X(3.1)}" y="{Y(15)+4}" font-size="11" font-weight="700" fill="#333" text-anchor="middle">USB-C</text>')
    module(MPU, "#2350a8", "MPU6050 (GY-521)", "à plat, bien fixé")
    module(MINI, "#1f6b45", "Mini360", "réglé à 5,0 V avant soudure")
    o.append(f'<rect x="{X(CAPA[0])}" y="{Y(CAPA[1]+CAPA[3])}" width="{CAPA[2]*S}" height="{CAPA[3]*S}" rx="{4*S}" fill="#1c1d20" stroke="#000"/>')
    o.append(f'<rect x="{X(CAPA[0]+CAPA[2]-2.4)}" y="{Y(CAPA[1]+CAPA[3])+2}" width="{1.6*S}" height="{CAPA[3]*S-4}" fill="#9aa0a6"/>')
    o.append(f'<text x="{X(CAPA[0]+4.6)}" y="{Y(CAPA[1]+CAPA[3]/2)+5}" font-size="12" font-weight="700" fill="#fff" text-anchor="middle">C1 (+ à gauche)</text>')
    for n, y, val in res:
        o.append(f'<line x1="{X(42)}" y1="{Y(y)}" x2="{X(48.9)}" y2="{Y(y)}" stroke="#b8bcc2" stroke-width="2"/>')
        o.append(f'<rect x="{X(43.1)}" y="{Y(y)-0.95*S}" width="{4.7*S}" height="{1.9*S}" rx="{0.95*S}" fill="#e3cf9f" stroke="#6b5a35"/>')
        o.append(f'<text x="{X(45.45)}" y="{Y(y)+4}" font-size="10" font-weight="600" fill="#3b2f16" text-anchor="middle">{n} {val}</text>')
    o.append(f'<path d="M{X(38.8)} {Y(38.3)} H{X(44.7)} A {3.0*S} {1.9*S} 0 0 0 {X(38.8)} {Y(38.3)} Z" fill="#111" transform="translate(0,{0.2*S})"/>')
    o.append(f'<text x="{X(41.74)}" y="{Y(38.3)-0.5*S}" font-size="10" font-weight="700" fill="#fff" text-anchor="middle">Q1</text>')

    # etiquettes de broches des modules
    for n in power:
        x, y = pins["E_" + n]
        o.append(f'<text x="{X(x)}" y="{Y(y)-11}" font-size="9" fill="#ffffff" text-anchor="middle">{n}</text>')
    for n in gpio:
        x, y = pins["E_" + n]
        o.append(f'<text x="{X(x)}" y="{Y(y)+19}" font-size="9" fill="#ffffff" text-anchor="middle">{n}</text>')
    for n in mpu_names:
        x, y = pins["M_" + n]
        o.append(f'<text x="{X(x)}" y="{Y(y)-11}" font-size="9" fill="#ffffff" text-anchor="middle">{n}</text>')
        if "M_" + n not in net_of:
            o.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="3.4" fill="#e6c25a" stroke="#6b5a20"/>')
    for n in power + gpio:
        if "E_" + n not in net_of:
            x, y = pins["E_" + n]
            o.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="3.4" fill="#e6c25a" stroke="#6b5a20"/>')
    for k, lab, dx, anc in [("U1_IN+", "IN+", 13, "start"), ("U1_IN-", "IN−", 13, "start"), ("U1_OUT+", "OUT+", -13, "end"), ("U1_OUT-", "OUT−", -13, "end")]:
        x, y = pins[k]
        o.append(f'<text x="{X(x)+dx}" y="{Y(y)+4}" font-size="10" fill="#ffffff" text-anchor="{anc}">{lab}</text>')
    for k, lab in [("Q1_E", "E"), ("Q1_B", "B"), ("Q1_C", "C")]:
        x, y = pins[k]
        o.append(f'<text x="{X(x)}" y="{Y(y)+20}" font-size="9" fill="#ffffff" text-anchor="middle">{lab}</text>')
    for k in ["J2_1", "J2_6", "J2_4", "J2_3", "J2_5"]:
        x, y = pins[k]
        o.append(f'<text x="{X(x)}" y="{Y(y)+20}" font-size="9" fill="#ffffff" text-anchor="middle">{k[3:]}</text>')
    o.append(f'<text x="{X(30.1)}" y="{Y(38.6)+31}" font-size="9" fill="#dfe3e8" text-anchor="middle">fils vers la fiche (n° de broche)</text>')

    # pastilles numerotees
    for k, (num, col) in net_of.items():
        x, y = pins[k]
        o.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="8.2" fill="{C[col]}" stroke="#ffffff" stroke-width="1.6"/>')
        o.append(f'<text x="{X(x):.1f}" y="{Y(y)+3.6:.1f}" font-size="9.5" font-weight="700" fill="#ffffff" text-anchor="middle">{num}</text>')

    # legende : reseaux
    lx, ly = X(BOARD_W) + 26, TOP + 4
    o.append(f'<text x="{lx}" y="{ly}" font-size="14" font-weight="700" fill="#1f2328">À relier ensemble</text>')
    yy = ly + 10
    for num, col, name, pads in NETS:
        yy += 25
        o.append(f'<circle cx="{lx+9}" cy="{yy-4}" r="8.2" fill="{C[col]}"/>')
        o.append(f'<text x="{lx+9}" y="{yy-0.4}" font-size="9.5" font-weight="700" fill="#fff" text-anchor="middle">{num}</text>')
        o.append(f'<text x="{lx+24}" y="{yy-6}" font-size="11" font-weight="700" fill="#1f2328">{e(name)}</text>')
        items, lines_, cur = [LABELS[p_] for p_ in pads], [], ""
        for it in items:
            cand = (cur + ", " + it) if cur else it
            if len(cand) > 46:
                lines_.append(cur + ","); cur = it
            else:
                cur = cand
        lines_.append(cur)
        for li, txt in enumerate(lines_):
            o.append(f'<text x="{lx+24}" y="{yy+7+li*12}" font-size="10" fill="#59636e">{e(txt)}</text>')
        yy += 12 * (len(lines_) - 1)
    notes = ["Pastilles jaunes sans numéro : non utilisées.",
             "Cercles pointillés : vis M2, rien à souder.",
             "Ordre des broches de l'ESP : vérifie la sérigraphie",
             "de ta carte (certaines ont les rangées inversées).",
             "Hauteur max. sous le couvercle : 9 mm au centre.",
             "⚠ Q1 : le brochage dépend du modèle ! Face plate",
             "vers toi : BC547 = C B E, 2N2222 (TO-92) = E B C.",
             "Soude d'après les lettres E, B, C du plan, pas",
             "d'après la position des pattes."]
    for i, t_ in enumerate(notes):
        o.append(f'<text x="{lx}" y="{yy + 34 + i*16}" font-size="10.5" fill="#59636e">{e(t_)}</text>')
    o.append("</svg>")
    return "\n".join(o) + "\n"


def main():
    d = schema()
    OUT_SCHEMA.write_bytes(d.get_imagedata("svg"))
    OUT_PLAN.write_text(plan(), encoding="utf-8")
    print("écrit :", OUT_SCHEMA.relative_to(ROOT), "et", OUT_PLAN.relative_to(ROOT))


if __name__ == "__main__":
    main()
