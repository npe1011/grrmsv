import copy
import dataclasses
from decimal import Decimal
from typing import List, Optional

import matplotlib.pyplot as plt

from grrmsv.structure import Structure
from grrmsv.opt import OPTJob
from grrmsv.freq import FREQJob
from grrmsv.utils import extract_sub_block, calc_limit_for_plot

import config


@dataclasses.dataclass()
class Point:
    length : Decimal
    energy : Decimal


class IRCPath:
    def __init__(self, path_block: List[str], num_atom: int, frozen_atom_coordinates: Optional[List[str]] = None):
        """
        :param path_block: data black with first line =  IRC FOLLOWING (FORWARD) STARTING FROM or etc.
        """
        self.structure_list: List[Structure] = []
        self.energy_list: List[Decimal] = []
        self.spin2_list: List[Decimal] = []
        self.opt_job: Optional[OPTJob] = None
        self.freq_job: Optional[FREQJob] = None
        self.mode: Optional[str] = None  # irc or softest or nsp (from non-stationary point)
        self.direction: Optional[str] = None # forward or backward
        self.num_atom: int = num_atom
        self.frozen_atom_coordinates: Optional[List[str]] = frozen_atom_coordinates

        if path_block is None or len(path_block) == 0:
            raise ValueError('IRC Path block is in valid.')

        # check IRC mode and direction
        if path_block[0].startswith('IRC FOLLOWING (FORWARD) STARTING FROM'):
            self.mode = 'irc'
            self.direction = 'forward'
        elif path_block[0].startswith('IRC FOLLOWING (BACKWARD) STARTING FROM'):
            self.mode = 'irc'
            self.direction = 'backward'
        elif path_block[0].startswith('SOFTEST MODE FOLLOWING (FORWARD) STARTING FROM'):
            self.mode = 'softest'
            self.direction = 'forward'
        elif path_block[0].startswith('SOFTEST MODE FOLLOWING (BACKWARD) STARTING FROM'):
            self.mode = 'softest'
            self.direction = 'backward'
        elif path_block[0].startswith('STEEPEST-DESCENT PATH FOLLOWING STARTING FROM NON-STATIONARY POINT'):
            self.mode = 'nsp'
            self.direction = 'forward'

        # Read path structures, energy, spin2
        for (i, line) in enumerate(path_block):
            if line.startswith('# STEP'):
                self.structure_list.append(Structure(path_block[i + 1:i + 1 + self.num_atom], name=line.strip(),
                                                     frozen_atom_coordinates=self.frozen_atom_coordinates))
                assert 'ENERGY' in path_block[i + 1 + self.num_atom].upper()
                self.energy_list.append(Decimal(path_block[i + 1 + self.num_atom].split('=')[1].strip().split()[0]))
                assert 'SPIN' in path_block[i + 2 + self.num_atom].upper()
                self.spin2_list.append(Decimal(path_block[i + 2 + self.num_atom].split('=')[1].strip().split()[0]))

        # Read opt and freq job if found.
        opt_block = extract_sub_block(path_block, 'opt')
        if opt_block is not None:
            self.opt_job = OPTJob(opt_block, frozen_atom_coordinates=self.frozen_atom_coordinates)

        freq_block = extract_sub_block(path_block, 'freq')
        if freq_block is not None:
            self.freq_job = FREQJob(freq_block, frozen_atom_coordinates=self.frozen_atom_coordinates)

    def save_xyz(self, file: str):
        with open(file, 'w') as f:
            for s in self.structure_list:
                f.write(str(s.num_atom + s.num_frozen_atom) + '\n')
                f.write(s.name + '\n')
                f.write(s.get_string(include_frozen_atoms=True))

    def get_xyz_string(self, reverse_flag: bool = True):
        """
        return xyz string for IRC visualization
        """
        xyz = ''
        for s in reversed(self.structure_list) if reverse_flag else self.structure_list:
            xyz += str(s.num_atom + s.num_frozen_atom) + '\n'
            xyz += s.name + '\n'
            xyz += s.get_string(include_frozen_atoms=True)
        return xyz

    def show_plot(self):
        xs = range(1, len(self.energy_list)+1)
        ys = self.energy_list

        title = 'IRC ({:})'.format(self.direction)
        plt.figure(title, figsize=config.IRC_PROFILE_PLOT_SIZE)
        plt.title(title)
        plt.ylim(*calc_limit_for_plot(ys))
        plt.xlabel('# STEP.')
        plt.ylabel('Energy (au)')
        plt.scatter(xs, ys)

        plt.tight_layout()
        plt.show()


