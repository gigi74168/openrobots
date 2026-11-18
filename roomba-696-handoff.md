# Projet Roomba 696 : passation (07/11/2026)

## Objectif
Remettre en état le Roomba 696 de Paul et le libérer du cloud iRobot (open source, contrôle local), en gardant les fonctions utiles (démarrer, retour base, planning). Paul a une grande imprimante 3D et déjà du self-hosting (Home Assistant possible).

## Faits établis
- Roomba 696 : Wi-Fi (app iRobot HOME), batterie Li-ion 1800 mAh, modes Clean / Schedule / Spot, pas de cartographie. Pas de Valetudo possible (Roomba verrouillé).
- Série 600 : port série Open Interface (mini-DIN), 115200 bauds, TX Roomba en 5 V. Pin 5 = BRC (réveil / anti-veille profonde). Firmware < 3.8.2 : pas de réveil par BRC sur la base.
- Limite de la spec sur les pins Vpwr : 200 mA en continu, 500 mA en pointe.

## 1. Brosse cassée (à confirmer : brosse latérale ou principale ?)
Prix relevés le 07/11/2026 (stock non garanti) :
- Lot de 3 brosses latérales iRobot ACC250 : 9,84 € (rueducommerce, 500/600/700, le 696 n'est pas cité)
- Brosse latérale iFixit : 8,95 € (page EU), rupture sur la page US
- Module complet iRobot (moteur + brosse) : 27,70 € (ManoMano via guide-piscine)
- Kit 13 pièces annoncé compatible 696 : 24,27 £ (ManoMano UK)
- Attention : un vendeur indique que les brosses à 3 branches ne sont PAS compatibles 650/671/691/696/698. Comparer avec la brosse cassée avant d'acheter.
Modèles 3D (non vérifiés sur 696) :
- Brosse latérale : https://stlfinder.com/model/roomba-side-brush-ok1QVC9f/6325298
- Engrenage moteur de brosse : https://talk.vanhack.ca/t/replacement-roomba-side-brush-gear-3d-print/13678
- Bague d'extrémité de brosse principale : https://www.stlfinder.com/model/main-brush-end-plate-for-roomba-500-600-series-wH0yoAVB/5680495

## 2. Hack : deux voies
A) Sans souder : contrôle local Wi-Fi (BLID + mot de passe via roombapy, app iRobot fermée), puis intégration Home Assistant Roomba ou dorita980/rest980.
B) ESP sur le port série (vrai open source) : voie recommandée = ESPRoomba (ShonP40), https://github.com/ShonP40/ESPRoomba
   - ESP32, ESPHome >= 2025.11.0, Home Assistant "Template Vacuum", MIT, testé séries 600/700/800
   - Date du dernier commit non vérifiée. Lire le README pour la carte, les broches et le câblage.
   - Plan B : ArduRoomba (pkyanam), 3 commits, 696 non cité.
Projets à éviter (obsolètes) : mannkind/ESPHomeRoombaComponent (archivé 2020), fork davidecavestro/brembygit (dépendances périmées), solarkennedy/roomba-bridge-esphome (archivé janv. 2025), crc.id.au (2019).

## Matériel et câblage
- ESP32-C3 SuperMini : 7,95 € à 8,95 € + 4,49 € de port (Fruugo). Pas de prix vérifié pour une carte ESP32 classique.
- Niveaux : TX Roomba (5 V) vers RX ESP (3,3 V) via diviseur 5 kΩ / 10 kΩ.
- Alim : buck converter (Mini360 : entrée 4,75-23 V) vers 5 V ; mesurer le pin 1 au multimètre. Ajouter 470-1000 µF. En test, alimenter l'ESP en USB.
- GPIO vers BRC (pin 5) ; impulsion basse au moins 1 fois par minute pour éviter la veille profonde.
- Mini-DIN : présent sur le dessus du 696, sous la bague décorative, à l'avant gauche (photos du 13/11/2026). Reste à vérifier : version du firmware.
- Impression 3D : boîtier / support ESP (la spec iRobot donne les bossages de vis internes et les cotes).

## Questions ouvertes
1. Quelle brosse est cassée ?
2. Paul a-t-il déjà un ESP32 ou faut-il commander (comparatif avec prix vérifiés) ?
3. Lire le README d'ESPRoomba pour choisir la carte et le câblage.

## Sources
- https://www.galaxus.ch/fr/s2/product/irobot-roomba-696-aspirateur-robot-6351061
- https://anrg.usc.edu/ee579/spring2016/Roomba/iRobot_Roomba_600_Open_Interface_Spec.pdf
- https://cdn.hackaday.io/files/1835247851890816/2021-04-13_iRobot_Roomba_600_Open_Interface_Spec-3.pdf
- https://github.com/ShonP40/ESPRoomba · https://github.com/pkyanam/ArduRoomba
- https://community.home-assistant.io/t/add-wifi-to-an-older-roomba/23282?page=2
- https://www.crc.id.au/hacking-the-roomba-600/ · https://hackaday.io/project/183524-old-roomba-new-tricks
- https://www.rueducommerce.fr/p/m24070756803.html
- https://www.ifixit.com/en-eu/products/irobot-roomba-600-series-brush-and-filter-maintenance-set-ir600set1332
- https://www.guide-piscine.fr/guide-d-achat/robot/irobot-83001-roomba-500-600-700-serie-module-de-brosse-lateral-90214_B
- https://www.fruugo.fr/esp32-c3-supermini-carte-de-developpement-wifi-bluetooth-esp32-mini-carte-de-developpement-esp32-c3-developme/p-335420146
- https://brianlovin.com/hn/38788326 (Valetudo / Roomba)
