// =====================================================================
//  EDGE-OUT GUITAR NECK CRADLE  —  parametric, print-at-home
//  Hangs ONE guitar EDGE-OUT (turned sideways) from a round pole, so
//  several instruments pack side-by-side in the climate vault.
//  Print one cradle per instrument.  Units: millimetres.
//
//  HOW IT WORKS: the neck drops into the pocket; the headstock (wider
//  than the neck) rests on the two front/back ledges; the pocket walls
//  hold the guitar turned 90° so its thin edge faces the door.
//
//  >>> Test-print one, hang a weight heavier than your guitar, and
//      confirm fit/strength BEFORE trusting your instruments. <<<
// =====================================================================

/* ----------------- ADJUST THESE ----------------- */
pole_dia    = 25.4;  // your hanging pole / rod diameter (1" = 25.4)
neck_width  = 58;    // WIDEST fretboard you'll hang  + ~6 mm clearance
neck_thick  = 32;    // THICKEST neck (+ felt + clearance)
pocket_h    = 30;    // how deep the neck sits in the cradle
ledge       = 14;    // front/back rest the headstock sits on (per side)
wall        = 9;     // side-wall thickness (along the pole)
flare       = 8;     // funnel at the mouth (eases loading)  (keep < wall)
clip_wall   = 7;     // wall thickness around the pole
clip_width  = 34;    // ring length along the pole
setscrew    = 4.2;   // M4 set-screw hole to lock spacing (0 = none)
fillet      = 3;
$fn         = 80;

/* ----------------- derived ----------------- */
ox = neck_thick + 2*wall;    // footprint along the pole (sets spacing)
oy = neck_width + 2*ledge;   // footprint front-to-back
ring_od = pole_dia + 2*clip_wall;
ztop = 26;                   // ring height above the cradle mouth

module rbox(s, r){
  hull() for(i=[-1,1], j=[-1,1], k=[-1,1])
    translate([i*(s[0]/2-r), j*(s[1]/2-r), k*(s[2]/2-r)]) sphere(r=r);
}

// pole ring — slides onto the pole (pole axis = X)
module ring(){
  difference(){
    rotate([0,90,0]) cylinder(h=clip_width, d=ring_od, center=true);
    rotate([0,90,0]) cylinder(h=clip_width+2, d=pole_dia+0.6, center=true);
    if (setscrew>0)
      translate([0,0,ring_od/2]) cylinder(h=ring_od+1, d=setscrew, center=true);
  }
}

// neck cradle — open-top pocket, headstock rests on the Y-ledges
module cradle(){
  difference(){
    translate([0,0,-(pocket_h+wall)/2]) rbox([ox, oy, pocket_h+wall], fillet);
    // the neck pocket
    translate([0,0,-(pocket_h)/2 + 0.5]) rbox([neck_thick, neck_width, pocket_h+1], fillet);
    // funnel flare at the mouth
    hull(){
      rbox([neck_thick, neck_width, 0.2], fillet);
      translate([0,0,flare]) rbox([neck_thick+2*flare, neck_width+2*flare, 0.2], fillet);
    }
  }
}

module hanger(){
  translate([0,0,ztop]) ring();
  // stem blends the ring into the cradle (main load path)
  hull(){
    translate([0,0,ztop]) rotate([0,90,0]) cylinder(h=clip_width*0.55, d=16, center=true);
    translate([0,0,-2]) rbox([ox, 22, 10], fillet);
  }
  cradle();
}

hanger();

// =====================================================================
//  PRINT / USE NOTES
//  • Material: PETG, ASA, or nylon (tough, heat- & creep-resistant).
//    Avoid PLA for a permanent load — it creeps/sags over time & in warmth.
//  • Strength: >=4 perimeters/walls, >=40-50% infill. Orient the print so
//    layer lines do NOT run straight across the stem (print it lying on a
//    side/back so the load crosses many layers).
//  • Padding: line the pocket + ledges with adhesive felt or thin silicone
//    for grip and finish protection. Use instrument-safe, low-odor padding
//    and let any adhesive fully cure/air out before it goes in the vault.
//  • Fit per instrument: measure each neck's WIDTH & THICKNESS just below
//    the headstock; set neck_width/neck_thick to the largest, or print
//    individual sizes. Confirm the headstock clearly overhangs the pocket.
//  • Best for guitars whose headstock is clearly wider than the neck.
//    In-line headstocks (some Fender-style) overhang one side only — add a
//    safety strap, or use a different holder for those.
//  • The OUD (round bowl + angled pegbox) is NOT a fit — give it a
//    dedicated cradle/sling.
// =====================================================================