class IRCJob:

    def __init__(self, irc_block_data: List[str], frozen_atom_coordinates: Optional[List[str]] = None):
        assert (irc_block_data[0].startswith('IRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRC'))

        self.row_data: List[str] = copy.deepcopy(irc_block_data)
        self.num_atom: int = -1
        self.init_structure: Optional[Structure] = None
        self.init_freq_job: Optional[FREQJob] = None
        self.paths: List[IRCPath] = []
        self.energy_profile_points: Optional[List[Point]] = None
        self.frozen_atom_coordinates: Optional[List[str]] = frozen_atom_coordinates

        self._read_initial_structure()
        self.num_atom = self.init_structure.num_atom

        self.name: Optional[str] = None

        # Get IRC Paths
        path_blocks = self._get_path_blocks()  # separated to blocks
        init_freq_block = extract_sub_block(path_blocks[0], job_type='freq')
        if init_freq_block is not None:
            self.init_freq_job = FREQJob(init_freq_block, frozen_atom_coordinates=self.frozen_atom_coordinates)
        if len(path_blocks) > 1:
            for block in path_blocks[1:]:
                self.paths.append(IRCPath(block, num_atom=self.num_atom,
                                          frozen_atom_coordinates=self.frozen_atom_coordinates))

        # Get Energy Profile
        start_profile_line = -1
        for (i, line) in enumerate(self.row_data):
            if line.startswith('Energy profile along IRC'):
                start_profile_line = i + 2
        if start_profile_line > 0:
            self.energy_profile_points = []
            for line in self.row_data[start_profile_line:]:
                if line.strip() == '' or line.startswith('Reverse'):
                    break
                else:
                    # TODO: SC-AFIRのとき、4列表示されてるものの解釈がわからない。とりあえず2列目をエネルギーとして取得
                    path_energy_terms = [Decimal(x) for x in line.strip().split()]
                    length = path_energy_terms[0]
                    energy = path_energy_terms[1]
                    self.energy_profile_points.append(Point(length=length, energy=energy))

    def _get_path_blocks(self):

        def is_block_start_line(l) -> bool:
            return l.startswith('IRC FOLLOWING (FORWARD) STARTING FROM') or \
                l.startswith('IRC FOLLOWING (BACKWARD) STARTING FROM') or \
                l.startswith('SOFTEST MODE FOLLOWING (FORWARD) STARTING FROM') or \
                l.startswith('SOFTEST MODE FOLLOWING (BACKWARD) STARTING FROM') or \
                l.startswith('STEEPEST-DESCENT PATH FOLLOWING STARTING FROM NON-STATIONARY POINT')

        path_blocks = []
        current_block = []

        for line in self.row_data:
            if line.startswith('Energy profile along IRC'):
                break
            if is_block_start_line(line):
                if len(current_block) > 0:
                    path_blocks.append(current_block)
                current_block = [line]
            else:
                current_block.append(line)
        if len(current_block) > 0:
            path_blocks.append(current_block)

        return path_blocks

    def _read_initial_structure(self):
        start_init_structure = -1
        end_init_structure = -1
        for (i, line) in enumerate(self.row_data):
            if line.startswith('INITIAL STRUCTURE'):
                if start_init_structure == -1:
                    start_init_structure = i + 1
                else:
                    raise ValueError('More than two initial structures are detected in IRC log.')
            if line.startswith('ENERGY'):
                if start_init_structure != -1:
                    end_init_structure = i
                    break

        self.init_structure = Structure(self.row_data[start_init_structure:end_init_structure],
                                        name='Initial Structure', frozen_atom_coordinates=self.frozen_atom_coordinates)

    def show_profile_plot(self, reverse_flag: bool = False):
        if reverse_flag:
            title = 'Energy Profile along IRC (reversed)'
            xs = [-p.length for p in self.energy_profile_points]
            ys = [p.energy for p in self.energy_profile_points]
        else:
            title = 'Energy Profile along IRC'
            xs = [p.length for p in self.energy_profile_points]
            ys = [p.energy for p in self.energy_profile_points]
        plt.figure(title, figsize=config.IRC_PROFILE_PLOT_SIZE)
        plt.title(title)
        plt.ylim(*calc_limit_for_plot(ys))
        plt.xlabel('Length (A amu1/2)')
        plt.ylabel('Energy (au)')
        plt.scatter(xs, ys)

        plt.tight_layout()
        plt.show()

    def save_full_irc_path_xyz(self, file: str, reverse_flag: bool = False):
        """
        save the full IRC path xyz file (forward > backward or backward > forward if reversed_flag)
        """

        # check whether both forward and backward exist.
        if len(self.paths) < 2:
            raise RuntimeError('Both forward and backward IRC paths are required for full visualization.')
        else:
            if self.paths[0].direction == 'forward' and self.paths[1].direction == 'backward':
                forward_path =  self.paths[0]
                backward_path = self.paths[1]
            elif self.paths[0].direction == 'backward' and self.paths[1].direction == 'forward':
                forward_path = self.paths[1]
                backward_path = self.paths[0]
            else:
                raise RuntimeError('Both forward and backward IRC paths are required for full visualization.')

        init_structure_string = str(self.init_structure.num_atom + self.init_structure.num_frozen_atom) + '\n'
        init_structure_string += '#. 0 Initial Structure for IRC\n'
        init_structure_string += self.init_structure.get_string(include_frozen_atoms=True)

        if reverse_flag:
            irc_xyz_string = backward_path.get_xyz_string(reverse_flag=True)
            irc_xyz_string += init_structure_string
            irc_xyz_string += forward_path.get_xyz_string(reverse_flag=False)
        else:
            irc_xyz_string = forward_path.get_xyz_string(reverse_flag=True)
            irc_xyz_string += init_structure_string
            irc_xyz_string += backward_path.get_xyz_string(reverse_flag=False)

        with open(file, 'w') as f:
            f.write(irc_xyz_string)

    @property
    def type(self) -> str:
        return 'irc'

