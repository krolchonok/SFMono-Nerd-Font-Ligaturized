# ORIGINAL SCRIPT https://pypi.org/project/otf2ttf/

#!/usr/bin/env python3

import argparse
import logging
import os
import sys

from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools import configLogger
from fontTools.misc.cliTools import makeOutputFileName
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable


log = logging.getLogger()

# default approximation error, measured in UPEM
MAX_ERR = 1.0

# default 'post' table format
POST_FORMAT = 2.0

# assuming the input contours' direction is correctly set (counter-clockwise),
# we just flip it to clockwise
REVERSE_DIRECTION = True


def glyphs_to_quadratic(glyphs, max_err=MAX_ERR, reverse_direction=REVERSE_DIRECTION):
    quadGlyphs = {}
    for gname in glyphs.keys():
        glyph = glyphs[gname]
        ttPen = TTGlyphPen(glyphs)
        cu2quPen = Cu2QuPen(ttPen, max_err, reverse_direction=reverse_direction)
        glyph.draw(cu2quPen)
        quadGlyphs[gname] = ttPen.glyph()
    return quadGlyphs


def update_hmtx(ttFont, glyf):
    hmtx = ttFont["hmtx"]
    for glyphName, glyph in glyf.glyphs.items():
        if hasattr(glyph, "xMin"):
            hmtx[glyphName] = (hmtx[glyphName][0], glyph.xMin)


def otf_to_ttf(ttFont, post_format=POST_FORMAT, **kwargs):
    assert ttFont.sfntVersion == "OTTO"
    assert "CFF " in ttFont

    glyphOrder = ttFont.getGlyphOrder()

    ttFont["loca"] = newTable("loca")
    ttFont["glyf"] = glyf = newTable("glyf")
    glyf.glyphOrder = glyphOrder
    glyf.glyphs = glyphs_to_quadratic(ttFont.getGlyphSet(), **kwargs)
    del ttFont["CFF "]
    glyf.compile(ttFont)
    update_hmtx(ttFont, glyf)

    ttFont["maxp"] = maxp = newTable("maxp")
    maxp.tableVersion = 0x00010000
    maxp.maxZones = 1
    maxp.maxTwilightPoints = 0
    maxp.maxStorage = 0
    maxp.maxFunctionDefs = 0
    maxp.maxInstructionDefs = 0
    maxp.maxStackElements = 0
    maxp.maxSizeOfInstructions = 0
    maxp.maxComponentElements = max(
        len(g.components if hasattr(g, "components") else [])
        for g in glyf.glyphs.values()
    )
    maxp.compile(ttFont)

    post = ttFont["post"]
    post.formatType = post_format
    post.extraNames = []
    post.mapping = {}
    post.glyphOrder = glyphOrder
    try:
        post.compile(ttFont)
    except OverflowError:
        post.formatType = 3
        log.warning("Dropping glyph names, they do not fit in 'post' table.")

    ttFont.sfntVersion = "\000\001\000\000"


def main(args=None):
    configLogger(logger=log)
    
    current_directory = os.getcwd()
    otf_files_in_directory = []
    
    for f in os.listdir(current_directory):
            full_path = os.path.join(current_directory, f)
            if os.path.isfile(full_path):
                if f.lower().endswith('.otf'):
                    otf_files_in_directory.append(f)
                    
    for path in otf_files_in_directory:
        font = TTFont(path)
        otf_to_ttf(
            font
        )
        font.save(path.replace(".otf", ".ttf"))


if __name__ == "__main__":
    sys.exit(main())
