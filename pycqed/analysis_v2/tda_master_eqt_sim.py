# -*- coding: utf-8 -*-
"""
Created on Thu Jan 10 11:54:50 2019

@author: Kerstin
"""

import logging
import lmfit
import numpy as np
import os
import h5py
from numpy.linalg import inv
import scipy as sp
import itertools
import matplotlib as mpl
from collections import OrderedDict
from pycqed.analysis import fitting_models as fit_mods
from pycqed.analysis import analysis_toolbox as a_tools
import pycqed.analysis_v2.base_analysis as ba
import pycqed.analysis_v2.readout_analysis as roa
import pycqed.analysis_v2.tomography_qudev as tomo
from pycqed.analysis.tools.plotting import SI_val_to_msg_str
from copy import deepcopy
try:
    import qutip as qtp
except ImportError as e:
    logging.warning('Could not import qutip, tomography code will not work')
import pycqed.analysis_v2.master_eqt_sim as mes

class AveragedTimedomainAnalysis(ba.BaseDataAnalysis):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.single_timestamp = True
        self.params_dict = {
            'value_names': 'value_names',
            'measured_values': 'measured_values',
            'measurementstring': 'measurementstring',
            'exp_metadata': 'exp_metadata'}
        self.numeric_params = []
        if kwargs.get('auto', True):
            self.run_analysis()

    def process_data(self):
        self.metadata = self.raw_data_dict.get('exp_metadata', {})
        if self.metadata is None:
            self.metadata = {}
        cal_points = self.metadata.get('cal_points', None)
        cal_points = self.options_dict.get('cal_points', cal_points)
        cal_points_list = roa.convert_channel_names_to_index(
            cal_points, len(self.raw_data_dict['measured_values'][0]),
            self.raw_data_dict['value_names'])
        self.proc_data_dict['cal_points_list'] = cal_points_list
        measured_values = self.raw_data_dict['measured_values']
        cal_idxs = self._find_calibration_indices()
        scales = [np.std(x[cal_idxs]) for x in measured_values]
        observable_vectors = np.zeros((len(cal_points_list),
                                       len(measured_values)))
        observable_vector_stds = np.ones_like(observable_vectors)
        for i, observable in enumerate(cal_points_list):
            for ch_idx, seg_idxs in enumerate(observable):
                x = measured_values[ch_idx][seg_idxs] / scales[ch_idx]
                if len(x) > 0:
                    observable_vectors[i][ch_idx] = np.mean(x)
                if len(x) > 1:
                    observable_vector_stds[i][ch_idx] = np.std(x)
        Omtx = (observable_vectors[1:] - observable_vectors[0]).T
        d0 = observable_vectors[0]
        corr_values = np.zeros(
            (len(cal_points_list) - 1, len(measured_values[0])))
        for i in range(len(measured_values[0])):
            d = np.array([x[i] / scale for x, scale in zip(measured_values,
                                                           scales)])
            corr_values[:, i] = inv(Omtx.T.dot(Omtx)).dot(Omtx.T).dot(d - d0)
        self.proc_data_dict['corr_values'] = corr_values

    def measurement_operators_and_results(self):
        """
        Converts the calibration points to measurement operators. Assumes that
        the calibration points are ordered the same as the basis states for
        the tomography calculation (e.g. for two qubits |gg>, |ge>, |eg>, |ee>).
        Also assumes that each calibration in the passed cal_points uses
        different segments.

        Returns:
            A tuple of
                the measured values with outthe calibration points;
                the measurement operators corresponding to each channel;
                and the expected covariation matrix between the operators.
        """
        d = len(self.proc_data_dict['cal_points_list'])
        cal_point_idxs = [set() for _ in range(d)]
        for i, idxs_lists in enumerate(self.proc_data_dict['cal_points_list']):
            for idxs in idxs_lists:
                cal_point_idxs[i].update(idxs)
        cal_point_idxs = [sorted(list(idxs)) for idxs in cal_point_idxs]
        cal_point_idxs = np.array(cal_point_idxs)
        raw_data = self.raw_data_dict['measured_values']
        means = [None] * d
        residuals = [list() for _ in raw_data]
        for i, cal_point_idx in enumerate(cal_point_idxs):
            means[i] = [np.mean(ch_data[cal_point_idx]) for ch_data in raw_data]
            for j, ch_residuals in enumerate(residuals):
                ch_residuals += list(raw_data[j][cal_point_idx] - means[i][j])
        means = np.array(means)
        residuals = np.array(residuals)
        Fs = [np.diag(ms) for ms in means.T]
        Omega = residuals.dot(residuals.T) / len(residuals.T)
        data_idxs = np.setdiff1d(np.arange(len(raw_data[0])),
                                 cal_point_idxs.flatten())
        data = np.array([ch_data[data_idxs] for ch_data in raw_data])
        return data, Fs, Omega

    def _find_calibration_indices(self):
        cal_indices = set()
        cal_points = self.options_dict['cal_points']
        nr_segments = self.raw_data_dict['measured_values'].shape[-1]
        for observable in cal_points:
            if isinstance(observable, (list, np.ndarray)):
                for idxs in observable:
                    cal_indices.update({idx % nr_segments for idx in idxs})
            else:  # assume dictionaries
                for idxs in observable.values():
                    cal_indices.update({idx % nr_segments for idx in idxs})
        return list(cal_indices)


def all_cal_points(d, nr_ch, reps=1):
    """
    Generates a list of calibration points for a Hilbert space of dimension d,
    with nr_ch channels and reps reprtitions of each calibration point.
    """
    return [[list(range(-reps*i, -reps*(i-1)))]*nr_ch for i in range(d, 0, -1)]


class Single_Qubit_TimeDomainAnalysis(ba.BaseDataAnalysis):

    def process_data(self):
        """
        This takes care of rotating and normalizing the data if required.
        this should work for several input types.
            - I/Q values (2 quadratures + cal points)
            - weight functions (1 quadrature + cal points)
            - counts (no cal points)

        There are several options possible to specify the normalization
        using the options dict.
            cal_points (tuple) of indices of the calibrati  on points

            zero_coord, one_coord
        """

        cal_points = self.options_dict.get('cal_points', None)
        zero_coord = self.options_dict.get('zero_coord', None)
        one_coord = self.options_dict.get('one_coord', None)

        if cal_points is None:
            # default for all standard Timedomain experiments
            cal_points = [list(range(-4, -2)), list(range(-2, 0))]

        if len(self.raw_data_dict['measured_values']) == 1:
            # if only one weight function is used rotation is not required
            self.proc_data_dict['corr_data'] = a_tools.normalize_data_v3(
                self.raw_data_dict['measured_values'][0],
                cal_zero_points=cal_points[0],
                cal_one_points=cal_points[1])
        else:
            self.proc_data_dict['corr_data'], zero_coord, one_coord = \
                a_tools.rotate_and_normalize_data(
                    data=self.raw_data_dict['measured_values'][0:2],
                    zero_coord=zero_coord,
                    one_coord=one_coord,
                    cal_zero_points=cal_points[0],
                    cal_one_points=cal_points[1])

        # This should be added to the hdf5 datafile but cannot because of the
        # way that the "new" analysis works.

        # self.add_dataset_to_analysisgroup('Corrected data',
        #                                   self.proc_data_dict['corr_data'])


class MultiQubit_TimeDomain_Analysis(ba.BaseDataAnalysis):

    def __init__(self, t_start: str=None, t_stop: str=None,
                 data_file_path: str=None, single_timestamp: bool=False,
                 options_dict: dict=None, extract_only: bool=False,
                 do_fitting: bool=True, auto=False):

        super().__init__(t_start=t_start, t_stop=t_stop,
                         data_file_path=data_file_path,
                         options_dict=options_dict,
                         extract_only=extract_only,
                         do_fitting=do_fitting)

        self.params_dict = {'xlabel': 'sweep_name',
                            'xunit': 'sweep_unit',
                            'measurementstring': 'measurementstring',
                            'sweep_points': 'sweep_points',
                            'value_names': 'value_names',
                            'value_units': 'value_units',
                            'measured_values': 'measured_values',
                            'exp_metadata': 'exp_metadata'}
        if self.options_dict.get('TwoD', False):
            self.params_dict['sweep_points_2D'] = 'sweep_points_2D'

        self.single_timestamp = single_timestamp
        self.numeric_params = []
        self.channel_map = self.options_dict['channel_map']

        if auto:
            self.run_analysis()


    def process_data(self):
        """
        This takes care of rotating and normalizing the data if required.
        There are several options possible to specify the normalization
        using the options dict.
            cal_points (tuple) of indices of the calibration points

            zero_coord, one_coord
        """

        self.metadata = self.raw_data_dict.get('exp_metadata', [{}])[0]
        if self.metadata is None:
            self.metadata = {}
        self.channel_map = self.options_dict['channel_map']
        ch_map_lists = {k:v for k,v in self.channel_map.items()
                        if isinstance(v, list)}
        if np.any([len(v) > 2 for v in ch_map_lists.values()]):
            raise ValueError('{} have more than 2 RO channels. There is no '
                             'support for this case.'.format(
                ','.join([k for k, v in ch_map_lists.items() if len(v) > 2])))

        measured_RO_channels = list(self.raw_data_dict[
                                        'measured_values_ord_dict'])
        meas_results_per_qb_per_ROch = {}
        for qb_name, RO_channels in self.channel_map.items():
            meas_results_per_qb_per_ROch[qb_name] = {}
            if isinstance(RO_channels, str):
                meas_ROs_per_qb = [RO_ch for RO_ch in measured_RO_channels
                                   if RO_channels in RO_ch]
                for meas_RO in meas_ROs_per_qb:
                    meas_results_per_qb_per_ROch[qb_name][meas_RO] = \
                        self.raw_data_dict[
                            'measured_values_ord_dict'][meas_RO][0]

            elif isinstance(RO_channels, list):
                for qb_RO_ch in RO_channels:
                    meas_ROs_per_qb = [RO_ch for RO_ch in measured_RO_channels
                                      if qb_RO_ch in RO_ch]
                    for meas_RO in meas_ROs_per_qb:
                        meas_results_per_qb_per_ROch[qb_name][meas_RO] = \
                            self.raw_data_dict[
                                'measured_values_ord_dict'][meas_RO][0]
            else:
                raise TypeError('The RO channels for {} must either a list '
                                'or a string.'.format(qb_name))
        self.proc_data_dict['meas_results_per_qb_per_ROch'] = \
            meas_results_per_qb_per_ROch

        use_cal_points = self.metadata.get('cal_points', True)
        if use_cal_points:
            self.cal_points = self.options_dict.get('cal_points', None)
            zero_coord = self.options_dict.get('zero_coord', None)
            one_coord = self.options_dict.get('one_coord', None)
            if self.options_dict.get('TwoD', False):
                self.sweep_points_2D = self.raw_data_dict['sweep_points_2D'][0]
                self.proc_data_dict['corr_data'] = \
                    self.rotate_data_TwoD(meas_results_per_qb_per_ROch,
                                          self.channel_map,
                                          self.cal_points,
                                          zero_coord, one_coord)
            else:
                self.proc_data_dict['corr_data'] = \
                    self.rotate_data(meas_results_per_qb_per_ROch,
                                     self.channel_map,
                                     self.cal_points,
                                     zero_coord, one_coord)

            if self.cal_points is not None:
                self.NoCalPoints = len(np.array(self.cal_points).flatten())
                self.sweep_points = \
                    self.raw_data_dict['sweep_points'][0][:-self.NoCalPoints]
            else:
                self.NoCalPoints = 0
                self.sweep_points = self.raw_data_dict['sweep_points'][0]

        else:
            self.NoCalPoints = 0
            self.sweep_points = self.raw_data_dict['sweep_points'][0]

    @staticmethod
    def rotate_data(meas_results_per_qb_per_ROch, channel_map,
                    cal_points=None, zero_coord=None, one_coord=None):

        rotated_data_dict = deepcopy(channel_map)
        for qb_name, meas_res_dict in meas_results_per_qb_per_ROch.items():
            if len(meas_res_dict) == 1:
                # one RO channel per qubit
                rotated_data_dict[qb_name] = \
                    a_tools.normalize_data_v3(
                        data=meas_res_dict[list(meas_res_dict)[0]],
                        cal_zero_points=cal_points[0],
                        cal_one_points=cal_points[1])
            elif list(meas_res_dict) == channel_map[qb_name]:
                # two RO channels per qubit
                rotated_data_dict[qb_name], _, _ = \
                    a_tools.rotate_and_normalize_data(
                        data=np.array([v for v in meas_res_dict.values()]),
                        zero_coord=zero_coord,
                        one_coord=one_coord,
                        cal_zero_points=cal_points[0],
                        cal_one_points=cal_points[1])
            else:
                # multiple readouts per qubit per channel
                rotated_data_dict[qb_name] = {}
                if isinstance(channel_map[qb_name], str):
                    qb_ro_ch0 = channel_map[qb_name]
                else:
                    qb_ro_ch0 = channel_map[qb_name][0]
                ro_suffixes = [s[len(qb_ro_ch0)+1::] for s in
                               list(meas_res_dict) if qb_ro_ch0 in s]
                for i, ro_suf in enumerate(ro_suffixes):
                    if len(ro_suffixes) == len(meas_res_dict):
                        # one RO ch per qubit
                        rotated_data_dict[qb_name][ro_suf] = \
                            a_tools.normalize_data_v3(
                                data=meas_res_dict[list(meas_res_dict)[i]],
                                cal_zero_points=cal_points[0],
                                cal_one_points=cal_points[1])
                    else:
                        # two RO ch per qubit
                        keys = [k for k in meas_res_dict if ro_suf in k]
                        correct_keys = [k for k in keys
                                        if k[len(qb_ro_ch0)+1::] == ro_suf]
                        data_array = np.array([meas_res_dict[k]
                                               for k in correct_keys])
                        rotated_data_dict[qb_name][ro_suf], \
                        _, _ = \
                            a_tools.rotate_and_normalize_data(
                                data=data_array,
                                zero_coord=zero_coord,
                                one_coord=one_coord,
                                cal_zero_points=cal_points[0],
                                cal_one_points=cal_points[1])

        return rotated_data_dict

    @staticmethod
    def rotate_data_TwoD(meas_results_per_qb_per_ROch, channel_map,
                    cal_points=None, zero_coord=None, one_coord=None):

        rotated_data_dict = deepcopy(channel_map)
        for qb_name, meas_res_dict in meas_results_per_qb_per_ROch.items():
            if len(meas_res_dict) == 1:
                # one RO channel per qubit
                raw_data_arr = meas_res_dict[list(meas_res_dict)[0]]
                rotated_data_dict[qb_name] = \
                    deepcopy(raw_data_arr.transpose())
                for col in range(raw_data_arr.shape[1]):
                    rotated_data_dict[qb_name][col] = \
                        a_tools.normalize_data_v3(
                            data=raw_data_arr[:, col],
                            cal_zero_points=cal_points[0],
                            cal_one_points=cal_points[1])
            elif list(meas_res_dict) == channel_map[qb_name]:
                # two RO channels per qubit
                raw_data_arr = meas_res_dict[list(meas_res_dict)[0]]
                rotated_data_dict[qb_name] = \
                    deepcopy(raw_data_arr.transpose())
                for col in range(raw_data_arr.shape[1]):
                    data_array = np.array(
                        [v[:, col] for v in meas_res_dict.values()])
                    rotated_data_dict[qb_name][col], _, _ = \
                        a_tools.rotate_and_normalize_data(
                            data=data_array,
                            zero_coord=zero_coord,
                            one_coord=one_coord,
                            cal_zero_points=cal_points[0],
                            cal_one_points=cal_points[1])
            else:
                # multiple readouts per qubit per channel
                rotated_data_dict[qb_name] = {}
                if isinstance(channel_map[qb_name], str):
                    qb_ro_ch0 = channel_map[qb_name]
                else:
                    qb_ro_ch0 = channel_map[qb_name][0]
                ro_suffixes = [s[len(qb_ro_ch0)+1::] for s in
                               list(meas_res_dict) if qb_ro_ch0 in s]
                for i, ro_suf in enumerate(ro_suffixes):
                    if len(ro_suffixes) == len(meas_res_dict):
                        # one RO ch per qubit
                        raw_data_arr = meas_res_dict[list(meas_res_dict)[i]]
                        rotated_data_dict[qb_name][ro_suf] = \
                            deepcopy(raw_data_arr.transpose())
                        for col in range(raw_data_arr.shape[1]):
                            rotated_data_dict[qb_name][
                                ro_suf][col] = \
                                a_tools.normalize_data_v3(
                                    data=raw_data_arr[:, col],
                                    cal_zero_points=cal_points[0],
                                    cal_one_points=cal_points[1])
                    else:
                        # two RO ch per qubit
                        raw_data_arr = meas_res_dict[list(meas_res_dict)[i]]
                        rotated_data_dict[qb_name][ro_suf] = \
                            deepcopy(raw_data_arr.transpose())
                        for col in range(raw_data_arr.shape[1]):
                            data_array = np.array(
                                [v[:, col] for k, v in meas_res_dict.items()
                                 if ro_suf in k])
                            rotated_data_dict[qb_name][ro_suf][col], _, _ = \
                                a_tools.rotate_and_normalize_data(
                                    data=data_array,
                                    zero_coord=zero_coord,
                                    one_coord=one_coord,
                                    cal_zero_points=cal_points[0],
                                    cal_one_points=cal_points[1])

        return rotated_data_dict

    def prepare_plots(self):
        for qb_name, corr_data in self.proc_data_dict['corr_data'].items():
            if isinstance(corr_data, dict):
                for ro_suffix, data in corr_data.items():
                    plot_name = 'base_plot_' + qb_name + ro_suffix
                    self.prepare_base_plot(
                        plot_name, data,
                        ref_state_plot_labels=(
                            'exc_state_' + qb_name + ro_suffix,
                            'gnd_state_' + qb_name + ro_suffix))

            else:
                plot_name = 'base_plot_' + qb_name
                self.prepare_base_plot(
                    plot_name, corr_data,
                    ref_state_plot_labels=(
                        'exc_state_' + qb_name,
                        'gnd_state_' + qb_name))

    def prepare_base_plot(self, plot_name, data,
                          ref_state_plot_labels=('exc_state', 'gnd_state')):
        if self.NoCalPoints != 0:
            assert (len(ref_state_plot_labels) == len(self.cal_points))
            yvals = data[:-self.NoCalPoints]

            # plot cal points
            for i, cal_pts_idxs in enumerate(self.cal_points[::-1]):
                self.plot_dicts[ref_state_plot_labels[i]] = {
                    'ax_id': plot_name,
                    'plotfn': self.plot_line,
                    'xvals': self.raw_data_dict['sweep_points'][0][cal_pts_idxs],
                    'yvals': np.mean([data[cal_pts_idxs],
                                      data[cal_pts_idxs]],
                                     axis=0),
                    'setlabel': r'$|e\rangle$' if i == 0 \
                        else r'$|g\rangle$',
                    'do_legend': True,
                    'legend_bbox_to_anchor': (1, 0.5),
                    'legend_pos': 'center left',
                    'linestyle': 'none',
                    'line_kws': {'color': 'gray' if i == 0 else 'k'}}

        else:
            yvals = data

        self.plot_dicts[plot_name] = {
            'plotfn': self.plot_line,
            'xvals': self.sweep_points,
            'xlabel': self.raw_data_dict['xlabel'][0],
            'xunit': self.raw_data_dict['xunit'][0],
            'yvals': yvals,
            'ylabel': 'Excited state population',
            'yunit': '',
            'setlabel': '',
            'title': (self.raw_data_dict['timestamps'][0] + ' ' +
                      self.raw_data_dict['measurementstring'][0]),
            'linestyle': 'none',
            'do_legend': True,
            'legend_bbox_to_anchor': (1, 0.5),
            'legend_pos': 'center left'}


