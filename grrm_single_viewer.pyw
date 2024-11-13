import os
import sys
import os.path
from asyncio import current_task
from decimal import Decimal
from typing import Optional, List

import wx
import wx.grid
from wx import xrc

APP_DIR = (os.path.dirname(os.path.abspath(__file__)))
sys.path.append(APP_DIR)

from grrmsv.grrm_single_job import GRRMSingleJob
from grrmsv.opt import OPTJob
from grrmsv.freq import FREQJob, ThermalData
from grrmsv.irc import IRCPath, IRCJob
from grrmsv.lup import LUPPath, LUPJob
from grrmsv.afirpath import AFIRPath
from grrmsv import molview
from grrmsv import utils

import config


__VERSION__ = '1.3 on 2024/11/13'


class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self.window = window # drop target

    def OnDropFiles(self, x, y, file_list: List[str]): # when drop event
        self.window.load_file(file_list[0])
        return True


class TextViewFrame(wx.Frame):
    def __init__(self, parent, title, text, job = None):
        wx.Frame.__init__(self, parent, -1, title)

        self.job = job
        self.SetSize(config.TEXT_VIEW_FRAME_SIZE)
        self.init_frame()

        self.text_ctrl_main.SetValue(text)

    def init_frame(self):

        # set controls
        panel = wx.Panel(self, wx.ID_ANY)
        layout = wx.BoxSizer(wx.VERTICAL)
        self.text_ctrl_main = wx.TextCtrl(panel, wx.ID_ANY, style=wx.TE_READONLY | wx.TE_MULTILINE )
        font = wx.Font(12, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.text_ctrl_main.SetFont(font)
        layout.Add(self.text_ctrl_main, 1, wx.EXPAND | wx.ALL, border=3)
        panel.SetSizerAndFit(layout)

        # set menu and event
        file_menu = wx.Menu()
        save = file_menu.Append(11, '&Save\tCtrl+S')
        self.Bind(wx.EVT_MENU, self.on_menu_save, save)
        # set menu bar
        menu_bar = wx.MenuBar()
        menu_bar.Append(file_menu, '&File')
        self.SetMenuBar(menu_bar)

    def save_xyz(self, file):
        self.job : GRRMSingleJob
        atom_coordinates_string = self.text_ctrl_main.GetValue().rstrip() + '\n'
        num_atom = len(atom_coordinates_string.strip().split('\n'))
        with open(file, 'w', encoding='utf-8', newline='\n') as f:
            f.write(str(num_atom) + '\n')
            f.write('\n')
            f.write(atom_coordinates_string)

    def save_gjf(self, file):
        self.job: GRRMSingleJob
        self.job: GRRMSingleJob
        atom_coordinates_string = self.text_ctrl_main.GetValue().rstrip() + '\n'

        # method line
        if self.job.method is None:
            method_line = '# SP B3LYP/dev2SVP\n'
        else:
            method_line = utils.method_convert_grrm_to_gjf(self.job.method)

        # charge/multi line
        if self.job.charge is None:
            charge = 0
        else:
            charge = self.job.charge
        if self.job.multi is None:
            multi = 1
        else:
            multi = self.job.multi

        # options
        if self.job.method_options is None:
            options = []
        else:
            options = utils.options_convert_grrm_to_gjf(self.job.method_options)

        with open(file, 'w', encoding='utf-8', newline='\n') as f:
            f.write(method_line)
            f.write('\n')
            f.write('title\n')
            f.write('\n')
            f.write(str(charge) + ' ' + str(multi) + '\n')
            f.write(atom_coordinates_string)
            f.write('\n')
            for line in options:
                f.write(line)
            f.write('\n')

    def save_grrm_com(self, file):
        self.job: GRRMSingleJob
        atom_coordinates_string = self.text_ctrl_main.GetValue().rstrip() + '\n'

        # method line
        if self.job.method is None:
            method_line = '#MIN/B3LYP/dev2SVP\n'
        else:
            method_line = self.job.method.rstrip() + '\n'

        # charge/multi line
        if self.job.charge is None:
            charge = 0
        else:
            charge = self.job.charge
        if self.job.multi is None:
            multi = 1
        else:
            multi = self.job.multi

        # options
        if self.job.method_options is None:
            options = []
        else:
            options = self.job.method_options

        with open(file, 'w', encoding='utf-8', newline='\n') as f:
            f.write(method_line)
            f.write('\n')
            f.write(str(charge) + ' ' + str(multi) + '\n')
            f.write(atom_coordinates_string)
            f.write('Options\n')
            for line in options:
                f.write(line)

    def on_menu_save(self, event):

        try:
            current_dir = os.path.dirname(self.job.log_file)
        except:
            current_dir = None

        # get save file name
        dialog = wx.FileDialog(None, 'save file name',
                               wildcard='GRRM Job (*.com)|*.com|Gaussian job (*.gjf)|*.gjf|xyz file (*.xyz)|*.xyz|All files (*.*)|*.*',
                               style=wx.FD_SAVE)
        if current_dir is not None:
            dialog.SetDirectory(current_dir)
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
            dialog.Destroy()
        else:
            dialog.Destroy()
            return

        # overwrite confirmation
        if os.path.exists(file):
            msgbox = wx.MessageDialog(None, 'File already exists. Overwrite?', 'Overwrite?', style=wx.YES_NO)
            overwrite = msgbox.ShowModal()
            if overwrite == wx.ID_YES:
                msgbox.Destroy()
            else:
                msgbox.Destroy()
                return

        # save
        ext = os.path.splitext(file)[1]

        if ext.lower() in ['.gjf', 'gjc']:
            self.save_gjf(file)
        elif ext.lower() == '.com':
            self.save_grrm_com(file)
        else:
            self.save_xyz(file)


class GRRMSingleViewerApp(wx.App):

    def OnInit(self):
        self.job: Optional[GRRMSingleJob] = None
        self.current_general: Optional[GRRMSingleJob] = None
        self.current_opt: Optional[OPTJob] = None
        self.current_freq: Optional[FREQJob]  = None
        self.current_thermal_data: Optional[ThermalData] = None
        self.current_irc: Optional[IRCJob] = None
        self.current_irc_path: Optional[IRCPath] = None
        self.current_lup: Optional[LUPJob] = None
        self.current_lup_path: Optional[LUPPath] = None
        self.current_afirpath: Optional[AFIRPath] = None
        self.res: xrc.XmlResource = xrc.XmlResource('./wxgui.xrc')
        self.init_frame()
        return True

    def init_frame(self):
        self.frame = self.res.LoadFrame(None, 'frame')
        self.frame.SetSize(config.WINDOW_SIZE)

        # get control objects from xrc and initialization and set event handler
        self.get_controls_from_xrc()
        self.init_controls()
        self.set_event()
        self.set_menu()

        # set drop target
        dt = MyFileDropTarget(self)
        self.frame.SetDropTarget(dt)

        # show
        if not config.DEBUG:
            self.set_detail_panel('none')

        # redirect
        sys.stdout = self.text_ctrl_log
        sys.stderr = self.text_ctrl_log

        self.frame.Show()

    # For initialization
    def get_controls_from_xrc(self):
        self.tree_ctrl_jobs: wx.TreeCtrl = xrc.XRCCTRL(self.frame, 'tree_ctrl_jobs')
        self.text_ctrl_log: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_log')

        # notebook and panels
        self.notebook_detail: wx.Notebook = xrc.XRCCTRL(self.frame, 'notebook_detail')
        self.notebook_detail_panel_general: wx.Panel = xrc.XRCCTRL(self.frame, 'notebook_detail_panel_general')
        self.notebook_detail_panel_opt: wx.Panel = xrc.XRCCTRL(self.frame, 'notebook_detail_panel_opt')
        self.notebook_detail_panel_freq: wx.Panel = xrc.XRCCTRL(self.frame, 'notebook_detail_panel_freq')
        self.notebook_detail_panel_irc: wx.Panel = xrc.XRCCTRL(self.frame, 'notebook_detail_panel_irc')
        self.notebook_detail_panel_lup: wx.Panel = xrc.XRCCTRL(self.frame, 'notebook_detail_panel_lup')
        self.notebook_detail_panel_afirpath: wx.Panel = xrc.XRCCTRL(self.frame, 'notebook_detail_panel_afirpath')

        # controls for general
        self.text_ctrl_general_link_options: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_general_link_options')
        self.text_ctrl_general_method: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_general_method')
        self.text_ctrl_general_options: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_general_options')
        self.text_ctrl_general_charge: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_general_charge')
        self.text_ctrl_general_multi: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_general_multi')
        self.text_ctrl_general_normal_termination: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_general_normal_termination')

        # controls for opt
        self.button_opt_first: wx.Button = xrc.XRCCTRL(self.frame, 'button_opt_first')
        self.button_opt_prev: wx.Button = xrc.XRCCTRL(self.frame, 'button_opt_prev')
        self.text_ctrl_opt_step: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_opt_step')
        self.text_ctrl_opt_max_step: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_opt_max_step')
        self.button_opt_next: wx.Button = xrc.XRCCTRL(self.frame, 'button_opt_next')
        self.button_opt_last: wx.Button = xrc.XRCCTRL(self.frame, 'button_opt_last')
        self.grid_opt: wx.grid.Grid = xrc.XRCCTRL(self.frame, 'grid_opt')
        self.button_opt_view_current: wx.Button = xrc.XRCCTRL(self.frame, 'button_opt_view_current')
        self.button_opt_text_current: wx.Button = xrc.XRCCTRL(self.frame, 'button_opt_text_current')
        self.button_opt_plot: wx.Button = xrc.XRCCTRL(self.frame, 'button_opt_plot')
        self.button_opt_trajectory: wx.Button = xrc.XRCCTRL(self.frame, 'button_opt_trajectory')
        self.text_ctrl_opt_status: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_opt_status')
        self.text_ctrl_opt_optimized_energy: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_opt_optimized_energy')
        self.text_ctrl_opt_optimized_energy1: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_opt_optimized_energy1')
        self.text_ctrl_opt_optimized_energy2: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_opt_optimized_energy2')
        self.text_ctrl_opt_optimized_spin2: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_opt_optimized_spin2')
        self.button_opt_view_optimized: wx.Button = xrc.XRCCTRL(self.frame, 'button_opt_view_optimized')
        self.button_opt_text_optimized: wx.Button = xrc.XRCCTRL(self.frame, 'button_opt_text_optimized')
        self.text_ctrl_truncated_path_start: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_truncated_path_start')
        self.text_ctrl_truncated_path_end: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_truncated_path_end')
        self.button_save_truncated_path: wx.Button = xrc.XRCCTRL(self.frame, 'button_save_truncated_path')
        self.checkbox_save_truncated_path_include_frozen_atom: wx.CheckBox = xrc.XRCCTRL(self.frame, 'checkbox_save_truncated_path_include_frozen_atom')

        # controls for freq
        self.button_freq_view: wx.Button = xrc.XRCCTRL(self.frame, 'button_freq_view')
        self.text_ctrl_freq_step: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_freq_step')
        self.text_ctrl_freq_shift: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_freq_shift')
        self.list_box_freq: wx.ListBox = xrc.XRCCTRL(self.frame, 'list_box_freq')
        self.combo_box_thermal_data: wx.ComboBox = xrc.XRCCTRL(self.frame, 'combo_box_thermal_data')
        self.grid_thermal_data: wx.grid.Grid = xrc.XRCCTRL(self.frame, 'grid_thermal_data')

        # controls for IRC
        self.button_irc_plot_profile: wx.Button = xrc.XRCCTRL(self.frame, 'button_irc_plot_profile')
        self.button_irc_plot_profile_reversed: wx.Button = xrc.XRCCTRL(self.frame, 'button_irc_plot_profile_reversed')
        self.button_irc_full_trajectory_f2b: wx.Button = xrc.XRCCTRL(self.frame, 'button_irc_full_trajectory_f2b')
        self.button_irc_full_trajectory_b2f: wx.Button = xrc.XRCCTRL(self.frame, 'button_irc_full_trajectory_b2f')
        self.combo_box_irc_direction: wx.ComboBox = xrc.XRCCTRL(self.frame, 'combo_box_irc_direction')
        self.text_ctrl_irc_mode: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_irc_mode')
        self.button_irc_first: wx.Button = xrc.XRCCTRL(self.frame, 'button_irc_first')
        self.button_irc_prev: wx.Button = xrc.XRCCTRL(self.frame, 'button_irc_prev')
        self.text_ctrl_irc_step: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_irc_step')
        self.text_ctrl_irc_max_step: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_irc_max_step')
        self.button_irc_next: wx.Button = xrc.XRCCTRL(self.frame, 'button_irc_next')
        self.button_irc_last: wx.Button = xrc.XRCCTRL(self.frame, 'button_irc_last')
        self.grid_irc: wx.grid.Grid = xrc.XRCCTRL(self.frame, 'grid_irc')
        self.button_irc_view_current: wx.Button = xrc.XRCCTRL(self.frame, 'button_irc_view_current')
        self.button_irc_text_current: wx.Button = xrc.XRCCTRL(self.frame, 'button_irc_text_current')
        self.button_irc_plot: wx.Button = xrc.XRCCTRL(self.frame, 'button_irc_plot')
        self.button_irc_trajectory: wx.Button = xrc.XRCCTRL(self.frame, 'button_irc_trajectory')

        # controls for LUP
        self.combo_box_lup_path: wx.ComboBox = xrc.XRCCTRL(self.frame, 'combo_box_lup_path')
        self.button_lup_plot_step: wx.Button = xrc.XRCCTRL(self.frame, 'button_lup_plot_step')
        self.button_lup_plot_length: wx.Button = xrc.XRCCTRL(self.frame, 'button_lup_plot_length')
        self.button_lup_data: wx.Button = xrc.XRCCTRL(self.frame, 'button_lup_data')
        self.button_lup_trajectory: wx.Button = xrc.XRCCTRL(self.frame, 'button_lup_trajectory')
        self.text_ctrl_lup_node: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_lup_node')
        self.text_ctrl_lup_max_node: wx.TextCtrl = xrc.XRCCTRL(self.frame, 'text_ctrl_lup_max_node')
        self.button_lup_node_view: wx.Button = xrc.XRCCTRL(self.frame, 'button_lup_node_view')
        self.button_lup_node_text: wx.Button = xrc.XRCCTRL(self.frame, 'button_lup_node_text')
        self.list_box_lup_structures: wx.ListBox = xrc.XRCCTRL(self.frame, 'list_box_lup_structures')
        self.button_lup_structure_view: wx.Button = xrc.XRCCTRL(self.frame, 'button_lup_structure_view')
        self.button_lup_structure_text: wx.Button = xrc.XRCCTRL(self.frame, 'button_lup_structure_text')

        # controls for AFIR Path
        self.button_afirpath_plot_step: wx.Button = xrc.XRCCTRL(self.frame, 'button_afirpath_plot_step')
        self.button_afirpath_plot_length: wx.Button = xrc.XRCCTRL(self.frame, 'button_afirpath_plot_length')
        self.button_afirpath_data: wx.Button = xrc.XRCCTRL(self.frame, 'button_afirpath_data')
        self.list_box_afirpath_structures: wx.ListBox = xrc.XRCCTRL(self.frame, 'list_box_afirpath_structures')
        self.button_afirpath_structure_view: wx.Button = xrc.XRCCTRL(self.frame, 'button_afirpath_structure_view')
        self.button_afirpath_structure_text: wx.Button = xrc.XRCCTRL(self.frame, 'button_afirpath_structure_text')

    def init_controls(self):
        self.init_general()
        self.init_opt()
        self.init_freq()
        self.init_irc()
        self.init_lup()
        self.init_afirpath()

    def init_general(self):
        pass

    def init_opt(self):
        # init table
        self.grid_opt.CreateGrid(11, 3)
        self.grid_opt.SetRowLabelValue(0, 'Energy')
        self.grid_opt.SetRowLabelValue(1, 'E1')
        self.grid_opt.SetRowLabelValue(2, 'E2')
        self.grid_opt.SetRowLabelValue(3, 'Spin**2')
        self.grid_opt.SetRowLabelValue(4, 'Lambda')
        self.grid_opt.SetRowLabelValue(5, 'Trust Radii')
        self.grid_opt.SetRowLabelValue(6, 'Step Radii')
        self.grid_opt.SetRowLabelValue(7, 'Max Force')
        self.grid_opt.SetRowLabelValue(8, 'RMS Force')
        self.grid_opt.SetRowLabelValue(9, 'Max Displacement')
        self.grid_opt.SetRowLabelValue(10, 'RMS Displacement')
        self.grid_opt.SetColLabelValue(0, 'Value')
        self.grid_opt.SetColLabelValue(1, 'Threshold')
        self.grid_opt.SetColLabelValue(2, 'Converged?')
        self.grid_opt.SetColSize(0, config.OPT_GRID_VALUE_WIDTH)
        self.grid_opt.SetColSize(1, config.OPT_GRID_THRESHOLD_WIDTH)
        self.grid_opt.SetColSize(2, config.OPT_GRID_CONVERGED_WIDTH)
        self.grid_opt.SetRowLabelSize(config.OPT_GRID_LABEL_WIDTH)
        self.grid_opt.SetRowLabelAlignment(wx.ALIGN_LEFT, wx.ALIGN_CENTER)
        for n in range(11):
            self.grid_opt.SetCellAlignment(n, 0, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
            self.grid_opt.SetCellAlignment(n, 1, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
            self.grid_opt.SetCellAlignment(n, 2, wx.ALIGN_CENTER, wx.ALIGN_CENTER)
            self.grid_opt.DisableRowResize(n)
        for n in range(3):
            self.grid_opt.DisableColResize(n)
        self.grid_opt.EnableEditing(False)

    def init_freq(self):

        # freq settings
        self.text_ctrl_freq_step.SetValue(str(config.FREQ_VIEW_DEFAULT_STEP))
        self.text_ctrl_freq_shift.SetValue(str(config.FREQ_VIEW_DEFAULT_SHIFT))

        # init thermal data table
        self.grid_thermal_data.CreateGrid(16, 1)
        self.grid_thermal_data.HideColLabels()
        self.grid_thermal_data.SetRowLabelValue(0, 'Temp. (K)')
        self.grid_thermal_data.SetRowLabelValue(1, 'Press. (atm)')
        self.grid_thermal_data.SetRowLabelValue(2, 'E(el) (au)')
        self.grid_thermal_data.SetRowLabelValue(3, 'ZPVE (au)')
        self.grid_thermal_data.SetRowLabelValue(4, 'Enthalpie(0K) (au)')
        self.grid_thermal_data.SetRowLabelValue(5, 'E(tr) (au)')
        self.grid_thermal_data.SetRowLabelValue(6, 'E(rot) (au)')
        self.grid_thermal_data.SetRowLabelValue(7, 'E(vib) (au)')
        self.grid_thermal_data.SetRowLabelValue(8, 'H-E(el) (au)')
        self.grid_thermal_data.SetRowLabelValue(9, 'Enthalpie (au)')
        self.grid_thermal_data.SetRowLabelValue(10, 'S(el) (au)')
        self.grid_thermal_data.SetRowLabelValue(11, 'S(tr) (au)')
        self.grid_thermal_data.SetRowLabelValue(12, 'S(rot) (au)')
        self.grid_thermal_data.SetRowLabelValue(13, 'S(vib) (au)')
        self.grid_thermal_data.SetRowLabelValue(14, 'G-E(el) (au)')
        self.grid_thermal_data.SetRowLabelValue(15, 'G (au)')
        self.grid_thermal_data.SetRowLabelSize(config.THERMAL_DATA_GRID_LABEL_WIDTH)
        self.grid_thermal_data.SetColSize(0, config.THERMAL_DATA_GRID_COLUMN_WIDTH)
        self.grid_thermal_data.SetRowLabelAlignment(wx.ALIGN_LEFT, wx.ALIGN_CENTER)
        for n in range(16):
            self.grid_thermal_data.SetCellAlignment(n, 0, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
            self.grid_thermal_data.DisableRowResize(n)
        self.grid_thermal_data.DisableColResize(0)
        self.grid_thermal_data.EnableEditing(False)

    def init_irc(self):

        # init table
        self.grid_irc.CreateGrid(2, 1)
        self.grid_irc.HideColLabels()
        self.grid_irc.SetRowLabelValue(0, 'Energy')
        self.grid_irc.SetRowLabelValue(1, 'Spin**2')
        self.grid_irc.SetColSize(0, config.IRC_GRID_VALUE_WIDTH)
        self.grid_irc.SetRowLabelSize(config.IRC_GRID_LABEL_WIDTH)
        self.grid_irc.SetRowLabelAlignment(wx.ALIGN_LEFT, wx.ALIGN_CENTER)
        for n in range(2):
            self.grid_irc.SetCellAlignment(n, 0, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
            self.grid_irc.DisableRowResize(n)
        for n in range(1):
            self.grid_irc.DisableColResize(n)
        self.grid_irc.EnableEditing(False)

    def init_afirpath(self):
        pass

    def init_lup(self):
        pass

    def set_event(self):

        self.frame.Bind(wx.EVT_CLOSE, self.on_exit)

        # Job Tree
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_activated_tree_ctrl_jobs, self.tree_ctrl_jobs)

        # OPT
        self.text_ctrl_opt_step.Bind(wx.EVT_TEXT_ENTER, self.on_enter_text_ctrl_opt_step)
        self.button_opt_first.Bind(wx.EVT_BUTTON, self.on_button_opt_first)
        self.button_opt_prev.Bind(wx.EVT_BUTTON, self.on_button_opt_prev)
        self.button_opt_next.Bind(wx.EVT_BUTTON, self.on_button_opt_next)
        self.button_opt_last.Bind(wx.EVT_BUTTON, self.on_button_opt_last)
        self.button_opt_plot.Bind(wx.EVT_BUTTON, self.on_button_opt_plot)
        self.button_opt_trajectory.Bind(wx.EVT_BUTTON, self.on_button_opt_trajectory)
        self.button_opt_view_current.Bind(wx.EVT_BUTTON, self.on_button_opt_view_current)
        self.button_opt_text_current.Bind(wx.EVT_BUTTON, self.on_button_opt_text_current)
        self.button_opt_view_optimized.Bind(wx.EVT_BUTTON, self.on_button_opt_view_optimized)
        self.button_opt_text_optimized.Bind(wx.EVT_BUTTON, self.on_button_opt_text_optimized)
        self.grid_opt.Bind(wx.EVT_KEY_DOWN, self.on_key_down_grid_opt)
        self.button_save_truncated_path.Bind(wx.EVT_BUTTON, self.on_button_save_truncated_path)

        # FREQ
        self.button_freq_view.Bind(wx.EVT_BUTTON, self.on_button_freq_view)
        self.grid_thermal_data.Bind(wx.EVT_KEY_DOWN, self.on_key_down_grid_thermal_data)
        self.combo_box_thermal_data.Bind(wx.EVT_COMBOBOX, self.on_combo_box_thermal_data)

        # IRC
        self.button_irc_plot_profile.Bind(wx.EVT_BUTTON, self.on_button_irc_plot_profile)
        self.button_irc_plot_profile_reversed.Bind(wx.EVT_BUTTON, self.on_button_irc_plot_profile_reversed)
        self.button_irc_full_trajectory_f2b.Bind(wx.EVT_BUTTON, self.on_button_irc_full_trajectory_f2b)
        self.button_irc_full_trajectory_b2f.Bind(wx.EVT_BUTTON, self.on_button_irc_full_trajectory_b2f)
        self.combo_box_irc_direction.Bind(wx.EVT_COMBOBOX, self.on_text_combo_box_irc_direction)
        self.text_ctrl_irc_step.Bind(wx.EVT_TEXT_ENTER, self.on_enter_text_ctrl_irc_step)
        self.button_irc_first.Bind(wx.EVT_BUTTON, self.on_button_irc_first)
        self.button_irc_prev.Bind(wx.EVT_BUTTON, self.on_button_irc_prev)
        self.button_irc_next.Bind(wx.EVT_BUTTON, self.on_button_irc_next)
        self.button_irc_last.Bind(wx.EVT_BUTTON, self.on_button_irc_last)
        self.button_irc_view_current.Bind(wx.EVT_BUTTON, self.on_button_irc_view_current)
        self.button_irc_text_current.Bind(wx.EVT_BUTTON, self.on_button_irc_text_current)
        self.button_irc_plot.Bind(wx.EVT_BUTTON, self.on_button_irc_plot)
        self.button_irc_trajectory.Bind(wx.EVT_BUTTON, self.on_button_irc_trajectory)
        self.grid_irc.Bind(wx.EVT_KEY_DOWN, self.on_key_down_grid_irc)

        # LUP
        self.combo_box_lup_path.Bind(wx.EVT_COMBOBOX, self.on_text_combo_box_lup_path)
        self.button_lup_plot_step.Bind(wx.EVT_BUTTON, self.on_button_lup_plot_step)
        self.button_lup_plot_length.Bind(wx.EVT_BUTTON, self.on_button_button_lup_plot_length)
        self.button_lup_data.Bind(wx.EVT_BUTTON, self.on_button_lup_data)
        self.button_lup_trajectory.Bind(wx.EVT_BUTTON, self.on_button_lup_trajectory)
        self.button_lup_node_view.Bind(wx.EVT_BUTTON, self.on_button_lup_node_view)
        self.button_lup_node_text.Bind(wx.EVT_BUTTON, self.on_button_lup_node_text)
        self.button_lup_structure_view.Bind(wx.EVT_BUTTON, self.on_button_lup_structure_view)
        self.button_lup_structure_text.Bind(wx.EVT_BUTTON, self.on_button_lup_structure_text)

        # AFIR PAth
        self.button_afirpath_plot_step.Bind(wx.EVT_BUTTON, self.on_button_afirpath_plot_step)
        self.button_afirpath_plot_length.Bind(wx.EVT_BUTTON, self.on_button_afirpath_plot_length)
        self.button_afirpath_data.Bind(wx.EVT_BUTTON, self.on_button_afirpath_data)
        self.button_afirpath_structure_view.Bind(wx.EVT_BUTTON, self.on_button_afirpath_structure_view)
        self.button_afirpath_structure_text.Bind(wx.EVT_BUTTON, self.on_button_afirpath_structure_text)

    def set_menu(self):
        # set menu and event
        menu_file = wx.Menu()
        menu_item_open = menu_file.Append(11, '&Open\tCtrl+O')
        self.Bind(wx.EVT_MENU, self.on_menu_open, menu_item_open)
        # set menu bar
        menu_bar = wx.MenuBar()
        menu_bar.Append(menu_file, '&File')
        self.frame.SetMenuBar(menu_bar)

    # For reset (make empty) controls
    def reset_detail_notebook(self):
        self.reset_general()
        self.reset_opt()
        self.reset_freq()
        self.reset_irc()
        self.reset_lup()
        self.reset_afirpath()

    def reset_general(self):
        self.text_ctrl_general_link_options.SetValue('')
        self.text_ctrl_general_method.SetValue('')
        self.text_ctrl_general_options.SetValue('')
        self.text_ctrl_general_charge.SetValue('')
        self.text_ctrl_general_multi.SetValue('')
        self.text_ctrl_general_normal_termination.SetValue('')

    def reset_opt(self):
        self.clear_opt_grid()
        self.text_ctrl_opt_step.SetValue('')
        self.text_ctrl_opt_max_step.SetValue('')
        self.text_ctrl_opt_status.SetValue('')
        self.text_ctrl_opt_optimized_energy.SetValue('')
        self.text_ctrl_opt_optimized_energy1.SetValue('')
        self.text_ctrl_opt_optimized_energy2.SetValue('')
        self.text_ctrl_opt_optimized_spin2.SetValue('')

    def reset_freq(self):
        self.list_box_freq.Clear()
        self.clear_thermal_data_grid()
        self.combo_box_thermal_data.Clear()
        self.text_ctrl_freq_step.SetValue(str(config.FREQ_VIEW_DEFAULT_STEP))
        self.text_ctrl_freq_shift.SetValue(str(config.FREQ_VIEW_DEFAULT_SHIFT))

    def clear_thermal_data_grid(self):
        for i in range(16):
            self.grid_thermal_data.SetCellValue(i, 0, '')

    def reset_irc(self):
        self.combo_box_irc_direction.Clear()
        self.text_ctrl_irc_mode.SetValue('')
        self.clear_irc_grid()

    def reset_lup(self):
        self.combo_box_lup_path.Clear()
        self.text_ctrl_lup_node.SetValue('')
        self.text_ctrl_lup_max_node.SetValue('')
        self.list_box_lup_structures.Clear()

    def reset_afirpath(self):
        self.list_box_afirpath_structures.Clear()

    # For executions ###################################################################################
    def logging(self, message):
        """
        logging
        :param message: tuple、list、str
        :return:
        """
        log_string = (''.join(message)).rstrip()
        self.text_ctrl_log.write(log_string + '\n')
        if config.DEBUG:
            print(log_string)

    def load_job_tree(self):
        self.reset_detail_notebook()
        self.purge_current_jobs()
        self.tree_ctrl_jobs.DeleteAllItems()

        root = self.tree_ctrl_jobs.AddRoot(self.job.log_file)
        self.tree_ctrl_jobs.SetItemData(root, self.job)

        for (i, job) in enumerate(self.job.jobs):
            if job.name is None:
                label = '#.' + str(i+1) + ' : ' + job.type.upper()
            else:
                label = '#.' + str(i+1) + ' : ' + job.type.upper() + ' ({:})'.format(job.name).replace('-', ' ')
            item = self.tree_ctrl_jobs.AppendItem(root, label)
            self.tree_ctrl_jobs.SetItemData(item, job)

            # In case IRC Job, OPT/FREQ Jobs in its Path are also added as the subitems.
            if job.type == 'irc':
                job : IRCJob
                if job.init_freq_job is not None:
                    subitem = self.tree_ctrl_jobs.AppendItem(item, 'initial/FREQ')
                    self.tree_ctrl_jobs.SetItemData(subitem, job.init_freq_job)
                for path in job.paths:
                    if path.opt_job is not None:
                        label = path.direction + '/' + 'OPT'
                        subitem = self.tree_ctrl_jobs.AppendItem(item, label)
                        self.tree_ctrl_jobs.SetItemData(subitem, path.opt_job)
                    if path.freq_job is not None:
                        label = path.direction + '/' + 'FREQ'
                        subitem = self.tree_ctrl_jobs.AppendItem(item, label)
                        self.tree_ctrl_jobs.SetItemData(subitem, path.freq_job)

            # In case LUP Job, subjobs are added as subitems.
            if job.type == 'lup':
                job : LUPJob
                for subjob in job.subjobs:
                    label = subjob.name  + '/' + subjob.type.upper()
                    subitem = self.tree_ctrl_jobs.AppendItem(item, label)
                    self.tree_ctrl_jobs.SetItemData(subitem, subjob)

                    # In case of IRC:
                    if subjob.type == 'irc':
                        subjob : IRCJob
                        if subjob.init_freq_job is not None:
                            subsubitem = self.tree_ctrl_jobs.AppendItem(subitem, 'initial/FREQ')
                            self.tree_ctrl_jobs.SetItemData(subsubitem, subjob.init_freq_job)
                        for path in subjob.paths:
                            if path.opt_job is not None:
                                label = path.direction + '/' + 'OPT'
                                subsubitem = self.tree_ctrl_jobs.AppendItem(subitem, label)
                                self.tree_ctrl_jobs.SetItemData(subsubitem, path.opt_job)
                            if path.freq_job is not None:
                                label = path.direction + '/' + 'FREQ'
                                subsubitem = self.tree_ctrl_jobs.AppendItem(subitem, label)
                                self.tree_ctrl_jobs.SetItemData(subsubitem, path.freq_job)

        if self.job.afirpath is not None:
            item = self.tree_ctrl_jobs.AppendItem(root, 'AFIR Path')
            self.tree_ctrl_jobs.SetItemData(item, self.job.afirpath)

        self.tree_ctrl_jobs.ExpandAll()
        self.current_general = self.job
        self.load_general()

    def load_general(self):
        self.reset_detail_notebook()
        self.set_detail_panel('general')
        job = self.current_general

        if job is None:
            return

        if job.link_options is not None:
            self.text_ctrl_general_link_options.SetValue(''.join(job.link_options))
        if job.method is not None:
            self.text_ctrl_general_method.SetValue(job.method)
        if job.method_options is not None:
            self.text_ctrl_general_options.SetValue(''.join(job.method_options))
        if job.charge is not None:
            self.text_ctrl_general_charge.SetValue(str(job.charge))
        if job.multi is not None:
            self.text_ctrl_general_multi.SetValue(str(job.multi))
        if job.normal_termination:
            self.text_ctrl_general_normal_termination.SetValue('Yes')
        else:
            self.text_ctrl_general_normal_termination.SetValue('No')

    def load_opt(self):
        self.reset_detail_notebook()
        self.set_detail_panel('opt')
        job = self.current_opt

        if job is None:
            return

        self.text_ctrl_opt_step.SetValue(str(len(job.energy_list)-1))
        self.text_ctrl_opt_max_step.SetValue(str(len(job.energy_list)-1))
        self.text_ctrl_opt_status.SetValue(utils.tostring(job.status))
        self.text_ctrl_opt_optimized_energy.SetValue(utils.tostring(job.optimized_energy))
        self.text_ctrl_opt_optimized_energy1.SetValue(utils.tostring(job.optimized_energy1))
        self.text_ctrl_opt_optimized_energy2.SetValue(utils.tostring(job.optimized_energy2))
        self.text_ctrl_opt_optimized_spin2.SetValue(utils.tostring(job.optimized_spin2))
        self.load_opt_grid()

    def load_opt_grid(self):
        step = int(self.text_ctrl_opt_step.GetValue())
        job = self.current_opt
        self.grid_opt.SetCellValue(0, 0, utils.tostring(job.energy_list[step]))
        self.grid_opt.SetCellValue(1, 0, utils.tostring(job.energy1_list[step]))
        self.grid_opt.SetCellValue(2, 0, utils.tostring(job.energy2_list[step]))
        self.grid_opt.SetCellValue(3, 0, utils.tostring(job.spin2_list[step]))
        self.grid_opt.SetCellValue(4, 0, utils.tostring(job.lambda_list[step]))
        self.grid_opt.SetCellValue(5, 0, utils.tostring(job.trust_radii_list[step]))
        self.grid_opt.SetCellValue(6, 0, utils.tostring(job.step_radii_list[step]))
        self.grid_opt.SetCellValue(7, 0, utils.tostring(job.maximum_force_list[step]))
        self.grid_opt.SetCellValue(7, 1, utils.tostring(job.maximum_force_th_list[step]))
        self.grid_opt.SetCellValue(7, 2, utils.tostring(job.maximum_force_conv_list[step]))
        self.grid_opt.SetCellValue(8, 0, utils.tostring(job.rms_force_list[step]))
        self.grid_opt.SetCellValue(8, 1, utils.tostring(job.rms_force_th_list[step]))
        self.grid_opt.SetCellValue(8, 2, utils.tostring(job.rms_force_conv_list[step]))
        self.grid_opt.SetCellValue(9, 0, utils.tostring(job.maximum_displacement_list[step]))
        self.grid_opt.SetCellValue(9, 1, utils.tostring(job.maximum_displacement_th_list[step]))
        self.grid_opt.SetCellValue(9, 2, utils.tostring(job.maximum_displacement_conv_list[step]))
        self.grid_opt.SetCellValue(10, 0, utils.tostring(job.rms_displacement_list[step]))
        self.grid_opt.SetCellValue(10, 1, utils.tostring(job.rms_displacement_th_list[step]))
        self.grid_opt.SetCellValue(10, 2, utils.tostring(job.rms_displacement_conv_list[step]))

    def clear_opt_grid(self):
        for i in range(11):
            for j in range(3):
                self.grid_opt.SetCellValue(i, j, '')

    def correct_opt_step(self) -> bool:
        """
        correct opt step number. If corrected or OK, return True
        if fails, remove the value and return False
        :return: bool
        """
        job = self.current_opt
        try:
            max_step = len(job.energy_list)-1
        except:
            self.text_ctrl_opt_step.SetValue('')
            return False

        value = self.text_ctrl_opt_step.GetValue()
        try:
            value = int(value)
        except:
            value = max_step

        if value < 0:
            value = 0
        elif value > max_step:
            value = max_step

        self.text_ctrl_opt_step.SetValue(str(value))
        return True

    def load_freq(self):
        self.reset_detail_notebook()
        self.set_detail_panel('freq')
        job = self.current_freq

        if job is None:
            return

        # List Box for Freq
        self.list_box_freq.Clear()
        for (i, freq) in enumerate(job.freq_list):
            item = '# ' + str(i) + ' : ' + str(freq) + ' cm-1'
            if freq < 0.0:
                item += '  *imag'
            self.list_box_freq.Append(item)

        # Combo box for thermal data
        if len(job.thermal_data_list) == 0:
            return
        for td in job.thermal_data_list:
            self.combo_box_thermal_data.Append(td.header)
        self.combo_box_thermal_data.SetSelection(len(job.thermal_data_list)-1)
        self.current_thermal_data = job.thermal_data_list[-1]
        self.load_thermal_data()

    def load_thermal_data(self):
        self.clear_thermal_data_grid()
        td = self.current_thermal_data
        if td is None:
            return
        # Set grd
        self.grid_thermal_data.SetCellValue(0, 0, utils.tostring(td.temperature))
        self.grid_thermal_data.SetCellValue(1, 0, utils.tostring(td.pressure))
        self.grid_thermal_data.SetCellValue(2, 0, utils.tostring(td.e_el))
        self.grid_thermal_data.SetCellValue(3, 0, utils.tostring(td.zpve))
        self.grid_thermal_data.SetCellValue(4, 0, utils.tostring(td.h_zero))
        self.grid_thermal_data.SetCellValue(5, 0, utils.tostring(td.e_tr))
        self.grid_thermal_data.SetCellValue(6, 0, utils.tostring(td.e_rot))
        self.grid_thermal_data.SetCellValue(7, 0, utils.tostring(td.e_vib))
        self.grid_thermal_data.SetCellValue(8, 0, utils.tostring(td.h_corr))
        self.grid_thermal_data.SetCellValue(9, 0, utils.tostring(td.h))
        self.grid_thermal_data.SetCellValue(10, 0, utils.tostring(td.s_el))
        self.grid_thermal_data.SetCellValue(11, 0, utils.tostring(td.s_tr))
        self.grid_thermal_data.SetCellValue(12, 0, utils.tostring(td.s_rot))
        self.grid_thermal_data.SetCellValue(13, 0, utils.tostring(td.s_vib))
        self.grid_thermal_data.SetCellValue(14, 0, utils.tostring(td.g_corr))
        self.grid_thermal_data.SetCellValue(15, 0, utils.tostring(td.g))

    def correct_freq_settings(self):
        step = self.text_ctrl_freq_step.GetValue()
        try:
            step = int(step)
            assert step > 0
        except:
            step = config.FREQ_VIEW_DEFAULT_STEP
        self.text_ctrl_freq_step.SetValue(str(step))

        shift = self.text_ctrl_freq_shift.GetValue()
        try:
            shift = Decimal(shift)
            assert shift > 0
        except:
            shift = config.FREQ_VIEW_DEFAULT_SHIFT
        self.text_ctrl_freq_shift.SetValue(str(shift))

    def load_irc(self):
        self.reset_detail_notebook()
        self.set_detail_panel('irc')
        job = self.current_irc

        if job is None:
            return

        if job.paths is None or len(job.paths) == 0:
            return

        for path in job.paths:
            self.combo_box_irc_direction.Append(path.direction)
        self.combo_box_irc_direction.SetSelection(0)
        self.current_irc_path = job.paths[0]

        self.load_irc_path()

    def load_irc_path(self):
        irc_path = self.current_irc_path

        if irc_path is None:
            self.clear_irc_grid()
            return

        if irc_path.mode == 'irc':
            self.text_ctrl_irc_mode.SetValue('IRC')
        elif irc_path.mode == 'softest':
            self.text_ctrl_irc_mode.SetValue('Softest Mode')
        elif irc_path.mode == 'nsp':
            self.text_ctrl_irc_mode.SetValue('Steepest-Descent from Non-Stationary Point')

        max_step = len(irc_path.energy_list)
        self.text_ctrl_irc_max_step.SetValue(utils.tostring(max_step))
        self.text_ctrl_irc_step.SetValue(utils.tostring(max_step))
        self.clear_irc_grid()
        self.load_irc_grid()

    def load_irc_grid(self):
        irc_path = self.current_irc_path
        if irc_path is None:
            self.clear_irc_grid()
            return

        step = int(self.text_ctrl_irc_step.GetValue())
        self.grid_irc.SetCellValue(0, 0, utils.tostring(irc_path.energy_list[step-1]))
        self.grid_irc.SetCellValue(1, 0, utils.tostring(irc_path.spin2_list[step-1]))

    def clear_irc_grid(self):
        for i in range(2):
            for j in range(1):
                self.grid_irc.SetCellValue(i, j, '')

    def correct_irc_step(self) -> bool:
        """
        correct irc step number. If corrected or OK, return True
        if fails, remove the value and return False
        :return: bool
        """
        irc_path = self.current_irc_path
        irc_path : IRCPath

        try:
            max_step = len(irc_path.energy_list)
        except:
            self.text_ctrl_irc_step.SetValue('')
            return False

        value = self.text_ctrl_irc_step.GetValue()
        try:
            value = int(value)
        except:
            value = max_step

        if value < 1:
            value = 1
        elif value > max_step:
            value = max_step

        self.text_ctrl_irc_step.SetValue(str(value))
        return True

    def load_afirpath(self):
        self.reset_detail_notebook()
        self.set_detail_panel('afirpath')
        job = self.current_afirpath

        if job is None:
            return

        self.list_box_afirpath_structures.Clear()

        for (structure, energy) in zip(job.approximate_structures, job.approximate_structure_energy_list):
            label = structure.name + ': EE = ' + utils.tostring(energy)
            self.list_box_afirpath_structures.Append(label)

    def load_lup(self):
        self.reset_detail_notebook()
        self.set_detail_panel('lup')
        job = self.current_lup

        if job is None:
            return

        self.list_box_lup_structures.Clear()
        for (structure, energy) in zip(job.approximate_structures, job.approximate_structure_energy_list):
            label = structure.name + ': EE = ' + utils.tostring(energy)
            self.list_box_lup_structures.Append(label)

        if len(job.itr_paths) == 0:
            return

        for path in job.itr_paths:
            path : LUPPath
            self.combo_box_lup_path.Append(path.name)
        self.combo_box_lup_path.SetSelection(len(job.itr_paths) - 1)
        self.current_lup_path = job.itr_paths[len(job.itr_paths) - 1]
        self.load_lup_path()

    def load_lup_path(self):
        lup_path = self.current_lup_path
        if lup_path is None:
            self.text_ctrl_lup_node.SetValue('')
            self.text_ctrl_lup_max_node.SetValue('')
            return
        self.text_ctrl_lup_node.SetValue(str(lup_path.num_node - 1))
        self.text_ctrl_lup_max_node.SetValue(str(lup_path.num_node - 1))

    def correct_lup_node(self) -> bool:
        """
        correct LUP node number. If corrected or OK, return True
        if fails, remove the value and return False
        :return: bool
        """
        job = self.current_lup_path

        try:
            max_node = job.num_node - 1
        except:
            self.text_ctrl_lup_max_node.SetValue('')
            return False

        value = self.text_ctrl_lup_node.GetValue()
        try:
            value = int(value)
        except:
            value = max_node

        if value < 0:
            value = 0
        elif value > max_node:
            value = max_node

        self.text_ctrl_lup_node.SetValue(str(value))
        return True

    def set_detail_panel(self, page: str):
        """
        :param page: 'general', 'opt', 'freq', 'irc', 'lup', 'afirpath', 'none'
        """
        num_page = self.notebook_detail.GetPageCount()

        if page == 'none':
            for n in range(num_page):
                self.notebook_detail.RemovePage(0)
            return

        page = page.lower()
        panels = {'general' : self.notebook_detail_panel_general,
                  'opt' : self.notebook_detail_panel_opt,
                  'freq' : self.notebook_detail_panel_freq,
                  'irc' : self.notebook_detail_panel_irc,
                  'lup' : self.notebook_detail_panel_lup,
                  'afirpath' : self.notebook_detail_panel_afirpath}
        labels = {'general' : 'General',
                  'opt' : 'OPT',
                  'freq' : 'FREQ',
                  'irc' : 'IRC',
                  'lup' : 'LUP',
                  'afirpath' : 'AFIR Path'}

        assert page in panels and page in labels

        num_page = self.notebook_detail.GetPageCount()
        for n in range(num_page):
            self.notebook_detail.RemovePage(0)
        panel = panels[page]
        label = labels[page]
        self.notebook_detail.AddPage(panel, label)

    def purge_current_jobs(self):
        self.current_general = None
        self.current_opt = None
        self.current_freq = None
        self.current_irc = None
        self.current_irc_path = None
        self.current_lup = None
        self.current_lup_path = None
        self.current_afirpath = None

    def copy_grid(self, grid):

        # In case, not selected but focused
        if len(grid.GetSelectionBlockBottomRight()) == 0:
            data = str(grid.GetCellValue(grid.GetGridCursorRow(), grid.GetGridCursorCol()))

        else:
            rows = grid.GetSelectionBlockBottomRight()[0][0] - grid.GetSelectionBlockTopLeft()[0][0] + 1
            cols = grid.GetSelectionBlockBottomRight()[0][1] - grid.GetSelectionBlockTopLeft()[0][1] + 1

            data = ''
            for r in range(rows):
                for c in range(cols):
                    data = data + str(grid.GetCellValue(grid.GetSelectionBlockTopLeft()[0][0] + r,
                                                        grid.GetSelectionBlockTopLeft()[0][1] + c))
                    if c < cols - 1:
                        data = data + '\t'
                data = data + '\n'

        clipboard = wx.TextDataObject()
        clipboard.SetText(data)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(clipboard)
            wx.TheClipboard.Close()
        else:
            pass

    def show_text_frame(self, title: str, text: str):
        text_view = TextViewFrame(self.frame, title, text, self.job)
        text_view.Show(True)

    # file load function (not an Event handler, but called by dropping a file) ########################
    def load_file(self, file: str):
        """
        load file and set controls
        :param file: com or log file
        """
        dir = os.path.dirname(file)
        base = os.path.basename(file)
        root, ext = os.path.splitext(base)
        if ext.lower() == '.com':
            log_file = os.path.join(dir, root + '.log')
            com_file = file
        elif ext.lower() == '.log':
            log_file = file
            com_file = os.path.join(dir, root + '.com')
        if not os.path.exists(log_file):
            raise FileNotFoundError(log_file + ' is not found.')
        if not os.path.exists(com_file):
            self.logging(com_file + ' is not found.')
            com_file = utils.find_parent_com_file(log_file)
            if com_file is None:
                self.logging('Some data are not loaded.')
            else:
                self.logging('Instead, ' + com_file + ' is found.')

        self.logging('load: ' + log_file)
        if com_file is not None:
            self.logging('load: ' + com_file)
        self.job = GRRMSingleJob(log_file=log_file, com_file=com_file)
        self.load_job_tree()

    # Event Handlers ###################################################################################
    def on_exit(self, event):
        try:
            pass
        finally:
            wx.Exit()

    def on_activated_tree_ctrl_jobs(self, event):
        self.purge_current_jobs()
        item = event.GetItem()
        job = self.tree_ctrl_jobs.GetItemData(item)
        if job.type == 'general':
            self.current_general = job
            self.load_general()
        elif job.type == 'opt':
            self.current_opt = job
            self.load_opt()
        elif job.type == 'freq':
            self.current_freq = job
            self.load_freq()
        elif job.type == 'irc':
            self.current_irc = job
            self.load_irc()
        elif job.type == 'lup':
            self.current_lup = job
            self.load_lup()
        elif job.type == 'afirpath':
            self.current_afirpath = job
            self.load_afirpath()
        else:
            raise ValueError(job.type + ' is not recognized.')

    # Fof OPT panel ####################################################################################
    def on_enter_text_ctrl_opt_step(self, event):
        if self.correct_opt_step():
            self.load_opt_grid()
        else:
            self.clear_opt_grid()

    def on_button_opt_first(self, event):
        job = self.current_opt
        if job is None:
            self.clear_opt_grid()
            return
        self.text_ctrl_opt_step.SetValue('0')
        self.load_opt_grid()

    def on_button_opt_prev(self, event):
        job = self.current_opt
        if job is None:
            self.clear_opt_grid()
            return

        value = self.text_ctrl_opt_step.GetValue()

        # Not int >> 0
        try:
            value = int(value)
        except:
            self.text_ctrl_opt_step.SetValue('0')
            self.load_opt_grid()
            return

        self.text_ctrl_opt_step.SetValue(str(value-1))
        if self.correct_opt_step():
            self.load_opt_grid()
        else:
            self.clear_opt_grid()

    def on_button_opt_next(self, event):
        job = self.current_opt
        if job is None:
            self.clear_opt_grid()
            return

        value = self.text_ctrl_opt_step.GetValue()

        # Not int >> last
        try:
            value = int(value)
        except:
            max_step = len(job.energy_list) - 1
            self.text_ctrl_opt_step.SetValue(str(max_step))
            self.load_opt_grid()
            return

        self.text_ctrl_opt_step.SetValue(str(value+1))
        if self.correct_opt_step():
            self.load_opt_grid()
        else:
            self.clear_opt_grid()

    def on_button_opt_last(self, event):
        job = self.current_opt
        if job is None:
            self.clear_opt_grid()
            return

        max_step = len(job.energy_list) - 1
        self.text_ctrl_opt_step.SetValue(str(max_step))
        self.load_opt_grid()

    def on_button_opt_plot(self, event):
        job = self.current_opt
        if job is not None:
            job.show_plot()

    def on_button_opt_view_current(self, event):
        job = self.current_opt
        if job is None:
            return
        if self.correct_opt_step():
            structure = job.structure_list[int(self.text_ctrl_opt_step.GetValue())]
            name = 'itr_' + self.text_ctrl_opt_step.GetValue() + '.xyz'
            molview.show_structure(structure, name=name)

    def on_button_opt_text_current(self, event):
        job = self.current_opt
        if job is None:
            return
        if self.correct_opt_step():
            structure = job.structure_list[int(self.text_ctrl_opt_step.GetValue())]
            title = '# ITR. ' + self.text_ctrl_opt_step.GetValue()
            text = structure.get_string()
            self.show_text_frame(title=title, text=text)

    def on_button_opt_trajectory(self, event):
        job = self.current_opt
        if job is None:
            return

        file = utils.get_temp_file_name('opt_trajectory_', '.xyz')
        job.save_xyz(file)
        molview.show_multi_xyz(file)

    def on_button_opt_view_optimized(self, event):
        job = self.current_opt
        if job is None:
            return
        if job.optimized_structure is None:
            self.logging('No optimized structure.')
            return
        molview.show_structure(job.optimized_structure, name='optimized.xyz')

    def on_button_opt_text_optimized(self, event):
        job = self.current_opt
        if job is None:
            return
        if job.optimized_structure is None:
            self.logging('No optimized structure.')
            return
        title = 'Optimized Structure'
        text = job.optimized_structure.get_string()
        self.show_text_frame(title=title, text=text)

    def on_button_save_truncated_path(self, event):
        job = self.current_opt
        if job is None:
            return
        try:
            start = int(self.text_ctrl_truncated_path_start.GetValue())
            end = int(self.text_ctrl_truncated_path_end.GetValue())
            assert start >= 0
            assert end < len(job.structure_list)
        except:
            self.logging('Invalid start/end iteration index.')
            return
        include_frozen_atom = self.checkbox_save_truncated_path_include_frozen_atom.IsChecked()

        # Get save file name
        dialog = wx.FileDialog(None, 'save file name',
                               wildcard='GRRM log (*.log)|*.log|All files (*.*)|*.*',
                               style=wx.FD_SAVE)
        # Save in the same directory of log file
        current_dir = os.path.dirname(self.job.log_file)
        if current_dir:
            dialog.SetDirectory(current_dir)
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
            dialog.Destroy()
        else:
            dialog.Destroy()
            return
        job.save_truncated_path(file=file, start_iter=start, end_iter=end, include_frozen_atom=include_frozen_atom)

    def on_key_down_grid_opt(self, event):
        if event.ControlDown() and event.GetKeyCode() == 67:
            self.copy_grid(self.grid_opt)

    # Fof FREQ panel ###################################################################################
    def on_button_freq_view(self, event):
        job = self.current_freq
        if job is None:
            return

        normal_mode = self.list_box_freq.GetSelection()
        if normal_mode is None:
            return
        self.correct_freq_settings()
        step = int(self.text_ctrl_freq_step.GetValue())
        shift = float(self.text_ctrl_freq_shift.GetValue())
        file = utils.get_temp_file_name('normal_mode_' + str(normal_mode) + '_' ,'.xyz')
        job.save_xyz(normal_mode=normal_mode, file=file, step=step, max_shift=shift)
        molview.show_multi_xyz(file)

    def  on_combo_box_thermal_data(self, event):
        if self.current_freq is None:
            return
        select = self.combo_box_thermal_data.GetSelection()
        self.current_thermal_data = self.current_freq.thermal_data_list[select]
        self.load_thermal_data()

    def on_key_down_grid_thermal_data(self, event):
        if event.ControlDown() and event.GetKeyCode() == 67:
            self.copy_grid(self.grid_thermal_data)

    # For IRC panel ####################################################################################
    def on_button_irc_plot_profile(self, event):
        job = self.current_irc
        if job is None:
            return

        job.show_profile_plot(reverse_flag=False)

    def on_button_irc_plot_profile_reversed(self, event):
        job = self.current_irc
        if job is None:
            return

        job.show_profile_plot(reverse_flag=True)

    def on_button_irc_full_trajectory_f2b(self, event):
        job = self.current_irc
        if job is None:
            return

        file = utils.get_temp_file_name('irc_full_trajectory_f2b_', '.xyz')
        job.save_full_irc_path_xyz(file, reverse_flag=False)
        molview.show_multi_xyz(file)

    def on_button_irc_full_trajectory_b2f(self, event):
        job = self.current_irc
        if job is None:
            return

        file = utils.get_temp_file_name('irc_full_trajectory_b2f_', '.xyz')
        job.save_full_irc_path_xyz(file, reverse_flag=True)
        molview.show_multi_xyz(file)

    def on_text_combo_box_irc_direction(self, event):
        job = self.current_irc
        if job is None:
            return

        select = self.combo_box_irc_direction.GetSelection()
        self.current_irc_path = job.paths[select]
        self.load_irc_path()

    def on_enter_text_ctrl_irc_step(self, event):
        if self.correct_irc_step():
            self.load_irc_grid()
        else:
            self.clear_irc_grid()

    def on_button_irc_first(self, event):
        path = self.current_irc_path
        if path is None:
            self.clear_irc_grid()
            return

        self.text_ctrl_irc_step.SetValue('1')
        self.load_irc_grid()

    def on_button_irc_prev(self, event):
        path = self.current_irc_path
        if path is None:
            self.clear_irc_grid()
            return

        value = self.text_ctrl_irc_step.GetValue()

        # Not int >> 0
        try:
            value = int(value)
        except:
            self.text_ctrl_irc_step.SetValue('1')
            self.load_irc_grid()
            return

        self.text_ctrl_irc_step.SetValue(str(value - 1))
        if self.correct_irc_step():
            self.load_irc_grid()
        else:
            self.clear_irc_grid()

    def on_button_irc_next(self, event):
        path = self.current_irc_path
        if path is None:
            self.clear_irc_grid()
            return

        value = self.text_ctrl_irc_step.GetValue()

        # Not int >> last
        try:
            value = int(value)
        except:
            max_step = len(path.energy_list)
            self.text_ctrl_irc_step.SetValue(str(max_step))
            self.load_irc_grid()
            return

        self.text_ctrl_irc_step.SetValue(str(value + 1))
        if self.correct_irc_step():
            self.load_irc_grid()
        else:
            self.clear_irc_grid()

    def on_button_irc_last(self, event):
        path = self.current_irc_path
        if path is None:
            self.clear_irc_grid()
            return

        max_step = len(path.energy_list)
        self.text_ctrl_irc_step.SetValue(str(max_step))
        self.load_irc_grid()

    def on_button_irc_view_current(self, event):
        path = self.current_irc_path
        if path is None:
            return

        if self.correct_irc_step():
            structure = path.structure_list[int(self.text_ctrl_irc_step.GetValue())-1]
            name = 'step_' + self.text_ctrl_irc_step.GetValue() + '.xyz'
            molview.show_structure(structure, name=name)

    def on_button_irc_text_current(self, event):
        path = self.current_irc_path
        if path is None:
            return

        if self.correct_irc_step():
            structure = path.structure_list[int(self.text_ctrl_irc_step.GetValue())-1]
            title = 'STEP #. ' + self.text_ctrl_irc_step.GetValue()
            text = structure.get_string()
            self.show_text_frame(title=title, text=text)

    def on_button_irc_plot(self, event):
        path = self.current_irc_path
        if path is None:
            return

        path.show_plot()

    def on_button_irc_trajectory(self, event):
        path = self.current_irc_path
        if path is None:
            return

        file = utils.get_temp_file_name('irc_trajectory_', '.xyz')
        path.save_xyz(file)
        molview.show_multi_xyz(file)

    def on_key_down_grid_irc(self, event):
        if event.ControlDown() and event.GetKeyCode() == 67:
            self.copy_grid(self.grid_irc)

    # For LUP panel ####################################################################################
    def on_text_combo_box_lup_path(self, event):
        job = self.current_lup
        if job is None:
            return

        select = self.combo_box_lup_path.GetSelection()
        self.current_lup_path = job.itr_paths[select]
        self.load_lup_path()

    def on_button_lup_plot_step(self, event):
        job = self.current_lup_path
        if job is None:
            return
        job.show_plot_by_step()

    def on_button_button_lup_plot_length(self, event):
        job = self.current_lup_path
        if job is None:
            return
        job.show_plot_by_length()

    def on_button_lup_data(self, event):
        job = self.current_lup_path
        if job is None:
            return
        text = job.get_profile_string()
        title = 'LUP Path Profile'
        self.show_text_frame(title=title, text=text)

    def on_button_lup_trajectory(self, event):
        job = self.current_lup_path
        if job is None:
            return

        file = utils.get_temp_file_name('lup_trajectory_', '.xyz')
        job.save_xyz(file)
        molview.show_multi_xyz(file)

    def on_button_lup_node_view(self, event):
        job = self.current_lup_path
        if job is None:
            return

        if self.correct_lup_node():
            structure = job.structure_list[int(self.text_ctrl_lup_node.GetValue())]
            name = 'lup_node_' + self.text_ctrl_lup_node.GetValue() + '.xyz'
            molview.show_structure(structure, name=name)

    def on_button_lup_node_text(self, event):
        job = self.current_lup_path
        if job is None:
            return

        if self.correct_lup_node():
            structure = job.structure_list[int(self.text_ctrl_lup_node.GetValue())]
            title = '# NODE. ' + self.text_ctrl_lup_node.GetValue()
            text = structure.get_string()
            self.show_text_frame(title=title, text=text)

    def on_button_lup_structure_view(self, event):
        job = self.current_lup
        if job is None:
            return

        select = self.list_box_lup_structures.GetSelection()
        if select is None:
            return
        else:
            structure = job.approximate_structures[select]
            molview.show_structure(structure, name='lup_path_structure.xyz')

    def on_button_lup_structure_text(self, event):
        job = self.current_lup
        if job is None:
            return

        select = self.list_box_lup_structures.GetSelection()
        if select is None:
            return
        else:
            structure = job.approximate_structures[select]
            text = structure.get_string()
            title = 'LUP Path Node Structure'
            self.show_text_frame(title=title, text=text)

    # For AFIR Path panel ##############################################################################
    def on_button_afirpath_plot_step(self, event):
        job = self.current_afirpath
        if job is None:
            return
        job.show_plot_by_step()

    def on_button_afirpath_plot_length(self, event):
        job = self.current_afirpath
        if job is None:
            return
        job.show_plot_by_length()

    def on_button_afirpath_data(self, event):
        job = self.current_afirpath
        if job is None:
            return
        text = job.get_profile_string()
        title = 'AFIR Path Profile'
        self.show_text_frame(title=title, text=text)

    def on_button_afirpath_structure_view(self, event):
        job = self.current_afirpath
        if job is None:
            return

        select = self.list_box_afirpath_structures.GetSelection()
        if select is None:
            return
        else:
            structure = job.approximate_structures[select]
            molview.show_structure(structure, name='AFIR_path_structure.xyz')

    def on_button_afirpath_structure_text(self, event):
        job = self.current_afirpath
        if job is None:
            return

        select = self.list_box_afirpath_structures.GetSelection()
        if select is None:
            return
        else:
            structure = job.approximate_structures[select]
            text = structure.get_string()
            title = 'AFIR Path Structure'
            self.show_text_frame(title=title, text=text)

    def on_menu_open(self, event):
        dialog = wx.FileDialog(None,'Select GRRM file',
                               wildcard='(*.com;*.log)|*.com;*.log',
                               style=wx.FD_OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            file = dialog.GetPath()
            self.load_file(file)
            dialog.Destroy()
        else:
            dialog.Destroy()
            return


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    app = GRRMSingleViewerApp(False)
    app.MainLoop()