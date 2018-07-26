import logging
import itertools
import numpy as np
from copy import deepcopy
import pycqed.measurement.waveform_control.sequence as sequence
from pycqed.utilities.general import add_suffix_to_dict_keys
from pycqed.measurement.pulse_sequences.standard_elements import \
    multi_pulse_elt, distort_and_compensate
import pycqed.measurement.randomized_benchmarking.randomized_benchmarking as rb
import pycqed.measurement.waveform_control.fluxpulse_predistortion as \
    fluxpulse_predistortion
from pycqed.measurement.pulse_sequences.single_qubit_tek_seq_elts import \
    get_pulse_dict_from_pars

station = None
kernel_dir = 'kernels/'
# You need to explicitly set this before running any functions from this module
# I guess there are cleaner solutions :)
cached_kernels = {}


def avoided_crossing_spec_seq(operation_dict, q0, q1, RO_target,
                              verbose=False,
                              upload=True):

    seq_name = 'avoidec_crossing_spec'
    seq = sequence.Sequence(seq_name)
    station.pulsar.update_channel_settings()
    el_list = []
    sequencer_config = operation_dict['sequencer_config']

    # N.B. Identities not needed in all cases
    pulse_combinations = ['X180 '+q0, 'SpecPulse '+q1, 'RO '+RO_target]
    pulses = []
    for p in pulse_combinations:
        pulses += [operation_dict[p]]
    el = multi_pulse_elt(0, station, pulses, sequencer_config)
    el_list.append(el)
    seq.append_element(el, trigger_wait=True)
    if upload:
        station.pulsar.program_awgs(seq, *el_list, verbose=verbose)
    return seq, el_list


def two_qubit_off_on(q0_pulse_pars, q1_pulse_pars, RO_pars,
                     return_seq=False, verbose=False):

    seq_name = '2_qubit_OffOn_sequence'
    seq = sequence.Sequence(seq_name)
    station.pulsar.update_channel_settings()
    el_list = []
    # Create a dict with the parameters for all the pulses
    q0_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q0_pulse_pars), ' q0')
    q1_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q1_pulse_pars), ' q1')
    RO_dict = {'RO': RO_pars}

    pulse_dict = {}
    pulse_dict.update(q0_pulses)
    pulse_dict.update(q1_pulses)
    pulse_dict.update(RO_dict)

    # N.B. Identities not needed in all cases
    pulse_combinations = [['I q0', 'I q1', 'RO'],
                          ['X180 q0', 'I q1', 'RO'],
                          ['I q0', 'X180 q1', 'RO'],
                          ['X180 q0', 'X180 q1', 'RO']]

    for i, pulse_comb in enumerate(pulse_combinations):
        pulses = []
        for p in pulse_comb:
            pulses += [pulse_dict[p]]

        el = multi_pulse_elt(i, station, pulses)
        el_list.append(el)
        seq.append_element(el, trigger_wait=True)
    station.pulsar.program_awgs(seq, *el_list, verbose=verbose)
    if return_seq:
        return seq, el_list
    else:
        return seq_name


def three_qubit_off_on(q0_pulse_pars, q1_pulse_pars, q2_pulse_pars, RO_pars,
                       return_seq=False, verbose=False):

    seq_name = '3_qubit_OffOn_sequence'
    seq = sequence.Sequence(seq_name)
    station.pulsar.update_channel_settings()
    el_list = []
    # Create a dict with the parameters for all the pulses
    q0_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q0_pulse_pars), ' q0')
    q1_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q1_pulse_pars), ' q1')
    q2_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q2_pulse_pars), ' q2')
    RO_dict = {'RO': RO_pars}

    pulse_dict = {}
    pulse_dict.update(q0_pulses)
    pulse_dict.update(q1_pulses)
    pulse_dict.update(q2_pulses)
    pulse_dict.update(RO_dict)

    # N.B. Identities not needed in all cases
    pulse_combinations = [['I q0', 'I q1', 'I q2', 'RO'],
                          ['X180 q0', 'I q1', 'I q2', 'RO'],
                          ['I q0', 'X180 q1', 'I q2', 'RO'],
                          ['X180 q0', 'X180 q1', 'I q2', 'RO'],
                          ['I q0', 'I q1', 'X180 q2', 'RO'],
                          ['X180 q0', 'I q1', 'X180 q2', 'RO'],
                          ['I q0', 'X180 q1', 'X180 q2', 'RO'],
                          ['X180 q0', 'X180 q1', 'X180 q2', 'RO']]

    for i, pulse_comb in enumerate(pulse_combinations):
        pulses = []
        for p in pulse_comb:
            pulses += [pulse_dict[p]]

        el = multi_pulse_elt(i, station, pulses)
        el_list.append(el)
        seq.append_element(el, trigger_wait=True)
    station.pulsar.program_awgs(seq, *el_list, verbose=verbose)
    if return_seq:
        return seq, el_list
    else:
        return seq_name


def four_qubit_off_on(q0_pulse_pars,
                      q1_pulse_pars,
                      q2_pulse_pars,
                      q3_pulse_pars,
                      RO_pars,
                      return_seq=False, verbose=False):

    seq_name = '4_qubit_OffOn_sequence'
    seq = sequence.Sequence(seq_name)
    station.pulsar.update_channel_settings()
    el_list = []
    # Create a dict with the parameters for all the pulses
    q0_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q0_pulse_pars), ' q0')
    q1_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q1_pulse_pars), ' q1')
    q2_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q2_pulse_pars), ' q2')
    q3_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q3_pulse_pars), ' q3')
    RO_dict = {'RO': RO_pars}

    pulse_dict = {}
    pulse_dict.update(q0_pulses)
    pulse_dict.update(q1_pulses)
    pulse_dict.update(q2_pulses)
    pulse_dict.update(q3_pulses)
    pulse_dict.update(RO_dict)

    # N.B. Identities not needed in all cases
    pulse_combinations = [['I q0', 'I q1', 'I q2', 'I q3', 'RO'],
                          ['X180 q0', 'I q1', 'I q2', 'I q3', 'RO'],
                          ['I q0', 'X180 q1', 'I q2', 'I q3', 'RO'],
                          ['X180 q0', 'X180 q1', 'I q2', 'I q3', 'RO'],
                          ['I q0', 'I q1', 'X180 q2', 'I q3', 'RO'],
                          ['X180 q0', 'I q1', 'X180 q2', 'I q3', 'RO'],
                          ['I q0', 'X180 q1', 'X180 q2',  'I q3', 'RO'],
                          ['X180 q0', 'X180 q1', 'X180 q2',  'I q3', 'RO'],
                          ['I q0', 'I q1', 'I q2', 'X180 q3', 'RO'],
                          ['X180 q0', 'I q1', 'I q2', 'X180 q3', 'RO'],
                          ['I q0', 'X180 q1', 'I q2', 'X180 q3', 'RO'],
                          ['X180 q0', 'X180 q1', 'I q2', 'X180 q3', 'RO'],
                          ['I q0', 'I q1', 'X180 q2', 'X180 q3', 'RO'],
                          ['X180 q0', 'I q1', 'X180 q2', 'X180 q3', 'RO'],
                          ['I q0', 'X180 q1', 'X180 q2',  'X180 q3', 'RO'],
                          ['X180 q0', 'X180 q1', 'X180 q2',  'X180 q3', 'RO']]

    for i, pulse_comb in enumerate(pulse_combinations):
        pulses = []
        for p in pulse_comb:
            pulses += [pulse_dict[p]]

        el = multi_pulse_elt(i, station, pulses)
        el_list.append(el)
        seq.append_element(el, trigger_wait=True)
    station.pulsar.program_awgs(seq, *el_list, verbose=verbose)
    if return_seq:
        return seq, el_list
    else:
        return seq_name


def five_qubit_off_on(q0_pulse_pars,
                      q1_pulse_pars,
                      q2_pulse_pars,
                      q3_pulse_pars,
                      q4_pulse_pars,
                      RO_pars,
                      return_seq=False, verbose=False):

    seq_name = '5_qubit_OffOn_sequence'
    seq = sequence.Sequence(seq_name)
    station.pulsar.update_channel_settings()
    el_list = []
    # Create a dict with the parameters for all the pulses
    q0_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q0_pulse_pars), ' q0')
    q1_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q1_pulse_pars), ' q1')
    q2_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q2_pulse_pars), ' q2')
    q3_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q3_pulse_pars), ' q3')
    q4_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q4_pulse_pars), ' q4')
    RO_dict = {'RO': RO_pars}

    pulse_dict = {}
    pulse_dict.update(q0_pulses)
    pulse_dict.update(q1_pulses)
    pulse_dict.update(q2_pulses)
    pulse_dict.update(q3_pulses)
    pulse_dict.update(q4_pulses)
    pulse_dict.update(RO_dict)

    # N.B. Identities not needed in all cases
    pulse_combinations = [['I q0', 'I q1', 'I q2', 'I q3', 'I q4', 'RO'],
                          ['X180 q0', 'I q1', 'I q2', 'I q3', 'I q4', 'RO'],
                          ['I q0', 'X180 q1', 'I q2', 'I q3', 'I q4', 'RO'],
                          ['X180 q0', 'X180 q1', 'I q2', 'I q3', 'I q4', 'RO'],
                          ['I q0', 'I q1', 'X180 q2', 'I q3', 'I q4', 'RO'],
                          ['X180 q0', 'I q1', 'X180 q2', 'I q3', 'I q4', 'RO'],
                          ['I q0', 'X180 q1', 'X180 q2',
                              'I q3', 'I q4', 'RO'],
                          ['X180 q0', 'X180 q1', 'X180 q2',
                              'I q3', 'I q4', 'RO'],
                          ['I q0', 'I q1', 'I q2', 'X180 q3', 'I q4', 'RO'],
                          ['X180 q0', 'I q1', 'I q2', 'X180 q3', 'I q4', 'RO'],
                          ['I q0', 'X180 q1', 'I q2', 'X180 q3', 'I q4', 'RO'],
                          ['X180 q0', 'X180 q1', 'I q2',
                              'X180 q3', 'I q4', 'RO'],
                          ['I q0', 'I q1', 'X180 q2', 'X180 q3', 'I q4', 'RO'],
                          ['X180 q0', 'I q1', 'X180 q2',
                              'X180 q3', 'I q4', 'RO'],
                          ['I q0', 'X180 q1', 'X180 q2',
                              'X180 q3', 'I q4', 'RO'],
                          ['X180 q0', 'X180 q1', 'X180 q2',
                              'X180 q3', 'I q4', 'RO'],
                          ['I q0', 'I q1', 'I q2', 'I q3', 'X180 q4', 'RO'],
                          ['X180 q0', 'I q1', 'I q2', 'I q3', 'X180 q4', 'RO'],
                          ['I q0', 'X180 q1', 'I q2', 'I q3', 'X180 q4', 'RO'],
                          ['X180 q0', 'X180 q1', 'I q2',
                              'I q3', 'X180 q4', 'RO'],
                          ['I q0', 'I q1', 'X180 q2', 'I q3', 'X180 q4', 'RO'],
                          ['X180 q0', 'I q1', 'X180 q2',
                              'I q3', 'X180 q4', 'RO'],
                          ['I q0', 'X180 q1', 'X180 q2',
                              'I q3', 'X180 q4', 'RO'],
                          ['X180 q0', 'X180 q1', 'X180 q2',
                              'I q3', 'X180 q4', 'RO'],
                          ['I q0', 'I q1', 'I q2', 'X180 q3', 'X180 q4', 'RO'],
                          ['X180 q0', 'I q1', 'I q2',
                              'X180 q3', 'X180 q4', 'RO'],
                          ['I q0', 'X180 q1', 'I q2',
                              'X180 q3', 'X180 q4', 'RO'],
                          ['X180 q0', 'X180 q1', 'I q2',
                              'X180 q3', 'X180 q4', 'RO'],
                          ['I q0', 'I q1', 'X180 q2',
                              'X180 q3', 'X180 q4', 'RO'],
                          ['X180 q0', 'I q1', 'X180 q2',
                              'X180 q3', 'X180 q4', 'RO'],
                          ['I q0', 'X180 q1', 'X180 q2',
                              'X180 q3', 'X180 q4', 'RO'],
                          ['X180 q0', 'X180 q1', 'X180 q2',  'X180 q3', 'X180 q4', 'RO']]

    for i, pulse_comb in enumerate(pulse_combinations):
        pulses = []
        for p in pulse_comb:
            pulses += [pulse_dict[p]]

        el = multi_pulse_elt(i, station, pulses)
        el_list.append(el)
        seq.append_element(el, trigger_wait=True)
    station.pulsar.program_awgs(seq, *el_list, verbose=verbose)
    if return_seq:
        return seq, el_list
    else:
        return seq_name


