import copy
import dataclasses
from decimal import Decimal
from typing import List, Optional

import matplotlib.pyplot as plt

from grrmsv.structure import Structure
from grrmsv.opt import OPTJob
from grrmsv.freq import FREQJob
from grrmsv.irc import IRCJob
from grrmsv.utils import get_line_type, calc_limit_for_plot

import config


@dataclasses.dataclass
class PathPoint:
    node : int
    length : Decimal
    energy : Decimal


class LUPPath:
    def __init__(self, lup_itr_block_data: List[str], frozen_atom_coordinates: Optional[List[str]] = None):
        assert lup_itr_block_data[0].startswith('ITR.') and 'of LUP-path optimization' in lup_itr_block_data[0]

        self.row_data: List[str] = copy.deepcopy(lup_itr_block_data)
        self.num_atom: int = -1
        self.structure_list: List[Structure] = []
        self.energy_list: List[Decimal] = []
        self.path_profile_data: List[str] = []
        self.points: List[PathPoint] = []
        self.name: Optional[str] = None
        self.frozen_atom_coordinates: Optional[List[str]] = frozen_atom_coordinates
        self._parse_row_data()

    def _set_num_atom(self):
        """
        set self.num_atom from self.row_data
        """
        for (i, line) in enumerate(self.row_data):
            if line.startswith('# NODE'):
                start_line_init = i
            elif line.startswith('ENERGY'):
                self.num_atom = i - 1 - start_line_init
                break

    def _parse_row_data(self):
        self._set_num_atom()
        self.name = self.row_data[0].split('of')[0].strip()  # name: ITR. @

        # get node start lines
        node_start_line_list = []
        for (i, line) in enumerate(self.row_data):
            if line.startswith('# NODE'):
                node_start_line_list.append(i)

        # get node structures and energies
        for node_start_line in node_start_line_list:
            structure_block = self.row_data[node_start_line + 1 : node_start_line + self.num_atom + 1]
            name = self.row_data[node_start_line].strip()
            assert 'ENERGY' in self.row_data[node_start_line + self.num_atom + 1].upper()
            energy = Decimal(self.row_data[node_start_line + self.num_atom + 1].split()[-1].strip())
            self.structure_list.append(Structure(structure_block, name=name,
                                                 frozen_atom_coordinates=self.frozen_atom_coordinates))
            self.energy_list.append(energy)

        # get start line for ---Profile of LUP path
        profile_start_line = -1
        for (i, line) in enumerate(self.row_data):
            if line.startswith('---Profile of LUP path'):
                profile_start_line = i

        if profile_start_line == -1:
            raise ValueError('---Profile of LUP path section is not found.')

        # read profile
        self.path_profile_data.append(self.row_data[profile_start_line])
        self.path_profile_data.append(self.row_data[profile_start_line+1])
        for line in self.row_data[profile_start_line+2:]:
            if line.strip() == '':
                break
            self.path_profile_data.append(line)
            line_data = line.strip().split()
            node = int(line_data[0])
            length = Decimal(line_data[1])
            energy = Decimal(line_data[2])
            point = PathPoint(node=node, energy=energy, length=length)
            self.points.append(point)

    def show_plot_by_step(self):
        xs = [p.node for p in self.points]
        ys = [p.energy for p in self.points]
        plt.figure('LUP Path Energy ', figsize=config.LUP_PATH_PLOT_SIZE)
        plt.title('LUP Path Energy')
        plt.ylim(*calc_limit_for_plot(ys))
        plt.xlabel('# NODE.')
        plt.ylabel('Energy')
        plt.scatter(xs, ys)

        plt.tight_layout()
        plt.show()
        # plt.clf()
        # plt.close()

    def show_plot_by_length(self):
        labels = [p.node for p in self.points]
        xs = [p.length for p in self.points]
        ys = [p.energy for p in self.points]
        plt.figure('LUP Path Energy ', figsize=config.AFIR_PATH_PLOT_SIZE)
        plt.title('LUP Path Energy (labels = # NODE.)')
        plt.ylim(*calc_limit_for_plot(ys))
        plt.xlabel('length (ang)')
        plt.ylabel('Energy')

        for (i, j, k) in zip(xs, ys, labels):
            plt.plot(i, j, 'o', color='blue')
            plt.annotate(str(k), xy=(float(i), float(j)))

        plt.tight_layout()
        plt.show()
        # plt.clf()
        # plt.close()

    def get_profile_string(self):
        return ''.join(self.path_profile_data)

    def save_xyz(self, file):
        with open(file, 'w') as f:
            for s in self.structure_list:
                f.write(str(s.num_atom + s.num_frozen_atom) + '\n')
                f.write(s.name.replace('\n', ' ') + '\n')
                f.write(s.get_string(include_frozen_atoms=True))

    @property
    def num_node(self):
        return len(self.structure_list)


