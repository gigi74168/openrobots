// Boitier Aerobot : ESP32-C3 SuperMini + Mini360 + MPU6050 sur une petite plaque (perfboard).
// OpenSCAD : F6 pour rendre, puis Exporter en STL. Mettre part = "box" puis part = "lid".
// IMPORTANT : les cotes du Roomba 696 ne sont pas connues ici. Mesurer la place disponible sous
// le capot et ajuster inner_* / les bossages avant d'imprimer. Imprimer d'abord un gabarit (part="mock").

part = "box";          // "box" | "lid" | "mock" (cadre plat pour tester l'emprise)

inner_l = 52;          // longueur interieure (mm)
inner_w = 38;          // largeur
inner_h = 16;          // hauteur (sous le capot : a mesurer)
wall = 1.6;
tol = 0.3;

post_d = 6;            // plots de vis du couvercle
screw_d = 2.4;         // M2 (trou d'auto-taraudage)

// perfboard 40 x 30, vissee sur 4 plots
board_l = 40; board_w = 30; board_post_h = 4; board_hole = 2.2;

// ouverture cable (fil vers le mini-DIN) et micro-USB/USB-C de l'ESP
cable_slot_w = 10; cable_slot_h = 6;
usb_w = 10; usb_h = 4;

module rounded_box(l, w, h, r=2) {
  hull() for (x=[r, l-r], y=[r, w-r]) translate([x, y, 0]) cylinder(r=r, h=h, $fn=24);
}

module box() {
  difference() {
    rounded_box(inner_l + 2*wall, inner_w + 2*wall, inner_h + wall);
    translate([wall, wall, wall]) rounded_box(inner_l, inner_w, inner_h + 1, 1);
    // sortie cable (cote arriere)
    translate([-1, (inner_w + 2*wall - cable_slot_w)/2, wall + 2]) cube([wall + 2, cable_slot_w, cable_slot_h]);
    // acces USB (cote avant)
    translate([inner_l + wall - 1, (inner_w + 2*wall - usb_w)/2, wall + board_post_h + 1.5]) cube([wall + 2, usb_w, usb_h]);
  }
  // plots du couvercle (4 coins)
  for (x=[wall + post_d/2, inner_l + wall - post_d/2], y=[wall + post_d/2, inner_w + wall - post_d/2])
    translate([x, y, wall]) difference() {
      cylinder(d=post_d, h=inner_h - 1, $fn=24);
      translate([0, 0, 2]) cylinder(d=screw_d, h=inner_h, $fn=16);
    }
  // plots de la plaque (perfboard)
  ox = wall + (inner_l - board_l)/2;
  oy = wall + (inner_w - board_w)/2;
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
    for (i=[0:4]) translate([wall + 10 + i*7, wall + inner_w/2 - 8, -1]) cube([2, 16, wall + 2]);
  }
}

module mock() {  // cadre plat : verifie que ca rentre sous le capot
  difference() {
    rounded_box(inner_l + 2*wall, inner_w + 2*wall, 3);
    translate([wall, wall, -1]) rounded_box(inner_l, inner_w, 5, 1);
  }
}

if (part == "box") box();
else if (part == "lid") lid();
else mock();
