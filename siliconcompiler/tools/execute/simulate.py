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
                original_name = os.path.basename(value)
                name_part, extension = os.path.splitext(original_name)
                
                clean_name = name_part.rpartition('_')[0]
                final_filename = f"{clean_name}{extension}" if clean_name else original_name
                
                dest_path = os.path.join("inputs/", final_filename)
                shutil.copy2(value, dest_path)

        process = subprocess.Popen(
            [f"./{exe_file}"],
            cwd=exe_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        for line in process.stdout:
            print(line, end="")

        process.wait()

        for report_file in glob.glob("inputs/reports/*"):
            shutil.move(report_file, "reports/")

        return process.returncode