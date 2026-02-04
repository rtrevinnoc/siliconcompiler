from siliconcompiler import Task

import glob, os.path, shutil, subprocess, os

class SimulateTask(Task):
    def __init__(self):
        super().__init__()

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

        for lib, fileset in self.project.get_filesets():
            for value in lib.get_file(fileset=fileset, filetype="meminit"):
                shutil.copy2(value, "inputs/")

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