def two_qubit_AllXY(operation_dict, q0='q0', q1='q1', RO_target='all',
                    sequence_type='simultaneous',
                    replace_q1_pulses_X180=False,
                    double_points=True,
                    verbose=False, upload=True,
                    return_seq=False):
    """
    Performs an AllXY sequence on two qubits.
    Has the option of replacing pulses on q1 with pi pulses

    Args:
        operation_dict (dict) : dictionary containing all pulse parameters
        q0, q1         (str) : target qubits for the sequence
        RO_target      (str) : target for the RO, can be a qubit name or 'all'
        sequence_type  (str) : sequential | interleaved | simultaneous | sandwiched
                              q0|q0|q1|q1   q0|q1|q0|q1   q01|q01      q1|q0|q0|q1
            describes the order of the AllXY pulses
        replace_q1_pulses_X180 (bool) : if True replaces all pulses on q1 with
            X180 pulses.

        double_points (bool) : if True measures each point in the AllXY twice
        verbose       (bool) : verbose sequence generation
        upload        (bool) :
    """
    seq_name = 'two_qubit_AllXY_{}_{}'.format(q0, q1)
    seq = sequence.Sequence(seq_name)
    station.pulsar.update_channel_settings()
    el_list = []
    sequencer_config = operation_dict['sequencer_config']

    AllXY_pulse_combinations = [['I ', 'I '], ['X180 ', 'X180 '], ['Y180 ', 'Y180 '],
                                ['X180 ', 'Y180 '], ['Y180 ', 'X180 '],
                                ['X90 ', 'I '], ['Y90 ', 'I '], [
                                    'X90 ', 'Y90 '],
                                ['Y90 ', 'X90 '], ['X90 ', 'Y180 '], [
                                    'Y90 ', 'X180 '],
                                ['X180 ', 'Y90 '], ['Y180 ', 'X90 '], [
                                    'X90 ', 'X180 '],
                                ['X180 ', 'X90 '], ['Y90 ', 'Y180 '], [
                                    'Y180 ', 'Y90 '],
                                ['X180 ', 'I '], ['Y180 ', 'I '], [
                                    'X90 ', 'X90 '],
                                ['Y90 ', 'Y90 ']]
    if double_points:
        AllXY_pulse_combinations = [val for val in AllXY_pulse_combinations
                                    for _ in (0, 1)]

    if sequence_type == 'simultaneous':
        operation_dict = deepcopy(operation_dict)  # prevents overwriting of dict
        for key in operation_dict.keys():
            if q1 in key:
                operation_dict[key]['refpoint'] = 'start'
                operation_dict[key]['pulse_delay'] = 0

    pulse_list = []
    if not replace_q1_pulses_X180:
        for pulse_comb in AllXY_pulse_combinations:
            if sequence_type == 'interleaved' or sequence_type == 'simultaneous':
                pulse_list += [[pulse_comb[0] + q0] + [pulse_comb[0] + q1] +
                               [pulse_comb[1] + q0] + [pulse_comb[1] + q1] +
                               ['RO ' + RO_target]]
            elif sequence_type == 'sequential':
                pulse_list += [[pulse_comb[0] + q0] + [pulse_comb[1] + q0] +
                               [pulse_comb[0] + q1] + [pulse_comb[1] + q1] +
                               ['RO ' + RO_target]]
            elif sequence_type == 'sandwiched':
                pulse_list += [[pulse_comb[0] + q1] + [pulse_comb[0] + q0] +
                               [pulse_comb[1] + q0] + [pulse_comb[1] + q1] +
                               ['RO ' + RO_target]]
            else:
                raise ValueError("sequence_type {} must be in".format(sequence_type) +
                                 " ['interleaved', simultaneous', 'sequential', 'sandwiched']")
    else:
        for pulse_comb in AllXY_pulse_combinations:
            if sequence_type == 'interleaved' or sequence_type == 'simultaneous':
                pulse_list += [[pulse_comb[0] + q0] + ['X180 ' + q1] +
                               [pulse_comb[1] + q0] + ['X180 ' + q1] +
                               ['RO ' + RO_target]]
            elif sequence_type == 'sequential':
                pulse_list += [[pulse_comb[0] + q0] + [pulse_comb[1] + q0] +
                               ['X180 ' + q1] + ['X180 ' + q1] +
                               ['RO ' + RO_target]]
            elif sequence_type == 'sandwiched':
                pulse_list += [['X180 ' + q1] + [pulse_comb[0] + q0] +
                               [pulse_comb[1] + q0] + ['X180 ' + q1] +
                               ['RO ' + RO_target]]
            else:
                raise ValueError("sequence_type {} must be in".format(sequence_type) +
                                 " ['interleaved', simultaneous', 'sequential', 'sandwiched']")

    for i, pulse_comb in enumerate(pulse_list):
        pulses = []
        for p in pulse_comb:
            pulses += [operation_dict[p]]

        el = multi_pulse_elt(i, station, pulses, sequencer_config)
        el_list.append(el)
        seq.append_element(el, trigger_wait=True)
    if upload:
        station.pulsar.program_awgs(seq, *el_list, verbose=verbose)
    if return_seq:
        return seq, el_list
    else:
        return seq_name


def two_qubit_tomo_cardinal(cardinal,
                            q0_pulse_pars,
                            q1_pulse_pars,
                            RO_pars,
                            timings_dict,
                            verbose=False,
                            upload=True,
                            return_seq=False):

    seq_name = '2_qubit_Card_%d_seq' % cardinal
    seq = sequence.Sequence(seq_name)
    station.pulsar.update_channel_settings()
    el_list = []
    # Create a dict with the parameters for all the pulses
    q0_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q0_pulse_pars), ' q0')
    q1_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q1_pulse_pars), ' q1')
    RO_dict = {'RO': RO_pars}

    pulse_dict = {}
    pulse_dict.update(q0_pulses)
    pulse_dict.update(q1_pulses)
    pulse_dict.update(RO_dict)

    # Timings
    # FIXME: This dictionary should not be required? -MAR
    # NOTE: required in the CPhase tomo as input but not used
    QQ_buffer = timings_dict['QQ_buffer']
    wait_time = timings_dict['wait_time']
    msmt_buffer = timings_dict['msmt_buffer']

    tomo_list_q0 = ['I q0', 'X180 q0', 'Y90 q0',
                    'mY90 q0', 'X90 q0', 'mX90 q0']
    tomo_list_q1 = ['I q1', 'X180 q1', 'Y90 q1',
                    'mY90 q1', 'X90 q1', 'mX90 q1']

    # inner loop on q0
    prep_idx_q0 = int(cardinal % 6)
    prep_idx_q1 = int(((cardinal - prep_idx_q0)/6) % 6)

    prep_pulse_q0 = pulse_dict[tomo_list_q0[prep_idx_q0]]
    prep_pulse_q1 = pulse_dict[tomo_list_q1[prep_idx_q1]]

    prep_pulse_q1['pulse_delay'] = QQ_buffer + (prep_pulse_q0['sigma'] *
                                                prep_pulse_q0['nr_sigma'])

    RO_pars['pulse_delay'] += msmt_buffer - (prep_pulse_q1['sigma'] *
                                             prep_pulse_q1['nr_sigma'])

    # Calibration points
    cal_points = [['I q0', 'I q1', 'RO'],
                  ['I q0', 'I q1', 'RO'],
                  ['I q0', 'I q1', 'RO'],
                  ['I q0', 'I q1', 'RO'],
                  ['I q0', 'I q1', 'RO'],
                  ['I q0', 'I q1', 'RO'],
                  ['I q0', 'I q1', 'RO'],
                  ['X180 q0', 'I q1', 'RO'],
                  ['X180 q0', 'I q1', 'RO'],
                  ['X180 q0', 'I q1', 'RO'],
                  ['X180 q0', 'I q1', 'RO'],
                  ['X180 q0', 'I q1', 'RO'],
                  ['X180 q0', 'I q1', 'RO'],
                  ['X180 q0', 'I q1', 'RO'],
                  ['I q0', 'X180 q1', 'RO'],
                  ['I q0', 'X180 q1', 'RO'],
                  ['I q0', 'X180 q1', 'RO'],
                  ['I q0', 'X180 q1', 'RO'],
                  ['I q0', 'X180 q1', 'RO'],
                  ['I q0', 'X180 q1', 'RO'],
                  ['I q0', 'X180 q1', 'RO'],
                  ['X180 q0', 'X180 q1', 'RO'],
                  ['X180 q0', 'X180 q1', 'RO'],
                  ['X180 q0', 'X180 q1', 'RO'],
                  ['X180 q0', 'X180 q1', 'RO'],
                  ['X180 q0', 'X180 q1', 'RO'],
                  ['X180 q0', 'X180 q1', 'RO'],
                  ['X180 q0', 'X180 q1', 'RO']]

    for i in range(36):
        tomo_idx_q0 = int(i % 6)
        tomo_idx_q1 = int(((i - tomo_idx_q0)/6) % 6)

        # print(i,tomo_idx_q0,tomo_idx_q1)

        tomo_pulse_q0 = pulse_dict[tomo_list_q0[tomo_idx_q0]]
        tomo_pulse_q1 = pulse_dict[tomo_list_q1[tomo_idx_q1]]

        tomo_pulse_q0['pulse_delay'] = wait_time + (prep_pulse_q1['sigma'] *
                                                    prep_pulse_q1['nr_sigma'])

        tomo_pulse_q1['pulse_delay'] = QQ_buffer + (tomo_pulse_q0['sigma'] *
                                                    tomo_pulse_q0['nr_sigma'])
        pulse_list = [prep_pulse_q0,
                      prep_pulse_q1,
                      tomo_pulse_q0,
                      tomo_pulse_q1,
                      RO_pars]
        el = multi_pulse_elt(i, station, pulse_list)
        el_list.append(el)
        seq.append_element(el, trigger_wait=True)

    for i, pulse_comb in enumerate(cal_points):
        pulses = []
        for p in pulse_comb:
            pulses += [pulse_dict[p]]

        el = multi_pulse_elt(35+i, station, pulses)
        el_list.append(el)
        seq.append_element(el, trigger_wait=True)

    station.pulsar.program_awgs(seq, *el_list, verbose=verbose)
    if return_seq:
        return seq, el_list
    else:
        return seq_name


