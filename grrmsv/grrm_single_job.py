from typing import Optional, Union, List

from grrmsv.opt import OPTJob
from grrmsv.freq import FREQJob
from grrmsv.irc import IRCJob
from grrmsv.lup import LUPJob
from grrmsv.afirpath import AFIRPath

from grrmsv.utils import get_line_type


class GRRMSingleJob:
    def __init__(self, log_file: str, com_file: Optional[str] = None):
        # read from log
        self.jobs: List[Union[OPTJob, FREQJob, IRCJob, LUPJob]] = []
        self.log_file: Optional[str] = None
        self.log_data: List[str] = []
        self.normal_termination: bool = False
        self.afirpath: Optional[AFIRPath] = None
        # read from com
        self.com_file: Optional[str] = None
        self.com_data: List[str] = []
        self.link_options: List[str] = []
        self.method: Optional[str] = None
        self.method_options: Optional[List[str]] = None
        self.charge: Optional[int] = None
        self.multi: Optional[int] = None
        self.frozen_atom_coordinates: Optional[List[str]] = None

        if com_file is not None:
            self._parse_com_file(com_file)

        self._parse_log_file(log_file)

    def _parse_log_file(self, log_file: str):

        self.log_file = log_file
        with open(self.log_file, 'r') as f:
            self.log_data = f.readlines()

        current_type = ''  # opt/freq/irc/lup
        current_block_buffer = []
        current_name = None
        for (i, line) in enumerate(self.log_data):
            if line.startswith('Normal termination of the GRRM Program'):
                self.normal_termination = True
            # For GRRM23 LUP job (followed by OPT job for appEQs)
            if line.strip().startswith('>>Start') or line.strip().startswith('>>>Start') and current_type == '':
                if 'AppEQ' in line.split()[-1]:
                    current_name = line.split()[-1].strip()
                else:
                    current_name = None
            line_type = get_line_type(line)
            if line_type == 'data':
                if current_type != '':
                    current_block_buffer.append(line)
                continue
            if current_type == '':
                current_type = line_type
                current_block_buffer = []
                current_block_buffer.append(line)
                continue
            if current_type == line_type:
                current_block_buffer.append(line)
                self._parse_job_block(current_block_buffer, name=current_name)
                current_name = None
                current_block_buffer = []
                current_type = ''
                continue
            else:
                current_block_buffer.append(line)
                continue

        if len(current_block_buffer) > 0 and current_type != '':
            self._parse_job_block(current_block_buffer, name=current_name)

        # check AFIR Path block
        for (i, line) in enumerate(self.log_data):
            if line.startswith('---Profile of AFIR path'):
                self.afirpath = AFIRPath(self.log_data[i:])
                break

    def _parse_job_block(self, block, name: Optional[str] = None):

        if block[0].startswith('OPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPT'):
            job = OPTJob(block, frozen_atom_coordinates=self.frozen_atom_coordinates)
        if block[0].startswith('IRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRC'):
            job = IRCJob(block, frozen_atom_coordinates=self.frozen_atom_coordinates)
        if block[0].startswith('FREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQ'):
            job = FREQJob(block, frozen_atom_coordinates=self.frozen_atom_coordinates)
        if block[0].startswith('LUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUP'):
            job = LUPJob(block, frozen_atom_coordinates=self.frozen_atom_coordinates)
        job.name = name
        self.jobs.append(job)

    def _parse_com_file(self, com_file: str):
        self.com_file = com_file
        with open(com_file, 'r') as f:
            self.com_data = f.readlines()

        # read and omit % lines
        com_body = []
        for (i, line) in enumerate(self.com_data):
            if line.lstrip().startswith('%'):
                self.link_options.append(line)
            else:
                com_body.append(line)

        # read method (#) line
        self.method = com_body[0].strip()
        assert self.method.startswith('#')
        assert com_body[1].strip() == ''
        charge, multi = com_body[2].strip().split()
        self.charge = int(charge)
        self.multi = int(multi)

        # read options
        self.method_options = []
        option_flag = False
        for line in com_body:
            if line.lower().strip() == 'options':
                option_flag = True
            elif option_flag:
                self.method_options.append(line)

        # read frozen atoms
        frozen_atoms = -1
        for (i, line) in enumerate(self.com_data):
            if line.lstrip().lower().startswith('frozen atoms'):
                frozen_atoms = i + 1
        if frozen_atoms >= 0:
            self.frozen_atom_coordinates = []
            for line in self.com_data[frozen_atoms:]:
                if line.strip() == '' or line.strip().lower().startswith('options'):
                    break
                else:
                    self.frozen_atom_coordinates.append(line)

    @property
    def type(self):
        return 'general'