class LUPJob:
    def __init__(self, lup_block_data, frozen_atom_coordinates = None):
        assert (lup_block_data[0].startswith('LUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUP'))
        self.row_data = copy.deepcopy(lup_block_data)
        self.itr_paths = []
        self.approximate_structures = []
        self.approximate_structure_energy_list = []
        self.subjobs = []

        self.name = None

        self.frozen_atom_coordinates = frozen_atom_coordinates

        self._parse_row_data()

    def _parse_row_data(self):

        start_itr_block_lines = []  # indices for ITR. @ of LUP-path optimization
        for (i, line) in enumerate(self.row_data):
            if line.startswith('ITR.') and 'of LUP-path optimization' in line:
                start_itr_block_lines.append(i)

        if len(start_itr_block_lines) == 0:
            return

        itr_blocks = []
        # separate and store iteration blocks, except for the last one
        for n in range(len(start_itr_block_lines)-1):
            start = start_itr_block_lines[n]
            end = start_itr_block_lines[n+1]
            itr_blocks.append(self.row_data[start:end])

        last_block = []
        end_flag = False
        for line in self.row_data[start_itr_block_lines[-1]:]:
            if line.startswith('-------------------------------------') or  line.startswith('---Approximate'):
                end_flag = True
                break
            else:
                last_block.append(line)
        if end_flag:
            itr_blocks.append(last_block)

        for itr_block in itr_blocks:
            self.itr_paths.append(LUPPath(itr_block, frozen_atom_coordinates=self.frozen_atom_coordinates))

        if len(self.itr_paths) == 0:
            return

        self.num_atom = self.itr_paths[0].num_atom

        # get approximate TS/EQ
        count_ts = 0
        count_eq = 0
        for (i, line) in enumerate(self.row_data):
            if line.startswith('---Approximate'):
                structure_type = line.split()[1]  # TS or EQ
                if structure_type == 'EQ':
                    structure_id = count_eq
                    count_eq += 1
                elif structure_type == 'TS':
                    structure_id = count_ts
                    count_ts += 1
                name = line.replace('---', '').replace(' geometry ', ' ').strip() + ' : App{0:} {1:}'.format(structure_type, structure_id)
                self.approximate_structures.append(Structure(self.row_data[i + 1:i + self.num_atom + 1], name=name,
                                                             frozen_atom_coordinates=self.frozen_atom_coordinates))
                self.approximate_structure_energy_list.append(Decimal(self.row_data[i + self.num_atom + 1].split()[2]))

        # read # Geometry of App blocks (each block contains OPT/FREQ/IRC Job blocks)
        start_geometry_block_lines = []
        for (i, line) in enumerate(self.row_data):
            if line.startswith('# Geometry of App'):
                start_geometry_block_lines.append(i)
        geometry_blocks = []
        for n in range(len(start_geometry_block_lines)-1):
            start = start_geometry_block_lines[n]
            end = start_geometry_block_lines[n+1]
            geometry_blocks.append(self.row_data[start:end])
        if len(start_geometry_block_lines) > 0:
            geometry_blocks.append(self.row_data[start_geometry_block_lines[-1]:])

        for geometry_block in geometry_blocks:
            name = ' '.join(geometry_block[0].split()[3:5]).rstrip(',')

            current_type = ''  # opt/freq/irc/lup
            current_block_buffer = []
            for line in geometry_block:
                line_type = get_line_type(line)
                if line_type == 'data':
                    if current_type != '':
                        current_block_buffer.append(line)
                    continue
                if current_type == '':
                    current_type = line_type
                    current_block_buffer = [line]
                    continue
                if current_type == line_type:
                    current_block_buffer.append(line)
                    self._parse_subjob_block(current_block_buffer, name=name)
                    current_block_buffer = []
                    current_type = ''
                    continue
                else:
                    current_block_buffer.append(line)
                    continue

            if len(current_block_buffer) > 0 and current_type != '':
                self._parse_subjob_block(current_block_buffer, name=name)

        # in case "# Geometry of App" is not found
        if len(start_geometry_block_lines) == 0:
            start = 0
            for (i, line) in enumerate(self.row_data):
                if line.strip().startswith('---Approximate'):
                    start = i
            if start == 0:
                return

            count = 1
            name = 'sub'
            remain_data = self.row_data[start:]
            current_type = ''  # opt/freq/irc/lup
            current_block_buffer = []
            for line in remain_data:
                line_type = get_line_type(line)
                if line_type == 'data':
                    if current_type != '':
                        current_block_buffer.append(line)
                    continue
                if current_type == '':
                    current_type = line_type
                    current_block_buffer = [line]
                    continue
                if current_type == line_type:
                    current_block_buffer.append(line)
                    self._parse_subjob_block(current_block_buffer, name=name + '#.' + str(count))
                    count += 1
                    current_block_buffer = []
                    current_type = ''
                    continue
                else:
                    current_block_buffer.append(line)
                    continue

            if len(current_block_buffer) > 0 and current_type != '':
                self._parse_subjob_block(current_block_buffer, name=name + '#.' + str(count))


    def _parse_subjob_block(self, block: List[str], name: Optional[str]):

        if block[0].startswith('OPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPT'):
            job = OPTJob(block, frozen_atom_coordinates=self.frozen_atom_coordinates)
        if block[0].startswith('IRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRC'):
            job = IRCJob(block, frozen_atom_coordinates=self.frozen_atom_coordinates)
        if block[0].startswith('FREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQ'):
            job = FREQJob(block, frozen_atom_coordinates=self.frozen_atom_coordinates)
        if block[0].startswith('LUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUP'):
            return
        job.name = name
        self.subjobs.append(job)

    @property
    def type(self) -> str:
        return 'lup'