def two_qubit_tomo_bell(bell_state,
                        operation_dict,
                        qS,
                        qCZ,
                        RO_target,
                        distortion_dict,
                        CZ_disabled=False,
                        cal_points_with_flux_pulses=True,
                        verbose=False,
                        upload=True):
    '''

        qS is swap qubit
        qCZ is cphase qubit
    '''
    sequencer_config = operation_dict['sequencer_config']

    seq_name = '2_qubit_Bell_Tomo_%d_seq' % bell_state
    seq = sequence.Sequence(seq_name)
    station.pulsar.update_channel_settings()
    el_list = []
    tomo_list_qS = []
    tomo_list_qCZ = []
    # Tomo pulses span a basis covering all the cardinal points
    tomo_pulses = ['I ', 'X180 ', 'Y90 ', 'mY90 ', 'X90 ', 'mX90 ']
    for tp in tomo_pulses:
        tomo_list_qS += [tp+qS]
        tomo_list_qCZ += [tp+qCZ]

    ###########################
    # Defining sub sequences #
    ###########################
    # This forms the base sequence, note that gate1, gate2 and after_pulse will
    # be replaced to prepare the desired state and tomo1 and tomo2 will be
    # replaced with tomography pulses
    base_sequence = (
        ['gate1 ' + qS, 'gate2 ' + qCZ,
         'SWAP '+qS, 'CZ ' + qCZ, 'rSWAP ' + qS,
         'SWAP_corr ' + qS, 'CZ_corr ' + qCZ,
         'after_pulse ' + qCZ, 'tomo1 '+qCZ, 'tomo2 '+qS, 'RO '+RO_target])

    # Calibration points
    # every calibration point is repeated 7 times to have 64 elts in totalb
    cal_points = [['I '+qCZ, 'I '+qS, 'RO '+RO_target]]*7 +\
                  [['I '+qCZ, 'X180 '+qS, 'RO '+RO_target]]*7 +\
                  [['X180 '+qCZ, 'I '+qS, 'RO '+RO_target]]*7 +\
                  [['X180 '+qCZ, 'X180 '+qS, 'RO '+RO_target]]*7

    if CZ_disabled:
        operation_dict['CZ '+qCZ]['amplitude'] = 0
        operation_dict['CZ '+qCZ]['phase_corr_pulse_amp'] = 0

    ################################################
    # Creating additional pulses for this sequence #
    ################################################
    # the recovery SWAP is identical to the regular SWAP operation, unless
    # an rSWAP is explicitly contained in the operation dict
    if ('rSWAP ' + qS) not in operation_dict.keys():
        operation_dict['rSWAP ' + qS] = deepcopy(operation_dict['SWAP ' + qS])
    operation_dict['CZ_corr ' + qCZ]['refpoint'] = 'simultaneous'

    ################
    # Bell states  #
    ################
    if bell_state == 0:  # |Phi_m>=|00>-|11>
        gate1 = 'Y90 ' + qS
        gate2 = 'Y90 ' + qCZ
        after_pulse = 'mY90 ' + qCZ
    elif bell_state == 1:  # |Phi_p>=|00>+|11>
        gate1 = 'mY90 ' + qS
        gate2 = 'Y90 ' + qCZ
        after_pulse = 'mY90 ' + qCZ
    elif bell_state == 2:  # |Psi_m>=|01> - |10>
        gate1 = 'Y90 ' + qS
        gate2 = 'mY90 ' + qCZ
        after_pulse = 'mY90 ' + qCZ
    elif bell_state == 3:  # |Psi_p>=|01> + |10>
        gate1 = 'mY90 ' + qS
        gate2 = 'mY90 ' + qCZ
        after_pulse = 'mY90 ' + qCZ

    # Below are states with the initial pulse on the CP-qubit disabled
    # these are not Bell states but are used for debugging
    elif bell_state == 0+10:  # |00>+|11>
        gate1 = 'Y90 ' + qS
        gate2 = 'I ' + qCZ
        after_pulse = 'mY90 ' + qCZ
    elif bell_state == 1+10:
        gate1 = 'mY90 ' + qS
        gate2 = 'I ' + qCZ
        after_pulse = 'mY90 ' + qCZ
    elif bell_state == 2+10:  # |01> - |10>
        gate1 = 'Y90 ' + qS
        gate2 = 'I ' + qCZ
        after_pulse = 'mY90 ' + qCZ
    elif bell_state == 3+10:
        gate1 = 'mY90 ' + qS
        gate2 = 'I ' + qCZ
        after_pulse = 'mY90 ' + qCZ

    # Below are states with the initial pulse on the SWAP-qubit disabled
    # these are not Bell states but are used for debugging
    elif bell_state == 0 + 20:  # |00>+|11>
        gate1 = 'I ' + qS
        gate2 = 'Y90 ' + qCZ
        after_pulse = 'mY90 ' + qCZ
    elif bell_state == 1 + 20:  # |01> - |10>
        gate1 = 'I ' + qS
        gate2 = 'Y90 ' + qCZ
        after_pulse = 'mY90 ' + qCZ
    elif bell_state == 2 + 20:
        gate1 = 'I ' + qS
        gate2 = 'mY90 ' + qCZ
        after_pulse = 'mY90 ' + qCZ
    elif bell_state == 3 + 20:
        gate1 = 'mY90 ' + qS
        gate2 = 'mY90 ' + qCZ
        after_pulse = 'mY90 ' + qCZ

    print('Compensation qCP {:.3f}'.format(
        operation_dict['CZ_corr ' + qCZ]['amplitude']))
    print('Compensation qS {:.3f}'.format(
        operation_dict['SWAP_corr ' + qS]['amplitude']))

    ########################################################
    #  Here the actual pulses of all elements get defined  #
    ########################################################
    # We start by replacing the state prepartion pulses
    base_sequence[0] = gate1
    base_sequence[1] = gate2
    base_sequence[7] = after_pulse

    seq_pulse_list = []

    for i in range(36):
        tomo_idx_qS = int(i % 6)
        tomo_idx_qCZ = int(((i - tomo_idx_qS)/6) % 6)
        base_sequence[8] = tomo_list_qCZ[tomo_idx_qCZ]
        base_sequence[9] = tomo_list_qS[tomo_idx_qS]
        seq_pulse_list += [deepcopy(base_sequence)]
    print(len(cal_points))
    for cal_pulses in cal_points:
        if cal_points_with_flux_pulses:
            base_sequence[0] = 'I ' + qS
            base_sequence[1] = 'I ' + qCZ
            base_sequence[7] = 'I ' + qCZ
            base_sequence[-3:] = cal_pulses
            seq_pulse_list += [deepcopy(base_sequence)]
        else:
            seq_pulse_list += [cal_pulses]

    for i, pulse_list in enumerate(seq_pulse_list):
        pulses = []
        for p in pulse_list:
            pulses += [operation_dict[p]]
        el = multi_pulse_elt(i, station, pulses, sequencer_config)
        if distortion_dict is not None:
            print('\rDistorting element {}/{} '.format(i+1,
                                                       len(seq_pulse_list)),
                  end='')
            el = distort_and_compensate(
                el, distortion_dict)
        el_list.append(el)
        seq.append_element(el, trigger_wait=True)

    station.pulsar.program_awgs(seq, *el_list, verbose=verbose)

    return seq, el_list


def cphase_fringes(phases, q0_pulse_pars, q1_pulse_pars, RO_pars,
                   swap_pars_q0, cphase_pars_q1, timings_dict,
                   distortion_dict, verbose=False, upload=True, return_seq=False):
    '''
    '''
    preloaded_kernels_vec = preload_kernels_func(distortion_dict)
    original_delay = deepcopy(RO_pars)[0]['pulse_delay']
    seq_name = 'CPhase'
    seq = sequence.Sequence(seq_name)
    station.pulsar.update_channel_settings()
    el_list = []
    # print(q0_pulse_pars)
    q0_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q0_pulse_pars[0]), ' q0')
    q1_pulses = add_suffix_to_dict_keys(
        get_pulse_dict_from_pars(q1_pulse_pars[0]), ' q1')

    pulse_dict = {}
    pulse_dict.update(q0_pulses)
    pulse_dict.update(q1_pulses)
    pulse_dict.update({'RO': RO_pars[0]})
    # print({'RO': RO_pars})

    # Timings
    buffer_mw_flux = timings_dict[0]['buffer_mw_flux']
    buffer_flux_mw = timings_dict[0]['buffer_flux_mw']
    msmt_buffer = timings_dict[0]['msmt_buffer']
    dead_time = timings_dict[0]['dead_time']
    # print(buffer_mw_flux,buffer_flux_mw,msmt_buffer,dead_time)

    # defining main pulses
    exc_pulse = deepcopy(pulse_dict['X180 q0'])
    exc_pulse['pulse_delay'] += 0.01e-6
    swap_pulse_1 = deepcopy(swap_pars_q0[0])
    # print(swap_pulse_1)
    swap_pulse_1['pulse_delay'] = buffer_mw_flux + \
        exc_pulse['sigma']*exc_pulse['nr_sigma']

    ramsey_1 = deepcopy(pulse_dict['Y90 q1'])
    ramsey_1['pulse_delay'] = buffer_flux_mw + swap_pulse_1['length']
    cphase_pulse = cphase_pars_q1[0]
    cphase_amp = cphase_pulse['amplitude']
    cphase_pulse['pulse_delay'] = buffer_mw_flux + \
        ramsey_1['sigma']*ramsey_1['nr_sigma']
    ramsey_2 = deepcopy(pulse_dict['X90 q1'])
    ramsey_2['pulse_delay'] = buffer_flux_mw + cphase_pulse['length']

    swap_pulse_2 = deepcopy(swap_pars_q0[0])
    swap_pulse_2['pulse_delay'] = buffer_mw_flux + \
        ramsey_2['sigma']*ramsey_2['nr_sigma']
    RO_pars[0]['pulse_delay'] = msmt_buffer + swap_pulse_2['length']

    # defining compensation pulses
    swap_comp_1 = deepcopy(swap_pulse_1)
    swap_pulse_1['pulse_delay'] = RO_pars[0]['length'] + dead_time
    cphase_comp = deepcopy(cphase_pulse)
    swap_comp_2 = deepcopy(swap_pulse_2)

    dead_time_pulse = {'pulse_type': 'SquarePulse',
                       'pulse_delay': RO_pars[0]['pulse_delay'],
                       'channel': swap_pars_q0[0]['channel'],
                       'amplitude': 0,
                       'length': dead_time}

    for i, ph2 in enumerate(phases[0]):
        # print(ph2)
        ramsey_2['phase'] = ph2

        cphase_pulse['amplitude'] = cphase_amp
        pulse_list = [exc_pulse,
                      swap_pulse_1,
                      ramsey_1,
                      cphase_pulse,
                      ramsey_2,
                      swap_pulse_2,
                      RO_pars[0],
                      swap_comp_1,
                      cphase_comp,
                      swap_comp_2,
                      dead_time_pulse]
        el = multi_pulse_elt(2*i, station, pulse_list)
        el_list.append(el)

        cphase_pulse['amplitude'] = 0.
        pulse_list = [exc_pulse,
                      swap_pulse_1,
                      ramsey_1,
                      cphase_pulse,
                      ramsey_2,
                      swap_pulse_2,
                      RO_pars[0],
                      swap_comp_1,
                      cphase_comp,
                      swap_comp_2,
                      dead_time_pulse]
        el = multi_pulse_elt(2*i+1, station, pulse_list)
        el_list.append(el)

    # Compensations
    for i, el in enumerate(el_list):
        if distortion_dict is not None:
            el = distort_and_compensate(
                el, distortion_dict, preloaded_kernels_vec)
            el_list[i] = el
        seq.append_element(el, trigger_wait=True)
    cal_points = 4
    RO_pars[0]['pulse_delay'] = original_delay

    # Calibration points
    cal_points = [['I q0', 'I q1', 'RO'],
                  ['I q0', 'I q1', 'RO'],
                  ['X180 q0', 'I q1', 'RO'],
                  ['X180 q0', 'I q1', 'RO'],
                  ['I q0', 'X180 q1', 'RO'],
                  ['I q0', 'X180 q1', 'RO'],
                  ['X180 q0', 'X180 q1', 'RO'],
                  ['X180 q0', 'X180 q1', 'RO']]

    for i, pulse_comb in enumerate(cal_points):
        pulses = []
        for p in pulse_comb:
            pulses += [pulse_dict[p]]
        pulses[0]['pulse_delay'] += 0.01e-6

        el = multi_pulse_elt(2*len(phases)+i, station, pulses)
        el_list.append(el)
        seq.append_element(el, trigger_wait=True)

    # upload
    if upload:
        station.pulsar.program_awgs(seq, *el_list, verbose=verbose)
    if return_seq:
        return seq, el_list
    else:
        return seq


