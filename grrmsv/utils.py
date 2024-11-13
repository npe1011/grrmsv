import os
import re
import tempfile
import atexit
from pathlib import Path
from decimal import Decimal
from typing import Tuple, List, Optional, Any, Union


class TempFileManager:
    def __init__(self):
        self.file_list: List[Path] = []

    def add_file(self, file: str):
        self.file_list.append(Path(file))

    def delete_files(self):
        for file in self.file_list:
            try:
                file.unlink()
            except:
                pass


temp_file_manager = TempFileManager()


@atexit.register
def temp_file_cleanup():
    temp_file_manager.delete_files()


def get_temp_file_name(prefix: str, suffix: str) -> str:
    fd, file = tempfile.mkstemp(prefix=prefix, suffix=suffix)
    temp_file_manager.add_file(file)
    return file


def extract_sub_block(data: List[str], job_type: str) -> Optional[List[str]]:
    """
    Extract sub block (str list). Only the first block is returned if several ones are detected.
    dtype = 'opt' or 'freq' or 'irc'
    """
    if job_type.lower() == 'opt':
        separate_line = 'OPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPT'
    elif job_type.lower() == 'freq':
        separate_line = 'FREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQ'
    elif job_type.lower() == 'irc':
        separate_line = 'IRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRC'
    else:
        raise ValueError('type should be opt/freq/irc to extract sub blocks')

    start = -1
    end = -1
    for (i, line) in enumerate(data):
        if line.startswith(separate_line):
            if start == -1:
                start = i
                continue
            else:
                end = i + 1
                break

    if start == -1:
        return None

    # for opt/freq
    if job_type.lower() in ['opt', 'irc']:
        if end == -1:
            return data[start:]
        else:
            return data[start:end]

    # for freq (return None if not finished)
    elif job_type.lower() == 'freq':
        if end == -1:
            return None
        else:
            return data[start:end]


def get_line_type(line: str) -> str:
    """
    return 'opt', 'irc', 'freq', or 'data
    """
    if line.startswith('OPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPT'):
        return 'opt'
    if line.startswith('IRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRCIRC'):
        return 'irc'
    if line.startswith('FREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQFREQ'):
        return 'freq'
    if line.startswith('LUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUPLUP'):
        return 'lup'
    else:
        return 'data'


def tostring(value: Any) -> str:

    if value is None:
        return ''

    if type(value) == bool:
        if value:
            return 'Yes'
        else:
            return 'No'

    if type(value) == Decimal or type(value) == float:
        return '{:.12f}'.format(value)

    else:
        return str(value)


def calc_limit_for_plot(value_list: List[Union[float, Decimal]]) -> Tuple[float, float]:
    """
    for pyplot return (min, max) in float
    :param value_list: list, of which element can be cast to float
    :return: min, max
    """
    min_v = float(min(value_list))
    max_v = float(max(value_list))
    # Avoid causing warnings when max = min
    if min_v == max_v:
        return min_v - 0.00001, max_v + 0.00001
    buff = (max_v - min_v) * 0.05
    min_v = min_v - buff
    max_v = max_v + buff
    return min_v, max_v


def method_convert_grrm_to_gjf(method_string: str) -> str:

    split_data = method_string.lstrip().lstrip('#').lstrip().split() # Method Additional

    method_main = split_data[0]

    if len(split_data) > 1:
        additional_string = ' '.join(split_data[1:])
    else:
        additional_string = ''

    split_method_main = method_main.split('/')

    if len(split_method_main) == 1:
        gaussian_method = 'SP'
    elif len(split_method_main) == 2:
        gaussian_method = 'SP' + ' ' + split_method_main[1]
    elif len(split_method_main) == 3:
        gaussian_method = 'SP' + ' ' + split_method_main[1] + '/' + split_method_main[2]
    else:
        gaussian_method = 'SP B3LYP/def2SVP'

    return ('# ' + gaussian_method + ' ' + additional_string).rstrip() + '\n'


def options_convert_grrm_to_gjf(options: List[str]) -> List[str]:
    gaussian_options = []

    gauinpb_flag = False
    for line in options:
        if line.lower().lstrip().startswith('gauinpb'):
            gauinpb_flag = True
            continue
        if gauinpb_flag:
            if line.lower().lstrip().startswith('end'):
                gauinpb_flag = False
                continue
            else:
                gaussian_options.append(line)
                continue
        else:
            continue

    return gaussian_options


def find_parent_com_file(log_file: Union[str, Path]) -> Optional[str]:
    """
    :return: parent com file path or None if not exist.
    """
    logdir = os.path.dirname(log_file)
    base = os.path.basename(log_file)   # xxxxxx_PT100.log / xxxxxx.log

    pos = base.rfind('_')
    if pos == -1:
        return None

    parent_base_root = base[:pos]
    suffix_and_ext = base[pos:]

    if '.log' not in suffix_and_ext:
        return None
    suffix = suffix_and_ext[:-4]

    if re.fullmatch(r'_[a-zA-Z]{1,2}\d+', suffix):
        parent_com_file = os.path.join(logdir, parent_base_root + '.com')
        if os.path.exists(parent_com_file):
            return parent_com_file

    return None


def remove_extra_blanks(text: str) -> str:
    _t = text.replace('\t', ' ')
    _t = re.sub(r' +', ' ', _t)
    return _t