class Idling_Error_Rate_Analyisis(ba.BaseDataAnalysis):

    def __init__(self, t_start: str=None, t_stop: str=None,
                 label: str='', data_file_path: str=None,
                 options_dict: dict=None, extract_only: bool=False,
                 do_fitting: bool=True, auto=True):
        super().__init__(t_start=t_start, t_stop=t_stop,
                         label=label,
                         data_file_path=data_file_path,
                         options_dict=options_dict,
                         extract_only=extract_only, do_fitting=do_fitting)

        self.params_dict = {'xlabel': 'sweep_name',
                            'xunit': 'sweep_unit',
                            'xvals': 'sweep_points',
                            'measurementstring': 'measurementstring',
                            'value_names': 'value_names',
                            'value_units': 'value_units',
                            'measured_values': 'measured_values'}
        self.numeric_params = []
        if auto:
            self.run_analysis()

    def process_data(self):
        post_sel_th = self.options_dict.get('post_sel_th', 0.5)
        raw_shots = self.raw_data_dict['measured_values'][0][0]
        post_sel_shots = raw_shots[::2]
        data_shots = raw_shots[1::2]
        data_shots[np.where(post_sel_shots > post_sel_th)] = np.nan

        states = ['0', '1', '+']
        self.proc_data_dict['xvals'] = np.unique(self.raw_data_dict['xvals'])
        for i, state in enumerate(states):
            self.proc_data_dict['shots_{}'.format(state)] =data_shots[i::3]

            self.proc_data_dict['yvals_{}'.format(state)] = \
                np.nanmean(np.reshape(self.proc_data_dict['shots_{}'.format(state)],
                               (len(self.proc_data_dict['xvals']), -1),
                               order='F'), axis=1)


    def prepare_plots(self):
        # assumes that value names are unique in an experiment
        states = ['0', '1', '+']
        for i, state in enumerate(states):
            yvals = self.proc_data_dict['yvals_{}'.format(state)]
            xvals =  self.proc_data_dict['xvals']

            self.plot_dicts['Prepare in {}'.format(state)] = {
                'ax_id': 'main',
                'plotfn': self.plot_line,
                'xvals': xvals,
                'xlabel': self.raw_data_dict['xlabel'][0],
                'xunit': self.raw_data_dict['xunit'][0][0],
                'yvals': yvals,
                'ylabel': 'Counts',
                'yrange': [0, 1],
                'xrange': self.options_dict.get('xrange', None),
                'yunit': 'frac',
                'setlabel': 'Prepare in {}'.format(state),
                'do_legend':True,
                'title': (self.raw_data_dict['timestamps'][0]+' - ' +
                          self.raw_data_dict['timestamps'][-1] + '\n' +
                          self.raw_data_dict['measurementstring'][0]),
                'legend_pos': 'upper right'}
        if self.do_fitting:
            for state in ['0', '1', '+']:
                self.plot_dicts['fit_{}'.format(state)] = {
                    'ax_id': 'main',
                    'plotfn': self.plot_fit,
                    'fit_res': self.fit_dicts['fit {}'.format(state)]['fit_res'],
                    'plot_init': self.options_dict['plot_init'],
                    'setlabel': 'fit |{}>'.format(state),
                    'do_legend': True,
                    'legend_pos': 'upper right'}

                self.plot_dicts['fit_text']={
                    'ax_id':'main',
                    'box_props': 'fancy',
                    'xpos':1.05,
                    'horizontalalignment':'left',
                    'plotfn': self.plot_text,
                    'text_string': self.proc_data_dict['fit_msg']}



    def analyze_fit_results(self):
        fit_msg =''
        states = ['0', '1', '+']
        for state in states:
            fr = self.fit_res['fit {}'.format(state)]
            N1 = fr.params['N1'].value, fr.params['N1'].stderr
            N2 = fr.params['N2'].value, fr.params['N2'].stderr
            fit_msg += ('Prep |{}> : \n\tN_1 = {:.2g} $\pm$ {:.2g}'
                    '\n\tN_2 = {:.2g} $\pm$ {:.2g}\n').format(
                state, N1[0], N1[1], N2[0], N2[1])

        self.proc_data_dict['fit_msg'] = fit_msg

    def prepare_fitting(self):
        self.fit_dicts = OrderedDict()
        states = ['0', '1', '+']
        for i, state in enumerate(states):
            yvals = self.proc_data_dict['yvals_{}'.format(state)]
            xvals =  self.proc_data_dict['xvals']

            mod = lmfit.Model(fit_mods.idle_error_rate_exp_decay)
            mod.guess = fit_mods.idle_err_rate_guess.__get__(mod, mod.__class__)

            # Done here explicitly so that I can overwrite a specific guess
            guess_pars = mod.guess(N=xvals, data=yvals)
            vary_N2 = self.options_dict.get('vary_N2', True)

            if not vary_N2:
                guess_pars['N2'].value = 1e21
                guess_pars['N2'].vary = False
            # print(guess_pars)
            self.fit_dicts['fit {}'.format(states[i])] = {
                'model': mod,
                'fit_xvals': {'N': xvals},
                'fit_yvals': {'data': yvals},
                'guess_pars': guess_pars}
            # Allows fixing the double exponential coefficient


class Grovers_TwoQubitAllStates_Analysis(ba.BaseDataAnalysis):

    def __init__(self, t_start: str=None, t_stop: str=None,
                 label: str='', data_file_path: str=None,
                 options_dict: dict=None, extract_only: bool=False,
                 do_fitting: bool=True, auto=True):
        super().__init__(t_start=t_start, t_stop=t_stop,
                         label=label,
                         data_file_path=data_file_path,
                         options_dict=options_dict,
                         extract_only=extract_only, do_fitting=do_fitting)

        self.params_dict = {'xlabel': 'sweep_name',
                            'xunit': 'sweep_unit',
                            'xvals': 'sweep_points',
                            'measurementstring': 'measurementstring',
                            'value_names': 'value_names',
                            'value_units': 'value_units',
                            'measured_values': 'measured_values'}
        self.numeric_params = []
        if auto:
            self.run_analysis()

    def process_data(self):
        self.proc_data_dict = OrderedDict()
        normalize_to_cal_points = self.options_dict.get('normalize_to_cal_points', True)
        cal_points = [
                        [[-4, -3], [-2, -1]],
                        [[-4, -2], [-3, -1]],
                       ]
        for idx in [0,1]:
            yvals = list(self.raw_data_dict['measured_values_ord_dict'].values())[idx][0]

            self.proc_data_dict['ylabel_{}'.format(idx)] = \
                self.raw_data_dict['value_names'][0][idx]
            self.proc_data_dict['yunit'] = self.raw_data_dict['value_units'][0][idx]

            if normalize_to_cal_points:
                yvals = a_tools.normalize_data_v3(yvals,
                    cal_zero_points=cal_points[idx][0],
                    cal_one_points=cal_points[idx][1])
            self.proc_data_dict['yvals_{}'.format(idx)] = yvals

        y0 = self.proc_data_dict['yvals_0']
        y1 = self.proc_data_dict['yvals_1']
        p_success = ((y0[0]*y1[0]) +
                     (1-y0[1])*y1[1] +
                     (y0[2])*(1-y1[2]) +
                     (1-y0[3])*(1-y1[3]) )/4
        print(y0[0]*y1[0])
        print((1-y0[1])*y1[1])
        print((y0[2])*(1-y1[2]))
        print((1-y0[3])*(1-y1[3]))
        self.proc_data_dict['p_success'] = p_success


    def prepare_plots(self):
        # assumes that value names are unique in an experiment
        for i in [0, 1]:
            yvals = self.proc_data_dict['yvals_{}'.format(i)]
            xvals =  self.raw_data_dict['xvals'][0]
            ylabel = self.proc_data_dict['ylabel_{}'.format(i)]
            self.plot_dicts['main_{}'.format(ylabel)] = {
                'plotfn': self.plot_line,
                'xvals': self.raw_data_dict['xvals'][0],
                'xlabel': self.raw_data_dict['xlabel'][0],
                'xunit': self.raw_data_dict['xunit'][0][0],
                'yvals': self.proc_data_dict['yvals_{}'.format(i)],
                'ylabel': ylabel,
                'yunit': self.proc_data_dict['yunit'],
                'title': (self.raw_data_dict['timestamps'][0] + ' \n' +
                          self.raw_data_dict['measurementstring'][0]),
                'do_legend': False,
                'legend_pos': 'upper right'}


        self.plot_dicts['limit_text']={
            'ax_id':'main_{}'.format(ylabel),
            'box_props': 'fancy',
            'xpos':1.05,
            'horizontalalignment':'left',
            'plotfn': self.plot_text,
            'text_string': 'P succes = {:.3f}'.format(self.proc_data_dict['p_success'])}








