import copy
import dataclasses
from decimal import Decimal
from typing import List, Optional

import numpy as np

from grrmsv import utils
from grrmsv.structure import Structure


@dataclasses.dataclass
class ThermalData:
    header: str
    temperature : Decimal
    pressure : Decimal
    e_el : Decimal
    zpve : Decimal
    h_zero: Decimal
    e_tr: Decimal
    e_rot: Decimal
    e_vib: Decimal
    h_corr : Decimal
    h : Decimal
    s_el: Decimal
    s_tr: Decimal
    s_rot: Decimal
    s_vib: Decimal
    g_corr : Decimal
    g : Decimal


class FREQJob:

    def __init__(self, freq_block_data: List[str], frozen_atom_coordinates: Optional[List[str]] = None):
        assert (freq_block_data[0].startswith('FREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQ'))

        self.row_data: List[str] = copy.deepcopy(freq_block_data)
        self.num_atom: int = -1
        self.init_structure: Optional[Structure] = None
        self.freq_list: List[Decimal] = []  # frequency value list
        self.freq_matrix_list: List[np.ndarray] = []  # List of array(num_atom, 3)
        self.name: Optional[str] = None
        self.frozen_atom_coordinates: Optional[List[str]] = frozen_atom_coordinates
        self.thermal_data_list: List[ThermalData] = []

        self._parse_row_data()

    def _parse_row_data(self):
        # Set initial structure and num_atom
        start_init_structure = -1
        end_init_structure = -1
        for (i, line) in enumerate(self.row_data):
            if line.startswith('Geometry (Origin = Center of Mass'):
                start_init_structure = i
            elif start_init_structure >= 0 and line.strip() == '':
                end_init_structure = i
                break
        self.init_structure = Structure(self.row_data[start_init_structure + 1:end_init_structure], name='Initial Structure',
                                        frozen_atom_coordinates=self.frozen_atom_coordinates)
        self.num_atom = self.init_structure.num_atom

        # separate freq result into blocks
        freq_blocks = []
        block = []
        i = end_init_structure + 1
        first_start_thermochemistry_line = -1
        while i < len(self.row_data):
            # separated by a blank line
            if self.row_data[i].strip() == '':
                freq_blocks.append(copy.deepcopy(block))
                block = []
            # Thermochemistry line indicates the end.
            elif self.row_data[i].startswith('Thermochemistry'):
                first_start_thermochemistry_line = i
                break
            else:
                block.append(self.row_data[i])
            i += 1

        if first_start_thermochemistry_line < 0:
            return

        # read each freq sub-blocks
        for block in freq_blocks:
            # number of freq data in block (1, 2, 3)
            column_num = len(block[0].strip().split())
            assert 1<= column_num <= 3

            # get freq values in
            # Freq.  :	  1256.54809523	  1272.49620328	  1273.57870656
            self.freq_list.extend([Decimal(f) for f in block[1].split(':')[1].strip().split()])

            # retain freq matrix (num_atom*3; array) list in this block
            freq_matrix_list_in_block = []
            for c in range(column_num):
                freq_matrix_list_in_block.append(np.zeros(shape=(self.num_atom, 3), dtype='float64'))

            # read 3 lines at once （i:x, i+1:y, i+2:z）
            for i in range(3, 3 * self.num_atom + 3, 3):
                # _xs/_ys/_zs contains up to 3 values (str)
                _xs = block[i].split(':')[1].strip().split()
                _ys = block[i + 1].split(':')[1].strip().split()
                _zs = block[i + 2].split(':')[1].strip().split()

                for c in range(column_num):
                    freq_matrix_list_in_block[c][(i // 3) - 1] = (np.array([_xs[c], _ys[c], _zs[c]])).astype(dtype=float)

            self.freq_matrix_list.extend(freq_matrix_list_in_block)

        # Read after 'Thermochemistry' line
        self._parse_thermal_data_part(self.row_data[first_start_thermochemistry_line:])


    def save_xyz(self, normal_mode: int, file: str, step: int = 20, max_shift: float = 0.5):
        """
        save a xyz file for visualization of normal mode.
        :param normal_mode: number of normal mode (0,1,...)
        :param file: save file name
        :param step: step for each direction
        :param max_shift:  max shift for atoms in angstrom
        """

        # weight: move move_matrix * weight in each step
        move_matrix = self.freq_matrix_list[normal_mode]
        max_vector_size = np.sqrt(np.max(np.sum(move_matrix * move_matrix, axis=1)))
        weight = max_shift / (max_vector_size * step)

        init_coordinate = self.init_structure.get_coordinates_np()
        atoms = self.init_structure.get_atoms()

        output_num_atom = self.num_atom
        frozen_atom_string = ''
        if self.frozen_atom_coordinates is not None:
            for line in self.frozen_atom_coordinates:
                if line.strip() == '':
                    continue
                else:
                    atom, x, y, z, *_ = line.strip().split()
                    x = Decimal(x)
                    y = Decimal(y)
                    z = Decimal(z)
                    atom = atom.capitalize()
                    frozen_atom_string += '{0:<4} {1:>20.12f} {2:>20.12f} {3:>20.12f}\n'.format(atom, x, y, z)
                    output_num_atom += 1

        with open(file, 'w') as f:
            forward_coordinates = [init_coordinate + s * weight * move_matrix for s in range(1, step+1)]
            backward_coordinates = [init_coordinate - s * weight * move_matrix for s in range(1, step+1)]

            # forward
            f.write(str(output_num_atom ) + '\n')
            f.write('Initial Structure\n')
            f.write(self._structure_string_from_atoms_and_coordinate_array(atoms, init_coordinate) + frozen_atom_string)
            for coordinate in forward_coordinates:
                f.write(str(output_num_atom ) + '\n')
                f.write('\n')
                f.write(self._structure_string_from_atoms_and_coordinate_array(atoms, coordinate) + frozen_atom_string)
            for coordinate in reversed(forward_coordinates):
                f.write(str(output_num_atom ) + '\n')
                f.write('\n')
                f.write(self._structure_string_from_atoms_and_coordinate_array(atoms, coordinate) + frozen_atom_string)

            # backward
            f.write(str(output_num_atom ) + '\n')
            f.write('Initial Structure\n')
            f.write(self._structure_string_from_atoms_and_coordinate_array(atoms, init_coordinate) + frozen_atom_string)
            for coordinate in backward_coordinates:
                f.write(str(output_num_atom ) + '\n')
                f.write('\n')
                f.write(self._structure_string_from_atoms_and_coordinate_array(atoms, coordinate) + frozen_atom_string)
            for coordinate in reversed(backward_coordinates):
                f.write(str(output_num_atom ) + '\n')
                f.write('\n')
                f.write(self._structure_string_from_atoms_and_coordinate_array(atoms, coordinate) + frozen_atom_string)

            f.write(str(output_num_atom ) + '\n')
            f.write('Initial Structure\n')
            f.write(self._structure_string_from_atoms_and_coordinate_array(atoms, init_coordinate) + frozen_atom_string)

    @staticmethod
    def _structure_string_from_atoms_and_coordinate_array(atoms: List[str], coordinate_array: np.ndarray):
        structure_string = ''
        assert len(atoms) == coordinate_array.shape[0]
        for i in range(len(atoms)):
            structure_string += '{0:<4} {1:>20.12f} {2:>20.12f} {3:>20.12f}\n'.format(
                atoms[i], coordinate_array[i,0], coordinate_array[i,1], coordinate_array[i,2])
        return structure_string

    def _parse_thermal_data_part(self, data: List[str]):

        def _check_and_read_value(_line: str, _start: str) -> Decimal:
            assert _line.strip().startswith(_start)
            return Decimal(_line.strip().split('=', maxsplit=1)[1].split('(')[0].strip())

        start_line_indices = []
        for i, line in enumerate(data):
            if line.startswith('Thermochemistry'):
                start_line_indices.append(i)

        for start_line in start_line_indices:
            # Header line including temp and press.
            header = utils.remove_extra_blanks(data[start_line]).strip()
            terms = header.split()
            temperature = Decimal(-1)
            pressure = Decimal(-1)
            for i in range(len(terms)-1):
                try:
                    v = Decimal(terms[i])
                except:
                    continue
                else:
                    if terms[i+1].startswith('K'):
                        temperature = v
                    elif terms[i+1].startswith('Atm'):
                        pressure = v

            e_el = _check_and_read_value(data[start_line+1], 'E(el)')
            zpve = _check_and_read_value(data[start_line+2], 'ZPVE')
            h_zero = _check_and_read_value(data[start_line+3], 'Enthalpie(0K)')
            e_tr = _check_and_read_value(data[start_line+4], 'E(tr)')
            e_rot = _check_and_read_value(data[start_line+5], 'E(rot)')
            e_vib = _check_and_read_value(data[start_line+6], 'E(vib)')
            h_corr = _check_and_read_value(data[start_line+7], 'H-E(el)')
            h = _check_and_read_value(data[start_line+8], 'Enthalpie')
            s_el = _check_and_read_value(data[start_line+9], 'S(el)')
            s_tr = _check_and_read_value(data[start_line+10], 'S(tr)')
            s_rot = _check_and_read_value(data[start_line+11], 'S(rot)')
            s_vib = _check_and_read_value(data[start_line+12], 'S(vib)')
            g_corr = _check_and_read_value(data[start_line+13], 'G-E(el)')
            g = _check_and_read_value(data[start_line+14], 'Free Energy')

            self.thermal_data_list.append(ThermalData(header=header,
                                                      temperature=temperature,
                                                      pressure=pressure,
                                                      e_el=e_el,
                                                      zpve=zpve,
                                                      h_zero=h_zero,
                                                      e_tr=e_tr,
                                                      e_rot=e_rot,
                                                      e_vib=e_vib,
                                                      h_corr=h_corr,
                                                      h = h,
                                                      s_el = s_el,
                                                      s_tr=s_tr,
                                                      s_rot=s_rot,
                                                      s_vib=s_vib,
                                                      g_corr=g_corr,
                                                      g=g))

    @property
    def type(self) -> str:
        return 'freq'





