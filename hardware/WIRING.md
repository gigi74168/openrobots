# Câblage Aérobot — Roomba 696 ↔ ESP32-C3 SuperMini

> ⚠️ **Avant de brancher quoi que ce soit** : mesurer au multimètre la tension du pin 1 (Vpwr) sur le robot (batterie non régulée, probablement ~14-17 V, **non vérifié**). Vérifier la polarité avec la spec iRobot. Un mauvais câblage peut griller le port série du Roomba ou l'ESP.

## Mini-DIN 7 broches du Roomba (spec OI série 600)
| Pin | Nom | Fonction |
|---|---|---|
| 1, 2 | Vpwr | Batterie non régulée (fusible ; 200 mA continu, 500 mA crête) |
| 3 | RXD | Entrée du Roomba (reçoit de l'ESP) |
| 4 | TXD | Sortie du Roomba, **logique 0-5 V** |
| 5 | BRC | Réveil / anti-veille (impulsion à 0 V) |
| 6, 7 | GND | Masse |

Le brochage du connecteur se lit dans la spec (PDF dans `roomba-696-handoff.md`). Vérifier le sens du connecteur avant de souder.

### Position des trous sur Dimitri (déduite, à confirmer au multimètre)
Image annotée : [`brochage_port_dimitri.png`](brochage_port_dimitri.png). La spec OI 2021, p. 3, donne un schéma « vue de dessus du connecteur femelle » :

```
Schéma de la spec (encoche en haut)          Sur Dimitri (photo, encoche en bas à gauche)
        6                                               
   7    6    5      rangée de 3                  3 en haut à gauche, 1 en haut, 2 à droite,
   4   [ ]   3      2 trous + clé centrale        5 à gauche, 6 et 7 en bas à gauche, 4 en bas à droite
     2     1        rangée de 2                   (voir l'image annotée pour la position exacte)
```
Seule la symétrie du schéma et la position de l'encoche ont servi : **1 et 2** (Vpwr) sont sûrs ; **6** (GND) est sûr (au centre de la rangée de 3, côté encoche). **3/4** et **5/7** peuvent être inversés si le schéma de la spec est en réalité une vue de dessous : à vérifier avant de relier les données (voir TUTORIEL).

## Schéma

```
Roomba pin 1 (Vpwr) ──► Mini360 IN+            Mini360 OUT+ (réglé à 5,0 V) ──► ESP32-C3 5V
Roomba pin 6/7 (GND) ─► Mini360 IN-  ── GND commun ── Mini360 OUT- ──► ESP32-C3 GND
                         (+ 470-1000 µF 16 V entre OUT+ et GND, au plus près de l'ESP)

Roomba pin 4 (TXD, 5 V) ──[ 5 kΩ ]──┬──► ESP GPIO7 (RX)
                                    [ 10 kΩ ]
                                     └── GND
Roomba pin 3 (RXD)  ◄── ESP GPIO6 (TX)        (3,3 V suffit pour un niveau haut du Roomba)

Roomba pin 5 (BRC)  ◄── collecteur NPN (BC547 / 2N2222)
                          émetteur ──► GND
                          base ──[ 1 kΩ ]── ESP GPIO10        (GPIO10 = 1 → BRC à 0 V)

MPU6050 (GY-521) : VCC → ESP 3V3 ; GND → GND ; SDA → GPIO4 ; SCL → GPIO3
```

Notes :
- **Mini360 réglé à 5,0 V** (mesurer sa sortie *avant* de le connecter à l'ESP, en tournant la vis). La SuperMini a son propre régulateur 3,3 V et accepte 5 V sur sa broche 5V. ESPRoomba régule directement à 3,3 V ; les deux fonctionnent, 5 V est plus simple à vérifier.
- Le diviseur 5k/10k donne ~3,3 V quand le Roomba sort 5 V. Ne pas supprimer, même si d'autres schémas le font.
- Le transistor évite d'imposer du 3,3 V (ou de recevoir du 5 V) sur le GPIO : le BRC du Roomba est tiré à 5 V en interne.
- Le schéma Fritzing de ShonP40/ESPRoomba ne correspond pas à son YAML (issue #4) : ne pas le suivre.
- Les broches choisies évitent les broches « strapping » du C3 (GPIO2, 8, 9) ; GPIO8 est la LED de la carte.

## MPU6050 : orientation
- Fixer **à plat, rigide**, axe Z vertical, **loin du moteur de brosse** (vibrations).
- Si le cap tourne à l'envers (le robot tourne à gauche et θ diminue), ajouter `id(roomba).set_gyro_scale(-1.0f);` dans `on_boot` de `roomba.yaml`.

## Alimentation : à mesurer
1. Premier test : ESP alimenté en **USB**, seulement UART+BRC reliés au Roomba (GND commun).
2. Deuxième test : alimentation par Vpwr, multimètre en série (mode mA) : le courant tiré sur Vpwr doit rester **< 200 mA** avec le Wi-Fi actif (pic à l'association Wi-Fi inclus).
3. Si > 200 mA : ne pas ajouter d'autres charges ; envisager une alimentation directe sur la batterie avec fusible 0,5 A (hors spec iRobot, à documenter).

## Liste de courses (estimations, prix à vérifier)
| Pièce | Qté |
|---|---|
| ESP32-C3 SuperMini | 1 (lot de 2 pour rechange) |
| Convertisseur Mini360 | 1-2 |
| MPU6050 GY-521 | 1 |
| NPN BC547 ou 2N2222 | 2 |
| Résistances 1 kΩ, 5 kΩ (ou 4,7k), 10 kΩ | 1 chacune |
| Condensateur 470-1000 µF 16 V | 1 |
| Mini-DIN 7 broches mâle (ou câble OI sacrifié) | 1 |
| Perfboard ~50×40 mm, fil fin, gaine thermo | — |
