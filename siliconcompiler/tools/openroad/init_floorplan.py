from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADPPLLayersParameter


class InitFloorplanTask(APRTask, OpenROADSTAParameter, OpenROADPPLLayersParameter):
    '''
    Perform floorplanning and initial pin placements
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("ifp_snap_strategy", "<none,site,grid>",
                           "Snapping strategy to use when placing macros.", defvalue="site")
        self.add_parameter("remove_synth_buffers", "bool",
                           "remove buffers inserted by synthesis", defvalue=True)
        self.add_parameter("remove_dead_logic", "bool",
                           "remove logic which does not drive a primary output", defvalue=True)

        self.add_parameter("padring", "[file]", "script to generate a padring using ICeWall in "
                           "OpenROAD")

    def task(self):
        return "init_floorplan"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_init_floorplan.tcl")

        # if chip.valid('input', 'asic', 'floorplan') and \
        #    chip.get('input', 'asic', 'floorplan', step=step, index=index):
        #     chip.add('tool', tool, 'task', task, 'require',
        #              ",".join(['input', 'asic', 'floorplan']),
        #              step=step, index=index)

        # if f'{design}.vg' in input_provides(chip, step, index):
        #     chip.add('tool', tool, 'task', task, 'input', f'{design}.vg',
        #              step=step, index=index)
        # else:
        #     chip.add('tool', tool, 'task', task, 'require', 'input,netlist,verilog',
        #              step=step, index=index)
        if f"{self.design_topmodule}.vg" in self.get_files_from_input_nodes():
            self.add_input_file(ext="vg")
        else:
            pass

        self._set_reports([
            'check_setup',
            'setup',
            'unconstrained',
            'power'
        ])

        self.add_required_tool_key("var", "ifp_snap_strategy")
        self.add_required_tool_key("var", "remove_synth_buffers")
        self.add_required_tool_key("var", "remove_dead_logic")

        if self.get("var", "padring"):
            self.add_required_tool_key("var", "padring")

    def add_openroad_padring(self, file: str):
        self.add("var", "padring", file)


# def setup(chip):

#     # Generic apr tool setup.
#     apr_setup(chip)

#     # Task setup
#     design = chip.top()
#     step = chip.get('arg', 'step')
#     index = chip.get('arg', 'index')
#     tool, task = get_tool_task(chip, step, index)

#     chip.set('tool', tool, 'task', task, 'script', 'apr/sc_init_floorplan.tcl',
#              step=step, index=index)

#     # Setup task IO
#     set_pnr_inputs(chip)
#     set_pnr_outputs(chip)
#     add_common_file(chip, 'sc_pin_constraint', 'tcl/sc_pin_constraints.tcl')

#     # set default values for task
#     define_ord_params(chip)
#     define_sta_params(chip)
#     define_sdc_params(chip)
#     define_pad_params(chip)
#     define_ppl_params(chip)
#     define_tiecell_params(chip)

#     set_tool_task_var(chip, param_key='ifp_snap_strategy',
#                       default_value='site',
#                       schelp='Snapping strategy to use when placing macros. '
#                              'Allowed values: none, site, manufacturing_grid')

#     set_tool_task_var(chip, param_key='remove_synth_buffers',
#                       default_value=True,
#                       schelp='remove buffers inserted by synthesis')

#     set_tool_task_var(chip, param_key='remove_dead_logic',
#                       default_value=True,
#                       schelp='remove logic which does not drive a primary output')

#     # Handle additional input files
#     if chip.valid('input', 'asic', 'floorplan') and \
#        chip.get('input', 'asic', 'floorplan', step=step, index=index):
#         chip.add('tool', tool, 'task', task, 'require',
#                  ",".join(['input', 'asic', 'floorplan']),
#                  step=step, index=index)

#     if f'{design}.vg' in input_provides(chip, step, index):
#         chip.add('tool', tool, 'task', task, 'input', f'{design}.vg',
#                  step=step, index=index)
#     else:
#         chip.add('tool', tool, 'task', task, 'require', 'input,netlist,verilog',
#                  step=step, index=index)

#     set_reports(chip, [
#         'check_setup',
#         'setup',
#         'unconstrained',
#         'power'
#     ])

#     mainlib = get_mainlib(chip)

#     # Setup required
#     for component in chip.getkeys('constraint', 'component'):
#         for key in chip.getkeys('constraint', 'component', component):
#             if chip.get('constraint', 'component', component, key, step=step, index=index):
#                 chip.add('tool', tool, 'task', task, 'require',
#                          ','.join(['constraint', 'component', component, key]),
#                          step=step, index=index)
#     for pin in chip.getkeys('constraint', 'pin'):
#         for key in chip.getkeys('constraint', 'pin', pin):
#             if chip.get('constraint', 'pin', pin, key, step=step, index=index):
#                 chip.add('tool', tool, 'task', task, 'require',
#                          ','.join(['constraint', 'pin', pin, key]),
#                          step=step, index=index)
#     for ifp in ('aspectratio', 'density', 'corearea', 'coremargin', 'outline'):
#         if chip.get('constraint', ifp, step=step, index=index):
#             chip.add('tool', tool, 'task', task, 'require',
#                      ','.join(['constraint', ifp]),
#                      step=step, index=index)
#     if chip.valid('library', mainlib, 'option', 'file', 'openroad_tracks'):
#         chip.add('tool', tool, 'task', task, 'require',
#                  ','.join(['library', mainlib, 'option', 'file', 'openroad_tracks']),
#                  step=step, index=index)


# def pre_process(chip):
#     build_pex_corners(chip)
#     define_ord_files(chip)


# def post_process(chip):
#     extract_metrics(chip)