def preload_kernels_func(distortion_dict):
    output_dict = {ch: [] for ch in distortion_dict['ch_list']}
    for ch in distortion_dict['ch_list']:
        for kernel in distortion_dict[ch]:
            if kernel is not '':
                if kernel in cached_kernels.keys():
                    print('Cached {}'.format(kernel_dir+kernel))
                    output_dict[ch].append(cached_kernels[kernel])
                else:
                    print('Loading {}'.format(kernel_dir+kernel))
                    # print(os.path.isfile('kernels/'+kernel))
                    kernel_vec = np.loadtxt(kernel_dir+kernel)
                    output_dict[ch].append(kernel_vec)
                    cached_kernels.update({kernel: kernel_vec})
    return output_dict

def two_qubit_tomo_cphase_cardinal(cardinal_state,
                        operation_dict,
                        qS,
                        qCZ,
                        RO_target,
                        distortion_dict,
                        CZ_disabled=False,
                        cal_points_with_flux_pulses=True,
                        verbose=False,
                        upload=True):
    '''
        qS is swap qubit
        qCZ is cphase qubit
    '''
    sequencer_config = operation_dict['sequencer_config']

    seq_name = '2_qubit_CPhase_Cardinal_Tomo_%d_seq' % cardinal_state
    seq = sequence.Sequence(seq_name)
    station.pulsar.update_channel_settings()
    el_list = []
    tomo_list_qS = []
    tomo_list_qCZ = []
    # Tomo pulses span a basis covering all the cardinal points
    tomo_pulses = ['I ', 'X180 ', 'Y90 ', 'mY90 ', 'X90 ', 'mX90 ']
    for tp in tomo_pulses:
        tomo_list_qS += [tp+qS]
        tomo_list_qCZ += [tp+qCZ]

    ###########################
    # Defining sub sequences #
    ###########################
    # This forms the base sequence, note that gate1, gate2 and after_pulse will
    # be replaced to prepare the desired state and tomo1 and tomo2 will be
    # replaced with tomography pulses
    base_sequence = (
        ['gate1 ' + qS, 'gate2 ' + qCZ,
         'SWAP '+qS, 'CZ ' + qCZ, 'rSWAP ' + qS,
         'SWAP_corr ' + qS, 'CZ_corr ' + qCZ,
         'after_pulse ' + qCZ, 'tomo1 '+qCZ, 'tomo2 '+qS, 'RO '+RO_target])

    # Calibration points
    # every calibration point is repeated 7 times to have 64 elts in total
    cal_points = [['I '+qCZ, 'I '+qS, 'RO '+RO_target]]*7 +\
                  [['I '+qCZ, 'X180 '+qS, 'RO '+RO_target]]*7 +\
                  [['X180 '+qCZ, 'I '+qS, 'RO '+RO_target]]*7 +\
                  [['X180 '+qCZ, 'X180 '+qS, 'RO '+RO_target]]*7

    if CZ_disabled:
        operation_dict['CZ '+qCZ]['amplitude'] = 0
        operation_dict['CZ '+qCZ]['phase_corr_pulse_amp'] = 0

    ################################################
    # Creating additional pulses for this sequence #
    ################################################
    # the recovery SWAP is identical to the regular SWAP operation, unless
    # an rSWAP is explicitly contained in the operation dict
    if ('rSWAP ' + qS) not in operation_dict.keys():
        operation_dict['rSWAP ' + qS] = deepcopy(operation_dict['SWAP ' + qS])
    operation_dict['CZ_corr ' + qCZ]['refpoint'] = 'simultaneous'

    ################
    # cardinal states  #
    ################
    # here select the qubit gates (depending on cardinal_state)
    prep_idx_qS = int(cardinal_state % 6)
    prep_idx_qCZ = int(((cardinal_state - prep_idx_qS)/6) % 6)

    print('Compensation qCP {:.3f}'.format(
        operation_dict['CZ_corr ' + qCZ]['amplitude']))
    print('Compensation qS {:.3f}'.format(
        operation_dict['SWAP_corr ' + qS]['amplitude']))

    ########################################################
    #  Here the actual pulses of all elements get defined  #
    ########################################################
    # We start by replacing the state prepartion pulses
    base_sequence[0] = tomo_list_qS[prep_idx_qS]
    base_sequence[1] = tomo_list_qCZ[prep_idx_qCZ]
    base_sequence[7] = 'I ' + qCZ

    seq_pulse_list = []

    for i in range(36):
        tomo_idx_qS = int(i % 6)
        tomo_idx_qCZ = int(((i - tomo_idx_qS)/6) % 6)
        base_sequence[8] = tomo_list_qCZ[tomo_idx_qCZ]
        base_sequence[9] = tomo_list_qS[tomo_idx_qS]
        seq_pulse_list += [deepcopy(base_sequence)]
    print(len(cal_points))
    for cal_pulses in cal_points:
        if cal_points_with_flux_pulses:
            base_sequence[0] = 'I ' + qS
            base_sequence[1] = 'I ' + qCZ
            base_sequence[7] = 'I ' + qCZ
            base_sequence[-3:] = cal_pulses
            seq_pulse_list += [deepcopy(base_sequence)]
        else:
            seq_pulse_list += [cal_pulses]

    for i, pulse_list in enumerate(seq_pulse_list):
        pulses = []
        for p in pulse_list:
            pulses += [operation_dict[p]]
        el = multi_pulse_elt(i, station, pulses, sequencer_config)
        if distortion_dict is not None:
            print('\rDistorting element {}/{} '.format(i+1,
                                                       len(seq_pulse_list)),
                  end='')
            el = distort_and_compensate(
                el, distortion_dict)
        el_list.append(el)
        seq.append_element(el, trigger_wait=True)

    station.pulsar.program_awgs(seq, *el_list, verbose=verbose)

    return seq, el_list


def n_qubit_off_on(pulse_pars_list, RO_pars, return_seq=False, verbose=False,
                   parallel_pulses=False, preselection=False, upload=True,
                   RO_spacing=200e-9):
    n = len(pulse_pars_list)
    seq_name = '{}_qubit_OffOn_sequence'.format(n)
    seq = sequence.Sequence(seq_name)
    el_list = []

    # Create a dict with the parameters for all the pulses
    pulse_dict = {'RO': RO_pars, 'RO presel': deepcopy(RO_pars)}
    pulse_dict['RO presel']['refpoint'] = 'start'
    pulse_dict['RO presel']['pulse_delay'] = -RO_spacing
    for i, pulse_pars in enumerate(pulse_pars_list):
        pars = pulse_pars.copy()
        if i != 0 and parallel_pulses:
            pars['refpoint'] = 'simultaneous'
        pulses = add_suffix_to_dict_keys(
            get_pulse_dict_from_pars(pars), ' {}'.format(i))
        pulse_dict.update(pulses)

    # spacer to shift the reference point from the end of preselection RO
    # to end of the second RO
    spacerpulse = {'pulse_type': 'SquarePulse',
                    'channel': RO_pars['acq_marker_channel'],
                    'amplitude': 0.0,
                    'length': RO_spacing,
                    'refpoint': 'simultaneous',
                    'pulse_delay': 0}
    pulse_dict.update({'spacer': spacerpulse})

    # Create a list of required pulses
    pulse_combinations = []

    for pulse_list in itertools.product(*(n*[['I', 'X180']])):
        pulse_comb = (n+1)*['']
        for i, pulse in enumerate(pulse_list):
            pulse_comb[i] = pulse + ' {}'.format(i)
        pulse_comb[-1] = 'RO'
        if preselection:
            pulse_comb = pulse_comb + ['RO presel', 'spacer']
        pulse_combinations.append(pulse_comb)
    print('reloaded')
    for i, pulse_comb in enumerate(pulse_combinations):
        pulses = []
        for j, p in enumerate(pulse_comb):
            pulses += [pulse_dict[p]]

        el = multi_pulse_elt(i, station, pulses)
        el_list.append(el)
        seq.append_element(el, trigger_wait=True)
    if upload:
        station.pulsar.program_awgs(seq, *el_list, verbose=verbose)
    if return_seq:
        return seq, el_list
    else:
        return seq_name


