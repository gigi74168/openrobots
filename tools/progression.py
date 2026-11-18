#!/usr/bin/env python3
"""Met a jour la barre de progression du README a partir de la « Feuille de route ».

Usage (depuis la racine du depot) :  python tools/progression.py

Le script lit les cases a cocher de la section « ## Feuille de route » du README,
groupees par phase (lignes « **Nom de la phase** »), puis :
  - regenere docs/progression.svg (s'adapte au theme clair ou sombre de GitHub) ;
  - reecrit la ligne de resume entre <!-- progression:debut --> et <!-- progression:fin -->.
Aucune dependance : bibliotheque standard uniquement.
"""
import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
SVG = ROOT / "docs" / "progression.svg"


def lire_feuille_de_route(texte):
    m = re.search(r"^## Feuille de route\n(.*?)(?=^## )", texte, re.S | re.M)
    if not m:
        sys.exit("Section « ## Feuille de route » introuvable dans README.md")
    phases, courante = [], None
    for ligne in m.group(1).splitlines():
        p = re.match(r"^\*\*(.+?)\*\*\s*$", ligne.strip())
        if p:
            courante = {"nom": p.group(1), "etapes": []}
            phases.append(courante)
            continue
        c = re.match(r"^- \[( |x|X)\] (.+)$", ligne.strip())
        if c:
            if courante is None:
                courante = {"nom": "Étapes", "etapes": []}
                phases.append(courante)
            courante["etapes"].append((c.group(1).lower() == "x", c.group(2)))
    if not any(ph["etapes"] for ph in phases):
        sys.exit("Aucune case a cocher trouvee dans la feuille de route")
    return [ph for ph in phases if ph["etapes"]]


def faire_svg(phases, fait, total, pct, prochaine):
    W, H, gap = 760, 132, 4
    n = total
    seg = (W - (n - 1) * gap) / n
    e = html.escape
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="Progression du projet : {pct} %, {fait} étapes sur {total}">',
           "<style>",
           "text{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif}",
           ".t{fill:#1f2328}.m{fill:#59636e}.a{fill:#c9480f}.todo{fill:#dfe3e8}.done{fill:#c9480f}.br{stroke:#b6bec7}",
           "@media (prefers-color-scheme:dark){.t{fill:#e6edf3}.m{fill:#9198a1}.a{fill:#ff7a3d}.todo{fill:#2d333b}.done{fill:#ff7a3d}.br{stroke:#4a525c}}",
           "</style>",
           '<text class="t" x="0" y="20" font-size="16" font-weight="600">Progression du projet</text>',
           f'<text class="a" x="{W}" y="22" font-size="24" font-weight="700" text-anchor="end">{pct} %</text>',
           f'<text class="m" x="{W - 76}" y="21" font-size="12" text-anchor="end">{fait} étapes sur {total}</text>']
    y = 36
    i = 0
    for ph in phases:
        x0 = i * (seg + gap)
        for ok, nom in ph["etapes"]:
            x = i * (seg + gap)
            out.append(f'<rect class="{"done" if ok else "todo"}" x="{x:.1f}" y="{y}" width="{seg:.1f}" height="18" rx="3">'
                       f'<title>{"✔" if ok else "○"} {e(nom)}</title></rect>')
            i += 1
        x1 = (i - 1) * (seg + gap) + seg
        cx = (x0 + x1) / 2
        k = sum(1 for ok, _ in ph["etapes"] if ok)
        out.append(f'<path class="br" d="M{x0 + 1:.1f} 60 V64 H{x1 - 1:.1f} V60" fill="none" stroke-width="1"/>')
        out.append(f'<text class="t" x="{cx:.1f}" y="80" font-size="12" font-weight="600" text-anchor="middle">{e(ph["nom"])}</text>')
        out.append(f'<text class="m" x="{cx:.1f}" y="95" font-size="11" text-anchor="middle">{k}/{len(ph["etapes"])}</text>')
    suite = f"Prochaine étape : {e(prochaine)}" if prochaine else "Toutes les étapes sont faites"
    out.append(f'<text class="m" x="0" y="122" font-size="12">{suite}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    texte = README.read_text(encoding="utf-8")
    phases = lire_feuille_de_route(texte)
    etapes = [s for ph in phases for s in ph["etapes"]]
    total = len(etapes)
    fait = sum(1 for ok, _ in etapes if ok)
    pct = round(100 * fait / total)
    prochaine = next((nom for ok, nom in etapes if not ok), None)
    SVG.write_text(faire_svg(phases, fait, total, pct, prochaine), encoding="utf-8")

    plein = round(20 * fait / total)
    detail = " · ".join(f'{ph["nom"]} {sum(1 for ok, _ in ph["etapes"] if ok)}/{len(ph["etapes"])}' for ph in phases)
    bloc = ("<!-- progression:debut -->\n"
            '<p align="center"><img src="docs/progression.svg" alt="Progression du projet : '
            f'{pct} %, {fait} étapes sur {total}" width="100%"></p>\n\n'
            f"**Avancement : {pct} %** `{'█' * plein}{'░' * (20 - plein)}` {fait} étapes sur {total} ({detail})"
            + (f". Prochaine étape : {prochaine[0].lower() + prochaine[1:]}." if prochaine else ".")
            + " Détail : [Feuille de route](#feuille-de-route).\n"
            "<!-- progression:fin -->")
    if "<!-- progression:debut -->" not in texte:
        sys.exit("Marqueurs <!-- progression:debut --> / <!-- progression:fin --> absents du README")
    texte = re.sub(r"<!-- progression:debut -->.*?<!-- progression:fin -->", lambda _: bloc, texte, flags=re.S)
    README.write_text(texte, encoding="utf-8")
    print(f"{pct} % ({fait}/{total}) ; prochaine étape : {prochaine}")


if __name__ == "__main__":
    main()
