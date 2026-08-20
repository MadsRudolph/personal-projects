"""Merge the via blank into a board. The one place that touches pcbnew.

Footprints are built here rather than loaded from a .pretty, so the plugin has
no library-path dependency: nothing to add to fp-lib-table, nothing to break
when the project moves. They come out ``board_only``, so Update PCB from
Schematic leaves them alone, and locked, so KiCad-Autoplace never moves them.
"""
import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

from . import geometry as g


def make_footprint(board, name, pts):
    """A footprint whose pads are `pts`, all on one node.

    Every pad shares number "1", so KiCad treats the whole footprint as one
    electrical node: assigning GND to any pad assigns it to all of them.
    """
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("via_blank", name))
    fp.SetReference("VB**")
    fp.SetValue(name)
    fp.SetLibDescription(
        "SRM-20 via blank: %d plated %.1f mm holes on GND, tied to the F.Cu "
        "plane." % (len(pts), g.HOLE))
    fp.SetKeywords("via blank stitching ground plane SRM-20 mill")
    fp.SetAttributes(pcbnew.FP_THROUGH_HOLE
                     | pcbnew.FP_BOARD_ONLY
                     | pcbnew.FP_EXCLUDE_FROM_BOM
                     | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    fp.Reference().SetLayer(pcbnew.F_Fab)
    fp.Value().SetLayer(pcbnew.F_Fab)
    for x, y in pts:
        pad = pcbnew.PAD(fp)
        pad.SetNumber("1")
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(VECTOR2I(FromMM(g.PAD), FromMM(g.PAD)))
        pad.SetDrillSize(VECTOR2I(FromMM(g.HOLE), FromMM(g.HOLE)))
        pad.SetLayerSet(pad.PTHMask())
        # Solid to the plane, never a thermal relief -- see millable(). Set here
        # too so the footprint carries the right behaviour into any board, not
        # only one whose zones this module has normalised.
        pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        pad.SetFPRelativePosition(VECTOR2I(FromMM(x), FromMM(y)))
        fp.Add(pad)
    return fp


def _inside(pts, cx, cy, box, clearance):
    """True if every pad of an instance placed at (cx, cy) clears the outline."""
    r = g.PAD / 2 + clearance
    return all(box.GetLeft() <= FromMM(cx + x - r) and
               FromMM(cx + x + r) <= box.GetRight() and
               box.GetTop() <= FromMM(cy + y - r) and
               FromMM(cy + y + r) <= box.GetBottom()
               for x, y in pts)


def _gnd(board):
    net = board.FindNet("GND")
    if net is None:
        net = pcbnew.NETINFO_ITEM(board, "GND")
        board.Add(net)
    return net


ENVELOPE_GROUP = "via_blank_envelope"


def _add_envelope(board, cx, cy):
    """Reference rectangles on User.Drawings: how far the board could grow.

    Deliberately *not* Edge.Cuts -- these are advisory, and putting them on the
    board outline would make them the placement boundary and land them in the
    fab output. Deliberately not a footprint either: a footprint spanning the
    machine envelope is exactly the giant bounding box that makes
    KiCad-Autoplace's push_apart shove every component into the border. Plain
    graphics in a named group, which the placement engine never looks at and
    a re-import can find and remove.
    """
    grp = pcbnew.PCB_GROUP(board)
    grp.SetName(ENVELOPE_GROUP)
    board.Add(grp)
    for w, h, width, label in (
            (g.BLANK_W, g.BLANK_H, 0.2,
             "via blank  %g x %g" % (g.BLANK_W, g.BLANK_H)),
            (g.SRM20_X, g.SRM20_Y, 0.1,
             "SRM-20 stroke  %g x %g" % (g.SRM20_X, g.SRM20_Y))):
        rect = pcbnew.PCB_SHAPE(board)
        rect.SetShape(pcbnew.SHAPE_T_RECT)
        rect.SetStart(VECTOR2I(FromMM(cx - w / 2), FromMM(cy - h / 2)))
        rect.SetEnd(VECTOR2I(FromMM(cx + w / 2), FromMM(cy + h / 2)))
        rect.SetLayer(pcbnew.Dwgs_User)
        rect.SetWidth(FromMM(width))
        rect.SetFilled(False)
        board.Add(rect)
        grp.AddItem(rect)

        txt = pcbnew.PCB_TEXT(board)
        txt.SetText(label)
        txt.SetPosition(VECTOR2I(FromMM(cx - w / 2 + 1.5),
                                 FromMM(cy - h / 2 - 1.8)))
        txt.SetLayer(pcbnew.Dwgs_User)
        txt.SetTextSize(VECTOR2I(FromMM(2.0), FromMM(2.0)))
        txt.SetTextThickness(FromMM(0.3))
        txt.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        board.Add(txt)
        grp.AddItem(txt)
    return 2


def _drop_envelope(board):
    """Remove a previous envelope so re-importing replaces it."""
    n = 0
    for grp in list(board.Groups()):
        if grp.GetName() != ENVELOPE_GROUP:
            continue
        items = list(grp.GetItems())
        grp.RemoveAll()               # detach before deleting, or the group
        for it in items:              # holds dangling pointers
            board.Delete(it)
            n += 1
        board.Delete(grp)
    return n


def _drop_previous(board):
    """Remove an earlier merge, so re-running replaces rather than duplicates.

    ``Delete`` and not ``Remove``: on KiCad 10 ``Remove`` only detaches the
    footprint and leaves SWIG holding an owned pointer with no destructor, which
    aborts the subsequent save. ``Delete`` removes and destroys.
    """
    gone = [fp for fp in board.Footprints()
            if fp.GetFPIDAsString().startswith("via_blank:")]
    for fp in gone:
        board.Delete(fp)
    return len(gone)


def millable(zone):
    """Force a GND zone to numbers the mill can actually cut.

    Two things. Every gap the fill leaves is a cut the 0.8 mm endmill has to
    make, so the zone's own clearances have to clear the tool -- KiCad's 0.5 mm
    defaults would draw rings the mill cannot enter, and each one comes off the
    machine as a short.

    And **no thermal relief**: solid pad connection everywhere. On the real
    blank the copper around a hole *is* the plane -- one fabricated sheet -- so
    a relief ring is a fiction of modelling holes as pads, and the F.Cu gerber
    that drives the top-side milling would cut every one of them. Four spokes
    and a ring per hole is a lot of cutting for a tie that wants to be solid and
    low-inductance anyway.

    (Thermal relief was *not* breaking connectivity -- the template filled and
    read 0 unconnected with it on. The thermal numbers stay set as a floor in
    case a pad inherits thermal from somewhere this does not reach, since a
    relief narrower than the endmill comes off the machine as a short.)
    """
    zone.SetLocalClearance(FromMM(g.CLEARANCE))
    zone.SetMinThickness(FromMM(g.ENDMILL))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    zone.SetThermalReliefGap(FromMM(g.CLEARANCE))
    zone.SetThermalReliefSpokeWidth(FromMM(g.TRACK))


def _add_plane(board, net, box):
    """GND plane on F.Cu; KiCad clips the fill to the real Edge.Cuts outline.

    Existing GND pours are normalised rather than left as they are: a stale one
    from an earlier import would otherwise keep its thermal settings and quietly
    disconnect the clusters.
    """
    existing = None
    for i in range(board.GetAreaCount()):
        z = board.GetArea(i)
        if z.GetNetname() == "GND":
            millable(z)
            if z.IsOnLayer(pcbnew.F_Cu):
                existing = z
    if existing is not None:
        return False
    zone = pcbnew.ZONE(board)
    zone.SetLayer(pcbnew.F_Cu)
    zone.SetNet(net)
    zone.SetIsFilled(False)
    millable(zone)
    # Hold the plane off the routed edge, as a fab would. Measured from the
    # bounding box, which spans the Edge.Cuts *stroke* -- drawing to the box
    # itself puts copper slightly outside the outline centreline.
    e = FromMM(g.EDGE_PULLBACK + g.OUTLINE_SLOP)
    o = zone.Outline()
    o.NewOutline()
    for x, y in ((box.GetLeft() + e, box.GetTop() + e),
                 (box.GetRight() - e, box.GetTop() + e),
                 (box.GetRight() - e, box.GetBottom() - e),
                 (box.GetLeft() + e, box.GetBottom() - e)):
        o.Append(x, y)
    board.Add(zone)
    return True


class OutlineProblem(Exception):
    """The target board's Edge.Cuts cannot take the blank."""


def _anchor(board):
    """Where to centre the envelope, and what it was centred on.

    The outline if there is one. Otherwise the parts -- a board with no
    Edge.Cuts yet is exactly when "how big can this get?" is worth asking, so
    that case has to work rather than error.
    """
    box = board.GetBoardEdgesBoundingBox()
    if box.GetWidth() > 0:
        c = box.GetCenter()
        return ToMM(c.x), ToMM(c.y), box, "the board outline"
    fps = list(board.Footprints())
    if fps:
        bb = fps[0].GetBoundingBox(False)
        for f in fps[1:]:
            bb.Merge(f.GetBoundingBox(False))
        c = bb.GetCenter()
        return ToMM(c.x), ToMM(c.y), None, "the placed parts (no outline yet)"
    return 150.0, 100.0, None, "the sheet (empty board)"


def outlines_only(board):
    """Draw the reference envelope and nothing else.

    No size guard here: a board already larger than the blank is precisely the
    one whose owner needs to see by how much.
    """
    cx, cy, box, anchored = _anchor(board)
    _drop_envelope(board)
    _add_envelope(board, cx, cy)
    stats = {"mode": g.OUTLINES, "anchored": anchored}
    if box is not None:
        w = ToMM(box.GetWidth()) - g.OUTLINE_SLOP
        h = ToMM(box.GetHeight()) - g.OUTLINE_SLOP
        stats["outline"] = (w, h)
        stats["room"] = (g.BLANK_W - w, g.BLANK_H - h)
    return stats


def merge(board, pattern):
    """Drop the blank's holes and ground plane into `board`. Returns stats.

    Only instances that fall entirely inside the outline are placed. That one
    rule does the right thing at both sizes: on the full blank you get the
    border fence too, and on a smaller board milled out of a blank the fence --
    which lives at the blank's edge and would be cut away -- drops out on its
    own, leaving the clusters.
    """
    if pattern == g.OUTLINES:
        return outlines_only(board)

    box = board.GetBoardEdgesBoundingBox()
    if box.GetWidth() == 0:
        raise OutlineProblem(
            "This board has no Edge.Cuts outline.\n\n"
            "Draw one first - it is both the placement boundary and the "
            "region the blank is clipped to.\n\n"
            "Or pick 'outlines', which only draws the reference rectangles "
            "and does not need an outline.")
    # GetBoardEdgesBoundingBox spans the Edge.Cuts *stroke*, so a 190 mm board
    # drawn with a 0.1 mm line measures 190.1. Allow for any sane line width
    # rather than rejecting a board that is exactly blank-sized.
    w = ToMM(box.GetWidth()) - g.OUTLINE_SLOP
    h = ToMM(box.GetHeight()) - g.OUTLINE_SLOP
    if w > g.BLANK_W or h > g.BLANK_H:
        raise OutlineProblem(
            "Outline is %.1f x %.1f mm, but the blank is only %.0f x %.0f mm.\n\n"
            "Shrink the outline, or mill this one on bare stock."
            % (w, h, g.BLANK_W, g.BLANK_H))

    cx, cy = ToMM(box.GetCenter().x), ToMM(box.GetCenter().y)
    stats = {"outline": (w, h), "replaced": _drop_previous(board),
             "placed": 0, "holes": 0, "skipped": {}}
    _drop_envelope(board)
    net = _gnd(board)
    _add_envelope(board, cx, cy)
    stats["room"] = (g.BLANK_W - w, g.BLANK_H - h)

    for name, (pts, at) in sorted(g.runs(pattern).items()):
        for x, y in at:
            if not _inside(pts, cx + x, cy + y, box, g.CLEARANCE):
                stats["skipped"][name] = stats["skipped"].get(name, 0) + 1
                continue
            fp = make_footprint(board, "ViaBlank_" + name, pts)
            stats["placed"] += 1
            stats["holes"] += len(pts)
            fp.SetReference("VB%d" % stats["placed"])
            fp.SetPosition(VECTOR2I(FromMM(cx + x), FromMM(cy + y)))
            for pad in fp.Pads():
                pad.SetNet(net)
            fp.SetLocked(True)
            board.Add(fp)

    stats["plane"] = _add_plane(board, net, box)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    return stats


def _room_line(stats):
    """How much bigger the board could get -- or by how much it already missed."""
    if "room" not in stats:
        return None
    rw, rh = stats["room"]
    if rw < 0 or rh < 0:
        over = ([("%.0f mm too wide" % -rw)] if rw < 0 else []) + \
               ([("%.0f mm too tall" % -rh)] if rh < 0 else [])
        return ("Too big for the blank: %s. This outline will not fit %g x %g "
                "stock - see User.Drawings."
                % (" and ".join(over), g.BLANK_W, g.BLANK_H))
    return ("Room to grow: %.0f mm wider, %.0f mm taller before the outline "
            "hits the blank edge (drawn on User.Drawings)" % (rw, rh))


def summary(pattern, stats):
    envelope = ("Envelope: via blank %g x %g and SRM-20 stroke %g x %g, on "
                "User.Drawings" % (g.BLANK_W, g.BLANK_H, g.SRM20_X, g.SRM20_Y))

    if stats.get("mode") == g.OUTLINES:
        lines = ["Imported: outlines only - no holes, no ground plane",
                 "Centred on: %s" % stats["anchored"], envelope]
        if "outline" in stats:
            w, h = stats["outline"]
            lines.insert(2, "Outline: %.0f x %.0f mm" % (w, h))
            lines.append(_room_line(stats))
        return "\n".join(lines)

    w, h = stats["outline"]
    lines = ["Blank: %s" % pattern,
             "Outline: %.0f x %.0f mm" % (w, h),
             "Placed: %d footprints, %d plated holes on GND"
             % (stats["placed"], stats["holes"])]
    if stats["replaced"]:
        lines.append("Replaced: %d footprints from a previous import"
                     % stats["replaced"])
    for name, c in sorted(stats["skipped"].items()):
        lines.append("Skipped: %d x %s (outside the outline)" % (c, name))
    lines.append("F.Cu plane: %s"
                 % ("added" if stats["plane"] else "already present, normalised"))
    lines.append(_room_line(stats))
    return "\n".join(lines)