def n_qubit_simultaneous_randomized_benchmarking_seq(qubit_list, RO_pars,
                                                     nr_cliffords_value, #scalar
                                                     nr_seeds,           #array
                                                     CxC_RB=True,
                                                     idx_for_RB=0,
                                                     net_clifford=0,
                                                     gate_decomposition='HZ',
                                                     interleaved_gate=None,
                                                     CZ_info_dict=None,
                                                     interleave_CZ=False,
                                                     cal_points=False,
                                                     spacing=30e-9,
                                                     post_msmt_delay=1e-6,
                                                     upload=True,
                                                     seq_name=None,
                                                     verbose=False,
                                                     return_seq=False):

    """
    Args:
        qubit_list (list): list of qubit objects to perfomr RB on
        RO_pars (dict): RO pulse pars for multiplexed RO on the qubits in
            qubit_list
        nr_cliffords_value (int): number of Cliffords in the sequence
        nr_seeds (numpy.ndarray): numpy.arange(nr_seeds_int) where nr_seeds_int
            is the number of times to repeat each Clifford sequence of
            length nr_cliffords_value
        CxC_RB (bool): whether to perform CxCxCx..xC RB or
            (CxIx..xI, IxCx..XI, ..., IxIx..xC) RB
        idx_for_RB (int): if CxC_RB==False, refers to the index of the
            pulse_pars in pulse_pars_list which will undergo the RB protocol
            (i.e. the position of the Z operator when we measure
            ZIII..I, IZII..I, IIZI..I etc.)
        net_clifford (int): 0 or 1; refers to the final state after the recovery
            Clifford has been applied. 0->gnd state, 1->exc state.
        gate_decomposition (str): 'HZ' or 'XY'
        interleaved_gate (str): used for regular single qubit Clifford IRB
            string referring to one of the gates in the single qubit
            Clifford group
        CZ_info_dict (dict): dict indicating which qbs in the CZ gates are the
            control and the target. Can have the following forms:
            either:    {'qbc': qb_control_name_CZ,
                        'qbt': qb_target_name_CZ}
            if only one CZ gate is interleaved;
            or:       {'CZi': {'qbc': qb_control_name_CZ,
                               'qbt': qb_target_name_CZ}}
            if multiple CZ gates are interleaved; CZi = [CZ0, CZ1, ...] where
            CZi is the c-phase gate between qbc->qbt.
            (We start counting from zero because we are programmers.)
        interleave_CZ (bool): Only used if CZ_info_dict != None
            True -> interleave the CZ gate
            False -> interleave the ICZ gate
        spacing (float): length of spacer pulse before and after the CZ's
        post_msmt_delay (float): NOT USED. Wait time between susequent RB
            sequences
        upload (bool): upload sequence to AWG or not
        seq_name (str): name of this sequences
        verbose (bool): print runtime info
        return_seq (bool): if True, returns seq, element list;
            if False, returns only seq_name
    """
    # get number of qubits
    n = len(qubit_list)

    # Get indices of qbc and qbt in the qubits_list and store them as
    # a list of tuples in CZ_info_list
    if CZ_info_dict is not None:
        qubit_names = [qb.name for qb in qubit_list]
        if type(list(CZ_info_dict.values())[0]) != dict:
            # if CZ_info_dict is not of the form
            # {'CZi': {'qbc': qbc_name, 'qbt': qbt_name}}
            CZ_info_list = [(qubit_names.index(CZ_info_dict['qbc']),
                             qubit_names.index(CZ_info_dict['qbt']))]
        else:
            # CZ_info_dict is of the form {'qbc': qbc_name, 'qbt': qbt_name}
            CZ_info_list = []
            for CZ_info in CZ_info_dict.values():
                CZ_info_list.append((qubit_names.index(CZ_info['qbc']),
                                     qubit_names.index(CZ_info['qbt'])))
        print('(qbc_idx, qbt_idx) = ', CZ_info_list)

    # Create a dict with the parameters for all the pulses
    pulse_dict = {'RO': RO_pars}

    for qb_nr, qb in enumerate(qubit_list):
        op_dict = qb.get_operation_dict()

        op_dict['Z0 ' + qb.name] = deepcopy(op_dict['Z180 ' + qb.name])
        op_dict['Z0 ' + qb.name]['basis_rotation'][qb.name] = 0

        spacerpulse = {'pulse_type': 'SquarePulse',
                       'channel': RO_pars['acq_marker_channel'],
                       'amplitude': 0.0,
                       'length': spacing,
                       'pulse_delay': 0,
                       'target_qubit': qb.name}
        op_dict.update({'spacer ' + qb.name: spacerpulse})

        if CZ_info_dict is not None:
            for CZ_idxs in CZ_info_list:
                qbc = qubit_list[CZ_idxs[0]]
                qbt = qubit_list[CZ_idxs[1]]
                # raise warning if the CZ pulse delay is not 0
                for i in op_dict:
                    if 'CZ' in i and op_dict[i]['pulse_delay']!=0:
                        raise ValueError('CZ {} {} pulse_delay is not 0!'.
                                         format(qbt.name, qbc.name))
                # if qb.name == qubit_list[CZ_idxs[1]].name:

                op_dict['ICZ ' + qb.name] = deepcopy(op_dict['I ' + qb.name])
                op_dict['ICZ ' + qb.name]['nr_sigma'] = 1
                op_dict['ICZ ' + qb.name]['sigma'] = \
                    qbc.get_operation_dict()[
                        'CZ ' + qbt.name + ' ' + qbc.name]['length']
        # if qb_nr != 0:
        for pulse_names in op_dict:
            op_dict[pulse_names]['refpoint'] = 'simultaneous'
        pulse_dict.update(op_dict)

    if CxC_RB:
        if seq_name is None:
            seq_name = 'CxC_RB_sequence'
        seq = sequence.Sequence(seq_name)
        el_list = []

        for elt_idx, i in enumerate(nr_seeds):

            if cal_points and (elt_idx == (len(nr_seeds)-2)):
                pulse_keys = n*['I']

                pulse_keys_w_suffix = []
                for k, pk in enumerate(pulse_keys):
                    pulse_keys_w_suffix.append(pk+' '+qubit_list[k % n].name)

                pulse_list = []
                for pkws in pulse_keys_w_suffix:
                    pulse_list.append(pulse_dict[pkws])

                if verbose:
                    from pprint import pprint
                    for i, p in enumerate(pulse_list):
                        print()
                        print(i % n)
                        pprint(p)

                el = multi_pulse_elt(elt_idx, station, pulse_list)

            elif cal_points and (elt_idx == (len(nr_seeds)-1)):
                pulse_keys = n*['X180']

                pulse_keys_w_suffix = []
                for k, pk in enumerate(pulse_keys):
                    pulse_keys_w_suffix.append(pk+' '+qubit_list[k % n].name)

                pulse_list = []
                for pkws in pulse_keys_w_suffix:
                    pulse_list.append(pulse_dict[pkws])

                if verbose:
                    from pprint import pprint
                    for i, p in enumerate(pulse_list):
                        print()
                        print(i % n)
                        pprint(p)
                el = multi_pulse_elt(elt_idx, station, pulse_list)
            else:
                clifford_sequence_list = []
                for index in range(n):
                    clifford_sequence_list.append(
                        rb.randomized_benchmarking_sequence(
                        nr_cliffords_value, desired_net_cl=net_clifford,
                        interleaved_gate=interleaved_gate))

                pulse_keys = rb.decompose_clifford_seq_n_qubits(
                    clifford_sequence_list,
                    gate_decomp=gate_decomposition)

                # interleave pulses for each qubit to obtain [pulse0_qb0,
                # pulse0_qb1,..pulse0_qbN,..,pulseN_qb0, pulseN_qb1,..,pulseN_qbN]
                pulse_keys_w_suffix = []
                for k, lst in enumerate(pulse_keys):
                    pulse_keys_w_suffix.append([x+' '+qubit_list[k % n].name
                                                for x in lst])

                if CZ_info_dict is not None:
                    # interleaved CZ_qbc and ICZ_qbt; this also changes
                    # pulse_keys_by_qubit
                    for pulse_keys_lst in pulse_keys_w_suffix[0:-2]:
                        if pulse_keys_lst[0][-3::] == qbc.name:
                            if interleave_CZ:
                                pulse_keys_lst.extend([
                                    'spacer ' + qbc.name,
                                    'CZ ' + qbt.name + ' ' + qbc.name,
                                    'spacer ' + qbc.name])
                            else:
                                pulse_keys_lst.extend([
                                    'spacer ' + qbc.name,
                                    'ICZ ' + qbc.name,
                                    'spacer ' + qbc.name])
                        if pulse_keys_lst[0][-3::] == qbt.name:
                            pulse_keys_lst.extend(['spacer '+qbt.name,
                                                   'ICZ ' + qbt.name,
                                                   'spacer '+qbt.name])

                pulse_keys_by_qubit = []
                for k in range(n):
                    pulse_keys_by_qubit.append([x for l in pulse_keys_w_suffix[k::n]
                                                for x in l])
                # make all qb sequences the same length
                max_len = 0
                for pl in pulse_keys_by_qubit:
                    if len(pl) > max_len:
                        max_len = len(pl)
                for ii, pl in enumerate(pulse_keys_by_qubit):
                    if len(pl) < max_len:
                        pl += (max_len-len(pl))*['I ' + qubit_list[ii].name]

                pulse_list = []
                for j in range(len(pulse_keys_by_qubit[0])):
                    for k in range(n):
                        pulse_list.append(deepcopy(pulse_dict[pulse_keys_by_qubit[k][j]]))

                refpoint = []
                # firstssb = False

                for p in pulse_list:
                    p['refpoint'] = 'end'

                a = [iii for iii in pulse_list if
                     iii['pulse_type']=='SSB_DRAG_pulse']
                a[0]['refpoint'] = 'end'
                refpoint = [a[0]['target_qubit']]

                for p in a[1:]:
                    if p['target_qubit'] not in refpoint:
                        p['refpoint'] = 'start'
                        refpoint.append(p['target_qubit'])
                    else:
                        p['refpoint'] = 'end'
                        refpoint = [p['target_qubit']]
                    # print(p['target_qubit'])
                    # print(p['refpoint'])
                    # print(refpoint)

                # # if qb0 has a Z_pulse, remove the 'refpoint' key in the pulse pars
                # # dict of the next qubit which has an SSB pulse
                # Zp0_idxs = [] # indices of the Z pulses on qb0
                # for w, px in enumerate(pulse_list):
                #     if (px['target_qubit'] == qubit_list[0].name and
                #                 px['pulse_type'] == 'Z_pulse'):
                #         Zp0_idxs.append(w)
                # if len(Zp0_idxs)>0:
                #     for y in Zp0_idxs:
                #         #look at the pulses applied on qb1...qbn
                #         qubit_length_pulse_list = pulse_list[y+1:y+n]
                #         # for each pulse in pulse_list where qb0 has a Z pulse,
                #         # look at the n-1 entries (qubits) and save the indices
                #         # of all SSB pulse parameters
                #         SSB_after_Z_on_qb0 = [y+1+qubit_length_pulse_list.index(j)
                #                               for j in qubit_length_pulse_list
                #                               if j['pulse_type'] != 'Z_pulse']
                #         if len(SSB_after_Z_on_qb0)>0:
                #             # if SSB pulses were found, delete the 'refpoint' entry
                #             # in the first qb after qb0 that has an SSB pulse
                #             first_SSB = next(y+1+qubit_length_pulse_list.index(j)
                #                              for j in qubit_length_pulse_list
                #                              if j['pulse_type'] != 'Z_pulse')
                #             temp_SSB_pulse = deepcopy(pulse_list[first_SSB])
                #             temp_SSB_pulse.pop('refpoint')
                #             pulse_list[first_SSB] = temp_SSB_pulse

                # add RO pulse pars at the end
                pulse_list += [RO_pars]

                # # find index of first pulse in pulse_list that is not
                # a Z pulse
                # # copy this pulse and set extra wait
                # try:
                #     first_x_pulse = next(j for j in pulse_list
                #                          if 'Z' not in j['pulse_type'])
                #     first_x_pulse_idx = pulse_list.index(first_x_pulse)
                # except:
                #     first_x_pulse_idx = 0
                # pulse_list[first_x_pulse_idx] = \
                #     deepcopy(pulse_list[first_x_pulse_idx])
                # pulse_list[first_x_pulse_idx]['pulse_delay'] += post_msmt_delay

                if verbose:
                    print('clifford_sequence_list')
                    for cl_l in clifford_sequence_list:
                        print(cl_l)
                    print('pulse_keys_by_qubit')
                    for p_l in pulse_keys_by_qubit:
                        print(p_l)
                    # print('\nfinal pulse_list ', pulse_list)
                    print('\nlen_pulse_list/nr_qubits ',(len(pulse_list)-1)/n)
                    print('\nnr_finite_duration_pulses/nr_qubits ',
                          len([x for x in pulse_list[:-1]
                               if 'Z' not in x['pulse_type']])/n)
                    print('\nnr_Z_pulses/nr_qubits ',
                          len([x for x in pulse_list
                               if 'Z' in x['pulse_type']])/n)
                    print('\nelt_idx ', elt_idx)
                    print('\ni ', i)

                    print('pulse_list')
                    from pprint import pprint
                    for i, p in enumerate(pulse_list):
                        print()
                        print(i % n)
                        pprint(p)

                el = multi_pulse_elt(elt_idx, station, pulse_list)
            el_list.append(el)
            seq.append_element(el, trigger_wait=True)

    else:

        if idx_for_RB > n-1:
            raise ValueError('idx_for_RB cannot exceed (nr_of_qubits-1).')

        if seq_name is None:
            seq_name = 'CxI_IxC_RB_sequence'
        seq = sequence.Sequence(seq_name)
        el_list = []

        for elt_idx, i in enumerate(nr_seeds):
            cl_seq = rb.randomized_benchmarking_sequence(
                nr_cliffords_value, desired_net_cl=net_clifford,
                interleaved_gate=interleaved_gate)
            pulse_keys = rb.decompose_clifford_seq(
                cl_seq,
                gate_decomp=gate_decomposition)

            C_pulse_list_keys = [x+' '+qubit_list[idx_for_RB].name
                                 for x in pulse_keys]
            pulse_list_keys = len(C_pulse_list_keys)*n*['']
            pulse_list_keys[idx_for_RB::n] = C_pulse_list_keys

            # populate remaining positions in pulse_list with I pulses if
            # the pulse from RB is a finite-duration pulse, or with Z0 if the
            # pulse from RB is a Z puls
            for index in range(0,int(len(pulse_list_keys)),n):
                for j, key in enumerate(pulse_list_keys[index:index+n]):
                    if key=='':
                        if 'Z' in pulse_list_keys[index:index+n][idx_for_RB]:
                            pulse_list_keys[index+j] = 'Z0 '+ qubit_list[j].name
                        else:
                            pulse_list_keys[index+j] = 'I '+ qubit_list[j].name

            # create pulse list to upload
            pulse_list = [pulse_dict[x] for x in pulse_list_keys]

            # if qb0 has a Z_pulse, remove the 'refpoint' key of the next
            # pulse dict which is not a Z_pulse
            Zp0_idxs = [] # indices of the Z pulses on qb0
            for w, px in enumerate(pulse_list):
                if (px['target_qubit'] == qubit_list[0].name
                        and px['pulse_type'] == 'Z_pulse'):
                    Zp0_idxs.append(w)
            if len(Zp0_idxs)>0:
                for y in Zp0_idxs:
                    #look at the pulses applied on qb1...qbn
                    qubit_length_pulse_list = pulse_list[y+1:y+n]
                    # for each pulse in pulse_list where qb0 has a Z pulse,
                    # look at the n-1 entries (qubits) and save the indices
                    # of all SSB pulse parameters
                    SSB_after_Z_on_qb0 = [y+1+qubit_length_pulse_list.index(j)
                                          for j in qubit_length_pulse_list
                                          if j['pulse_type']!='Z_pulse']
                    if len(SSB_after_Z_on_qb0)>0:
                        # if SSB pulses were found, delete the 'refpoint' entry
                        # in the first qb after qb0 that has an SSB pulse
                        first_SSB = next(y+1+qubit_length_pulse_list.index(j)
                                         for j in qubit_length_pulse_list
                                         if j['pulse_type']!='Z_pulse')
                        temp_SSB_pulse = deepcopy(pulse_list[first_SSB])
                        temp_SSB_pulse.pop('refpoint')
                        pulse_list[first_SSB] = temp_SSB_pulse

            # add RO pars
            pulse_list += [RO_pars]

            # # find first_x_pulse = first pulse in pulse_list that is not a Z pulse
            # # Copy this pulse and the next first_x_pulse_idx*n-first_x_pulse_idx,
            # # and set extra wait
            # try:
            #     first_x_pulse = next(j for j in pulse_list
            #                          if 'Z' not in j['pulse_type'])
            #     first_x_pulse_idx = pulse_list.index(first_x_pulse)
            # except:
            #     first_x_pulse_idx = 0
            # pulse_list[first_x_pulse_idx] = deepcopy(pulse_list[first_x_pulse_idx])
            # pulse_list[first_x_pulse_idx]['pulse_delay'] += post_msmt_delay

            if verbose:
                print('pulse_list_keys ', pulse_list_keys)
                # print('\nfinal pulse_list ', pulse_list)
                print('\nlen_pulse_list/nr_qubits ',(len(pulse_list)-1)/n)
                print('\nnr_finite_duration_pulses/nr_qubits ',
                      len([x for x in pulse_list[:-1]
                           if 'Z' not in x['pulse_type']])/n)
                print('\nnr_Z_pulses/nr_qubits ', len([x for x in pulse_list
                                                       if 'Z' in x['pulse_type']])/n)
                print('\n i ', i)
            el = multi_pulse_elt(elt_idx, station, pulse_list)
            el_list.append(el)
            seq.append_element(el, trigger_wait=True)

    if upload:
        station.pulsar.program_awgs(seq, *el_list, verbose=verbose)
    if return_seq:
        # return seq, el_list
        return pulse_list#pulse_keys_by_qubit
    else:
        return seq_name