class FlippingAnalysis(Single_Qubit_TimeDomainAnalysis):

    def __init__(self, t_start: str=None, t_stop: str=None,
                 data_file_path: str=None,
                 options_dict: dict=None, extract_only: bool=False,
                 do_fitting: bool=True, auto=True):
        super().__init__(t_start=t_start, t_stop=t_stop,
                         data_file_path=data_file_path,
                         options_dict=options_dict,
                         extract_only=extract_only, do_fitting=do_fitting)
        self.single_timestamp = True

        self.params_dict = {'xlabel': 'sweep_name',
                            'xunit': 'sweep_unit',
                            'measurementstring': 'measurementstring',
                            'sweep_points': 'sweep_points',
                            'value_names': 'value_names',
                            'value_units': 'value_units',
                            'measured_values': 'measured_values'}
        # This analysis makes a hardcoded assumption on the calibration points
        self.options_dict['cal_points'] = [list(range(-4, -2)),
                                           list(range(-2, 0))]

        self.numeric_params = []
        if auto:
            self.run_analysis()

    def prepare_fitting(self):
        self.fit_dicts = OrderedDict()
        # Even though we expect an exponentially damped oscillation we use
        # a simple cosine as this gives more reliable fitting and we are only
        # interested in extracting the frequency of the oscillation
        cos_mod = lmfit.Model(fit_mods.CosFunc)

        guess_pars = fit_mods.Cos_guess(
            model=cos_mod, t=self.raw_data_dict['sweep_points'][:-4],
            data=self.proc_data_dict['corr_data'][:-4])

        # This enforces the oscillation to start at the equator
        # and ensures that any over/under rotation is absorbed in the
        # frequency
        guess_pars['amplitude'].value = 0.5
        guess_pars['amplitude'].vary = False
        guess_pars['offset'].value = 0.5
        guess_pars['offset'].vary = False

        self.fit_dicts['cos_fit'] = {
            'fit_fn': fit_mods.CosFunc,
            'fit_xvals': {'t': self.raw_data_dict['sweep_points'][:-4]},
            'fit_yvals': {'data': self.proc_data_dict['corr_data'][:-4]},
            'guess_pars': guess_pars}

        # In the case there are very few periods we fall back on a small
        # angle approximation to extract the drive detuning
        poly_mod = lmfit.models.PolynomialModel(degree=1)
        # the detuning can be estimated using on a small angle approximation
        # c1 = d/dN (cos(2*pi*f N) ) evaluated at N = 0 -> c1 = -2*pi*f
        poly_mod.set_param_hint('frequency', expr='-c1/(2*pi)')
        guess_pars = poly_mod.guess(x=self.raw_data_dict['sweep_points'][:-4],
                                    data=self.proc_data_dict['corr_data'][:-4])
        # Constraining the line ensures that it will only give a good fit
        # if the small angle approximation holds
        guess_pars['c0'].vary = False
        guess_pars['c0'].value = 0.5

        self.fit_dicts['line_fit'] = {
            'model': poly_mod,
            'fit_xvals': {'x': self.raw_data_dict['sweep_points'][:-4]},
            'fit_yvals': {'data': self.proc_data_dict['corr_data'][:-4]},
            'guess_pars': guess_pars}

    def analyze_fit_results(self):
        sf_line = self._get_scale_factor_line()
        sf_cos = self._get_scale_factor_cos()
        self.proc_data_dict['scale_factor'] = self.get_scale_factor()

        msg = 'Scale fact. based on '
        if self.proc_data_dict['scale_factor'] == sf_cos:
            msg += 'cos fit\n'
        else:
            msg += 'line fit\n'
        msg += 'cos fit: {:.4f}\n'.format(sf_cos)
        msg += 'line fit: {:.4f}'.format(sf_line)

        self.raw_data_dict['scale_factor_msg'] = msg
        # TODO: save scale factor to file

    def get_scale_factor(self):
        """
        Returns the scale factor that should correct for the error in the
        pulse amplitude.
        """
        # Model selection based on the Bayesian Information Criterion (BIC)
        # as  calculated by lmfit
        if (self.fit_dicts['line_fit']['fit_res'].bic <
                self.fit_dicts['cos_fit']['fit_res'].bic):
            scale_factor = self._get_scale_factor_line()
        else:
            scale_factor = self._get_scale_factor_cos()
        return scale_factor

    def _get_scale_factor_cos(self):
        # 1/period of the oscillation corresponds to the (fractional)
        # over/under rotation error per gate
        frequency = self.fit_dicts['cos_fit']['fit_res'].params['frequency']

        # the square is needed to account for the difference between
        # power and amplitude
        scale_factor = (1+frequency)**2

        phase = np.rad2deg(self.fit_dicts['cos_fit']['fit_res'].params['phase']) % 360
        # phase ~90 indicates an under rotation so the scale factor
        # has to be larger than 1. A phase ~270 indicates an over
        # rotation so then the scale factor has to be smaller than one.
        if phase > 180:
            scale_factor = 1/scale_factor

        return scale_factor

    def _get_scale_factor_line(self):
        # 1/period of the oscillation corresponds to the (fractional)
        # over/under rotation error per gate
        frequency = self.fit_dicts['line_fit']['fit_res'].params['frequency']
        scale_factor = (1+frequency)**2
        # no phase sign check is needed here as this is contained in the
        # sign of the coefficient

        return scale_factor

    def prepare_plots(self):
        self.plot_dicts['main'] = {
            'plotfn': self.plot_line,
            'xvals': self.raw_data_dict['sweep_points'],
            'xlabel': self.raw_data_dict['xlabel'],
            'xunit': self.raw_data_dict['xunit'],  # does not do anything yet
            'yvals': self.proc_data_dict['corr_data'],
            'ylabel': 'Excited state population',
            'yunit': '',
            'setlabel': 'data',
            'title': (self.raw_data_dict['timestamp'] + ' ' +
                      self.raw_data_dict['measurementstring']),
            'do_legend': True,
            'legend_pos': 'upper right'}

        if self.do_fitting:
            self.plot_dicts['line_fit'] = {
                'ax_id': 'main',
                'plotfn': self.plot_fit,
                'fit_res': self.fit_dicts['line_fit']['fit_res'],
                'plot_init': self.options_dict['plot_init'],
                'setlabel': 'line fit',
                'do_legend': True,
                'legend_pos': 'upper right'}

            self.plot_dicts['cos_fit'] = {
                'ax_id': 'main',
                'plotfn': self.plot_fit,
                'fit_res': self.fit_dicts['cos_fit']['fit_res'],
                'plot_init': self.options_dict['plot_init'],
                'setlabel': 'cos fit',
                'do_legend': True,
                'legend_pos': 'upper right'}

            self.plot_dicts['text_msg'] = {
                'ax_id': 'main',
                'ypos': 0.15,
                'plotfn': self.plot_text,
                'box_props': 'fancy',
                'text_string': self.raw_data_dict['scale_factor_msg']}


class Intersect_Analysis(Single_Qubit_TimeDomainAnalysis):
    """
    Analysis to extract the intercept of two parameters.

    relevant options_dict parameters
        ch_idx_A (int) specifies first channel for intercept
        ch_idx_B (int) specifies second channel for intercept if same as first
            it will assume data was taken interleaved.
    """
    def __init__(self, t_start: str=None, t_stop: str=None,
                 data_file_path: str=None,
                 options_dict: dict=None, extract_only: bool=False,
                 do_fitting: bool=True, auto=True):

        super().__init__(t_start=t_start, t_stop=t_stop,
                         data_file_path=data_file_path,
                         options_dict=options_dict,
                         extract_only=extract_only, do_fitting=do_fitting)
        self.single_timestamp = False

        self.params_dict = {'xlabel': 'sweep_name',
                            'xvals': 'sweep_points',
                            'xunit': 'sweep_unit',
                            'measurementstring': 'measurementstring',
                            'value_names': 'value_names',
                            'value_units': 'value_units',
                            'measured_values': 'measured_values'}

        self.numeric_params = []
        if auto:
            self.run_analysis()


    def process_data(self):
        """
        selects the relevant acq channel based on "ch_idx_A" and "ch_idx_B"
        specified in the options dict. If ch_idx_A and ch_idx_B are the same
        it will unzip the data.
        """
        self.proc_data_dict = deepcopy(self.raw_data_dict)
        # The channel containing the data must be specified in the options dict
        ch_idx_A = self.options_dict.get('ch_idx_A', 0)
        ch_idx_B = self.options_dict.get('ch_idx_B', 0)


        self.proc_data_dict['ylabel'] = self.raw_data_dict['value_names'][0][ch_idx_A]
        self.proc_data_dict['yunit'] = self.raw_data_dict['value_units'][0][ch_idx_A]

        if ch_idx_A == ch_idx_B:
            yvals = list(self.raw_data_dict['measured_values_ord_dict'].values())[ch_idx_A][0]
            self.proc_data_dict['xvals_A'] = self.raw_data_dict['xvals'][0][::2]
            self.proc_data_dict['xvals_B'] = self.raw_data_dict['xvals'][0][1::2]
            self.proc_data_dict['yvals_A'] = yvals[::2]
            self.proc_data_dict['yvals_B'] = yvals[1::2]
        else:
            self.proc_data_dict['xvals_A'] = self.raw_data_dict['xvals'][0]
            self.proc_data_dict['xvals_B'] = self.raw_data_dict['xvals'][0]

            self.proc_data_dict['yvals_A'] = list(self.raw_data_dict
                ['measured_values_ord_dict'].values())[ch_idx_A][0]
            self.proc_data_dict['yvals_B'] = list(self.raw_data_dict
                ['measured_values_ord_dict'].values())[ch_idx_B][0]

    def prepare_fitting(self):
        self.fit_dicts = OrderedDict()

        self.fit_dicts['line_fit_A'] = {
            'model': lmfit.models.PolynomialModel(degree=2),
            'fit_xvals': {'x': self.proc_data_dict['xvals_A']},
            'fit_yvals': {'data': self.proc_data_dict['yvals_A']}}

        self.fit_dicts['line_fit_B'] = {
            'model': lmfit.models.PolynomialModel(degree=2),
            'fit_xvals': {'x': self.proc_data_dict['xvals_B']},
            'fit_yvals': {'data': self.proc_data_dict['yvals_B']}}


    def analyze_fit_results(self):
        fr_0 = self.fit_res['line_fit_A'].best_values
        fr_1 = self.fit_res['line_fit_B'].best_values

        c0 = (fr_0['c0'] - fr_1['c0'])
        c1 = (fr_0['c1'] - fr_1['c1'])
        c2 = (fr_0['c2'] - fr_1['c2'])
        poly_coeff = [c0, c1, c2]
        poly = np.polynomial.polynomial.Polynomial([fr_0['c0'],
                                                   fr_0['c1'], fr_0['c2']])
        ic = np.polynomial.polynomial.polyroots(poly_coeff)

        self.proc_data_dict['intersect_L'] = ic[0], poly(ic[0])
        self.proc_data_dict['intersect_R'] = ic[1], poly(ic[1])

        if (((np.min(self.proc_data_dict['xvals']))< ic[0]) and
                ( ic[0] < (np.max(self.proc_data_dict['xvals'])))):
            self.proc_data_dict['intersect'] =self.proc_data_dict['intersect_L']
        else:
            self.proc_data_dict['intersect'] =self.proc_data_dict['intersect_R']

    def prepare_plots(self):
        self.plot_dicts['main'] = {
            'plotfn': self.plot_line,
            'xvals': self.proc_data_dict['xvals_A'],
            'xlabel': self.proc_data_dict['xlabel'][0],
            'xunit': self.proc_data_dict['xunit'][0][0],
            'yvals': self.proc_data_dict['yvals_A'],
            'ylabel': self.proc_data_dict['ylabel'],
            'yunit': self.proc_data_dict['yunit'],
            'setlabel': 'A',
            'title': (self.proc_data_dict['timestamps'][0] + ' \n' +
                      self.proc_data_dict['measurementstring'][0]),
            'do_legend': True,
            'yrange': (0,1),
            'legend_pos': 'upper right'}

        self.plot_dicts['on'] = {
            'plotfn': self.plot_line,
            'ax_id': 'main',
            'xvals': self.proc_data_dict['xvals_B'],
            'xlabel': self.proc_data_dict['xlabel'][0],
            'xunit': self.proc_data_dict['xunit'][0][0],
            'yvals': self.proc_data_dict['yvals_B'],
            'ylabel': self.proc_data_dict['ylabel'],
            'yunit': self.proc_data_dict['yunit'],
            'setlabel': 'B',
            'do_legend': True,
            'legend_pos': 'upper right'}

        if self.do_fitting:
            self.plot_dicts['line_fit_A'] = {
                'ax_id': 'main',
                'plotfn': self.plot_fit,
                'fit_res': self.fit_dicts['line_fit_A']['fit_res'],
                'plot_init': self.options_dict['plot_init'],
                'setlabel': 'Fit A',
                'do_legend': True}
            self.plot_dicts['line_fit_B'] = {
                'ax_id': 'main',
                'plotfn': self.plot_fit,
                'fit_res': self.fit_dicts['line_fit_B']['fit_res'],
                'plot_init': self.options_dict['plot_init'],
                'setlabel': 'Fit B',
                'do_legend': True}


            ic, ic_unit = SI_val_to_msg_str(
                self.proc_data_dict['intersect'][0],
                 self.proc_data_dict['xunit'][0][0], return_type=float)
            self.plot_dicts['intercept_message'] = {
                'ax_id': 'main',
                'plotfn': self.plot_line,
                'xvals': [self.proc_data_dict['intersect'][0]],
                'yvals': [self.proc_data_dict['intersect'][1]],
                'line_kws': {'alpha': .5, 'color':'gray',
                            'markersize':15},
                'marker': 'o',
                'setlabel': 'Intercept: {:.1f} {}'.format(ic, ic_unit),
                'do_legend': True}

    def get_intersect(self):

        return self.proc_data_dict['intersect']



