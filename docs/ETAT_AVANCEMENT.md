# État d'avancement — Aérobot ESP

Dernière mise à jour : 18/11/2026.

## En une phrase

Le robot (« Dimitri », Roomba 696) est démonté, le port série est repéré sur le dessus et son brochage est déduit de la spec ; le boîtier 3D est dessiné et tout le logiciel est écrit, mais **rien n'a encore tourné sur du matériel**.

## Fait

| Élément | Détail | Vérifié sur matériel ? |
|---|---|---|
| Analyse du robot | Roomba 696 (r696040), app 3.5.62-95 | non (version série du firmware inconnue) |
| Démontage | batterie, brosse, pare-chocs et capot retirés, port série accessible | oui (photos) |
| Port série repéré | mini-DIN 7 broches sur le dessus, sous la bague décorative, avant gauche (~40° à gauche de la tourelle IR) | oui (photos) |
| Brochage du port | déduit du schéma de la spec iRobot, p. 3, voir [`hardware/brochage_port_dimitri.png`](../hardware/brochage_port_dimitri.png) | **non** : à confirmer au multimètre |
| Firmware ESPHome + composant `roomba_oi` | flux de capteurs, pose odométrie + gyro, pilotage, watchdog, réveil | **non compilé** |
| Config Home Assistant | aspirateur, planning, automations, carte, joystick | **non testée** |
| Mapper | grille 5 cm, rendu PNG, simulateur | oui, en simulation seulement |
| Tutoriel | 19 sections, sources S1-S40 | relu sur le papier, pas suivi de bout en bout |
| Boîtier 3D | `enclosure.scad` : boîtier posé sur le dessus, centré sur le port, fiche coudée par le fond, perfboard 50×40, 56×88×22 mm, cales séparées ; STL dans `hardware/stl/` | compilé sans avertissement (OpenSCAD 2021.01), pièces étanches ; **non imprimé**, position du port et hauteurs du dessus à mesurer |

## Brochage du port (état actuel)

Voir l'image et la note dans [`hardware/WIRING.md`](../hardware/WIRING.md).

- **Sûr** (symétrie des trous + position de l'encoche) : 1 et 2 = Vpwr (+16 V environ), 6 = GND.
- **Incertain** : 3 et 4 (RXD/TXD) et 5 et 7 (BRC/GND) peuvent être inversés si le schéma de la spec est une vue de dessous.
- **Test sans risque** en attendant le multimètre : ne rien brancher dans 1 et 2, alimenter l'ESP en USB, ne prendre la masse que sur 6, essayer 3/4 dans les deux sens, et essayer 5 puis 7 pour le BRC.

## À faire, dans l'ordre

1. Acheter un multimètre et le reste du matériel ([`hardware/WIRING.md`](../hardware/WIRING.md), liste de courses). *(Un multimètre est attendu d'ici environ une semaine ; le reste n'est pas commandé à notre connaissance.)*
2. Confirmer le brochage au multimètre : continuité avec les contacts de la batterie (batterie retirée), puis tension de Vpwr.
3. Compiler le firmware et corriger les erreurs (le composant a été écrit sans compilateur).
4. Banc d'essai : ESP en USB, UART + BRC + GND reliés au robot ; vérifier le flux de capteurs.
5. Lire la vraie version du firmware du robot (bouton « Lire version firmware ») pour savoir si le réveil par BRC est possible.
6. Mesurer le courant sur Vpwr (doit rester sous 200 mA), puis alimenter l'ESP depuis le robot.
7. Calibrer l'odométrie et le cap, puis tester la carte dans Home Assistant.
8. Imprimer le gabarit (`part = "mock"`), le poser sur le dessus pour caler la position du port, mesurer les hauteurs, puis imprimer le boîtier.

## Risques connus

| Risque | Conséquence | Piste |
|---|---|---|
| Firmware du robot trop ancien (< 3.8.2) | pas de réveil par BRC depuis la base | appui sur CLEAN, impulsions BRC régulières, transistor sur le bouton CLEAN |
| Brochage inversé (3/4, 5/7) | pas de données, sans danger | essayer les deux sens |
| Court-circuit sur Vpwr (broches 1 et 2) | fusible du robot, carte abîmée | ne brancher Vpwr qu'à la fin, avec un câble fiable |
| Courant de l'ESP > 200 mA | fusible du port qui coupe | alimenter l'ESP par USB pendant les tests |
| Dérive d'odométrie | carte déformée | calibration, recalage sur les murs |
| Code jamais compilé | erreurs de compilation probables | plan B : partir de `dynodix/esphome-roomba` |

## Pas encore décidé

- Câble final : fiche mini-DIN mâle (une fiche à 8 broches s'insère, d'après une source non vérifiée) ou fils soudés.
- Licence du dépôt.