def two_qubit_tomo_bell_qudev_seq(bell_state,
                                  qb_c,
                                  qb_t,
                                  RO_pars,
                                  basis_pulses=None,
                                  cal_state_repeats=7,
                                  spacing=100e-9,
                                  CZ_disabled=False,
                                  num_flux_pulses=0,
                                  verbose=False,
                                  # separation=100e-9,
                                  upload=True):
    '''
                 |spacing|spacing|
    |qCZ> --gate1--------*--------after_pulse-----| tomo |
                         |
    |qS > --gate2--------*------------------------| tomo |

        qb_c (qCZ) is the control qubit (pulsed)
        qb_t (qS) is the target qubit

    Args:
        bell_state (int): which Bell state to prepare according to:
            0 -> phi_Minus
            1 -> phi_Plus
            2 -> psi_Minus
            3 -> psi_Plus
        qb_c (qubit object): control qubit
        qb_t (qubit object): target qubit
        RO_pars (dict): RO pulse pars for multiplexed RO on the qb_c, qb_t
        basis_pulses (tuple): tomo pulses to be applied on each qubit
            default: ('I', 'X180', 'Y90', 'mY90', 'X90', 'mX90')
        cal_state_repeats (int): number of times to repeat each cal state
        spacing (float): spacing before and after CZ pulse; see diagram above
        CZ_disabled (bool): True -> same bell state preparation but without
            the CZ pulse; False -> normal bell state preparation
        num_flux_pulses (int): number of times to apply a flux pulse with the
            same length as the one used in the CZ gate before the entire
            sequence (before bell state prep).
            CURRENTLY NOT USED!
        verbose (bool): print runtime info
        upload (bool): whether to upload sequence to AWG or not
    Returns:
        seq: Sequence object
        el_list: list of elements
    '''


    if station is None:
        logging.warning('No station specified.')
    if basis_pulses is None:
        basis_pulses = ('I', 'X180', 'Y90', 'mY90', 'X90', 'mX90')
        logging.warning('basis_pulses not specified. Using the'
                        'following basis:\n{}'.format(basis_pulses))

    sequencer_config = station.sequencer_config
    seq_name = '2_qubit_Bell_Tomo_%d_seq' % bell_state
    seq = sequence.Sequence(seq_name)
    el_list = []

    operation_dict = {'RO': RO_pars}
    operation_dict.update(qb_c.get_operation_dict())
    operation_dict.update(qb_t.get_operation_dict())

    qCZ = qb_c.name
    qS = qb_t.name

    # add spacer pulses and ICZ pulses
    ##### very specific to GHZ preparation! #####
    for qb_name in [qCZ, qS]:
        spacerpulse = {'pulse_type': 'SquarePulse',
                       'channel': RO_pars['acq_marker_channel'],
                       'amplitude': 0.0,
                       'length': spacing,
                       'pulse_delay': 0,
                       'target_qubit': qb_name}
        operation_dict.update({'spacer ' + qb_name: spacerpulse})

        if not CZ_disabled:
            # create ICZ as a a copy of the I pulse but with the same length
            # as the CZ pulse
            for i, CZ_op in enumerate(['CZ ' + qS + ' ' + qCZ,
                                       'CZ ' + qS + ' ' + qCZ]):
                operation_dict['ICZ ' + qb_name] = \
                    deepcopy(operation_dict['I ' + qb_name])
                operation_dict['ICZ ' + qb_name]['sigma'] = \
                    operation_dict[CZ_op]['pulse_length']
                operation_dict['ICZ ' + qb_name]['nr_sigma'] = 1

    # make all pulses for qubit1 and qubit2 be simultaneous with qubit0
    for pulse_names in operation_dict:
        if operation_dict[pulse_names]['target_qubit'] == qS:
            operation_dict[pulse_names]['refpoint'] = 'start'

    # This forms the base sequences, note that gate1, gate2 and after_pulse will
    # be replaced to prepare the desired state.
    if not CZ_disabled:
        base_sequence = ['gate2 ' + qCZ, 'gate1 ' + qS,
                         'spacer ' + qCZ, 'spacer ' + qS,
                         'CZ ' + qS + ' ' + qCZ, 'ICZ ' + qS,
                         'spacer ' + qCZ, 'spacer ' + qS,
                         'after_pulse', 'I ' + qS]
        # base_sequence = num_flux_pulses*['flux ' + qCZ]
        # base_sequence.extend(
        #     ['gate1 ' + qS, 'gate2 ' + qCZ, 'CZ_corr ' + qS, 'CZ_corr ' + qCZ,
        #      'CZ ' + qCZ, 'after_pulse',
        #      'tomo1 '+qCZ, 'tomo2 '+qS])#, 'RO '+RO_target])
        cal_base_sequence = \
            ['I '+qCZ, 'I '+qS,
              'spacer ' + qCZ, 'spacer ' + qS,
              'ICZ ' + qCZ, 'ICZ '+qS,
              'spacer ' + qCZ, 'spacer ' + qS,
              'I '+qCZ, 'I '+qS]
    else:
        base_sequence = ['gate2 ' + qCZ, 'gate1 ' + qS,
                         'after_pulse', 'I ' + qS]
        cal_base_sequence = ['I '+qCZ, 'I '+qS, 'I '+qCZ, 'I '+qS]

    ################
    # Bell states  #
    ################
    if bell_state == 0:  # |Phi_m>=|00>-|11>
        gate2 = 'Y90 ' + qCZ
        gate1 = 'Y90 ' + qS
        after_pulse = 'mY90 ' + qCZ
    elif bell_state == 1:  # |Phi_p>=|00>+|11>
        gate2 = 'Y90 ' + qCZ
        gate1 = 'mY90 ' + qS
        after_pulse = 'mY90 ' + qCZ
    elif bell_state == 2:  # |Psi_m>=|01> - |10>
        gate2 = 'mY90 ' + qCZ
        gate1 = 'Y90 ' + qS
        after_pulse = 'mY90 ' + qCZ
    elif bell_state == 3:  # |Psi_p>=|01> + |10>
        gate2 = 'Y90 ' + qCZ
        gate1 = 'Y90 ' + qS
        after_pulse = 'Y90 ' + qCZ

    ########################################################
    #  Here the actual pulses of all elements get defined  #
    ########################################################
    # We start by replacing the state prepartion pulses
    base_sequence[base_sequence.index('gate1 ' + qS)] = gate1
    base_sequence[base_sequence.index('gate2 ' + qCZ)] = gate2
    base_sequence[base_sequence.index('after_pulse')] = after_pulse

    # Tomo pulses
    tomo_pulses = get_tomography_pulses(*[qCZ, qS],
                                        basis_pulses=basis_pulses)

    seq_pulse_list = len(tomo_pulses)*['']
    for i, t in enumerate(tomo_pulses):
        seq_pulse_list[i] = base_sequence + t

    # Calibration points
    # every calibration point is repeated 7 times to have 64 elts in totalb
    cal_pulses = get_tomography_pulses(*[qCZ, qS],
                                       basis_pulses=('I', 'X180'))
    for i, cal_p in enumerate(cal_pulses):
        cal_pulses[i] = cal_base_sequence + cal_p
    cal_pulses = [list(i) for i in np.repeat(np.asarray(cal_pulses),
                                            cal_state_repeats, axis=0)]
    for cal_p in cal_pulses:
        seq_pulse_list += [cal_p]

    # # set correct timing before making the pulse list
    # flux_pulse = operation_dict['CZ ' + qS + ' ' + qCZ]
    # flux_pulse['refpoint'] = 'end'
    # print('\n',separation)
    # print(flux_pulse['pulse_delay'])
    #
    # operation_dict['mY90afs ' + qCZ] = operation_dict['mY90s ' + qCZ]
    # operation_dict['mY90afs ' + qCZ]['pulse_delay'] = \
    #     separation - flux_pulse['pulse_delay']
    # operation_dict['mY90afs ' + qCZ]['refpoint'] = 'start'
    # if bell_state==3:
    #     operation_dict['Y90afs ' + qCZ] = operation_dict['Y90s ' + qCZ]
    #     operation_dict['Y90afs ' + qCZ]['pulse_delay'] = \
    #         separation - flux_pulse['pulse_delay']
    #     operation_dict['Y90afs ' + qCZ]['refpoint'] = 'start'

    for i, pulse_list in enumerate(seq_pulse_list):
        # print('pulse_list ', pulse_list)
        pulses = []
        for p in pulse_list:
            pulses += [operation_dict[p]]
            # if 'CZ' in p:
            #     from pprint import pprint
            #     pprint(operation_dict[p])
        # print('pulses ', len(pulses))
        # from pprint import pprint
        # pprint(pulses)
        # print('\n')
        pulses += [RO_pars]
        el = multi_pulse_elt(i, station, pulses, sequencer_config)
        el_list.append(el)
        seq.append_element(el, trigger_wait=True)

    if upload:
        station.pulsar.program_awgs(seq, *el_list, verbose=verbose)

    # return seq, seq_pulse_list
    return seq, el_list


