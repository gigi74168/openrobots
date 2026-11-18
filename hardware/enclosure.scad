// Boitier Aerobot : ESP32-C3 SuperMini + Mini360 + MPU6050 (GY-521) sur une perfboard.
// OpenSCAD : F5/F6 pour rendre, puis Exporter en STL. Mettre part = "box" puis part = "lid".
// part = "preview" montre le boitier, ses composants et un Roomba 696 en transparence.
//
// Cotes du robot : ~335 mm de diametre x 93 mm de haut (fiches vendeurs Icecat, Epey).
// La place LIBRE sous le capot, a cote du port serie, n'est PAS connue : mesurer, puis ajuster
// inner_* ci-dessous. Imprimer d'abord le gabarit (part = "mock").
// Mise a jour : plaque 48 x 32 (l'ancienne 40 x 30 ne portait pas ESP + MPU + Mini360)
// et plots de plaque decales pour ne plus toucher les plots du couvercle.

part = "preview";      // "box" | "lid" | "mock" | "preview"

inner_l = 56;          // longueur interieure (mm), axe X, la face USB est du cote +X
inner_w = 40;          // largeur interieure (mm), axe Y
inner_h = 18;          // hauteur interieure (mm), a mesurer sous le capot
wall = 1.6;
tol = 0.3;

post_d = 5.5;          // plots de vis du couvercle (4 coins)
screw_d = 2.4;         // M2 (trou d'auto-taraudage)

// perfboard 48 x 32, vissee sur 4 plots
board_l = 48; board_w = 32; board_t = 1.6; board_post_h = 4; board_hole = 2.2;

cable_slot_w = 10; cable_slot_h = 6;   // sortie du cable vers le mini-DIN (cote -X)
usb_w = 10; usb_h = 5;                 // acces USB-C de l'ESP (cote +X)

ox = wall + (inner_l - board_l)/2;     // origine de la plaque dans le boitier
oy = wall + (inner_w - board_w)/2;
zb = wall + board_post_h + board_t;    // dessus de la plaque

// positions des composants sur la plaque (x, y, longueur, largeur, hauteur)
esp   = [24, 12, 22.52, 18, 4.5];      // USB-C du cote +X
mpu   = [ 1, 14, 21,    16, 3  ];
mini  = [ 1,  1, 17,    11, 3.8];
capa  = [22,  1, 12,     8, 8  ];      // condensateur couche a plat (~470 uF 16 V)

module rounded_box(l, w, h, r=2) {
  hull() for (x=[r, l-r], y=[r, w-r]) translate([x, y, 0]) cylinder(r=r, h=h, $fn=24);
}

module box() {
  usb_y = oy + esp[1] + esp[3]/2 - usb_w/2;
  difference() {
    rounded_box(inner_l + 2*wall, inner_w + 2*wall, inner_h + wall);
    translate([wall, wall, wall]) rounded_box(inner_l, inner_w, inner_h + 1, 1);
    // sortie cable (cote -X)
    translate([-1, (inner_w + 2*wall - cable_slot_w)/2, wall + 2]) cube([wall + 2, cable_slot_w, cable_slot_h]);
    // acces USB (cote +X), au niveau de l'ESP
    translate([inner_l + wall - 1, usb_y, zb + 0.5]) cube([wall + 2, usb_w, usb_h]);
  }
  // plots du couvercle (4 coins)
  for (x=[wall + post_d/2, inner_l + wall - post_d/2], y=[wall + post_d/2, inner_w + wall - post_d/2])
    translate([x, y, wall]) difference() {
      cylinder(d=post_d, h=inner_h - 1, $fn=24);
      translate([0, 0, 2]) cylinder(d=screw_d, h=inner_h, $fn=16);
    }
  // plots de la plaque
  for (x=[3, board_l-3], y=[3, board_w-3])
    translate([ox + x, oy + y, wall]) difference() {
      cylinder(d=5, h=board_post_h, $fn=20);
      translate([0, 0, 1]) cylinder(d=board_hole, h=board_post_h, $fn=16);
    }
}

module lid() {
  difference() {
    rounded_box(inner_l + 2*wall, inner_w + 2*wall, wall);
    for (x=[wall + post_d/2, inner_l + wall - post_d/2], y=[wall + post_d/2, inner_w + wall - post_d/2])
      translate([x, y, -1]) cylinder(d=screw_d + 0.8, h=wall + 2, $fn=16);
    // ventilation
    for (i=[0:4]) translate([wall + 12 + i*7, wall + inner_w/2 - 8, -1]) cube([2, 16, wall + 2]);
  }
}

module mock() {  // cadre plat : verifie que ca rentre sous le capot
  difference() {
    rounded_box(inner_l + 2*wall, inner_w + 2*wall, 3);
    translate([wall, wall, -1]) rounded_box(inner_l, inner_w, 5, 1);
  }
}

module comp(c, col) {
  color(col) translate([ox + c[0], oy + c[1], zb]) cube([c[2], c[3], c[4]]);
}

module parts() {
  color("#1b6f3a") translate([ox, oy, wall + board_post_h]) cube([board_l, board_w, board_t]);
  comp(esp, "#222"); comp(mpu, "#2a4fb8"); comp(mini, "#2a4fb8"); comp(capa, "#444");
}

module roomba() {  // Roomba 696 : ~335 x 93 mm, rendu en transparence
  color("#888", 0.25) cylinder(d=335, h=93, $fn=96);
}

if (part == "box") box();
else if (part == "lid") lid();
else if (part == "mock") mock();
else {
  // vue d'ensemble : boitier a l'arriere droit du robot, pose a plat (z = 40 mm, hauteur sous capot a mesurer)
  roomba();
  translate([60, -125, 40]) rotate([0, 0, 45]) {
    color("#e8e8e8", 0.6) box();
    parts();
    color("#d0d0d0", 0.5) translate([0, 0, inner_h + wall]) lid();
  }
}
