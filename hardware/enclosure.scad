// Boitier Aerobot pose SUR le dessus du Roomba 696 ("Dimitri"), au-dessus du port serie.
// Contenu : ESP32-C3 SuperMini, MPU6050 (GY-521), Mini360, condensateur, resistances, NPN, sur une perfboard 50 x 40.
// La fiche mini-DIN (coudee) descend dans le port par un trou dans le fond du boitier.
//
// OpenSCAD : choisir part, F6, puis Fichier > Exporter > STL.
//   "mock"    gabarit plat de 1,2 mm a poser sur le robot : verifie l'emplacement et le trou du port
//   "box"     boitier, fond plat sur le plateau
//   "lid"     couvercle, deja retourne : face gravee sur le plateau
//   "feet"    4 cales (2 hautes, 2 basses) a coller sous le boitier
//   "preview" vue d'ensemble sur un Roomba simplifie
// Les pieces "mock", "box", "lid" et "feet" sortent deja orientees et centrees pour l'impression.
//
// Repere : origine = centre du robot, vu de dessus. Y = avant du robot (tourelle IR).
// Les angles sont comptes depuis l'avant, positifs vers la GAUCHE du robot.
//
// A MESURER sur Dimitri avant d'imprimer : port_r, port_a, feet_in_h, feet_out_h.
// Cotes connues : robot ~335 x 93 mm (fiches vendeurs Icecat, Epey).
// Position du port estimee sur docs/photos/port-serie-position.jpg (+-5 mm, +-5 deg).

part = "preview";            // "mock" | "box" | "lid" | "feet" | "preview"

// ---------- Robot ----------
port_r = 134;                // centre du robot -> centre du port (mm)
port_a = 39;                 // angle depuis l'avant, vers la gauche (deg)
face_z = 87.2;               // dessus du capot central (vue preview uniquement)
track_z = 84;                // dessus de la piste ou se trouve le port (preview)

// ---------- Boitier ----------
a_c = port_a;                // axe du boitier : centre sur le port
r_in = 56;                   // bord interieur (cote bouton CLEAN)
r_out = 144;                 // bord exterieur (reste avant le pare-chocs, ~152)
hw = 28;                     // demi-largeur exterieure (largeur totale 56)
corner_r = 4;
wall = 2; floor_t = 2; inner_h = 16; lid_t = 2; lip_h = 2; tol = 0.3;

feet_in_h = 2;               // cales posees sur le capot central (A MESURER)
feet_out_h = 5.2;            // cales posees dans la piste du port, plus basse (A MESURER)
feet_d = 10;
plug_hole_d = 20;            // passage de la fiche mini-DIN coudee

post_d = 6; screw_d = 2.4; screw_head_d = 4.2;     // vis M2 x 10 auto-taraudeuses

// ---------- Perfboard et composants (coordonnees sur la plaque, en mm) ----------
board_l = 50; board_w = 40; board_t = 1.6; board_post_h = 5; board_hole = 2.2;
plate_v0 = 62;               // distance du bord de plaque au centre du robot, le long de l'axe
header_h = 2.5;
esp  = [0.5,  6, 22.52, 18, 1  ];   // x, y, longueur, largeur, epaisseur ; USB-C cote x = 0
mpu  = [27,   6, 21,    16, 1.6];
mini = [ 6,  27, 17,    11, 1  ];
capa = [27,  26, 12,     8     ];   // condensateur couche (470-1000 uF 16 V)
usb_w = 11; usb_h = 5;
z_board = floor_t + board_post_h;             // dessous de la plaque
z_top = z_board + board_t;                    // dessus de la plaque
z_usb = z_top + header_h - 0.5;

function pt(r, a) = [-r*sin(a), r*cos(a)];

module outline2d(w=0) rotate([0, 0, a_c]) intersection() {
  difference() { circle(r=r_out - w, $fn=360); circle(r=r_in + w, $fn=360); }
  translate([-(hw - w), 0]) square([2*(hw - w), r_out + 1]);
}
module outline(w=0) { c = max(corner_r - w, 0.5); offset(r=c) offset(delta=-c) outline2d(w); }
module at_box() rotate([0, 0, a_c]) children();
module at_plate() at_box() translate([-board_l/2, plate_v0, 0]) children();