def n_qubit_reset(qubit_names, operation_dict, reset_cycle_time, nr_resets=1,
                  return_seq=False, verbose=False, codeword_indices=None,
                  upload=True):
    """

    Timing constraints:
        The reset_cycle_time and the readout fixed point should be commensurate
        with the UHFQC trigger grid and the granularity of the AWGs.

        When the -ro_acq_marker_delay of the readout pulse is larger than
        the drive pulse length, then it is important that its length is a
        multiple of the granularity of the AWG.
    """

    n = len(qubit_names)
    seq_name = '{}_reset_x{}_sequence'.format(','.join(qubit_names), nr_resets)
    seq = sequence.Sequence(seq_name)
    el_list = []
    operation_dict = deepcopy(operation_dict)

    # set all qubit drive pulse delays to the maximum over the qubits
    max_delay = float('-inf')
    for qbn in qubit_names:
        max_delay = max(max_delay, operation_dict['X180 ' + qbn]['pulse_delay'])
    for qbn in qubit_names:
        for op in ['X180 ', 'X180s ', 'I ', 'Is ']:
            operation_dict[op + qbn]['pulse_delay'] = max_delay

    # sort qubits by pulse length
    pulse_lengths = []
    for qbn in qubit_names:
        pulse = operation_dict['X180 ' + qbn]
        pulse_lengths.append(pulse['sigma']*pulse['nr_sigma'])
    qubits_sorted = []
    for idx in np.argsort(pulse_lengths):
        qubits_sorted.append(qubit_names[idx])

    # increase the readout pulse delay such that the trigger would just
    # fit in the feedback element
    mw_pulse = operation_dict['X180 ' + qubits_sorted[-1]]
    ro_pulse = operation_dict['RO']
    ro_pulse['pulse_delay'] = max(ro_pulse['pulse_delay'],
                                  -ro_pulse['acq_marker_delay']
                                  - mw_pulse['pulse_delay']
                                  - mw_pulse['sigma']*mw_pulse['nr_sigma'])

    # create the wait pulse such that the length of the reset element would be
    # reset_cycle_time
    wait_time = mw_pulse['pulse_delay'] + mw_pulse['sigma']*mw_pulse['nr_sigma']
    wait_time += ro_pulse['pulse_delay'] + ro_pulse['length']
    wait_time = reset_cycle_time - wait_time
    wait_time -= station.pulsar.inter_element_spacing()
    wait_pulse = {'pulse_type': 'SquarePulse',
                  'channel': ro_pulse['acq_marker_channel'],
                  'amplitude': 0.0,
                  'length': wait_time,
                  'pulse_delay': 0}
    operation_dict.update({'I_fb': wait_pulse})

    # create the state-preparation elements and the state reset elements
    # the longest drive pulse is added last so that the readout does not overlap
    # with the drive pulses.
    qubit_order = np.arange(len(qubit_names))[np.argsort(pulse_lengths)]
    for state in range(2 ** n):
        pulses = []
        for i, qbn in enumerate(qubits_sorted):
            if state & (1 << qubit_names.index(qbn)):
                if i == 0:
                    pulses.append(operation_dict['X180 ' + qbn])
                else:
                    pulses.append(operation_dict['X180s ' + qbn])
            else:
                if i == 0:
                    pulses.append(operation_dict['I ' + qbn])
                else:
                    pulses.append(operation_dict['Is ' + qbn])
        pulses += [operation_dict['RO'], operation_dict['I_fb']]
        statename = str(state).zfill(len(str(2 ** n - 1)))
        el = multi_pulse_elt(state, station, pulses, name='prepare' + statename)
        el_list.append(el)
        el = multi_pulse_elt(state, station, pulses, name='reset' + statename,
                             trigger=False)
        el_list.append(el)

    # Create the sequence
    for state in range(2 ** n):
        statename = str(state).zfill(len(str(2 ** n - 1)))
        seq.insert('prepare'+statename, 'prepare'+statename, trigger_wait=True)
        for i in range(nr_resets):
            seq.insert('codeword' + statename + '_' + str(i), 'codeword',
                       trigger_wait=False)

    # Create the codeword table
    if codeword_indices is None:
        codeword_indices = np.arange(n)
    for state in range(2 ** n):
        statename = str(state).zfill(len(str(2 ** n - 1)))
        codeword = 0
        for qb_idx in range(n):
            if state & (1 << qb_idx):
                codeword |= (1 << codeword_indices[qb_idx])
        seq.codewords[codeword] = 'reset' + statename

    if upload:
        station.pulsar.program_awgs(seq, *el_list, verbose=verbose)

    if return_seq:
        return seq, el_list
    else:
        return seq_name

def parity_correction_seq(
        q0n, q1n, q2n, operation_dict, feedback_delay=900e-9,
        prep_sequence=None, reset=True, nr_echo_pulses=4,
        tomography_basis=('I', 'X180', 'Y90', 'mY90', 'X90', 'mX90'),
        upload=True, verbose=False, return_seq=False, preselection=False,
        ro_spacing=1e-6, cpmg_scheme=True):
    """

    |              elem 1               |  elem 2  | elem 3

    |q0> |======|---------*------------------------|======|
         | prep |         |                        | tomo |
    |q1> | q0,  |--mY90s--*--*--Y90--meas===-------| q0,  |
         | q2   |            |             ||      | q2   |
    |q2> |======|------------*------------X180-----|======|

    required elements:
        prep_sequence:
            contains everything up to the first readout
        Echo decoupling elements
            contains nr_echo_pulses X180 equally-spaced pulses on q0n, q2n
            FOR THIS TO WORK, ALL QUBITS MUST HAVE THE SAME PI-PULSE LENGTH
        feedback x 2 (for the two readout results):
            contains conditional Y80 on q1 and q2
        tomography x 6**2:
            measure all observables of the two qubits X/Y/Z
    """

    operation_dict['RO mux_presel'] = operation_dict['RO mux'].copy()
    operation_dict['RO mux_presel']['pulse_delay'] = \
        -ro_spacing - operation_dict['RO mux']['length'] - feedback_delay
    # used when nr_echo_pulses == 0:
    # operation_dict['RO mux_presel']['refpoint'] = 'start'
    # used when nr_echo_pulses != 0:
    operation_dict['RO mux_presel']['refpoint'] = 'end'
    operation_dict['I_fb'] = {
        'pulse_type': 'SquarePulse',
        'channel': operation_dict['RO mux']['acq_marker_channel'],
        'amplitude': 0.0,
        'length': feedback_delay,
        'pulse_delay': 0}
    operation_dict['RO presel_dummy'] = {
        'pulse_type': 'SquarePulse',
        'channel': operation_dict['RO mux']['acq_marker_channel'],
        'amplitude': 0.0,
        'length': ro_spacing + feedback_delay,
        'pulse_delay': 0}

    if prep_sequence is None:
        # prep_sequence = ['Y90 ' + q0n, 'Y90s ' + q2n]
        prep_sequence = ['Y90 ' + q0n, 'mY90s ' + q1n]

    # create the elements
    el_list = []

    # main (first) element
    pulse_sequence = deepcopy(prep_sequence)
    # w/o Echo pulses between CZ gates
    # pulse_sequence.append('mY90s ' + q1n)
    # pulse_sequence.append('CZ ' + q1n + ' ' + q0n)
    # pulse_sequence.append('CZ ' + q1n + ' ' + q2n)
    # pulse_sequence.append('Y90 ' + q1n)
    # pulse_sequence.append('RO ' + q1n)

    # used when nr_echo_pulses == 0
    # pulse_sequence.append('I_fb')

    # with Echo pulses between CZ gates
    pulse_sequence.append('CZ ' + q1n + ' ' + q0n)
    pulse_sequence.append('Y180 ' + q0n)
    pulse_sequence.append('Y90s ' + q2n)
    pulse_sequence.append('CZ ' + q1n + ' ' + q2n)
    pulse_sequence.append('Y180 ' + q0n)
    pulse_sequence.append('Y90s ' + q1n)
    pulse_sequence.append('RO ' + q1n)

    pulse_list = [operation_dict[pulse] for pulse in pulse_sequence]

    if nr_echo_pulses > 0:
        echo_sequence = get_decoupling_pulses(q0n, q2n,
                                              nr_pulses=nr_echo_pulses)

        DRAG_length = deepcopy(operation_dict['X180 '+q0n]['nr_sigma']) * \
                      deepcopy(operation_dict['X180 '+q0n]['sigma'])
        total_echo_pulses_length = feedback_delay + \
                                   operation_dict['RO mux']['length']
        if cpmg_scheme:
            start_end_delay = (total_echo_pulses_length
                               - nr_echo_pulses*DRAG_length) / \
                              2 / nr_echo_pulses
            echo_pulse_delay = 2*start_end_delay

            if start_end_delay < 0:
                logging.error("Dynamical decoupling pulses don't fit into the "
                              "feedback delay time")
            operation_dict['I_echo'] = {
                'pulse_type': 'SquarePulse',
                'channel': operation_dict['RO mux']['acq_marker_channel'],
                'amplitude': 0.0,
                'length': start_end_delay,
                'pulse_delay': 0}

            for i, pulse in enumerate(echo_sequence):
                single_op_dict = deepcopy(operation_dict[pulse])
                if 's' not in pulse:
                    single_op_dict['pulse_delay'] = \
                        (start_end_delay if i == 0 else echo_pulse_delay)
                    if i == 0:
                        single_op_dict['refpoint'] = 'start'
                pulse_list.append(single_op_dict)

        else:
            pulse_positions_func = lambda idx, N: np.sin(np.pi*idx/(2*N+2))**2
            pulse_delays_func = (lambda idx, N: total_echo_pulses_length*(
                pulse_positions_func(idx, N) -
                pulse_positions_func(idx-1, N)) -
                    ((0.5 if idx == 1 else 1)*DRAG_length))

            # total_delays = np.sum([pulse_delays_func(j, nr_echo_pulses)
            #                        for j in np.arange(1, nr_echo_pulses+1)] +
            #                       [pulse_delays_func(1, nr_echo_pulses)])
            if nr_echo_pulses*DRAG_length > total_echo_pulses_length:
                raise ValueError("Dynamical decoupling pulses don't fit "
                                 "into the feedback delay time")

            operation_dict['I_echo'] = {
                'pulse_type': 'SquarePulse',
                'channel': operation_dict['RO mux']['acq_marker_channel'],
                'amplitude': 0.0,
                'length': pulse_delays_func(1, nr_echo_pulses),
                'pulse_delay': 0}

            echo_idx = 0
            for i, pulse in enumerate(echo_sequence):
                single_op_dict = deepcopy(operation_dict[pulse])
                if 's' not in pulse:
                    echo_idx += 1
                    single_op_dict['pulse_delay'] = \
                        pulse_delays_func(echo_idx, nr_echo_pulses)
                    if i == 0:
                        single_op_dict['refpoint'] = 'start'
                pulse_list.append(single_op_dict)

        pulse_list.append(operation_dict['I_echo'])

    # else:
    #     pulse_sequence.append('I_fb')
    #     operation_dict['RO mux_presel']['refpoint'] = 'start'
    #     operation_dict['RO mux_presel']['pulse_delay'] = \
    #         -ro_spacing - operation_dict['RO mux']['length']

    if preselection:
        pulse_list.append(operation_dict['RO mux_presel'])
        pulse_list.append(operation_dict['RO presel_dummy'])

    el_main = multi_pulse_elt(0, station, pulse_list, trigger=True, name='main')
    el_list.append(el_main)

    # feedback elements
    fb_sequence_0 = ['I ' + q2n]
    fb_sequence_1 = ['X180 ' + q2n] if reset else ['I ' + q2n]
    pulse_list = [operation_dict[pulse] for pulse in fb_sequence_0]
    el_list.append(multi_pulse_elt(0, station, pulse_list, name='feedback_0',
                                   trigger=False, previous_element=el_main))
    pulse_list = [operation_dict[pulse] for pulse in fb_sequence_1]
    el_fb = multi_pulse_elt(1, station, pulse_list, name='feedback_1',
                            trigger=False, previous_element=el_main)
    el_list.append(el_fb)


    # tomography elements
    tomography_sequences = get_tomography_pulses(q0n, q2n,
                                                 basis_pulses=tomography_basis)
    for i, tomography_sequence in enumerate(tomography_sequences):
        tomography_sequence.append('RO mux')
        pulse_list = [operation_dict[pulse] for pulse in tomography_sequence]
        el_list.append(multi_pulse_elt(i, station, pulse_list, trigger=False,
                                       name='tomography_{}'.format(i),
                                       previous_element=el_fb))

    # create the sequence
    seq_name = 'Two qubit entanglement by parity measurement'
    seq = sequence.Sequence(seq_name)
    seq.codewords[0] = 'feedback_0'
    seq.codewords[1] = 'feedback_1'
    for i in range(len(tomography_basis)**2):
        seq.append('main_{}'.format(i), 'main', trigger_wait=True)
        seq.append('feedback_{}'.format(i), 'codeword', trigger_wait=False)
        seq.append('tomography_{}'.format(i), 'tomography_{}'.format(i),
                   trigger_wait=False)

    if upload:
        station.pulsar.program_awgs(seq, *el_list, verbose=verbose)

    if return_seq:
        return seq, el_list
    else:
        return seq_name