class CZ_1QPhaseCal_Analysis(ba.BaseDataAnalysis):
    """
    Analysis to extract the intercept for a single qubit phase calibration
    experiment

    N.B. this is a less generic version of "Intersect_Analysis" and should
    be deprecated (MAR Dec 2017)
    """
    def __init__(self, t_start: str=None, t_stop: str=None,
                 data_file_path: str=None,
                 options_dict: dict=None, extract_only: bool=False,
                 do_fitting: bool=True, auto=True):
        super().__init__(t_start=t_start, t_stop=t_stop,
                         data_file_path=data_file_path,
                         options_dict=options_dict,
                         extract_only=extract_only, do_fitting=do_fitting)
        self.single_timestamp = False

        self.params_dict = {'xlabel': 'sweep_name',
                            'xunit': 'sweep_unit',
                            'xvals': 'sweep_points',
                            'measurementstring': 'measurementstring',
                            'value_names': 'value_names',
                            'value_units': 'value_units',
                            'measured_values': 'measured_values'}

        self.numeric_params = []
        if auto:
            self.run_analysis()

    def process_data(self):
        """
        selects the relevant acq channel based on "ch_idx" in options dict and
        then splits the data for th
        """
        self.proc_data_dict = OrderedDict()
        # The channel containing the data must be specified in the options dict
        ch_idx = self.options_dict['ch_idx']

        yvals = list(self.raw_data_dict['measured_values_ord_dict'].values())[ch_idx][0]

        self.proc_data_dict['ylabel'] = self.raw_data_dict['value_names'][0][ch_idx]
        self.proc_data_dict['yunit'] = self.raw_data_dict['value_units'][0][ch_idx]
        self.proc_data_dict['xvals_off'] = self.raw_data_dict['xvals'][0][::2]
        self.proc_data_dict['xvals_on'] = self.raw_data_dict['xvals'][0][1::2]
        self.proc_data_dict['yvals_off'] = yvals[::2]
        self.proc_data_dict['yvals_on'] = yvals[1::2]


    def prepare_fitting(self):
        self.fit_dicts = OrderedDict()

        self.fit_dicts['line_fit_off'] = {
            'model': lmfit.models.PolynomialModel(degree=1),
            'fit_xvals': {'x': self.proc_data_dict['xvals_off']},
            'fit_yvals': {'data': self.proc_data_dict['yvals_off']}}

        self.fit_dicts['line_fit_on'] = {
            'model': lmfit.models.PolynomialModel(degree=1),
            'fit_xvals': {'x': self.proc_data_dict['xvals_on']},
            'fit_yvals': {'data': self.proc_data_dict['yvals_on']}}


    def analyze_fit_results(self):
        fr_0 = self.fit_res['line_fit_off'].best_values
        fr_1 = self.fit_res['line_fit_on'].best_values
        ic = -(fr_0['c0'] - fr_1['c0'])/(fr_0['c1'] - fr_1['c1'])

        self.proc_data_dict['zero_phase_diff_intersect'] = ic


    def prepare_plots(self):
        self.plot_dicts['main'] = {
            'plotfn': self.plot_line,
            'xvals': self.proc_data_dict['xvals_off'],
            'xlabel': self.raw_data_dict['xlabel'][0],
            'xunit': self.raw_data_dict['xunit'][0][0],
            'yvals': self.proc_data_dict['yvals_off'],
            'ylabel': self.proc_data_dict['ylabel'],
            'yunit': self.proc_data_dict['yunit'],
            'setlabel': 'CZ off',
            'title': (self.raw_data_dict['timestamps'][0] + ' \n' +
                      self.raw_data_dict['measurementstring'][0]),
            'do_legend': True,
            'yrange': (0,1),
            'legend_pos': 'upper right'}

        self.plot_dicts['on'] = {
            'plotfn': self.plot_line,
            'ax_id': 'main',
            'xvals': self.proc_data_dict['xvals_on'],
            'xlabel': self.raw_data_dict['xlabel'][0],
            'xunit': self.raw_data_dict['xunit'][0][0],
            'yvals': self.proc_data_dict['yvals_on'],
            'ylabel': self.proc_data_dict['ylabel'],
            'yunit': self.proc_data_dict['yunit'],
            'setlabel': 'CZ on',
            'do_legend': True,
            'legend_pos': 'upper right'}

        if self.do_fitting:
            self.plot_dicts['line_fit_off'] = {
                'ax_id': 'main',
                'plotfn': self.plot_fit,
                'fit_res': self.fit_dicts['line_fit_off']['fit_res'],
                'plot_init': self.options_dict['plot_init'],
                'setlabel': 'Fit CZ off',
                'do_legend': True}
            self.plot_dicts['line_fit_on'] = {
                'ax_id': 'main',
                'plotfn': self.plot_fit,
                'fit_res': self.fit_dicts['line_fit_on']['fit_res'],
                'plot_init': self.options_dict['plot_init'],
                'setlabel': 'Fit CZ on',
                'do_legend': True}


            ic, ic_unit = SI_val_to_msg_str(
                self.proc_data_dict['zero_phase_diff_intersect'],
                 self.raw_data_dict['xunit'][0][0], return_type=float)
            self.plot_dicts['intercept_message'] = {
                'ax_id': 'main',
                'plotfn': self.plot_line,
                'xvals': [self.proc_data_dict['zero_phase_diff_intersect']],
                'yvals': [np.mean(self.proc_data_dict['xvals_on'])],
                'line_kws': {'alpha': 0},
                'setlabel': 'Intercept: {:.1f} {}'.format(ic, ic_unit),
                'do_legend': True}

    def get_zero_phase_diff_intersect(self):

        return self.proc_data_dict['zero_phase_diff_intersect']


class Oscillation_Analysis(ba.BaseDataAnalysis):
    """
    Very basic analysis to determine the phase of a single oscillation
    that has an assumed period of 360 degrees.
    """
    def __init__(self, t_start: str=None, t_stop: str=None,
                 data_file_path: str=None,
                 label: str='',
                 options_dict: dict=None, extract_only: bool=False,
                 do_fitting: bool=True, auto=True):
        super().__init__(t_start=t_start, t_stop=t_stop,
                         label=label,
                         data_file_path=data_file_path,
                         options_dict=options_dict,
                         extract_only=extract_only, do_fitting=do_fitting)
        self.single_timestamp = False

        self.params_dict = {'xlabel': 'sweep_name',
                            'xunit': 'sweep_unit',
                            'xvals': 'sweep_points',
                            'measurementstring': 'measurementstring',
                            'value_names': 'value_names',
                            'value_units': 'value_units',
                            'measured_values': 'measured_values'}

        self.numeric_params = []
        if auto:
            self.run_analysis()

    def process_data(self):
        self.proc_data_dict = OrderedDict()
        idx = 1

        self.proc_data_dict['yvals'] = list(self.raw_data_dict['measured_values_ord_dict'].values())[idx][0]
        self.proc_data_dict['ylabel'] = self.raw_data_dict['value_names'][0][idx]
        self.proc_data_dict['yunit'] = self.raw_data_dict['value_units'][0][idx]

    def prepare_fitting(self):
        self.fit_dicts = OrderedDict()
        cos_mod = lmfit.Model(fit_mods.CosFunc)
        cos_mod.guess = fit_mods.Cos_guess.__get__(cos_mod, cos_mod.__class__)
        self.fit_dicts['cos_fit'] = {
            'model': cos_mod,
            'guess_dict': {'frequency': {'value': 1/360, 'vary': False}},
            'fit_xvals': {'t': self.raw_data_dict['xvals'][0]},
            'fit_yvals': {'data': self.proc_data_dict['yvals']}}

    def analyze_fit_results(self):
        fr = self.fit_res['cos_fit'].best_values
        self.proc_data_dict['phi'] =  np.rad2deg(fr['phase'])


    def prepare_plots(self):
        self.plot_dicts['main'] = {
            'plotfn': self.plot_line,
            'xvals': self.raw_data_dict['xvals'][0],
            'xlabel': self.raw_data_dict['xlabel'][0],
            'xunit': self.raw_data_dict['xunit'][0][0],
            'yvals': self.proc_data_dict['yvals'],
            'ylabel': self.proc_data_dict['ylabel'],
            'yunit': self.proc_data_dict['yunit'],
            'title': (self.raw_data_dict['timestamps'][0] + ' \n' +
                      self.raw_data_dict['measurementstring'][0]),
            'do_legend': True,
            # 'yrange': (0,1),
            'legend_pos': 'upper right'}

        if self.do_fitting:
            self.plot_dicts['cos_fit'] = {
                'ax_id': 'main',
                'plotfn': self.plot_fit,
                'fit_res': self.fit_dicts['cos_fit']['fit_res'],
                'plot_init': self.options_dict['plot_init'],
                'setlabel': 'Fit',
                'do_legend': True}


