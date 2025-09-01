# KLayout script to export a .GDS file from a .DEF-formatted design.
#
# Source: The OpenROAD Project.
# https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/master/flow/util/def2stream.py
#
# License: BSD 3-Clause.
#
# Copyright (c) 2018, The Regents of the University of California
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#  list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#  this list of conditions and the following disclaimer in the documentation
#  and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#  contributors may be used to endorse or promote products derived from
#  this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import pya
import os
import sys
import fnmatch


def gds_export(design_name, in_def, in_files, out_file, tech, allow_missing, config_file='',
               seal_file='',
               timestamps=True):
    from klayout_utils import get_write_options  # noqa E402

    # Load def file
    main_layout = pya.Layout()
    main_layout.technology_name = tech.name
    main_layout.read(in_def, tech.load_layout_options)

    # List cells
    def_cells = []
    for def_cell in main_layout.each_cell():
        def_cells.append(def_cell.name)

    def_cells.remove(design_name)
    # Remove vias
    def_cells = sorted([cell for cell in def_cells if not cell.startswith("VIA_")])
    print(f"[INFO] Read in {len(def_cells)} cells from DEF file")
    for cell in def_cells:
        print(f"  [INFO] DEF cell: {cell}")

    if f"{design_name}_DEF_FILL" in def_cells:
        def_cells.remove(f"{design_name}_DEF_FILL")

    # Load in the gds to merge
    print("[INFO] Merging GDS/OAS files...")
    for fil in in_files:
        macro_layout = pya.Layout()
        macro_layout.read(fil)
        print(f"[INFO] Read in {fil}")
        for cell in list(def_cells):
            if macro_layout.has_cell(cell):
                subcell = main_layout.cell(cell)
                print(f"  [INFO] Merging in {cell}")
                subcell.copy_tree(macro_layout.cell(cell))
                def_cells.remove(cell)

    # Copy the top level only to a new layout
    print("[INFO] Copying toplevel cell '{0}'".format(design_name))
    top_only_layout = pya.Layout()
    top_only_layout.dbu = main_layout.dbu
    top = top_only_layout.create_cell(design_name)
    top.copy_tree(main_layout.cell(design_name))

    print("[INFO] Checking for missing GDS/OAS...")
    missing_cell = False
    for check_cell in def_cells:
        missing_cell = True
        allowed_missing = any([fnmatch.fnmatch(check_cell, pattern) for pattern in allow_missing])
        print(f"[{'WARNING' if allowed_missing else 'ERROR'}] LEF Cell '{check_cell}' has no "
              "matching GDS/OAS cell. Cell will be empty")

    if not missing_cell:
        print("[INFO] All LEF cells have matching GDS/OAS cells")

    print("[INFO] Checking for orphan cell in the final layout...")
    for i in top_only_layout.each_cell():
        if i.name != design_name and i.parent_cells() == 0:
            print("[ERROR] Found orphan cell '{0}'".format(i.name))

    if seal_file:
        top_cell = top_only_layout.top_cell()

        print("[INFO] Reading seal GDS/OAS file...")
        print("\t{0}".format(seal_file))
        top_only_layout.read(seal_file)

        for cell in top_only_layout.top_cells():
            if cell != top_cell:
                print("[INFO] Merging '{0}' as child of '{1}'".format(cell.name, top_cell.name))
                top.insert(pya.CellInstArray(cell.cell_index(), pya.Trans()))

    # Write out the GDS
    print("[INFO] Writing out GDS/OAS '{0}'".format(out_file))
    top_only_layout.write(out_file, get_write_options(out_file, timestamps))


def main():
    # SC_ROOT provided by CLI
    sys.path.append(SC_KLAYOUT_ROOT)  # noqa: F821
    sys.path.append(SC_TOOLS_ROOT)  # noqa: F821

    from klayout_utils import (
        technology,
        get_streams,
        save_technology,
        get_schema,
        generate_metrics
    )
    from klayout_show import show

    schema = get_schema(manifest='sc_manifest.json')

    # Extract info from manifest
    sc_step = schema.get('arg', 'step')
    sc_index = schema.get('arg', 'index')
    sc_stream = schema.get('tool', 'klayout', 'task', 'export', 'var', 'stream',
                           step=sc_step, index=sc_index)

    design_name = schema.get('option', 'design')
    fileset = schema.get("option", "fileset")[0]
    design = schema.get("library", design_name, "fileset", fileset, "topmodule")

    in_def = None
    for ext in ('def.gz', 'def'):
        in_def = os.path.join('inputs', f'{design}.{ext}')
        if os.path.exists(in_def):
            break
        in_def = None
    if not in_def:
        in_def = schema.get('input', 'layout', 'def', step=sc_step, index=sc_index)[0]

    out_file = os.path.join('outputs', f'{design}.{sc_stream}')

    in_files = []
    libs = schema.get("asic", "asiclib")
    for lib in libs:
        libobj = schema.get("library", lib, field="schema")
        for s in get_streams(schema):
            for fileset in libobj.get("asic", "aprfileset"):
                if libobj.valid("fileset", fileset, "file", s):
                    in_files.extend(libobj.get("fileset", fileset, "file", s))
                    break

    allow_missing = []
    for lib in libs:
        if schema.valid('library', lib, 'tool', 'klayout', 'allow_missing_cell'):
            patterns = [pattern for pattern in schema.get('library', lib, 'tool', 'klayout',
                                                          'allow_missing_cell') if pattern]
            allow_missing.extend(patterns)

    sc_timestamps = schema.get('tool', 'klayout', 'task', "export", 'var', 'timestamps',
                               step=sc_step, index=sc_index)
    sc_screenshot = schema.get('tool', 'klayout', 'task', "export", 'var', 'screenshot',
                               step=sc_step, index=sc_index)

    sc_tech = technology(design, schema)

    gds_export(design, in_def, in_files, out_file, sc_tech, allow_missing,
               config_file='', seal_file='', timestamps=sc_timestamps)

    if sc_screenshot:
        show(schema, sc_tech, out_file, f'outputs/{design}.png', screenshot=True)

    # Save tech files
    save_technology(design, sc_tech)

    generate_metrics()


if __name__ == '__main__':
    main()
