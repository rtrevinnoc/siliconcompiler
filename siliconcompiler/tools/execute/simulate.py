from siliconcompiler import Task

import glob, os.path, shutil, subprocess, os

class SimulateTask(Task):
    def __init__(self):
        super().__init__()

        self.add_parameter("additional_files", "[file]", "additional initialization files")

    def tool(self):
        return "execute"

    def task(self):
        return "simulate"

    def setup(self):
        super().setup()

        files = list(self.get_files_from_input_nodes().keys())

        self.add_input_file(files)

    def run(self):
        executables = glob.glob("inputs/*.vexe")
        if not executables:
            raise FileNotFoundError("No .vexe simulation executable found in 'inputs/'.")
        exe_path = executables[0]
        exe_dir = os.path.dirname(exe_path)
        exe_file = os.path.basename(exe_path)

        for src in self.get("var", "additional_files") or []:
            if not os.path.exists(src):
                raise FileNotFoundError(f"Additional file not found: {src}")
            shutil.copy2(src, "inputs/")

        result = subprocess.run(
            [f"./{exe_file}"], 
            cwd=exe_dir, 
            capture_output=True, 
            text=True
        )

        print(result.stdout)
        print(result.stderr)

        for report_file in glob.glob("inputs/reports/*"):
            shutil.move(report_file, "reports/")

        return result.returncode