class Conditional_Oscillation_Analysis(ba.BaseDataAnalysis):
    """
    Analysis to extract quantities from a conditional oscillation.

    """
    def __init__(self, t_start: str=None, t_stop: str=None,
                 data_file_path: str=None,
                 label: str='',
                 options_dict: dict=None, extract_only: bool=False,
                 do_fitting: bool=True, auto=True):
        super().__init__(t_start=t_start, t_stop=t_stop,
                         label=label,
                         data_file_path=data_file_path,
                         options_dict=options_dict,
                         extract_only=extract_only, do_fitting=do_fitting)
        self.single_timestamp = False

        self.params_dict = {'xlabel': 'sweep_name',
                            'xunit': 'sweep_unit',
                            'xvals': 'sweep_points',
                            'measurementstring': 'measurementstring',
                            'value_names': 'value_names',
                            'value_units': 'value_units',
                            'measured_values': 'measured_values'}

        self.numeric_params = []
        if auto:
            self.run_analysis()

    def process_data(self):
        """
        selects the relevant acq channel based on "ch_idx_osc" and
        "ch_idx_spec" in the options dict and then splits the data for the
        off and on cases
        """
        self.proc_data_dict = OrderedDict()
        # The channel containing the data must be specified in the options dict
        ch_idx_spec = self.options_dict.get('ch_idx_spec', 0)
        ch_idx_osc = self.options_dict.get('ch_idx_osc', 1)
        normalize_to_cal_points = self.options_dict.get('normalize_to_cal_points', True)
        cal_points = [
                        [[-4, -3], [-2, -1]],
                        [[-4, -2], [-3, -1]],
                       ]


        i = 0
        for idx, type_str in zip([ch_idx_osc, ch_idx_spec], ['osc', 'spec']):
            yvals = list(self.raw_data_dict['measured_values_ord_dict'].values())[idx][0]
            self.proc_data_dict['ylabel_{}'.format(type_str)] = self.raw_data_dict['value_names'][0][idx]
            self.proc_data_dict['yunit'] = self.raw_data_dict['value_units'][0][idx]

            if normalize_to_cal_points:
                yvals = a_tools.normalize_data_v3(yvals,
                    cal_zero_points=cal_points[i][0],
                    cal_one_points=cal_points[i][1])
                i +=1

                self.proc_data_dict['yvals_{}_off'.format(type_str)] = yvals[::2]
                self.proc_data_dict['yvals_{}_on'.format(type_str)] = yvals[1::2]
                self.proc_data_dict['xvals_off'] = self.raw_data_dict['xvals'][0][::2]
                self.proc_data_dict['xvals_on'] = self.raw_data_dict['xvals'][0][1::2]

            else:
                self.proc_data_dict['yvals_{}_off'.format(type_str)] = yvals[::2]
                self.proc_data_dict['yvals_{}_on'.format(type_str)] = yvals[1::2]


                self.proc_data_dict['xvals_off'] = self.raw_data_dict['xvals'][0][::2]
                self.proc_data_dict['xvals_on'] = self.raw_data_dict['xvals'][0][1::2]



    def prepare_fitting(self):
        self.fit_dicts = OrderedDict()
        cos_mod0 = lmfit.Model(fit_mods.CosFunc)
        cos_mod0.guess = fit_mods.Cos_guess.__get__(cos_mod0, cos_mod0.__class__)
        self.fit_dicts['cos_fit_off'] = {
            'model': cos_mod0,
            'guess_dict': {'frequency': {'value': 1/360, 'vary': False}},
            'fit_xvals': {'t': self.proc_data_dict['xvals_off'][:-2]},
            'fit_yvals': {'data': self.proc_data_dict['yvals_osc_off'][:-2]}}

        cos_mod1 = lmfit.Model(fit_mods.CosFunc)
        cos_mod1.guess = fit_mods.Cos_guess.__get__(cos_mod1, cos_mod1.__class__)
        self.fit_dicts['cos_fit_on'] = {
            'model': cos_mod1,
            'guess_dict': {'frequency': {'value': 1/360, 'vary': False}},
            'fit_xvals': {'t': self.proc_data_dict['xvals_on'][:-2]},
            'fit_yvals': {'data': self.proc_data_dict['yvals_osc_on'][:-2]}}

    def analyze_fit_results(self):
        fr_0 = self.fit_res['cos_fit_off'].params
        fr_1 = self.fit_res['cos_fit_on'].params

        phi0 = np.rad2deg(fr_0['phase'].value)
        phi1 = np.rad2deg(fr_1['phase'].value)

        phi0_stderr = np.rad2deg(fr_0['phase'].stderr)
        phi1_stderr = np.rad2deg(fr_1['phase'].stderr)

        self.proc_data_dict['phi_0'] = phi0, phi0_stderr
        self.proc_data_dict['phi_1'] = phi1, phi1_stderr
        phi_cond_stderr = (phi0_stderr**2+phi1_stderr**2)**.5
        self.proc_data_dict['phi_cond'] = (phi1 -phi0), phi_cond_stderr


        osc_amp = np.mean([fr_0['amplitude'], fr_1['amplitude']])
        osc_amp_stderr = np.sqrt(fr_0['amplitude'].stderr**2 +
                                 fr_1['amplitude']**2)/2

        self.proc_data_dict['osc_amp_0'] = (fr_0['amplitude'].value,
                                            fr_0['amplitude'].stderr)
        self.proc_data_dict['osc_amp_1'] = (fr_1['amplitude'].value,
                                            fr_1['amplitude'].stderr)

        self.proc_data_dict['osc_offs_0'] = (fr_0['offset'].value,
                                            fr_0['offset'].stderr)
        self.proc_data_dict['osc_offs_1'] = (fr_1['offset'].value,
                                            fr_1['offset'].stderr)


        offs_stderr = (fr_0['offset'].stderr**2+fr_1['offset'].stderr**2)**.5
        self.proc_data_dict['offs_diff'] = (
            fr_1['offset'].value - fr_0['offset'].value, offs_stderr)

        # self.proc_data_dict['osc_amp'] = (osc_amp, osc_amp_stderr)
        self.proc_data_dict['missing_fraction'] = (
            np.mean(self.proc_data_dict['yvals_spec_on'][:-2]) -
            np.mean(self.proc_data_dict['yvals_spec_off'][:-2]))


    def prepare_plots(self):
        self._prepare_main_oscillation_figure()
        self._prepare_spectator_qubit_figure()

    def _prepare_main_oscillation_figure(self):
        self.plot_dicts['main'] = {
            'plotfn': self.plot_line,
            'xvals': self.proc_data_dict['xvals_off'],
            'xlabel': self.raw_data_dict['xlabel'][0],
            'xunit': self.raw_data_dict['xunit'][0][0],
            'yvals': self.proc_data_dict['yvals_osc_off'],
            'ylabel': self.proc_data_dict['ylabel_osc'],
            'yunit': self.proc_data_dict['yunit'],
            'setlabel': 'CZ off',
            'title': (self.raw_data_dict['timestamps'][0] + ' \n' +
                      self.raw_data_dict['measurementstring'][0]),
            'do_legend': True,
            # 'yrange': (0,1),
            'legend_pos': 'upper right'}

        self.plot_dicts['on'] = {
            'plotfn': self.plot_line,
            'ax_id': 'main',
            'xvals': self.proc_data_dict['xvals_on'],
            'xlabel': self.raw_data_dict['xlabel'][0],
            'xunit': self.raw_data_dict['xunit'][0][0],
            'yvals': self.proc_data_dict['yvals_osc_on'],
            'ylabel': self.proc_data_dict['ylabel_osc'],
            'yunit': self.proc_data_dict['yunit'],
            'setlabel': 'CZ on',
            'do_legend': True,
            'legend_pos': 'upper right'}

        if self.do_fitting:
            self.plot_dicts['cos_fit_off'] = {
                'ax_id': 'main',
                'plotfn': self.plot_fit,
                'fit_res': self.fit_dicts['cos_fit_off']['fit_res'],
                'plot_init': self.options_dict['plot_init'],
                'setlabel': 'Fit CZ off',
                'do_legend': True}
            self.plot_dicts['cos_fit_on'] = {
                'ax_id': 'main',
                'plotfn': self.plot_fit,
                'fit_res': self.fit_dicts['cos_fit_on']['fit_res'],
                'plot_init': self.options_dict['plot_init'],
                'setlabel': 'Fit CZ on',
                'do_legend': True}

            # offset as a guide for the eye
            y = self.fit_res['cos_fit_off'].params['offset'].value
            self.plot_dicts['cos_off_offset'] ={
                'plotfn': self.plot_matplot_ax_method,
                'ax_id':'main',
                'func': 'axhline',
                'plot_kws': {
                    'y': y, 'color': 'C0', 'linestyle': 'dotted'}
                    }

            phase_message = (
                'Phase diff.: {:.1f} $\pm$ {:.1f} deg\n'
                'Phase off: {:.1f} $\pm$ {:.1f}deg\n'
                'Phase on: {:.1f} $\pm$ {:.1f}deg\n'
                'Osc. amp. off: {:.4f} $\pm$ {:.4f}\n'
                'Osc. amp. on: {:.4f} $\pm$ {:.4f}\n'
                'Offs. diff.: {:.4f} $\pm$ {:.4f}\n'
                'Osc. offs. off: {:.4f} $\pm$ {:.4f}\n'
                'Osc. offs. on: {:.4f} $\pm$ {:.4f}'.format(
                    self.proc_data_dict['phi_cond'][0],
                    self.proc_data_dict['phi_cond'][1],
                    self.proc_data_dict['phi_0'][0],
                    self.proc_data_dict['phi_0'][1],
                    self.proc_data_dict['phi_1'][0],
                    self.proc_data_dict['phi_1'][1],
                    self.proc_data_dict['osc_amp_0'][0],
                    self.proc_data_dict['osc_amp_0'][1],
                    self.proc_data_dict['osc_amp_1'][0],
                    self.proc_data_dict['osc_amp_1'][1],
                    self.proc_data_dict['offs_diff'][0],
                    self.proc_data_dict['offs_diff'][1],
                    self.proc_data_dict['osc_offs_0'][0],
                    self.proc_data_dict['osc_offs_0'][1],
                    self.proc_data_dict['osc_offs_1'][0],
                    self.proc_data_dict['osc_offs_1'][1]))
            self.plot_dicts['phase_message'] = {
                'ax_id': 'main',
                'ypos': 0.9,
                'xpos': 1.45,
                'plotfn': self.plot_text,
                'box_props': 'fancy',
                'line_kws': {'alpha': 0},
                'text_string': phase_message}

    def _prepare_spectator_qubit_figure(self):

        self.plot_dicts['spectator_qubit'] = {
            'plotfn': self.plot_line,
            'xvals': self.proc_data_dict['xvals_off'],
            'xlabel': self.raw_data_dict['xlabel'][0],
            'xunit': self.raw_data_dict['xunit'][0][0],
            'yvals': self.proc_data_dict['yvals_spec_off'],
            'ylabel': self.proc_data_dict['ylabel_spec'],
            'yunit': self.proc_data_dict['yunit'],
            'setlabel': 'CZ off',
            'title': (self.raw_data_dict['timestamps'][0] + ' \n' +
                      self.raw_data_dict['measurementstring'][0]),
            'do_legend': True,
            # 'yrange': (0,1),
            'legend_pos': 'upper right'}

        self.plot_dicts['spec_on'] = {
            'plotfn': self.plot_line,
            'ax_id': 'spectator_qubit',
            'xvals': self.proc_data_dict['xvals_on'],
            'xlabel': self.raw_data_dict['xlabel'][0],
            'xunit': self.raw_data_dict['xunit'][0][0],
            'yvals': self.proc_data_dict['yvals_spec_on'],
            'ylabel': self.proc_data_dict['ylabel_spec'],
            'yunit': self.proc_data_dict['yunit'],
            'setlabel': 'CZ on',
            'do_legend': True,
            'legend_pos': 'upper right'}

        if self.do_fitting:
            leak_msg = (
                'Missing fraction: {:.2f} % '.format(
                    self.proc_data_dict['missing_fraction']*100))
            self.plot_dicts['leak_msg'] = {
                'ax_id': 'spectator_qubit',
                'ypos': 0.7,
                'plotfn': self.plot_text,
                'box_props': 'fancy',
                'line_kws': {'alpha': 0},
                'text_string': leak_msg}
            # offset as a guide for the eye
            y = self.fit_res['cos_fit_on'].params['offset'].value
            self.plot_dicts['cos_on_offset'] ={
                'plotfn': self.plot_matplot_ax_method,
                'ax_id':'main',
                'func': 'axhline',
                'plot_kws': {
                    'y': y, 'color': 'C1', 'linestyle': 'dotted'}
                    }