// plots du couvercle : 2 cote CLEAN, 2 cote exterieur
function post_uv() = [for (r = [r_in + wall + post_d/2 + 0.5, r_out - wall - post_d/2 - 0.5], s = [-1, 1])
  let(u = s*(hw - wall - post_d/2 - 0.5)) [u, sqrt(r*r - u*u)]];

module box() {
  difference() {
    linear_extrude(floor_t + inner_h) outline();
    translate([0, 0, floor_t]) linear_extrude(inner_h + 1) outline(wall);
    // passage de la fiche, au-dessus du port
    translate(concat(pt(port_r, port_a), [-1])) cylinder(d=plug_hole_d, h=floor_t + 2, $fn=64);
    // USB-C de l'ESP, dans la paroi laterale cote arriere
    at_box() translate([-hw - 1, plate_v0 + esp[1] + esp[3]/2 - usb_w/2, z_usb]) cube([wall + 2.5, usb_w, usb_h]);
  }
  // plots du couvercle
  at_box() for (p = post_uv()) translate([p[0], p[1], floor_t - 0.01]) difference() {
    cylinder(d=post_d, h=inner_h - lip_h - 0.5, $fn=24);
    translate([0, 0, 2]) cylinder(d=screw_d, h=inner_h, $fn=16);
  }
  // plots de la perfboard
  at_plate() for (x = [2.5, board_l - 2.5], y = [2.5, board_w - 2.5]) translate([x, y, floor_t - 0.01]) difference() {
    cylinder(d=5, h=board_post_h, $fn=20);
    translate([0, 0, 1]) cylinder(d=board_hole, h=board_post_h, $fn=16);
  }
  // serre-cable : 2 plots, un collier passe entre eux
  at_box() for (s = [-1, 1]) translate([s*5, 112, floor_t - 0.01]) cylinder(d=4, h=6, $fn=16);
  // reperes de collage des cales (cercles graves 0,4 mm sous le fond)
}

// emplacement des cales sous le fond (repere du boitier) : [u, v, hauteur]
function feet_uvh() = [[-19, 70, feet_in_h], [19, 70, feet_in_h], [-19, 128, feet_out_h], [19, 128, feet_out_h]];

module box_printable() difference() {
  box();
  at_box() for (f = feet_uvh()) translate([f[0], f[1], -0.01]) difference() {
    cylinder(d=feet_d + 0.8, h=0.4, $fn=48); cylinder(d=feet_d, h=1, $fn=48);
  }
}

// cales, collees au fond avec de l'adhesif epais type VHB (ou de la colle cyano)
module feet() for (i = [0:3]) translate([(i - 1.5)*(feet_d + 4), 0, 0]) cylinder(d=feet_d, h=feet_uvh()[i][2], $fn=48);

module feet_placed() at_box() for (f = feet_uvh()) translate([f[0], f[1], -f[2]]) cylinder(d=feet_d, h=f[2] + 0.01, $fn=48);

module lid() {
  difference() {
    union() {
      linear_extrude(lid_t) outline();
      translate([0, 0, -lip_h]) linear_extrude(lip_h + 0.01) difference() { outline(wall + tol); outline(wall + tol + 1.2); }
    }
    // vis M2, fraisees
    at_box() for (p = post_uv()) {
      translate([p[0], p[1], -lip_h - 1]) cylinder(d=screw_d + 0.6, h=lid_t + lip_h + 2, $fn=16);
      translate([p[0], p[1], lid_t - 1.2]) cylinder(d1=screw_d + 0.6, d2=screw_head_d, h=1.21, $fn=24);
    }
    // aeration au-dessus du Mini360
    at_plate() for (y = [mini[1] + 1.5 : 3 : mini[1] + mini[3]]) translate([mini[0] + 1, y - 0.8, -lip_h - 1]) cube([15, 1.6, lid_t + lip_h + 2]);
    // LED et boutons BOOT / RESET de l'ESP (positions approximatives : verifier sur ta carte)
    at_plate() {
      translate([12, 10, -1]) cylinder(d=3, h=lid_t + 2, $fn=16);
      for (y = [8, 22]) translate([5, y, -1]) cylinder(d=2.5, h=lid_t + 2, $fn=16);
    }
    // gravure
    at_box() translate([0, 122, lid_t - 0.6]) linear_extrude(1)
      text("DIMITRI", size=7, halign="center", valign="center", font="Liberation Sans:style=Bold");
  }
}

