import logging
log = logging.getLogger(__name__)
from collections import OrderedDict
from copy import deepcopy
import numpy as np

class SweepPoints(list):
    """
    This class is used to create sweep points for any measurement.
    The SweepPoints object is a list of dictionaries of the form:
        [
            # 1st sweep dimension
            {param_name0: (values, unit, label),
             param_name1: (values, unit, label),
            ...
             param_nameN: (values, unit, label)},

            # 2nd sweep dimension
            {param_name0: (values, unit, label),
             param_name1: (values, unit, label),
            ...
             param_nameN: (values, unit, label)},

             .
             .
             .

            # D-th sweep dimension
            {param_name0: (values, unit, label),
             param_name1: (values, unit, label),
            ...
             param_nameN: (values, unit, label)},
        ]

    Example how to use this class to create a 2D sweep for 3 qubits, where
    the first (hard) sweep is over amplitudes and the :

    sp = SweepPoints()
    for qb in ['qb1', 'qb2', 'qb3']:
        sp.add_sweep_parameter(f'lengths_{qb}', np.linspace(10e-9, 1e-6, 80),
        's', 'Pulse length, $L$')
    sp.add_sweep_dimension()
    for qb in ['qb1', 'qb2', 'qb3']:
        sp.add_sweep_parameter(f'amps_{qb}', np.linspace(0, 1, 20),
        'V', 'Pulse amplitude, $A$')
    """
    def __init__(self, param_name=None, values=None, unit='', label=None):
        super().__init__()
        if param_name is not None and values is not None:
            if label is None:
                label = param_name
            self.append({param_name: (values, unit, label)})

    def add_sweep_parameter(self, param_name, values, unit='', label=None):
        if label is None:
            label = param_name
        if len(self) == 0:
            self.append({param_name: (values, unit, label)})
        else:
            self[-1].update({param_name: (values, unit, label)})

    def add_sweep_dimension(self):
        self.append(dict())

    def get_meas_obj_sweep_points_map(self, measured_objects):
        """
        Assumes the order of params in each sweep dimension corresponds to
        the order of keys in keys_list

        :param measured_objects: list of strings to be used as keys in the
            returned dictionary. These are the measured object names
        :return: {keys[k]: list(d)[k] for d in self for k in measured_objects}
        """

        if len(measured_objects) != len(self[0]):
            raise ValueError('The number of keys and number of sweep '
                             'parameters do not match.')

        sweep_points_map = OrderedDict()
        for i, key in enumerate(measured_objects):
            sweep_points_map[key] = [list(d)[i] for d in self]

        return sweep_points_map

    def sweep_pulse_params(self, base_pulse_list, sweep_dimension):

        sp_dict = self[sweep_dimension]
        swept_pulses = []
        nr_sp = len(sp_dict[next(iter(sp_dict))][0])
        for n in range(nr_sp):
            pulses_sp = deepcopy(base_pulse_list)
            for name, sp_pars in sp_dict.items():
                sp_vals = sp_pars[0]
                pulse_name, param_name = name.split('.')
                pulse_indices = [i for i, p in enumerate(base_pulse_list)
                                 if pulse_name in p.get('name', "")]
                if len(pulse_indices) == 0:
                    raise ValueError(
                        f"No pulse with name {pulse_name} found in list:"
                        f"{[p.get('name', 'No Name') for p in base_pulse_list]}")
                for p_idx in pulse_indices:
                    if isinstance(sp_vals, str):
                        sp_vals_func = eval(sp_vals)
                        prev_val = pulses_sp[p_idx][param_name]
                        sp_vals = sp_vals_func(self, prev_val)
                    if len(sp_vals) != nr_sp:
                        raise ValueError(
                            f'Entries in sweep dimension {sweep_dimension}'
                            f'are not all of the same length.')
                    pulses_sp[p_idx][param_name] = sp_vals[n]
            swept_pulses.append(pulses_sp)
        return swept_pulses
