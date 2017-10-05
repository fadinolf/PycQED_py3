import time
import logging
import os
import numpy as np
from . import zishell_NH as zs
from qcodes.utils import validators as vals
from .ZI_base_instrument import ZI_base_instrument
from qcodes.instrument.parameter import ManualParameter

import ctypes
from ctypes.wintypes import MAX_PATH


class ZI_HDAWG8(ZI_base_instrument):
    """
    This is PycQED/QCoDeS driver driver for the Zurich Instruments HD AWG-8.

    Parameter files are generated from the python API of the instrument
    using the "create_parameter_file" method in the ZI_base_instrument class.
    These are used to add parameters to the instrument.
    """

    def __init__(self, name, device: str,
                 server: str='localhost', port=8004,
                 num_codewords: int = 32, **kw):
        '''
        Input arguments:
            name:           (str) name of the instrument as seen by the user
            device          (str) the name of the device e.g., "dev8008"
            server          (str) the ZI data server
            port            (int) the port to connect to
        '''
        t0 = time.time()
        self._num_channels = 8
        self._num_codewords = num_codewords

        if os.name == 'nt':
            dll = ctypes.windll.shell32
            buf = ctypes.create_unicode_buffer(MAX_PATH + 1)
            if dll.SHGetSpecialFolderPathW(None, buf, 0x0005, False):
                _basedir = buf.value
            else:
                logging.warning('Could not extract my documents folder')
        else:
            _basedir = os.path.expanduser('~')
        self.lab_one_webserver_path = os.path.join(
            _basedir, 'Zurich Instruments', 'LabOne', 'WebServer')

        super().__init__(name=name, **kw)
        self._devname = device
        self._dev = zs.ziShellDevice()
        self._dev.connect_server(server, port)
        print("Trying to connect to device {}".format(self._devname))
        self._dev.connect_device(self._devname, '1GbE')

        dir_path = os.path.dirname(os.path.abspath(__file__))
        base_fn = os.path.join(dir_path, 'zi_parameter_files')

        try:
            self.add_parameters_from_file(
                filename=os.path.join(base_fn, 'node_doc_HDAWG8.json'))

        except FileNotFoundError:
            logging.warning("parameter file for data parameters"
                            " {} not found".format(self._d_file_name))
        self.add_ZIshell_device_methods_to_instrument()

        self._add_codeword_parameters()
        self._add_extra_parameters()
        self.connect_message(begin_time=t0)

    def _add_extra_parameters(self):
        self.add_parameter('timeout', unit='s',
                           initial_value=10,
                           parameter_class=ManualParameter)
        self.add_parameter(
            'cfg_num_codewords', label='Number of used codewords', docstring=(
                'This parameter is used to determine how many codewords to '
                'upload in "self.upload_codeword_program".'),
            initial_value=self._num_codewords,
            # N.B. I have commentd out numbers larger than self._num_codewords
            # see also issue #358
            vals=vals.Enum(2, 4, 8, 16, 32), # , 64, 128, 256, 1024),
            parameter_class=ManualParameter)

        self.add_parameter(
            'cfg_codeword_protocol', initial_value='identical',
            vals=vals.Enum('identical', 'microwave', 'flux'), docstring=(
                'Used in the configure codeword method to determine what DIO'
                ' pins are used in for which AWG numbers.'),
            parameter_class=ManualParameter)

    def snapshot_base(self, update=False, params_to_skip_update=None):
        if params_to_skip_update is None:
            params_to_skip_update = self._params_to_skip_update
        snap = super().snapshot_base(
            update=update, params_to_skip_update=params_to_skip_update)
        return snap

    def add_ZIshell_device_methods_to_instrument(self):
        """
        Some methods defined in the zishell are convenient as public
        methods of the instrument. These are added here.
        """
        self.reconnect = self._dev.reconnect
        self.restart_device = self._dev.restart_device
        self.poll = self._dev.poll
        self.sync = self._dev.sync
        self.configure_awg_from_string = self._dev.configure_awg_from_string
        self.read_from_scope = self._dev.read_from_scope
        self.restart_scope_module = self._dev.restart_scope_module
        self.restart_awg_module = self._dev.restart_awg_module

    def get_idn(self):
        idn_dict = {'vendor': 'ZurichInstruments',
                    'model': self._dev.daq.getByte(
                        '/{}/features/devtype'.format(self._devname)),
                    'serial': self._devname,
                    'firmware': self._dev.geti('system/fwrevision'),
                    'fpga_firmware': self._dev.geti('system/fpgarevision')
                    }
        return idn_dict

    def stop(self):
        """
        Stops the program on all AWG's part of this AWG8 unit
        """
        for i in range(4):
            self.set('awgs_{}_enable'.format(i), 0)

    def start(self):
        """
        Starts the program on all AWG's part of this AWG8 unit
        """
        for i in range(4):
            self.set('awgs_{}_enable'.format(i), 1)

    def _add_codeword_parameters(self):
        """
        Adds parameters parameters that are used for uploading codewords.
        It also contains initial values for each codeword to ensure
        that the "upload_codeword_program"

        """
        docst = ('Specifies a waveform to for a specific codeword. ' +
                 'The waveforms must be uploaded using ' +
                 '"upload_codeword_program". The channel number corresponds' +
                 ' to the channel as indicated on the device (1 is lowest).')
        self._params_to_skip_update = []
        for ch in range(self._num_channels):
            for cw in range(self._num_codewords):
                parname = 'wave_ch{}_cw{:03}'.format(ch+1, cw)
                self.add_parameter(
                    parname,
                    label='Waveform channel {} codeword {:03}'.format(
                        ch+1, cw),
                    vals=vals.Arrays(),  # min_value, max_value = unknown
                    set_cmd=self._gen_write_csv(parname),
                    get_cmd=self._gen_read_csv(parname),
                    docstring=docst)
                self._params_to_skip_update.append(parname)

    def _gen_write_csv(self, wf_name):
        def write_func(waveform):
            # The lenght of AWG8 waveforms should be a multiple of 8 samples.
            if (len(waveform) % 8) != 0:
                extra_zeros = 8-(len(waveform) % 8)
                waveform = np.concatenate([waveform, np.zeros(extra_zeros)])
            return self._write_csv_waveform(
                wf_name=wf_name, waveform=waveform)
        return write_func

    def _gen_read_csv(self, wf_name):
        def read_func():
            return self._read_csv_waveform(
                wf_name=wf_name)
        return read_func

    def _write_csv_waveform(self, wf_name: str, waveform):
        filename = os.path.join(
            self.lab_one_webserver_path, 'awg', 'waves',
            self._devname+'_'+wf_name+'.csv')
        with open(filename, 'w') as f:
            np.savetxt(filename, waveform, delimiter=",")

    def _read_csv_waveform(self, wf_name: str):
        filename = os.path.join(
            self.lab_one_webserver_path, 'awg', 'waves',
            self._devname+'_'+wf_name+'.csv')
        try:
            return np.genfromtxt(filename, delimiter=',')
        except OSError as e:
            # if the waveform does not exist yet dont raise exception
            logging.warning(e)
            print(e)
            return None

    # Note: This was added for debugging by NielsH.
    # If we do not need it for a few days we should remove it. (2/10/2017)
    # def stop_awg(self):
    #     test_program = """
    #     // 'Counting'  waveform
    #     const N = 80;
    #     setWaveDIO(0, ones(N), -ones(N));
    #     setWaveDIO(1,  ones(N), -ones(N));
    #     setWaveDIO(2, -ones(N),  ones(N));
    #     setWaveDIO(3,  ones(N),  ones(N));
    #     setWaveDIO(4,  -blackman(N, 1.0, 0.2),  -blackman(N, 1.0, 0.2));
    #     setWaveDIO(5,   blackman(N, 1.0, 0.2),  -blackman(N, 1.0, 0.2));
    #     setWaveDIO(6,  -blackman(N, 1.0, 0.2),  blackman(N, 1.0, 0.2));
    #     setWaveDIO(7,  blackman(N, 1.0, 0.2),  blackman(N, 1.0, 0.2));
    #     """

    #     for awg_nr in range(4):
    #         print('Configuring AWG {} with dummy program'.format(awg_nr))

    #         # disable all AWG channels
    #         self.set('awgs_{}_enable'.format(awg_nr), 0)
    #         self.configure_awg_from_string(awg_nr, test_program, self.timeout())
    #         self.set('awgs_{}_single'.format(awg_nr), 0)
    #         self.set('awgs_{}_enable'.format(awg_nr), 1)

    #     print('Waiting...')
    #     time.sleep(1)

    #     for awg_nr in range(4):
    #         # disable all AWG channels
    #         self.set('awgs_{}_enable'.format(awg_nr), 0)

    def initialze_all_codewords_to_zeros(self):
        """
        Generates all zeros waveforms for all codewords
        """
        t0 = time.time()
        wf = np.zeros(32)
        waveform_params = [value for key, value in self.parameters.items()
                           if 'wave_ch' in key.lower()]
        for par in waveform_params:
            par(wf)
        t1 = time.time()
        print('Set all zeros waveforms in {:.1f} s'.format(t1-t0))

    def upload_codeword_program(self):
        """
        Generates a program that plays the codeword waves for each channel.
        """

        for awg_nr in range(4):
            # disable all AWG channels
            self.set('awgs_{}_enable'.format(awg_nr), 0)

        codeword_mode_snippet = (
            'while (1) { \n '
            '\t// Wait for a trigger on the DIO interface\n'
            '\twaitDIOTrigger();\n'
            '\t// Play a waveform from the table based on the DIO code-word\n'
            '\tplayWaveDIO(); \n'
            '}')

        for ch in [1, 3, 5, 7]:
            waveform_table = '// Define the waveform table\n'
            for cw in range(self.cfg_num_codewords()):
                wf0_name = '{}_wave_ch{}_cw{:03}'.format(
                    self._devname, ch, cw)
                wf1_name = '{}_wave_ch{}_cw{:03}'.format(
                    self._devname, ch+1, cw)
                waveform_table += 'setWaveDIO({}, "{}", "{}");\n'.format(
                    cw, wf0_name, wf1_name)
            program = waveform_table + codeword_mode_snippet
            # N.B. awg_nr in goes from 0 to 3 in API while in LabOne it is 1 to
            # 4
            awg_nr = ch//2  # channels are coupled in pairs of 2
            self.configure_awg_from_string(awg_nr=awg_nr,
                                           program_string=program,
                                           timeout=self.timeout())
            self._configure_codeword_protocol()

    def _configure_codeword_protocol(self):
        """
        This method configures the AWG-8 codeword protocol.
        It includes specifying what bits are used to specify codewords
        as well as setting the delays on the different bits.

        The protocol uses several parts to specify the
        These parameters are specific to each AWG-8 channel and depend on the
        the function the AWG8 has in the setup.

        The parameter "cfg_codeword_protocol" defines what protocol is used.
        There are three options:
            identical : all AWGs have the same configuration
            microwave : AWGs 0 and 1 share bits

        Protocol definition:
        protocol
            - mask/value -> some bits are masked to allow using only a few bits
                            to specify a codeword.
            - mask/shift -> all acquired bits are shifted to allow specifying
                            which bits should be used.
        The parameters below are global to all AWG channels.
            - strobe/index -> this specifies which bit is the toggle/strobe bit
            - strobe/slope -> check for codewords on rissing/falling or both
                              edges of the toggle bit.
            - valid/index  -> specifies the codeword valid bit
            - valid/slope  -> specifies the slope of the valid bit

        Delay configuration
            In this part the DIO delay indices are set. These should be
            identical for each AWG channel.
            - dio/delay/index -> selects which delay to change next
            - dio/delay/value -> specifies an individual delay

        Trun on device
            The final step enablse the signal output of each AWG and sets
            it to the right mode.

        """
        ####################################################
        # Protocol definition
        ####################################################

        # Configure the DIO interface for triggering on

        for awg_nr in range(4):
            # This is the bit index of the valid bit,
            self.set('awgs_{}_dio_valid_index'.format(awg_nr), 31)
            # Valid polarity is 'high' (hardware value 2),
            # 'low' (hardware value 1), 'no valid needed' (hardware value 0)
            self.set('awgs_{}_dio_valid_polarity'.format(awg_nr), 2)
            # This is the bit index of the strobe signal (toggling signal),
            self.set('awgs_{}_dio_strobe_index'.format(awg_nr), 30)

            # Configure the DIO interface for triggering on the both edges of
            # the strobe/toggle bit signal.
            # 1: rising edge, 2: falling edge or 3: both edges
            self.set('awgs_{}_dio_strobe_slope'.format(awg_nr), 3)

            # the mask determines how many bits will be used in the protocol
            # e.g., mask 3 will mask the bits with bin(3) = 00000011 using
            # only the 2 Least Significant Bits.
            # N.B. cfg_num_codewords must be a power of 2
            self.set('awgs_{}_dio_mask_value'.format(awg_nr),
                     self.cfg_num_codewords()-1)


            if self.cfg_codeword_protocol() == 'identical':
                # In the identical protocol all bits are used to trigger
                # the same codewords on all AWG's

                # N.B. The shift is applied before the mask
                # The relevant bits can be selected by first shifting them
                # and then masking them.
                self.set('awgs_{}_dio_mask_shift'.format(awg_nr), 0)

        # In the mw protocol bits [0:7] -> CW0 and bits [(8+1):15] -> CW1
        # N.B. DIO bit 8 (first of 2nd byte)  not connected in AWG8!
        if self.cfg_codeword_protocol() == 'microwave':
            for awg_nr in [0, 1]:
                self.set('awgs_{}_dio_mask_shift'.format(awg_nr), 0)

            for awg_nr in [2, 3]:
                self.set('awgs_{}_dio_mask_shift'.format(awg_nr), 9)

        if self.cfg_codeword_protocol() == 'flux':
            raise NotImplementedError()

        ####################################################
        # Delay configuration
        ####################################################

        # Reset all DIO delays
        for i in range(32):
            self._dev.daq.setInt('/' + self._dev.device +
                                 '/awgs/*/dio/delay/index', i)
            self._dev.daq.setInt('/' + self._dev.device +
                                 '/awgs/*/dio/delay/value', 0)
        # Delay only the toggle/strobe bit by "codeword_delay" samples
        codeword_delay = 2
        self._dev.daq.setInt('/' + self._dev.device +
                             '/awgs/*/dio/delay/index', 30)
        self._dev.daq.setInt('/' + self._dev.device +
                             '/awgs/*/dio/delay/value', codeword_delay)

        ####################################################
        # Turn on device
        ####################################################

        time.sleep(1)
        self._dev.daq.setInt('/' + self._dev.device +
                             '/awgs/*/enable', 1)

        # Turn on all outputs
        self._dev.daq.setInt('/' + self._dev.device + '/sigouts/*/on', 1)
        # Disable all function generators
        self._dev.daq.setInt('/' + self._dev.device +
                             '/sigouts/*/enables/*', 0)
        # Switch all outputs in to DAC mode
        self._dev.daq.setInt('/' + self._dev.device + '/raw/sigouts/*/mode', 0)
