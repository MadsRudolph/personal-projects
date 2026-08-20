"""The PCB editor button: pick a blank, drop it into the open board.

Exists because pcbnew's copy/paste obeys the Selection Filter and so silently
skips the locked lattice, and File > Append Board drags the blank's own outline
along with it. Neither is what you want. This clips the blank to the board you
already have and locks what it places.
"""
import os

import pcbnew
import wx

from viablank import geometry as g
from viablank import merge as m

TITLE = "Import via blank"


class ViaBlankAction(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Import via blank..."
        self.category = "Modify PCB"
        self.description = ("Drop an SRM-20 via blank's plated hole pattern and "
                            "F.Cu ground plane into this board.")
        self.show_toolbar_button = True
        icon = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon):
            self.icon_file_name = icon

    def Run(self):
        board = pcbnew.GetBoard()
        names = list(g.MODES)
        choices = [g.describe(n) for n in names]

        dlg = wx.SingleChoiceDialog(
            None,
            "Which blank?\n\nOnly holes that fall entirely inside this board's\n"
            "outline are placed, so a board milled out of a larger blank\n"
            "keeps the clusters and drops the border fence.\n\n"
            "Every choice draws the build-space rectangles on User.Drawings.",
            TITLE, choices)
        try:
            dlg.SetSelection(0)
            if dlg.ShowModal() != wx.ID_OK:
                return
            pattern = names[dlg.GetSelection()]
        finally:
            dlg.Destroy()

        try:
            stats = m.merge(board, pattern)
        except m.OutlineProblem as exc:
            wx.MessageBox(str(exc), TITLE, wx.OK | wx.ICON_WARNING)
            return
        except Exception as exc:                       # noqa: BLE001
            import traceback
            wx.MessageBox("Import failed:\n\n%s\n\n%s"
                          % (exc, traceback.format_exc()),
                          TITLE, wx.OK | wx.ICON_ERROR)
            return

        pcbnew.Refresh()
        wx.MessageBox(m.summary(pattern, stats) +
                      "\n\nNothing is saved yet - Ctrl+Z undoes it.",
                      TITLE, wx.OK | wx.ICON_INFORMATION)
