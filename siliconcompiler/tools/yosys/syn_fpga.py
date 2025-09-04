import json

from siliconcompiler import sc_open

from siliconcompiler.tools.yosys import YosysTask


class FPGASynthesis(YosysTask):
    def __init__(self):
        super().__init__()

        self.add_parameter(
            "use_slang",
            "bool",
            "true/false, if true will attempt to use the slang frontend",
            False)
        self.add_parameter(
            "synth_opt_mode",
            "<none,delay,area>",
            "blah",
            "none")
        self.add_parameter(
            "synth_insert_buffers",
            "bool",
            "blah",
            True)

    def task(self):
        return "syn_fpga"

    def setup(self):
        super().setup()

        self.set_script("sc_synth_fpga.tcl")

        if f"{self.design_topmodule}.v" in self.get_files_from_input_nodes():
            self.set("input", f"{self.design_topmodule}.v")
        elif f"{self.design_topmodule}.sv" in self.get_files_from_input_nodes():
            self.set("input", f"{self.design_topmodule}.sv")
        else:
            filekeys = self.get_fileset_file_keys("systemverilog") + \
                self.get_fileset_file_keys("verilog")
            if not filekeys:
                self.add_required_key("library", self.design_name, "fileset",
                                      self.schema().get("option", "fileset")[0], "file", "verilog")
            else:
                for lib, key in filekeys:
                    self.add_required_key(lib, *key)
                # TODO, mark required for define and params

        self.add_output_file(ext="vg")
        self.add_output_file(ext="netlist.json")
        self.add_output_file(ext="blif")

    def post_process(self):
        super().post_process()

        self._synthesis_post_process()

        fpga = self.schema().get("fpga", "device")

        with sc_open("reports/stat.json") as f:
            metrics = json.load(f)
            if "design" in metrics:
                metrics = metrics["design"]
            else:
                return

            if "num_cells_by_type" in metrics:
                metrics = metrics["num_cells_by_type"]
            else:
                return

            dff_cells = []
            if self.schema().valid("library", fpga, "tool", "yosys", "registers"):
                dff_cells = self.schema().get("library", fpga, "tool", "yosys", "registers")
            brams_cells = []
            if self.schema().valid("library", fpga, "tool", "yosys", "brams"):
                brams_cells = self.schema().get("library", fpga, "tool", "yosys", "brams")
            dsps_cells = []
            if self.schema().valid("library", fpga, "tool", "yosys", "dsps"):
                dsps_cells = self.schema().get("library", fpga, "tool", "yosys", "dsps")

            data = {
                "registers": 0,
                "luts": 0,
                "dsps": 0,
                "brams": 0
            }
            for cell, count in metrics.items():
                if cell == "$lut":
                    data["luts"] += count
                elif cell in dff_cells:
                    data["registers"] += count
                elif cell in dsps_cells:
                    data["dsps"] += count
                elif cell in brams_cells:
                    data["brams"] += count

            for metric, value in data.items():
                self.record_metric(metric, value, source_file="reports/stat.json")