module mock() {  // gabarit 1,2 mm : cadre + anneau autour du port
  linear_extrude(1.2) {
    difference() { outline(); outline(3); }
    translate(pt(port_r, port_a)) difference() { circle(d=plug_hole_d + 6, $fn=64); circle(d=plug_hole_d, $fn=64); }
    at_box() translate([-1.5, port_r + plug_hole_d/2 + 2]) square([3, r_out - port_r - plug_hole_d/2 - 3]);
  }
}

module parts() {
  at_plate() {
    color("#1b6f3a") translate([0, 0, z_board]) cube([board_l, board_w, board_t]);
    color("#1a1d2b") translate([esp[0], esp[1], z_top + header_h]) cube([esp[2], esp[3], esp[4]]);
    color("#b8bcc0") translate([esp[0] - 0.5, esp[1] + esp[3]/2 - 4.5, z_top + header_h + 1]) cube([7.4, 9, 3.2]);
    color("#2350a8") translate([mpu[0], mpu[1], z_top + header_h]) cube([mpu[2], mpu[3], mpu[4]]);
    color("#1f6b45") translate([mini[0], mini[1], z_top + 0.8]) cube([mini[2], mini[3], mini[4]]);
    color("#333") translate([capa[0], capa[1] + capa[3]/2, z_top + capa[3]/2]) rotate([0, 90, 0]) cylinder(d=capa[3], h=capa[2], $fn=24);
  }
}

module robot() {
  color("#24282c") cylinder(r=152, h=80, $fn=128);
  color("#2e3338") difference() { cylinder(r=167.5, h=83, $fn=128); translate([0, 0, -1]) cylinder(r=152.5, h=90, $fn=128); }
  color("#3a3f45") translate([0, 0, 80]) difference() { cylinder(r=152, h=track_z - 80, $fn=128); translate([0, 0, -1]) cylinder(r=119, h=10, $fn=128); }
  color("#5d6268") translate([0, 0, 80]) difference() { cylinder(r=119, h=7.5, $fn=128); translate([0, 0, -1]) cylinder(r=97, h=10, $fn=128); }
  color("#0e1522") translate([0, 0, 80]) cylinder(r=97, h=face_z - 80, $fn=128);
  color("#c0c4c8") translate([0, 0, face_z]) cylinder(r=16, h=2.5, $fn=48);
  color("#111") translate(concat(pt(150, 0), [track_z])) cylinder(r=11.5, h=9, $fn=48);         // tourelle IR (avant)
  color("#999") translate(concat(pt(port_r, port_a), [track_z - 0.4])) difference() {
    cylinder(r=9, h=0.6, $fn=48); translate([0, 0, -1]) cylinder(r=4.8, h=3, $fn=32);
  }
}

// orientation d'impression : axe du boitier sur Y, centre a l'origine
module print_pose() translate([0, -(r_in + r_out)/2, 0]) rotate([0, 0, -a_c]) children();

if (part == "box") print_pose() box_printable();
else if (part == "lid") translate([0, 0, lid_t]) rotate([180, 0, 0]) print_pose() lid();
else if (part == "mock") print_pose() mock();
else if (part == "feet") feet();
else {
  robot();
  translate([0, 0, face_z + feet_in_h]) {
    color("#c9cdd1") box();
    color("#9a8f7a") feet_placed();
    parts();
    color("#c9cdd1", 0.5) translate([0, 0, floor_t + inner_h + 25]) lid();
  }
}