def n_qubit_tomo_seq(
        qubit_names, operation_dict, prep_sequence=None,
        prep_name=None,
        rots_basis=('I', 'X180', 'Y90', 'mY90', 'X90', 'mX90'),
        upload=True, verbose=False, return_seq=False,
        preselection=False, ro_spacing=1e-6):
    """

    """

    operation_dict['RO mux_presel'] = operation_dict['RO mux'].copy()
    operation_dict['RO mux_presel']['pulse_delay'] = -ro_spacing
    operation_dict['RO mux_presel']['refpoint'] = 'start'
    operation_dict['RO presel_dummy'] = {
        'pulse_type': 'SquarePulse',
        'channel': operation_dict['RO mux']['acq_marker_channel'],
        'amplitude': 0.0,
        'length': ro_spacing,
        'pulse_delay': 0}

    if prep_sequence is None:
        prep_sequence = ['Y90 ' + qubit_names[0]]

    # ######### add an I pulse of custom length
    # feedback_delay = 86*40e-9/3 - 100e-9
    # operation_dict['I_fb'] = {
    #     'pulse_type': 'SquarePulse',
    #     'channel': operation_dict['RO mux']['acq_marker_channel'],
    #     'amplitude': 0.0,
    #     'length': feedback_delay,
    #     'pulse_delay': 0,
    #     'refpoint': 'end'}
    # prep_sequence += ['I_fb']
    # operation_dict['RO mux_presel']['pulse_delay'] = \
    #     -ro_spacing - operation_dict['RO mux']['length'] - feedback_delay
    # operation_dict['RO presel_dummy']['length'] = ro_spacing + feedback_delay

    # create the elements
    el_list = []

    # tomography elements
    tomography_sequences = get_tomography_pulses(*qubit_names,
                                                 basis_pulses=rots_basis)
    for i, tomography_sequence in enumerate(tomography_sequences):
        pulse_list = [operation_dict[pulse] for pulse in prep_sequence]
        tomography_sequence.append('RO mux')
        if preselection:
            tomography_sequence.append('RO mux_presel')
            tomography_sequence.append('RO presel_dummy')
        pulse_list.extend([operation_dict[pulse] for pulse in
                           tomography_sequence])
        el_list.append(multi_pulse_elt(i, station, pulse_list, trigger=True,
                                       name='tomography_{}'.format(i)))

    # create the sequence
    if prep_name is None:
        seq_name = 'N-qubit tomography'
    else:
        seq_name = prep_name + ' tomography'
    seq = sequence.Sequence(seq_name)
    for i, tomography_sequence in enumerate(tomography_sequences):
        seq.append('tomography_{}'.format(i), 'tomography_{}'.format(i),
                   trigger_wait=True)

    if upload:
        station.pulsar.program_awgs(seq, *el_list, verbose=verbose)

    if return_seq:
        return seq, el_list
    else:
        return seq_name

def get_tomography_pulses(*qubit_names, basis_pulses=('I', 'X180', 'Y90',
                                                      'mY90', 'X90', 'mX90')):
    tomo_sequences = [[]]
    for i, qb in enumerate(qubit_names):
        if i == 0:
            qb = ' ' + qb
        else:
            qb = 's ' + qb
        tomo_sequences_new = []
        for sequence in tomo_sequences:
            for pulse in basis_pulses:
                tomo_sequences_new.append(sequence + [pulse+qb])
        tomo_sequences = tomo_sequences_new
    return tomo_sequences

def get_decoupling_pulses(*qubit_names, nr_pulses=4):
    if nr_pulses % 2 != 0:
        logging.warning('Odd number of dynamical decoupling pulses')
    echo_sequences = []
    for pulse in nr_pulses*['X180']:
        for i, qb in enumerate(qubit_names):
            if i == 0:
                qb = ' ' + qb
            else:
                qb = 's ' + qb
            echo_sequences.append(pulse+qb)
    return echo_sequences

def n_qubit_ref_seq(qubit_names, operation_dict, ref_desc, upload=True,
                    verbose=False, return_seq=False, preselection=False,
                    ro_spacing=1e-6):
    """
        Calibration points for arbitrary combinations

        Arguments:
            qubits: List of calibrated qubits for obtaining the pulse
                dictionaries.
            ref_desc: Description of the calibration sequence. Dictionary
                name of the state as key, and list of pulses names as values.
    """

    operation_dict['RO mux_presel'] = operation_dict['RO mux'].copy()
    operation_dict['RO mux_presel']['pulse_delay'] = -ro_spacing
    operation_dict['RO mux_presel']['refpoint'] = 'start'
    operation_dict['RO presel_dummy'] = {
        'pulse_type': 'SquarePulse',
        'channel': operation_dict['RO mux']['acq_marker_channel'],
        'amplitude': 0.0,
        'length': ro_spacing,
        'pulse_delay': 0}

    # create the elements
    el_list = []

    # calibration elements
    # calibration_sequences = []
    # for pulses in ref_desc:
    #     calibration_sequences.append(
    #         [pulse+' '+qb for qb, pulse in zip(qubit_names, pulses)])

    calibration_sequences = []
    for pulses in ref_desc:
        calibration_sequence_new = []
        for i, pulse in enumerate(pulses):
            if i == 0:
                qb = ' ' + qubit_names[i]
            else:
                qb = 's ' + qubit_names[i]
            calibration_sequence_new.append(pulse+qb)
        calibration_sequences.append(calibration_sequence_new)

    for i, calibration_sequence in enumerate(calibration_sequences):
        pulse_list = []
        calibration_sequence.append('RO mux')
        if preselection:
            calibration_sequence.append('RO mux_presel')
            calibration_sequence.append('RO presel_dummy')
        pulse_list.extend(
            [operation_dict[pulse] for pulse in calibration_sequence])
        el_list.append(multi_pulse_elt(i, station, pulse_list, trigger=True,
                                       name='Cal_{}'.format(i)))

    # create the sequence
    seq_name = 'Calibration'
    seq = sequence.Sequence(seq_name)
    for i, calibration_sequence in enumerate(calibration_sequences):
        seq.append('Cal_{}'.format(i), 'Cal_{}'.format(i), trigger_wait=True)

    if upload:
        station.pulsar.program_awgs(seq, *el_list, verbose=verbose)

    if return_seq:
        return seq, el_list
    else:
        return seq_name


def n_qubit_ref_all_seq(qubit_names, operation_dict, upload=True, verbose=False,
                        return_seq=False,
                        preselection=False, ro_spacing=1e-6):
    """
        Calibration points for all combinations
    """

    return n_qubit_ref_seq(qubit_names, operation_dict,
                           ref_desc=itertools.product(["I", "X180"],
                                                      repeat=len(qubit_names)),
                           upload=upload, verbose=verbose,
                           return_seq=return_seq, preselection=preselection,
                           ro_spacing=ro_spacing)

#### Multi-qubit time-domain
def n_qubit_Rabi_seq(
        qubit_names, operation_dict, prep_sequence=None,
        prep_name=None,
        rots_basis=('I', 'X180', 'Y90', 'mY90', 'X90', 'mX90'),
        upload=True, verbose=False, return_seq=False,
        preselection=False, ro_spacing=1e-6):

    pass

