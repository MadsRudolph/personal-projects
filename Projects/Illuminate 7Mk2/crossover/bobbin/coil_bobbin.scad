// Air-core crossover coil bobbin, two parts, prints flat without supports.
//
//   part A: bottom flange + core tube + spigot
//   part B: top flange, slides over the spigot onto the core shoulder; glue it
//
// Sizes per coil come from the winding table in ../README.md. Render one coil:
//   openscad -D 'coil="L201"' -o L201_bobbin.stl coil_bobbin.scad

coil = "L201";   // L101 | L102 | L201 | L202

// name, value, turns, core diameter, winding width, expected coil OD (all mm)
COILS = [
    ["L101", "0.20mH",  91, 20, 10, 40],
    ["L102", "0.25mH",  96, 22, 10, 42],
    ["L201", "0.70mH", 141, 28, 12, 52],
    ["L202", "2.0mH",  195, 40, 14, 68],
];
c = COILS[search([coil], COILS)[0]];
CORE_D  = c[3];
WIDTH   = c[4];
FLANGE_D = c[5] + 6;   // 3 mm of flange above the expected winding depth

BORE_D   = 8.4;   // M8 rod through the middle for the drill winder
FLANGE_T = 2.4;
SPIGOT_H = 2.0;   // how far the spigot reaches into part B
SPIGOT_STEP = 1.6;// core shoulder the top flange rests on
FIT      = 0.3;   // diametral clearance, part B over the spigot
SLOT_W   = 1.4;   // start-lead slot for 0.8 mm enamelled wire
TEXT_DEPTH = 0.6;
$fn = 128;

SPIGOT_D = CORE_D - 2 * SPIGOT_STEP;

module part_a() {
    difference() {
        union() {
            cylinder(d = FLANGE_D, h = FLANGE_T);
            cylinder(d = CORE_D, h = FLANGE_T + WIDTH);
            cylinder(d = SPIGOT_D, h = FLANGE_T + WIDTH + SPIGOT_H);
        }
        translate([0, 0, -1]) cylinder(d = BORE_D, h = FLANGE_T + WIDTH + SPIGOT_H + 2);
        // radial slot from the core surface out through the flange: the start
        // lead drops into it so the first layer lies flat
        translate([CORE_D / 2 - 0.5, -SLOT_W / 2, -1])
            cube([FLANGE_D, SLOT_W, FLANGE_T + 2]);
    }
}

module part_b() {
    difference() {
        cylinder(d = FLANGE_D, h = FLANGE_T);
        translate([0, 0, -1]) cylinder(d = SPIGOT_D + FIT, h = FLANGE_T + 2);
        // label on the outward (upper) face
        r_txt = (SPIGOT_D / 2 + FLANGE_D / 2) / 2;
        translate([0, 0, FLANGE_T - TEXT_DEPTH])
            linear_extrude(TEXT_DEPTH + 1)
                for (i = [0 : 1]) rotate(180 * i)
                    translate([0, r_txt]) text(i == 0 ? str(c[0], " ", c[1]) : str(c[2], " t"),
                        size = min(4, (FLANGE_D - SPIGOT_D) / 5), halign = "center", valign = "center",
                        font = "Liberation Sans:style=Bold");
    }
}

part_a();
translate([FLANGE_D + 5, 0, 0]) part_b();
