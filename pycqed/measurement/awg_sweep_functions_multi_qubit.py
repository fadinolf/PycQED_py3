import numpy as np
import logging
from pycqed.measurement import sweep_functions as swf
from pycqed.measurement.randomized_benchmarking import randomized_benchmarking as rb
from pycqed.measurement.pulse_sequences import standard_sequences as st_seqs
from pycqed.measurement.pulse_sequences import single_qubit_tek_seq_elts as sqs
from pycqed.measurement.pulse_sequences import multi_qubit_tek_seq_elts as sqs2
from measurement.pulse_sequences import fluxing_sequences as fsqs
default_gauss_width = 10  # magic number should be removed,
# note magic number only used in old mathematica seqs


class two_qubit_off_on(swf.Hard_Sweep):
    def __init__(self, q0_pulse_pars, q1_pulse_pars, RO_pars, upload=True,
                 return_seq=False, nr_samples=4, verbose=False):
        super().__init__()
        self.q0_pulse_pars = q0_pulse_pars
        self.q1_pulse_pars = q1_pulse_pars
        self.RO_pars = RO_pars
        self.upload = upload
        self.parameter_name = 'sample'
        self.unit = '#'
        self.sweep_points = np.arange(nr_samples)
        self.verbose = verbose
        self.return_seq = return_seq
        self.name = 'two_qubit_off_on'


    def prepare(self, **kw):
        if self.upload:
            sqs2.two_qubit_off_on(q0_pulse_pars=self.q0_pulse_pars,
                                  q1_pulse_pars=self.q1_pulse_pars,
                                RO_pars=self.RO_pars,
                                return_seq=self.return_seq,
                                verbose=self.verbose)


class three_qubit_off_on(swf.Hard_Sweep):
    def __init__(self, q0_pulse_pars, q1_pulse_pars, q2_pulse_pars, RO_pars, upload=True,
                 return_seq=False, nr_samples=4, verbose=False):
        super().__init__()
        self.q0_pulse_pars = q0_pulse_pars
        self.q1_pulse_pars = q1_pulse_pars
        self.q2_pulse_pars = q2_pulse_pars
        self.RO_pars = RO_pars
        self.upload = upload
        self.parameter_name = 'sample'
        self.unit = '#'
        self.sweep_points = np.arange(nr_samples)
        self.verbose = verbose
        self.return_seq = return_seq
        self.name = 'three_qubit_off_on'


    def prepare(self, **kw):
        if self.upload:
            sqs2.three_qubit_off_on(q0_pulse_pars=self.q0_pulse_pars,
                                  q1_pulse_pars=self.q1_pulse_pars,
                                  q2_pulse_pars=self.q2_pulse_pars,
                                RO_pars=self.RO_pars,
                                return_seq=self.return_seq,
                                verbose=self.verbose)

class four_qubit_off_on(swf.Hard_Sweep):
    def __init__(self, q0_pulse_pars, q1_pulse_pars, q2_pulse_pars,  q3_pulse_pars, RO_pars, upload=True,
                 return_seq=False, nr_samples=4, verbose=False):
        super().__init__()
        self.q0_pulse_pars = q0_pulse_pars
        self.q1_pulse_pars = q1_pulse_pars
        self.q2_pulse_pars = q2_pulse_pars
        self.q3_pulse_pars = q3_pulse_pars
        self.RO_pars = RO_pars
        self.upload = upload
        self.parameter_name = 'sample'
        self.unit = '#'
        self.sweep_points = np.arange(nr_samples)
        self.verbose = verbose
        self.return_seq = return_seq
        self.name = 'four_qubit_off_on'


    def prepare(self, **kw):
        if self.upload:
            sqs2.four_qubit_off_on(q0_pulse_pars=self.q0_pulse_pars,
                                  q1_pulse_pars=self.q1_pulse_pars,
                                  q2_pulse_pars=self.q2_pulse_pars,
                                q3_pulse_pars=self.q3_pulse_pars,
                                RO_pars=self.RO_pars,
                                return_seq=self.return_seq,
                                verbose=self.verbose)