class StateTomographyAnalysis(ba.BaseDataAnalysis):
    """
    Analyses the results of the state tomography experiment and calculates
    the corresponding quantum state.

    Possible options that can be passed in the options_dict parameter:
        cal_points: A data structure specifying the indices of the calibration
                    points. See the AveragedTimedomainAnalysis for format.
                    The calibration points need to be in the same order as the
                    used basis for the result.
        data_type: 'averaged' or 'singleshot'. For singleshot data each
                   measurement outcome is saved and arbitrary order correlations
                   between the states can be calculated.
        meas_operators: (optional) A list of qutip operators or numpy 2d arrays.
                        This overrides the measurement operators otherwise
                        found from the calibration points.
        covar_matrix: (optional) The covariance matrix of the measurement
                      operators as a 2d numpy array. Overrides the one found
                      from the calibration points.
        basis_rots_str: A list of standard PycQED pulse names that were
                             applied to qubits before measurement
        basis_rots: As an alternative to single_qubit_pulses, the basis
                    rotations applied to the system as qutip operators or numpy
                    matrices can be given.
        mle: True/False, whether to do maximum likelihood fit. If False, only
             least squares fit will be done, which could give negative
             eigenvalues for the density matrix.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.single_timestamp = True
        self.params_dict = {'exp_metadata': 'exp_metadata'}
        self.sim_dict = self.options_dict['sim_dict']
        self.numeric_params = []
        self.data_type = self.options_dict['data_type']
        
        
        if self.data_type == 'averaged':
            self.base_analysis = AveragedTimedomainAnalysis(*args,
                                                            **kwargs)
        elif self.data_type == 'singleshot':
            self.base_analysis = roa.MultiQubit_SingleShot_Analysis(
                *args, **kwargs)
        else:
            raise KeyError("Invalid tomography data mode: '" + self.data_type +
                           "'. Valid modes are 'averaged' and 'singleshot'.")

        if kwargs.get('auto', True):
            self.run_analysis()

    def process_data(self):
        print(self.raw_data_dict['folder'])
        tomography_qubits = self.options_dict.get('tomography_qubits', None)
        print(tomography_qubits)
        data, Fs, Omega = self.base_analysis.measurement_operators_and_results(
                              tomography_qubits)
        print(data.shape, len(Fs), Fs[0].shape)
        if 'data_filter' in self.options_dict:
            data = self.options_dict['data_filter'](data.T).T

        data = data.T
        for i, v in enumerate(data):
            data[i] = v / v.sum()
        data = data.T
        

        Fs = self.options_dict.get('meas_operators', Fs)
        Fs = [qtp.Qobj(F) for F in Fs]
        d = Fs[0].shape[0]
        self.proc_data_dict['d'] = d
        Omega = self.options_dict.get('covar_matrix', Omega)
        if Omega is None:
            Omega = np.diag(np.ones(len(Fs)))
        elif len(Omega.shape) == 1:
            Omega = np.diag(Omega)
        metadata = self.raw_data_dict.get('exp_metadata', {})
        if metadata is None:
            metadata = {}
        self.raw_data_dict['exp_metadata'] = metadata
        basis_rots_str = metadata.get('basis_rots_str', None)
        basis_rots_str = self.options_dict.get('basis_rots_str', basis_rots_str)
        if basis_rots_str is not None:
            nr_qubits = int(np.round(np.log2(d)))
            pulse_list = list(itertools.product(basis_rots_str,
                                                repeat=nr_qubits))
            rotations = tomo.standard_qubit_pulses_to_rotations(pulse_list)
        else:
            rotations = metadata.get('basis_rots', None)
            rotations = self.options_dict.get('basis_rots', rotations)
            if rotations is None:
                raise KeyError("Either 'basis_rots_str' or 'basis_rots' "
                               "parameter must be passed in the options "
                               "dictionary or in the experimental metadata.")
        rotations = [qtp.Qobj(U) for U in rotations]

        all_Fs = tomo.rotated_measurement_operators(rotations, Fs)
        all_Fs = list(itertools.chain(*np.array(all_Fs).T))
        all_mus = np.array(list(itertools.chain(*data.T)))
        all_Omegas = sp.linalg.block_diag(*[Omega] * len(data[0]))

        self.proc_data_dict['meas_operators'] = all_Fs
        self.proc_data_dict['covar_matrix'] = all_Omegas
        self.proc_data_dict['meas_results'] = all_mus

        rho_ls = tomo.least_squares_tomography(all_mus, all_Fs, all_Omegas)
        self.proc_data_dict['rho_ls'] = rho_ls
        self.proc_data_dict['rho'] = rho_ls
        if self.options_dict.get('mle', False):
            rho_mle = tomo.mle_tomography(all_mus, all_Fs, all_Omegas,
                                          rho_guess=rho_ls)
            self.proc_data_dict['rho_mle'] = rho_mle
            self.proc_data_dict['rho'] = rho_mle
        rho = self.proc_data_dict['rho']

        self.proc_data_dict['purity'] = (rho * rho).tr().real

        if d == 4:
            self.proc_data_dict['concurrence'] = tomo.concurrence(rho)
            
        
        self.compare_3(qubits=list(self.raw_data_dict['exp_metadata']['channel_map']),
                       H0=self.sim_dict['H0'],
                       path=self.raw_data_dict['folder'])
        
    # Compare the three: rho, rho_sim, rho_ideal
    def compare_3(self, qubits=None, H0=None, path=None):
        #Define the number of qubits
        N=len(qubits)
        mes.N = N
        print('Number of qubits:', N)
        #Initial our times-parameter
        T1, T2s = mes.t1t2s_extract(path, qubits) #Lifetime and Dephasing rates of qubits. We must have T2s[i] < 2*T1[i]
        #T1 = [15, 9, 15, 30] #Lifetime of the qubits
        #T2s = [13, 12, 14 , 8] #Dephasing rates of qubits. We must have T2s[i] < 2*T1[i]
        mes.times['T1'] = T1
        mes.times['T2s'] = T2s
        print('T1 =',mes.times['T1'])
        print('T2s =',mes.times['T2s'])
    
        #Initial our Sequence of manipulation
        prep_seq = self.sim_dict['prep_seq']
        if prep_seq is 'load':
            manip = mes.manip_extract(path) #Extract the manipulation information from a certain path
            print('manipulation sequence:', manip)
        
        if prep_seq is None:
            raise KeyError("You must either have a prep sequence file or specify the seqencu yourself for simulations")
        
        #Initial our rho_sim and rho_ideal
        rho_sim=mes.rho_0(N=N)
        rho_ideal=mes.rho_0(N=N)
        
        #Start to simulation
        rho_sim, rho_ideal = mes.manipulate(manip=manip, rho_sim=rho_sim, rho_ideal=rho_ideal, times=mes.times, H0=H0, N=N)
        self.proc_data_dict['rho_sim'] = rho_sim
        self.proc_data_dict['rho_ideal'] = rho_ideal
        
        rho = self.proc_data_dict['rho']
        rho.dims = rho_sim.dims
        qtp.matrix_histogram_complex(rho)
        qtp.matrix_histogram_complex(rho_sim)
        qtp.matrix_histogram_complex(rho_ideal)
        
        
        self.proc_data_dict['fidelity_ideal'] = tomo.fidelity(rho, rho_ideal)
        self.proc_data_dict['fidelity_sim'] = tomo.fidelity(rho, rho_sim)
        self.proc_data_dict['fidelity_sim_ideal'] = tomo.fidelity(rho_ideal, rho_sim)
        
        print('fidelity between experimental and ideal result:',tomo.fidelity(rho, rho_ideal))
        print('fidelity between experimental and simulation result:',tomo.fidelity(rho, rho_sim))
        print('fidelity between simulation and ideal result:',tomo.fidelity(rho_sim, rho_ideal)) 

    def prepare_plots(self):
        self.prepare_density_matrix_plot()
        self.prepare_mesimulation_density_matrix_plot()
        d = self.proc_data_dict['d']
        if 2 ** (d.bit_length() - 1) == d:
            # dimension is power of two, plot expectation values of pauli
            # operators
            self.prepare_pauli_basis_plot()
    
    def prepare_density_matrix_plot(self):
        self.tight_fig = self.options_dict.get('tight_fig', False)
        rho_sim = self.proc_data_dict['rho_sim']
        rho_target = self.proc_data_dict['rho_ideal']
        d = self.proc_data_dict['d']
        xtick_labels = self.options_dict.get('rho_ticklabels', None)
        ytick_labels = self.options_dict.get('rho_ticklabels', None)
        if 2 ** (d.bit_length() - 1) == d:
            nr_qubits = d.bit_length() - 1
            fmt_string = '{{:0{}b}}'.format(nr_qubits)
            labels = [fmt_string.format(i) for i in range(2 ** nr_qubits)]
            if xtick_labels is None:
                xtick_labels = ['$|' + lbl + r'\rangle$' for lbl in labels]
            if ytick_labels is None:
                ytick_labels = [r'$\langle' + lbl + '|$' for lbl in labels]
        color = (0.5 * np.angle(self.proc_data_dict['rho'].full()) / np.pi) % 1.
        cmap = self.options_dict.get('rho_colormap', self.default_phase_cmap())
        if self.options_dict.get('mle', False):
            title = 'Maximum likelihood fit of the density matrix\n'
        else:
            title = 'Least squares fit of the density matrix\n'
        empty_artist = mpl.patches.Rectangle((0, 0), 0, 0, visible=False)
        legend_entries = [(empty_artist,
                           r'Purity, $Tr(\rho^2) = {:.1f}\%$'.format(
                               100 * self.proc_data_dict['purity']))]
        if rho_target is not None:
            legend_entries += [
                (empty_artist, r'Fidelity_ideal, $F = {:.1f}\%$'.format(
                    100 * self.proc_data_dict['fidelity_ideal']))]
        if rho_sim is not None:
            legend_entries += [
                (empty_artist, r'Fidelity_mesim, $F = {:.1f}\%$'.format(
                    100 * self.proc_data_dict['fidelity_sim']))]
        if d == 4:
            legend_entries += [
                (empty_artist, r'Concurrence, $C = {:.2f}$'.format(
                    self.proc_data_dict['concurrence']))]
        meas_string = self.base_analysis.\
            raw_data_dict['measurementstring']
        if isinstance(meas_string, list):
            if len(meas_string) > 1:
                meas_string = meas_string[0] + ' to ' + meas_string[-1]
            else:
                meas_string = meas_string[0]
        self.plot_dicts['density_matrix'] = {
            'plotfn': self.plot_bar3D,
            '3d': True,
            '3d_azim': -35,
            '3d_elev': 35,
            'xvals': np.arange(d),
            'yvals': np.arange(d),
            'zvals': np.abs(self.proc_data_dict['rho'].full()),
            'zrange': (0, 1),
            'color': color,
            'colormap': cmap,
            'bar_widthx': 0.5,
            'bar_widthy': 0.5,
            'xtick_loc': np.arange(d),
            'xtick_labels': xtick_labels,
            'ytick_loc': np.arange(d),
            'ytick_labels': ytick_labels,
            'ctick_loc': np.linspace(0, 1, 5),
            'ctick_labels': ['$0$', r'$\frac{1}{2}\pi$', r'$\pi$',
                             r'$\frac{3}{2}\pi$', r'$2\pi$'],
            'clabel': 'Phase (rad)',
            'title': (title + self.raw_data_dict['timestamp'] + ' ' +
                      meas_string),
            'do_legend': True,
            'legend_entries': legend_entries,
            'legend_kws': dict(loc='upper left', bbox_to_anchor=(0, 0.94))
        }

        if rho_target is not None:
            rho_target = qtp.Qobj(rho_target)
            if rho_target.type == 'ket':
                rho_target = rho_target * rho_target.dag()
            elif rho_target.type == 'bra':
                rho_target = rho_target.dag() * rho_target
            self.plot_dicts['density_matrix_target'] = {
                'plotfn': self.plot_bar3D,
                '3d': True,
                '3d_azim': -35,
                '3d_elev': 35,
                'xvals': np.arange(d),
                'yvals': np.arange(d),
                'zvals': np.abs(rho_target.full()),
                'zrange': (0, 1),
                'color': (0.5 * np.angle(rho_target.full()) / np.pi) % 1.,
                'colormap': cmap,
                'bar_widthx': 0.5,
                'bar_widthy': 0.5,
                'xtick_loc': np.arange(d),
                'xtick_labels': xtick_labels,
                'ytick_loc': np.arange(d),
                'ytick_labels': ytick_labels,
                'ctick_loc': np.linspace(0, 1, 5),
                'ctick_labels': ['$0$', r'$\frac{1}{2}\pi$', r'$\pi$',
                                 r'$\frac{3}{2}\pi$', r'$2\pi$'],
                'clabel': 'Phase (rad)',
                'title': ('Target density matrix\n' +
                          self.raw_data_dict['timestamp'] + ' ' +
                          meas_string),
                'bar_kws': dict(zorder=1),
            }
            
                    
    
    
    def prepare_mesimulation_density_matrix_plot(self):
        self.tight_fig = self.options_dict.get('tight_fig', False)
        rho_sim = self.proc_data_dict['rho_sim']
        rho_target = self.proc_data_dict['rho_ideal']
        d = self.proc_data_dict['d']
        xtick_labels = self.options_dict.get('rho_ticklabels', None)
        ytick_labels = self.options_dict.get('rho_ticklabels', None)
        if 2 ** (d.bit_length() - 1) == d:
            nr_qubits = d.bit_length() - 1
            fmt_string = '{{:0{}b}}'.format(nr_qubits)
            labels = [fmt_string.format(i) for i in range(2 ** nr_qubits)]
            if xtick_labels is None:
                xtick_labels = ['$|' + lbl + r'\rangle$' for lbl in labels]
            if ytick_labels is None:
                ytick_labels = [r'$\langle' + lbl + '|$' for lbl in labels]
        cmap = self.options_dict.get('rho_colormap', self.default_phase_cmap())
        title = 'The master eqt simulation density matrix\n'
        empty_artist = mpl.patches.Rectangle((0, 0), 0, 0, visible=False)
        #legend_entries = [(empty_artist,
        #                   r'Purity, $Tr(\rho^2) = {:.1f}\%$'.format(
        #                       100 * self.proc_data_dict['purity']))]
        if rho_target is not None:
            legend_entries = [
                (empty_artist, r'Fidelity_mesim_ideal, $F = {:.1f}\%$'.format(
                    100 * self.proc_data_dict['fidelity_sim_ideal']))]
        if d == 4:
            legend_entries += [
                (empty_artist, r'Concurrence, $C = {:.2f}$'.format(
                    self.proc_data_dict['concurrence']))]
        meas_string = self.base_analysis.\
            raw_data_dict['measurementstring']
        if isinstance(meas_string, list):
            if len(meas_string) > 1:
                meas_string = meas_string[0] + ' to ' + meas_string[-1]
            else:
                meas_string = meas_string[0]
        if rho_sim is not None:
            self.plot_dicts['density_matrix_mesim'] = {
                'plotfn': self.plot_bar3D,
                '3d': True,
                '3d_azim': -35,
                '3d_elev': 35,
                'xvals': np.arange(d),
                'yvals': np.arange(d),
                'zvals': np.abs(rho_sim.full()),
                'zrange': (0, 1),
                'color': (0.5 * np.angle(rho_sim.full()) / np.pi) % 1.,
                'colormap': cmap,
                'bar_widthx': 0.5,
                'bar_widthy': 0.5,
                'xtick_loc': np.arange(d),
                'xtick_labels': xtick_labels,
                'ytick_loc': np.arange(d),
                'ytick_labels': ytick_labels,
                'ctick_loc': np.linspace(0, 1, 5),
                'ctick_labels': ['$0$', r'$\frac{1}{2}\pi$', r'$\pi$',
                                 r'$\frac{3}{2}\pi$', r'$2\pi$'],
                'clabel': 'Phase (rad)',
                'title': (title + self.raw_data_dict['timestamp'] + ' ' +
                          meas_string),
                'do_legend': True,
                'legend_entries': legend_entries,
                'legend_kws': dict(loc='upper left', bbox_to_anchor=(0, 0.94))
            }

    def prepare_pauli_basis_plot(self):
        yexp = tomo.density_matrix_to_pauli_basis(self.proc_data_dict['rho'])
        nr_qubits = self.proc_data_dict['d'].bit_length() - 1
        labels = list(itertools.product(*[['I', 'X', 'Y', 'Z']]*nr_qubits))
        labels = [''.join(label_list) for label_list in labels]
        if nr_qubits == 1:
            order = [1, 2, 3]
        elif nr_qubits == 2:
            order = [1, 2, 3, 4, 8, 12, 5, 6, 7, 9, 10, 11, 13, 14, 15]
        elif nr_qubits == 4:
            order = [1, 2, 3, 4, 8, 12, 16, 32, 48] + \
                    [5, 6, 7, 9, 10, 11, 13, 14, 15] + \
                    [17, 18, 19, 33, 34, 35, 49, 50, 51] + \
                    [20, 24, 28, 36, 40, 44, 52, 56, 60] + \
                    [21, 22, 23, 25, 26, 27, 29, 30, 31] + \
                    [37, 38, 39, 41, 42, 43, 45, 46, 47] + \
                    [53, 54, 55, 57, 58, 59, 61, 62, 63]
        else:
            order = np.arange(4**nr_qubits)[1:]
        if self.options_dict.get('mle', False):
            fit_type = 'maximum likelihood estimation'
        else:
            fit_type = 'least squares fit'
        meas_string = self.base_analysis. \
            raw_data_dict['measurementstring']
        if hasattr(meas_string, '__iter__'):
            if len(meas_string) > 1:
                meas_string = meas_string[0] + ' to ' + meas_string[-1]
            else:
                meas_string = meas_string[0]
        self.plot_dicts['pauli_basis'] = {
            'plotfn': self.plot_bar,
            'xcenters': np.arange(len(order)),
            'xwidth': 0.4,
            'xrange': (-1, len(order)),
            'yvals': np.array(yexp)[order],
            'xlabel': r'Pauli operator, $\hat{O}$',
            'ylabel': r'Expectation value, $\mathrm{Tr}(\hat{O} \hat{\rho})$',
            'title': 'Pauli operators, ' + fit_type + '\n' +
                      self.raw_data_dict['timestamp'] + ' ' + meas_string,
            'yrange': (-1.1, 1.1),
            'xtick_loc': np.arange(4**nr_qubits - 1),
            'xtick_rotation': 90,
            'xtick_labels': np.array(labels)[order],
            'bar_kws': dict(zorder=10),
            'setlabel': 'Fit to experiment',
            'do_legend': True
        }
        if nr_qubits > 2:
            self.plot_dicts['pauli_basis']['plotsize'] = (10, 5)

        rho_target = self.proc_data_dict['rho_ideal']
        if rho_target is not None:
            rho_target = qtp.Qobj(rho_target)
            ytar = tomo.density_matrix_to_pauli_basis(rho_target)
            self.plot_dicts['pauli_basis_target'] = {
                'plotfn': self.plot_bar,
                'ax_id': 'pauli_basis',
                'xcenters': np.arange(len(order)),
                'xwidth': 0.8,
                'yvals': np.array(ytar)[order],
                'xtick_loc': np.arange(len(order)),
                'xtick_labels': np.array(labels)[order],
                'bar_kws': dict(color='0.8', zorder=0),
                'setlabel': 'Target values',
                'do_legend': True
            }

        purity_str = r'Purity, $Tr(\rho^2) = {:.1f}\%$'.format(
            100 * self.proc_data_dict['purity'])
        if rho_target is not None:
            fidelity_str = '\n' + r'Fidelity, $F = {:.1f}\%$'.format(
                100 * self.proc_data_dict['fidelity_ideal'])
        else:
            fidelity_str = ''
        if self.proc_data_dict['d'] == 4:
            concurrence_str = '\n' + r'Concurrence, $C = {:.1f}\%$'.format(
                100 * self.proc_data_dict['concurrence'])
        else:
            concurrence_str = ''
        self.plot_dicts['pauli_info_labels'] = {
            'ax_id': 'pauli_basis',
            'plotfn': self.plot_line,
            'xvals': [0],
            'yvals': [0],
            'line_kws': {'alpha': 0},
            'setlabel': purity_str + fidelity_str,
            'do_legend': True
        }

    def default_phase_cmap(self):
        cols = np.array(((41, 39, 231), (61, 130, 163), (208, 170, 39),
                         (209, 126, 4), (181, 28, 20), (238, 76, 152),
                         (251, 130, 242), (162, 112, 251))) / 255
        n = len(cols)
        cdict = {
            'red': [[i/n, cols[i%n][0], cols[i%n][0]] for i in range(n+1)],
            'green': [[i/n, cols[i%n][1], cols[i%n][1]] for i in range(n+1)],
            'blue': [[i/n, cols[i%n][2], cols[i%n][2]] for i in range(n+1)],
        }

        return mpl.colors.LinearSegmentedColormap('DMDefault', cdict)


class ReadoutROPhotonsAnalysis(Single_Qubit_TimeDomainAnalysis):
    """
    Analyses the photon number in the RO based on the
    readout_photons_in_resonator function

    function specific options for options dict:
    f_qubit
    chi
    artif_detuning
    print_fit_results
    """

    def __init__(self, t_start: str=None, t_stop: str=None,
                 label: str='', data_file_path: str=None,
                 close_figs: bool=False, options_dict: dict=None,
                 extract_only: bool=False, do_fitting: bool=False,
                 auto: bool=True):
        super().__init__(t_start=t_start, t_stop=t_stop,
                         data_file_path=data_file_path,
                         options_dict=options_dict,
                         close_figs=close_figs, label=label,
                         extract_only=extract_only, do_fitting=do_fitting)
        if self.options_dict.get('TwoD', None) is None:
            self.options_dict['TwoD'] = True
        self.label = label
        self.params_dict = {
            'measurementstring': 'measurementstring',
            'sweep_points': 'sweep_points',
            'sweep_points_2D': 'sweep_points_2D',
            'value_names': 'value_names',
            'value_units': 'value_units',
            'measured_values': 'measured_values'}

        self.numeric_params = self.options_dict.get('numeric_params',
                                                   OrderedDict())

        self.kappa = self.options_dict.get('kappa_effective', None)
        self.chi = self.options_dict.get('chi', None)
        self.T2 = self.options_dict.get('T2echo', None)
        self.artif_detuning = self.options_dict.get('artif_detuning', 0)

        if (self.kappa is None) or (self.chi is None) or (self.T2 is None):
            raise ValueError('kappa_effective, chi and T2echo must be passed to '
                             'the options_dict.')

        if auto:
            self.run_analysis()

    def process_data(self):
        #print(len(self.raw_data_dict['measured_values'][0][0]))
        #print(len(self.raw_data_dict['measured_values_ord_dict']['raw w0 _measure'][0]))
        self.proc_data_dict = OrderedDict()
        self.proc_data_dict['qubit_state'] = [[],[]]
        self.proc_data_dict['delay_to_relax'] = self.raw_data_dict[
                                                    'sweep_points_2D'][0]
        self.proc_data_dict['ramsey_times'] = []

        for i,x in enumerate(np.transpose(self.raw_data_dict[
                        'measured_values_ord_dict']['raw w0 _measure'][0])):
            self.proc_data_dict['qubit_state'][0].append([])
            self.proc_data_dict['qubit_state'][1].append([])

            for j,y in enumerate(np.transpose(self.raw_data_dict[
                    'measured_values_ord_dict']['raw w0 _measure'][0])[i]):

                if j%2 == 0:
                    self.proc_data_dict['qubit_state'][0][i].append(y)

                else:
                    self.proc_data_dict['qubit_state'][1][i].append(y)
        for i,x in enumerate( self.raw_data_dict['sweep_points'][0]):
            if i % 2 == 0:
                self.proc_data_dict['ramsey_times'].append(x)

    #I STILL NEED to pass Chi
    def prepare_fitting(self):
        self.proc_data_dict['photon_number'] = [[],[]]
        self.proc_data_dict['fit_results'] = []
        self.proc_data_dict['ramsey_fit_results'] = [[],[]]


        for i,tau in enumerate(self.proc_data_dict['delay_to_relax']):

            self.proc_data_dict['ramsey_fit_results'][0].append(self.fit_Ramsey(
                            self.proc_data_dict['ramsey_times'][:-4],
                            self.proc_data_dict['qubit_state'][0][i][:-4]/
                            max(self.proc_data_dict['qubit_state'][0][i][:-4]),
                            state=0,
                            kw=self.options_dict))

            self.proc_data_dict['ramsey_fit_results'][1].append(self.fit_Ramsey(
                            self.proc_data_dict['ramsey_times'][:-4],
                            self.proc_data_dict['qubit_state'][1][i][:-4]/
                            max(self.proc_data_dict['qubit_state'][1][i][:-4]),
                            state=1,
                            kw=self.options_dict))

            n01 = self.proc_data_dict['ramsey_fit_results'
                                         ][0][i][0].params['n0'].value
            n02 = self.proc_data_dict['ramsey_fit_results'
                                         ][1][i][0].params['n0'].value

            self.proc_data_dict['photon_number'][0].append(n01)
            self.proc_data_dict['photon_number'][1].append(n02)


    def run_fitting(self):
        print_fit_results = self.params_dict.pop('print_fit_results',False)

        exp_dec_mod = lmfit.Model(fit_mods.ExpDecayFunc)
        exp_dec_mod.set_param_hint('n',
                                   value=1,
                                   vary=False)
        exp_dec_mod.set_param_hint('offset',
                                   value=0,
                                   min=0,
                                   vary=True)
        exp_dec_mod.set_param_hint('tau',
                                   value=self.proc_data_dict[
                                                'delay_to_relax'][-1],
                                   min=1e-11,
                                   vary=True)
        exp_dec_mod.set_param_hint('amplitude',
                                   value=1,
                                   min=0,
                                   vary=True)
        params = exp_dec_mod.make_params()
        self.fit_res = OrderedDict()
        self.fit_res['ground_state'] = exp_dec_mod.fit(
                                data=self.proc_data_dict['photon_number'][0],
                                params=params,
                                t=self.proc_data_dict['delay_to_relax'])
        self.fit_res['excited_state'] = exp_dec_mod.fit(
                                data=self.proc_data_dict['photon_number'][1],
                                params=params,
                                t=self.proc_data_dict['delay_to_relax'])
        if print_fit_results:
            print(self.fit_res['ground_state'].fit_report())
            print(self.fit_res['excited_state'].fit_report())

    def fit_Ramsey(self, x, y, state, **kw):

        x = np.array(x)

        y = np.array(y)

        exp_dec_p_mod = lmfit.Model(fit_mods.ExpDecayPmod)
        comb_exp_dec_mod = lmfit.Model(fit_mods.CombinedOszExpDecayFunc)

        average = np.mean(y)

        ft_of_data = np.fft.fft(y)
        index_of_fourier_maximum = np.argmax(np.abs(
            ft_of_data[1:len(ft_of_data) // 2])) + 1
        max_ramsey_delay = x[-1] - x[0]

        fft_axis_scaling = 1 / max_ramsey_delay
        freq_est = fft_axis_scaling * index_of_fourier_maximum

        n_est = (freq_est-self.artif_detuning)/(2 * self.chi)


        exp_dec_p_mod.set_param_hint('T2echo',
                                   value=self.T2,
                                   vary=False)
        exp_dec_p_mod.set_param_hint('offset',
                                   value=average,
                                   min=0,
                                   vary=True)
        exp_dec_p_mod.set_param_hint('delta',
                                   value=self.artif_detuning,
                                   vary=False)
        exp_dec_p_mod.set_param_hint('amplitude',
                                   value=1,
                                   min=0,
                                   vary=True)
        exp_dec_p_mod.set_param_hint('kappa',
                                   value=self.kappa[state],
                                   vary=False)
        exp_dec_p_mod.set_param_hint('chi',
                                   value=self.chi,
                                   vary=False)
        exp_dec_p_mod.set_param_hint('n0',
                                      value=n_est,
                                      min=0,
                                      vary=True)
        exp_dec_p_mod.set_param_hint('phase',
                                       value=0,
                                       vary=True)


        comb_exp_dec_mod.set_param_hint('tau',
                                     value=self.T2,
                                     vary=True)
        comb_exp_dec_mod.set_param_hint('offset',
                                        value=average,
                                        min=0,
                                        vary=True)
        comb_exp_dec_mod.set_param_hint('oscillation_offset',
                                        value=average,
                                        min=0,
                                        vary=True)
        comb_exp_dec_mod.set_param_hint('amplitude',
                                     value=1,
                                     min=0,
                                     vary=True)
        comb_exp_dec_mod.set_param_hint('tau_gauss',
                                     value=self.kappa[state],
                                     vary=True)
        comb_exp_dec_mod.set_param_hint('n0',
                                     value=n_est,
                                     min=0,
                                     vary=True)
        comb_exp_dec_mod.set_param_hint('phase',
                                     value=0,
                                     vary=True)
        comb_exp_dec_mod.set_param_hint('delta',
                                     value=self.artif_detuning,
                                     vary=False)
        comb_exp_dec_mod.set_param_hint('chi',
                                     value=self.chi,
                                     vary=False)

        if (np.average(y[:4]) >
                np.average(y[4:8])):
            phase_estimate = 0
        else:
            phase_estimate = np.pi
        exp_dec_p_mod.set_param_hint('phase',
                                     value=phase_estimate, vary=True)
        comb_exp_dec_mod.set_param_hint('phase',
                                     value=phase_estimate, vary=True)

        amplitude_guess = 0.5
        if np.all(np.logical_and(y >= 0, y <= 1)):
            exp_dec_p_mod.set_param_hint('amplitude',
                                         value=amplitude_guess,
                                         min=0.00,
                                         max=4.0,
                                         vary=True)
            comb_exp_dec_mod.set_param_hint('amplitude',
                                         value=amplitude_guess,
                                         min=0.00,
                                         max=4.0,
                                         vary=True)

        else:
            print('data is not normalized, varying amplitude')
            exp_dec_p_mod.set_param_hint('amplitude',
                                         value=max(y),
                                         min=0.00,
                                         max=4.0,
                                         vary=True)
            comb_exp_dec_mod.set_param_hint('amplitude',
                                        value=max(y),
                                        min=0.00,
                                        max=4.0,
                                        vary=True)

        fit_res_1 = exp_dec_p_mod.fit(data=y,
                                    t=x,
                                    params= exp_dec_p_mod.make_params())

        fit_res_2 = comb_exp_dec_mod.fit(data=y,
                                         t=x,
                                         params= comb_exp_dec_mod.make_params())


        if fit_res_1.chisqr > .35:
            logging.warning('Fit did not converge, varying phase')
            fit_res_lst = []

            for phase_estimate in np.linspace(0, 2*np.pi, 10):

                for i, del_amp in enumerate(np.linspace(
                        -max(y)/10, max(y)/10, 10)):
                    exp_dec_p_mod.set_param_hint('phase',
                                                 value=phase_estimate,
                                                 vary=False)
                    exp_dec_p_mod.set_param_hint('amplitude',
                                                 value=max(y)+ del_amp)

                    fit_res_lst += [exp_dec_p_mod.fit(
                        data=y,
                        t=x,
                        params= exp_dec_p_mod.make_params())]

            chisqr_lst = [fit_res_1.chisqr for fit_res_1 in fit_res_lst]
            fit_res_1 = fit_res_lst[np.argmin(chisqr_lst)]

        if fit_res_2.chisqr > .35:
            logging.warning('Fit did not converge, varying phase')
            fit_res_lst = []

            for phase_estimate in np.linspace(0, 2*np.pi, 10):

                for i, del_amp in enumerate(np.linspace(
                        -max(y)/10, max(y)/10, 10)):
                    comb_exp_dec_mod.set_param_hint('phase',
                                                 value=phase_estimate,
                                                 vary=False)
                    comb_exp_dec_mod.set_param_hint('amplitude',
                                                 value=max(y)+ del_amp)

                    fit_res_lst += [comb_exp_dec_mod.fit(
                        data=y,
                        t=x,
                        params= comb_exp_dec_mod.make_params())]

            chisqr_lst = [fit_res_2.chisqr for fit_res_2 in fit_res_lst]
            fit_res_2 = fit_res_lst[np.argmin(chisqr_lst)]

        if fit_res_1.chisqr < fit_res_2.chisqr:
            self.proc_data_dict['params'] = exp_dec_p_mod.make_params()
            return [fit_res_1,fit_res_1,fit_res_2]
        else:
            self.proc_data_dict['params'] = comb_exp_dec_mod.make_params()
            return [fit_res_2,fit_res_1,fit_res_2]


    def prepare_plots(self):
            self.prepare_2D_sweep_plot()
            self.prepare_photon_number_plot()
            self.prepare_ramsey_plots()

    def prepare_2D_sweep_plot(self):
        self.plot_dicts['off_full_data_'+self.label] = {
            'title': 'Raw data |g>',
            'plotfn': self.plot_colorxy,
            'xvals': self.proc_data_dict['ramsey_times'],
            'xlabel': 'Ramsey delays',
            'xunit': 's',
            'yvals': self.proc_data_dict['delay_to_relax'],
            'ylabel': 'Delay after first RO-pulse',
            'yunit': 's',
            'zvals': np.array(self.proc_data_dict['qubit_state'][0]) }

        self.plot_dicts['on_full_data_'+self.label] = {
            'title': 'Raw data |e>',
            'plotfn': self.plot_colorxy,
            'xvals': self.proc_data_dict['ramsey_times'],
            'xlabel': 'Ramsey delays',
            'xunit': 's',
            'yvals': self.proc_data_dict['delay_to_relax'],
            'ylabel': 'Delay after first RO-pulse',
            'yunit': 's',
            'zvals': np.array(self.proc_data_dict['qubit_state'][1])  }



    def prepare_ramsey_plots(self):
        x_fit = np.linspace(self.proc_data_dict['ramsey_times'][0],
                            max(self.proc_data_dict['ramsey_times']),101)
        for i in range(len(self.proc_data_dict['ramsey_fit_results'][0])):

            self.plot_dicts['off_'+str(i)] = {
                'title': 'Ramsey w t_delay = '+\
                         str(self.proc_data_dict['delay_to_relax'][i])+ \
                         ' s, in |g> state',
                'ax_id':'ramsey_off_'+str(i),
                'plotfn': self.plot_line,
                'xvals': self.proc_data_dict['ramsey_times'],
                'xlabel': 'Ramsey delays',
                'xunit': 's',
                'yvals': np.array(self.proc_data_dict['qubit_state'][0][i]/
                             max(self.proc_data_dict['qubit_state'][0][i][:-4])),
                'ylabel': 'Measured qubit state',
                'yunit': '',
                'marker': 'o',
                'setlabel': '|g> data_'+str(i),
                'do_legend': True }

            self.plot_dicts['off_fit_'+str(i)] = {
                'title': 'Ramsey w t_delay = '+ \
                         str(self.proc_data_dict['delay_to_relax'][i])+ \
                         ' s, in |g> state',
                'ax_id':'ramsey_off_'+str(i),
                'plotfn': self.plot_line,
                'xvals': x_fit,
                'yvals':  self.proc_data_dict['ramsey_fit_results'][0][i][1].eval(
                    self.proc_data_dict['ramsey_fit_results'][0][i][1].params,
                    t=x_fit),
                'linestyle': '-',
                'marker': '',
                'setlabel': '|g> fit_model'+str(i),
                'do_legend': True  }

            self.plot_dicts['off_fit_2_'+str(i)] = {
                'title': 'Ramsey w t_delay = '+ \
                         str(self.proc_data_dict['delay_to_relax'][i])+ \
                         ' s, in |g> state',
                'ax_id':'ramsey_off_'+str(i),
                'plotfn': self.plot_line,
                'xvals': x_fit,
                'yvals':  self.proc_data_dict['ramsey_fit_results'][0][i][2].eval(
                    self.proc_data_dict['ramsey_fit_results'][0][i][2].params,
                    t=x_fit),
                'linestyle': '-',
                'marker': '',
                'setlabel': '|g> fit_simpel_model'+str(i),
                'do_legend': True  }

            self.plot_dicts['hidden_g_'+str(i)] = {
                'ax_id':'ramsey_off_'+str(i),
                'plotfn': self.plot_line,
                'xvals': [0],
                'yvals': [0],
                'color': 'w',
                'setlabel': 'Residual photon count = '
                             ''+str(self.proc_data_dict['photon_number'][0][i]),
                'do_legend': True }


            self.plot_dicts['on_'+str(i)] = {
                'title': 'Ramsey w t_delay = '+ \
                         str(self.proc_data_dict['delay_to_relax'][i])+ \
                         ' s, in |e> state',
                'ax_id':'ramsey_on_'+str(i),
                'plotfn': self.plot_line,
                'xvals': self.proc_data_dict['ramsey_times'],
                'xlabel': 'Ramsey delays',
                'xunit': 's',
                'yvals':  np.array(self.proc_data_dict['qubit_state'][1][i]/
                             max(self.proc_data_dict['qubit_state'][1][i][:-4])),
                'ylabel': 'Measured qubit state',
                'yunit': '',
                'marker': 'o',
                'setlabel': '|e> data_'+str(i),
                'do_legend': True }

            self.plot_dicts['on_fit_'+str(i)] = {
                'title': 'Ramsey w t_delay = '+ \
                         str(self.proc_data_dict['delay_to_relax'][i])+ \
                         ' s, in |e> state',
                'ax_id':'ramsey_on_'+str(i),
                'plotfn': self.plot_line,
                'xvals': x_fit,
                'yvals':  self.proc_data_dict['ramsey_fit_results'][1][i][1].eval(
                    self.proc_data_dict['ramsey_fit_results'][1][i][1].params,
                    t=x_fit),
                'linestyle': '-',
                'marker': '',
                'setlabel': '|e> fit_model'+str(i),
                'do_legend': True }

            self.plot_dicts['on_fit_2_'+str(i)] = {
                'title': 'Ramsey w t_delay = '+ \
                         str(self.proc_data_dict['delay_to_relax'][i])+ \
                         ' s, in |e> state',
                'ax_id':'ramsey_on_'+str(i),
                'plotfn': self.plot_line,
                'xvals': x_fit,
                'yvals':  self.proc_data_dict['ramsey_fit_results'][1][i][2].eval(
                    self.proc_data_dict['ramsey_fit_results'][1][i][2].params,
                    t=x_fit),
                'linestyle': '-',
                'marker': '',
                'setlabel': '|e> fit_simpel_model'+str(i),
                'do_legend': True }

            self.plot_dicts['hidden_e_'+str(i)] = {
                'ax_id':'ramsey_on_'+str(i),
                'plotfn': self.plot_line,
                'xvals': [0],
                'yvals': [0],
                'color': 'w',
                'setlabel': 'Residual photon count = '
                            ''+str(self.proc_data_dict['photon_number'][1][i]),
                'do_legend': True }


    def prepare_photon_number_plot(self):


        ylabel = 'Average photon number'
        yunit = ''

        x_fit = np.linspace(min(self.proc_data_dict['delay_to_relax']),
                            max(self.proc_data_dict['delay_to_relax']),101)
        minmax_data = [min(min(self.proc_data_dict['photon_number'][0]),
                           min(self.proc_data_dict['photon_number'][1])),
                       max(max(self.proc_data_dict['photon_number'][0]),
                           max(self.proc_data_dict['photon_number'][1]))]
        minmax_data[0] -= minmax_data[0]/5
        minmax_data[1] += minmax_data[1]/5

        self.proc_data_dict['photon_number'][1],

        self.fit_res['excited_state'].eval(
            self.fit_res['excited_state'].params,
            t=x_fit)
        self.plot_dicts['Photon number count'] = {
            'plotfn': self.plot_line,
            'xlabel': 'Delay after first RO-pulse',
            'ax_id': 'Photon number count ',
            'xunit': 's',
            'xvals': self.proc_data_dict['delay_to_relax'],
            'yvals': self.proc_data_dict['photon_number'][0],
            'ylabel': ylabel,
            'yunit': yunit,
            'yrange': minmax_data,
            'title': 'Residual photon number',
            'color': 'b',
            'linestyle': '',
            'marker': 'o',
            'setlabel': '|g> data',
            'func': 'semilogy',
            'do_legend': True}

        self.plot_dicts['main2'] = {
            'plotfn': self.plot_line,
            'xunit': 's',
            'xvals': x_fit,
            'yvals': self.fit_res['ground_state'].eval(
                self.fit_res['ground_state'].params,
                t=x_fit),
            'yrange': minmax_data,
            'ax_id': 'Photon number count ',
            'color': 'b',
            'linestyle': '-',
            'marker': '',
            'setlabel': '|g> fit',
            'func': 'semilogy',
            'do_legend': True}

        self.plot_dicts['main3'] = {
            'plotfn': self.plot_line,
            'xunit': 's',
            'xvals': self.proc_data_dict['delay_to_relax'],
            'yvals': self.proc_data_dict['photon_number'][1],
            'yrange': minmax_data,
            'ax_id': 'Photon number count ',
            'color': 'r',
            'linestyle': '',
            'marker': 'o',
            'setlabel': '|e> data',
            'func': 'semilogy',
            'do_legend': True}

        self.plot_dicts['main4'] = {
            'plotfn': self.plot_line,
            'xunit': 's',
            'ax_id': 'Photon number count ',
            'xvals': x_fit,
            'yvals': self.fit_res['excited_state'].eval(
                self.fit_res['excited_state'].params,
                t=x_fit),
            'yrange': minmax_data,
            'ylabel': ylabel,
            'color': 'r',
            'linestyle': '-',
            'marker': '',
            'setlabel': '|e> fit',
            'func': 'semilogy',
            'do_legend': True}

        self.plot_dicts['hidden_1'] = {
            'ax_id': 'Photon number count ',
            'plotfn': self.plot_line,
            'yrange': minmax_data,
            'xvals': [0],
            'yvals': [0],
            'color': 'w',
            'setlabel': 'tau_g = '
                        ''+str("%.3f" %
                        (self.fit_res['ground_state'].params['tau'].value*1e9))+''
                        ' ns',
            'do_legend': True }


        self.plot_dicts['hidden_2'] = {
            'ax_id': 'Photon number count ',
            'plotfn': self.plot_line,
            'yrange': minmax_data,
            'xvals': [0],
            'yvals': [0],
            'color': 'w',
            'setlabel': 'tau_e = '
                        ''+str("%.3f" %
                        (self.fit_res['excited_state'].params['tau'].value*1e9))+''
                        ' ns',
            'do_legend': True}


class RODynamicPhaseAnalysis(MultiQubit_TimeDomain_Analysis):

    def __init__(self, t_start: str=None, t_stop: str=None,
                 data_file_path: str=None, single_timestamp: bool=False,
                 options_dict: dict=None, extract_only: bool=False,
                 do_fitting: bool=True, auto=True):

        super().__init__(t_start=t_start, t_stop=t_stop,
                         data_file_path=data_file_path,
                         options_dict=options_dict,
                         extract_only=extract_only,
                         do_fitting=do_fitting,
                         auto=False)

        if auto:
            self.run_analysis()

    def process_data(self):

        super().process_data()

        if 'qbp_name' in self.metadata:
            self.pulsed_qbname = self.metadata['qbp_name']
        else:
            self.pulsed_qbname = self.options_dict.get('pulsed_qbname')
        self.measured_qubits = [qbn for qbn in self.channel_map if
                                qbn != self.pulsed_qbname]

    def prepare_fitting(self):
        self.fit_dicts = OrderedDict()
        for qbn in self.measured_qubits:
            ro_dict = self.proc_data_dict['corr_data'][qbn]
            for ro_suff, data in ro_dict.items():
                cos_mod = lmfit.Model(fit_mods.CosFunc)
                if self.NoCalPoints != 0:
                    data = data[:-self.NoCalPoints]
                guess_pars = fit_mods.Cos_guess(
                    model=cos_mod, t=self.sweep_points, data=data)
                guess_pars['amplitude'].vary = True
                guess_pars['offset'].vary = True
                guess_pars['frequency'].vary = True
                guess_pars['phase'].vary = True

                key = 'cos_fit_{}{}'.format(qbn, ro_suff)
                self.fit_dicts[key] = {
                    'fit_fn': fit_mods.CosFunc,
                    'fit_xvals': {'t': self.sweep_points},
                    'fit_yvals': {'data': data},
                    'guess_pars': guess_pars}

    def analyze_fit_results(self):

        self.dynamic_phases = OrderedDict()
        for meas_qbn in self.measured_qubits:
            self.dynamic_phases[meas_qbn] = \
                (self.fit_dicts['cos_fit_{}_measure'.format(meas_qbn)][
                    'fit_res'].best_values['phase'] -
                 self.fit_dicts['cos_fit_{}_ref_measure'.format(meas_qbn)][
                    'fit_res'].best_values['phase'])*180/np.pi

    def prepare_plots(self):

        super().prepare_plots()

        if self.do_fitting:
            for meas_qbn in self.measured_qubits:
                if self.NoCalPoints != 0:
                    yvals = [self.proc_data_dict['corr_data'][meas_qbn][
                                 '_ref_measure'][:-self.NoCalPoints],
                             self.proc_data_dict['corr_data'][meas_qbn][
                                 '_measure'][:-self.NoCalPoints]]

                    # plot cal points
                    for i, cal_pts_idxs in enumerate(self.cal_points[::-1]):
                        key = 'exc_state_' + meas_qbn if i == 0 else \
                            'gnd_state_' + meas_qbn
                        self.plot_dicts[key] = {
                            'ax_id': 'dyn_phase_plot_' + meas_qbn,
                            'plotfn': self.plot_line,
                            'xvals': self.raw_data_dict['sweep_points'][0][
                                cal_pts_idxs],
                            'yvals': np.mean([
                                self.proc_data_dict['corr_data'][meas_qbn][
                                    '_ref_measure'][cal_pts_idxs],
                                self.proc_data_dict['corr_data'][meas_qbn][
                                    '_measure'][cal_pts_idxs]],
                                             axis=0),
                            'setlabel': r'$|e\rangle$' if i == 0 \
                                else r'$|g\rangle$',
                            'do_legend': True,
                            'legend_bbox_to_anchor': (1, 0.5),
                            'legend_pos': 'center left',
                            'linestyle': 'none',
                            'line_kws': {'color': 'gray' if i == 0 else 'k'}}

                else:
                    yvals = [self.proc_data_dict['corr_data'][meas_qbn][
                                 '_ref_measure'],
                             self.proc_data_dict['corr_data'][meas_qbn][
                                 '_measure']]

                self.plot_dicts['dyn_phase_plot_' + meas_qbn] = {
                    'plotfn': self.plot_line,
                    'xvals': [self.sweep_points, self.sweep_points],
                    'xlabel': self.raw_data_dict['xlabel'][0],
                    'xunit': self.raw_data_dict['xunit'][0],
                    'yvals': yvals,
                    'ylabel': 'Excited state population',
                    'yunit': '',
                    'setlabel': ['with measurement', 'no measurement'],
                    'title': (self.raw_data_dict['timestamps'][0] + ' ' +
                              self.raw_data_dict['measurementstring'][0]),
                    'linestyle': 'none',
                    'do_legend': True,
                    'legend_bbox_to_anchor': (1, 0.5),
                    'legend_pos': 'center left'}

                self.plot_dicts['cos_fit_' + meas_qbn + '_ref_measure'] = {
                    'ax_id': 'dyn_phase_plot_' + meas_qbn,
                    'plotfn': self.plot_fit,
                    'fit_res': self.fit_dicts['cos_fit_{}_ref_measure'.format(
                                    meas_qbn)]['fit_res'],
                    'setlabel': 'cos fit',
                    'do_legend': True,
                    'legend_bbox_to_anchor': (1, 0.5),
                    'legend_pos': 'center left'}

                self.plot_dicts['cos_fit_' + meas_qbn + '_measure'] = {
                    'ax_id': 'dyn_phase_plot_' + meas_qbn,
                    'plotfn': self.plot_fit,
                    'fit_res': self.fit_dicts['cos_fit_{}_measure'.format(
                                    meas_qbn)]['fit_res'],
                    'setlabel': 'cos fit',
                    'do_legend': True,
                    'legend_bbox_to_anchor': (1, 0.5),
                    'legend_pos': 'center left'}

                textstr = 'Dynamic phase = {:.2f}'.format(
                    self.dynamic_phases[meas_qbn]) + r'$^{\circ}$'
                self.plot_dicts['text_msg_' + meas_qbn] = {
                    'ax_id': 'dyn_phase_plot_' + meas_qbn,
                    'verticalalignment': 'bottom',
                    'horizontalalignment': 'left',
                    'ypos': 0,
                    'xpos': 1.05,
                    'plotfn': self.plot_text,
                    'box_props': None,
                    'text_string': textstr}
