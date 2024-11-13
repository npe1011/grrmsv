import copy
from codecs import strict_errors
from turtledemo.penrose import start

import matplotlib.pyplot as plt
from decimal import Decimal
from typing import List, Optional

from grrmsv.structure import Structure
from grrmsv.utils import calc_limit_for_plot

import config


class OPTJob:
    def __init__(self, opt_block_data: List[str], frozen_atom_coordinates: Optional[List[str]] = None):

        assert (opt_block_data[0].startswith('OPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPT'))

        self.row_data: List[str] = copy.deepcopy(opt_block_data)
        self.num_atom: int = -1
        self.structure_list: List[Structure] = []
        self.energy_list: List[Decimal] = []
        self.energy1_list: List[Decimal] = []
        self.energy2_list: List[Decimal] = []
        self.spin2_list: List[Decimal] = []
        self.lambda_list: List[Decimal] = []
        self.trust_radii_list: List[Decimal] = []
        self.step_radii_list: List[Decimal] = []
        self.maximum_force_list: List[Decimal] = []
        self.maximum_force_th_list: List[Decimal] = []
        self.maximum_force_conv_list: List[Decimal] = []
        self.rms_force_list: List[Decimal] = []
        self.rms_force_th_list: List[Decimal] = []
        self.rms_force_conv_list: List[Decimal] = []
        self.maximum_displacement_list: List[Decimal] = []
        self.maximum_displacement_th_list: List[Decimal] = []
        self.maximum_displacement_conv_list: List[Decimal] = []
        self.rms_displacement_list: List[Decimal] = []
        self.rms_displacement_th_list: List[Decimal] = []
        self.rms_displacement_conv_list: List[Decimal] = []
        self.optimized_structure: Optional[Structure] = None
        self.optimized_energy: Optional[Decimal] = None
        self.optimized_energy1: Optional[Decimal] = None
        self.optimized_energy2: Optional[Decimal] = None
        self.optimized_spin2: Optional[Decimal] = None
        self.status: str = 'unfinished'  # unfinished, MIN found, SADDLE found, finished without MIN/SADDLE

        self.frozen_atom_coordinates: Optional[List[str]] = frozen_atom_coordinates

        self._parse_row_data()  # main process: read row data and set value list.
        self._convergence_check()  # fill *_conv_list with True/False

        self.name: Optional[str] = None

    def _set_num_atom(self):
        """
        set self.num_atom from self.row_data
        """
        for (i, line) in enumerate(self.row_data):
            if line.startswith('# ITR. 0'):
                start_line_init = i
            elif 'Item' in line and 'Value' in line and 'Threshold' in line:
                self.num_atom = i - 1 - start_line_init
                break

    def _parse_row_data(self):
        """
        read self.row_data
        :return:
        """

        self._set_num_atom()
        for (i, line) in enumerate(self.row_data):
            if line.startswith('# ITR. '):
                self.structure_list.append(Structure(self.row_data[i + 1:i + 1 + self.num_atom], name=line.strip(),
                                                     frozen_atom_coordinates=self.frozen_atom_coordinates))
                # energy and bare energy
                assert 'ENERGY' in self.row_data[i + self.num_atom + 2].upper()
                self.energy_list.append(Decimal(self.row_data[i + self.num_atom + 2].strip().split()[1]))
                if '(' in self.row_data[i + self.num_atom + 2] and ':' in self.row_data[i + self.num_atom + 2]:
                    # Only in GRRM23
                    # ENERGY      	-756.738121237908	                          (-756.737782526435 : -756.738567916493)
                    #                                                                   e1               e2
                    e1, e2 = self.row_data[i + self.num_atom + 2].split('(')[1].split(':')
                    self.energy1_list.append(Decimal(e1.strip()))
                    self.energy2_list.append(Decimal(e2.strip().rstrip(')').strip()))
                else:
                    self.energy1_list.append(Decimal('0.000000000000'))  # for GRRM 17: (e1:e2) is not printed
                    self.energy2_list.append(Decimal('0.000000000000'))
                # spin**2
                assert 'SPIN' in self.row_data[i + self.num_atom + 3].upper()
                self.spin2_list.append(Decimal(self.row_data[i + self.num_atom + 3].strip().split()[1]))
                assert 'LAMDA' in self.row_data[i + self.num_atom + 4].upper()
                self.lambda_list.append(Decimal(self.row_data[i + self.num_atom + 4].strip().split()[1]))
                assert 'TRUST RADII' in self.row_data[i + self.num_atom + 5].upper()
                self.trust_radii_list.append(Decimal(self.row_data[i + self.num_atom + 5].strip().split()[2]))
                assert 'STEP RADII' in self.row_data[i + self.num_atom + 6]
                self.step_radii_list.append(Decimal(self.row_data[i + self.num_atom + 6].strip().split()[2]))
                assert 'MAXIMUM' in self.row_data[i + self.num_atom + 7].upper()
                assert 'FORCE' in self.row_data[i + self.num_atom + 7].upper()
                self.maximum_force_list.append(Decimal(self.row_data[i + self.num_atom + 7].strip().split()[2]))
                self.maximum_force_th_list.append(Decimal(self.row_data[i + self.num_atom + 7].strip().split()[3]))
                assert 'RMS' in self.row_data[i + self.num_atom + 8].upper()
                assert 'FORCE' in self.row_data[i + self.num_atom + 8].upper()
                self.rms_force_list.append(Decimal(self.row_data[i + self.num_atom + 8].strip().split()[2]))
                self.rms_force_th_list.append(Decimal(self.row_data[i + self.num_atom + 8].strip().split()[3]))
                assert 'MAXIMUM' in self.row_data[i + self.num_atom + 9].upper()
                assert 'DISPLACEMENT' in self.row_data[i + self.num_atom + 9].upper()
                self.maximum_displacement_list.append(Decimal(self.row_data[i + self.num_atom + 9].strip().split()[2]))
                self.maximum_displacement_th_list.append(Decimal(self.row_data[i + self.num_atom + 9].strip().split()[3]))
                assert 'RMS' in self.row_data[i + self.num_atom + 10].upper()
                assert 'DISPLACEMENT' in self.row_data[i + self.num_atom + 10].upper()
                self.rms_displacement_list.append(Decimal(self.row_data[i + self.num_atom + 10].strip().split()[2]))
                self.rms_displacement_th_list.append(Decimal(self.row_data[i + self.num_atom + 10].strip().split()[3]))
            if line.startswith('Optimized structure'):
                assert self.optimized_structure is None
                self.optimized_structure = Structure(self.row_data[i + 1:i + 1 + self.num_atom],
                                                     frozen_atom_coordinates=self.frozen_atom_coordinates)
                assert 'ENERGY' in self.row_data[i + self.num_atom + 1].upper()
                self.optimized_energy = Decimal(self.row_data[i + self.num_atom + 1].strip().split()[2])
                if '(' in self.row_data[i + self.num_atom + 1] and ':' in self.row_data[i + self.num_atom + 1]:
                    e1, e2 = self.optimized_bare_energy = self.row_data[i + self.num_atom + 1].split('(')[1].split(':')
                    self.optimized_energy1 = Decimal(e1.strip())
                    self.optimized_energy2 = Decimal(e2.strip().rstrip(')').strip())
                else:
                    self.optimized_energy1 = Decimal('0.000000000000')  # for GRRM 17: (e1:e2) is not printed
                    self.optimized_energy2 = Decimal('0.000000000000')  # for GRRM 17: (e1:e2) is not printed
                assert 'SPIN' in self.row_data[i + self.num_atom + 2].upper()
                self.optimized_spin2 = Decimal(self.row_data[i + self.num_atom + 2].strip().split()[2])
            if line.startswith('Minimum point was found'):
                assert self.optimized_structure is not None
                self.status = 'MIN found'
            if line.startswith('1st-Order Saddle point was found'):
                assert self.optimized_structure is not None
                self.status = 'SADDLE found'
            if line.startswith('Stationary point was found'):
                assert self.optimized_structure is not None
                self.status = 'Stationary point found'
            if line.startswith('The structure is dissociating'):
                self.status = 'dissociate'
            if line.startswith('OPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPT'):
                if i == 0:
                    continue
                if self.status == 'unfinished':
                    self.status = 'not converged'
                break

    def _convergence_check(self):
        self.maximum_force_conv_list = []
        self.rms_force_conv_list = []
        self.maximum_displacement_conv_list = []
        self.rms_displacement_conv_list = []
        for i in range(len(self.rms_force_list)):
            self.maximum_force_conv_list.append(self.maximum_force_list[i] <= self.maximum_force_th_list[i])
            self.rms_force_conv_list.append(self.rms_force_list[i] <= self.rms_force_th_list[i])
            self.maximum_displacement_conv_list.append(self.maximum_displacement_list[i] <= self.maximum_displacement_th_list[i])
            self.rms_displacement_conv_list.append(self.rms_displacement_list[i] <= self.rms_displacement_th_list[i])

    def save_xyz(self, file: str):
        with open(file, 'w') as f:
            for s in self.structure_list:
                f.write(str(s.num_atom + s.num_frozen_atom) + '\n')
                f.write(s.name + '\n')
                f.write(s.get_string(include_frozen_atoms=True))

    def save_truncated_path(self, file: str, start_iter: int, end_iter:int, include_frozen_atom: bool):
        if start_iter < 0 or end_iter >= len(self.structure_list):
            raise ValueError('Invalid start/end iteration number.')
        with open(file, 'w') as f:
            for i in range(start_iter, end_iter+1):
                f.write('# NODE {:d}\n'.format(i))
                f.write(self.structure_list[i].get_string(include_frozen_atoms=include_frozen_atom))
            f.write('\n')

    def show_plot(self):

        xs = range(len(self.energy_list))

        plt.figure('Optimization', figsize=config.OPT_PLOT_SIZE)
        # energy
        plt.subplot(7, 1, 1)
        plt.title('Energy')
        plt.ylim(*calc_limit_for_plot(self.energy_list))
        plt.plot(xs, self.energy_list)
        # E1 (bare energy or state1 1)
        plt.subplot(7, 1, 2)
        plt.title('E1')
        plt.ylim(*calc_limit_for_plot(self.energy1_list))
        plt.plot(xs, self.energy1_list)
        # E2 (bare energy or state1 1)
        plt.subplot(7, 1, 3)
        plt.title('E2')
        plt.ylim(*calc_limit_for_plot(self.energy2_list))
        plt.plot(xs, self.energy2_list)
        # Maximum Force
        plt.subplot(7, 1, 4)
        plt.title('Max Force')
        plt.ylim(*calc_limit_for_plot(self.maximum_force_list))
        plt.plot(xs, self.maximum_force_list)
        # RMS Force
        plt.subplot(7, 1, 5)
        plt.title('RMS Force')
        plt.ylim(*calc_limit_for_plot(self.rms_force_list))
        plt.plot(xs, self.rms_force_list)
        # Maximum Displacement
        plt.subplot(7, 1, 6)
        plt.title('Max Displacement')
        plt.ylim(*calc_limit_for_plot(self.maximum_displacement_list))
        plt.plot(xs, self.maximum_displacement_list)
        # RMS Force
        plt.subplot(7, 1, 7)
        plt.title('RMS Displacement')
        plt.ylim(*calc_limit_for_plot(self.rms_displacement_list))
        plt.plot(xs, self.rms_displacement_list)

        plt.tight_layout()
        plt.show()

        return True

    @property
    def type(self) -> str:
        return 'opt'