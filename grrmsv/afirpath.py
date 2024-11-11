import copy
import dataclasses
from decimal import Decimal
from typing import List, Optional

import matplotlib.pyplot as plt

from grrmsv.structure import Structure
from grrmsv.utils import calc_limit_for_plot

import config


@dataclasses.dataclass
class PathPoint:
    itr : int
    length : Decimal
    energy : Decimal


class AFIRPath:
    def __init__(self, afir_path_block_data: List[str], frozen_atom_coordinates: Optional[List[str]] = None):
        assert (afir_path_block_data[0].startswith('---Profile of AFIR path'))
        self.row_data: List[str] = copy.deepcopy(afir_path_block_data)
        self.path_profile_data: List[str] = []
        self.points: List[PathPoint] = []
        self.num_atom: int = -1
        self.approximate_structures: List[Structure] = []
        self.approximate_structure_energy_list: List[Decimal] = []
        self.frozen_atom_coordinates: Optional[List[str]] = frozen_atom_coordinates

        self.name: Optional[str] = None

        self._parse_row_data()

    def _parse_row_data(self):

        self.path_profile_data.append(self.row_data[0])
        self.path_profile_data.append(self.row_data[1])

        # get lengths and energies
        for (i, line) in enumerate(self.row_data[2:]):
            if line.strip() == '':
                break
            self.path_profile_data.append(line)
            line_data = line.strip().split()
            itr = int(line_data[0])
            length = Decimal(line_data[1])
            energy = Decimal(line_data[2])
            point = PathPoint(itr=itr, energy=energy, length=length)
            self.points.append(point)

        # check num atoms
        start = -1
        for (i, line) in enumerate(self.row_data):
            if line.startswith('---Approximate'):
                start = i + 1
                break
        if start == -1:   # Approximate TS/EQ not found.
            return
        for (i, line) in enumerate(self.row_data[start:]):
            if line.startswith('ENERGY'):
                self.num_atom = i
                break

        # get approximate EQ/TS structures
        for (i, line) in enumerate(self.row_data):
            if line.startswith('---Approximate'):
                name = line.replace('---', '').replace(' geometry ', ' ').replace('between ', '').replace(' and ', '-')
                self.approximate_structures.append(Structure(self.row_data[i+1:i+self.num_atom+1], name=name,
                                                             frozen_atom_coordinates=self.frozen_atom_coordinates))
                self.approximate_structure_energy_list.append(Decimal(self.row_data[i+self.num_atom+1].split()[2]))

    def show_plot_by_step(self):
        xs = [p.itr for p in self.points]
        ys = [p.energy for p in self.points]
        plt.figure('AFIR Path Energy ', figsize=config.AFIR_PATH_PLOT_SIZE)
        plt.title('AFIR Path Energy')
        plt.ylim(*calc_limit_for_plot(ys))
        plt.xlabel('# ITR.')
        plt.ylabel('Energy')
        plt.scatter(xs, ys)

        plt.tight_layout()
        plt.show()

    def show_plot_by_length(self):
        labels = [p.itr for p in self.points]
        xs = [p.length for p in self.points]
        ys = [p.energy for p in self.points]
        plt.figure('AFIR Path Energy ', figsize=config.AFIR_PATH_PLOT_SIZE)
        plt.title('AFIR Path Energy (labels = # ITR.)')
        plt.ylim(*calc_limit_for_plot(ys))
        plt.xlabel('length (ang)')
        plt.ylabel('Energy')

        for (i, j, k) in zip(xs, ys, labels):
            plt.plot(i, j, 'o', color='blue')
            plt.annotate(str(k), xy=(float(i), float(j)))

        plt.tight_layout()
        plt.show()

    def get_profile_string(self) -> str:
        return ''.join(self.path_profile_data)

    @property
    def type(self) -> str:
        return 'afirpath'