import numpy as np
from decimal import Decimal
from typing import Optional, List, Tuple, Union


class Structure:
    """
    molecular structure data class
    Internally, data are saved as [atom:str, x:Decimal, y:Decimal, z:Decimal]
    """

    def __init__(self,
                 atom_coordinates: Union[str, List[str]],
                 name: Optional[str] = None,
                 frozen_atom_coordinates: Union[None, str, List[str]] = None):

        self.name: Optional[str] = name
        self.atom_coordinates: List[Tuple[str, Decimal, Decimal, Decimal]] = []
        self.frozen_atom_coordinates: Optional[List[Tuple[str, Decimal, Decimal, Decimal]]] = None

        if type(atom_coordinates) == str:
            coord_list = atom_coordinates.split('\n')
        else:
            coord_list = list(atom_coordinates)

        for line in coord_list:
            if line.strip() == '':
                continue
            try:
                atom, x, y, z, *_ = line.strip().split()
            except:
                raise ValueError('Error reading structure line:', line.strip())
            atom = atom.strip().capitalize()
            x = Decimal(x.strip())
            y = Decimal(y.strip())
            z = Decimal(z.strip())
            self.atom_coordinates.append((atom, x, y, z))

        if frozen_atom_coordinates is not None:
            self.frozen_atom_coordinates = []
            if type(frozen_atom_coordinates) == str:
                coord_list = frozen_atom_coordinates.split('\n')
            else:
                coord_list = list(frozen_atom_coordinates)

            for line in coord_list:
                if line.strip() == '':
                    continue
                atom, x, y, z, *_ = line.strip().split()
                atom = atom.strip().capitalize()
                x = Decimal(x.strip())
                y = Decimal(y.strip())
                z = Decimal(z.strip())
                self.frozen_atom_coordinates.append((atom, x, y, z))

    @property
    def num_atom(self) -> int:
        return len(self.atom_coordinates)

    @property
    def num_frozen_atom(self) -> int:
        if self.frozen_atom_coordinates is None:
            return 0
        else:
            return len(self.frozen_atom_coordinates)

    def get_string(self, include_frozen_atoms: bool = True) -> str:
        """
        return string:
        atom1 x1 y1 z1
        atom2 x2 y2 z2
        ...
        """
        data = '\n'.join(['{0:<4} {1:>20.12f} {2:>20.12f} {3:>20.12f}'.format(
            atom_coord[0], atom_coord[1], atom_coord[2], atom_coord[3]) for atom_coord in self.atom_coordinates]) + '\n'

        if self.frozen_atom_coordinates is not None and include_frozen_atoms:
            data += '\n'.join(['{0:<4} {1:>20.12f} {2:>20.12f} {3:>20.12f}'.format(
            atom_coord[0], atom_coord[1], atom_coord[2], atom_coord[3]) for atom_coord in self.frozen_atom_coordinates]) + '\n'

        return data

    def get_coordinates_np(self) -> np.ndarray:
        """
        return xyz coordinates as n*3 numpy array (float)
        :return: numpy array
        """
        coordinates = []
        for atom_coordinate in self.atom_coordinates:
            coordinates.append([float(w) for w in atom_coordinate[1:]])  # slice xyz coordinates and converted to float
        return np.array(coordinates, dtype=float)

    def get_atoms(self) -> List[str]:
        return [line[0] for line in self.atom_coordinates]

    def save_xyz_file(self, file: str, title: str =''):
        with open(file, 'w') as f:
            f.write(str(self.num_atom + self.num_frozen_atom) + '\n')
            f.write(title.rstrip() + '\n')
            f.write(self.get_string(include_frozen_atoms=True))

    def __str__(self):
        return self.get_string()

