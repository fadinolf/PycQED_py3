import time
import numpy as np
import sys
import serial
import io
import visa
import unittest
from bitstring import BitArray

qcpath = 'D:\GitHubRepos\Qcodes'
if qcpath not in sys.path:
    sys.path.append(qcpath)

from qcodes.instrument.visa import VisaInstrument
from qcodes.utils import validators as vals

# cython drivers for encoding and decoding
import pyximport
pyximport.install(setup_args={"script_args": ["--compiler=msvc"],
                              "include_dirs": np.get_include()},
                  reload_support=True)

from ._ControlBox import defHeaders  # File containing bytestring commands
from ._ControlBox import decoder as d  # Cython based decoder
from ._ControlBox import codec as c
from ._ControlBox import test_suite# import CBox_tests
from importlib import reload # Useful for reloading during testin
reload(test_suite)

class QuTech_ControlBox(VisaInstrument):
    '''
    This is the qtlab driver for the 250 MS/s control box developed in
    collaboration with EWI.
    This is a direct port of the 'old' matlab drivers.

    Requirements:
    file defHeaders must be placed in the same folder to be importable

    Warning! this instrument can NOT be reloaded as reloading does not
    reopen the com-port used. This might be aleviated in versions where a
    different protocol (e.g. TCPIP is used).
    '''

    def __init__(self, name, address, reset=False, run_tests=False):
        super().__init__(name, address)
        # Establish communications
        self.add_parameter('firmware_version',
                           get_cmd=self._do_get_firmware_version)
        self.add_parameter('acquisition_mode', type=int,
                           set_cmd=self._do_set_acquisition_mode,
                           get_cmd=self._do_get_acquisition_mode)
        # self.add_parameter('signal_delay', type=int,
        #                    min=0, max=255,
        #                    flags=Instrument.FLAG_GETSET |
        #                    Instrument.FLAG_SOFTGET)
        # self.add_parameter('integration_length', type=int,
        #                    min=1, max=512,
        #                    flags=Instrument.FLAG_GETSET |
        #                    Instrument.FLAG_SOFTGET)
        # self.add_parameter('signal_threshold_line0', type=int,
        #                    min=-2**27, max=2**27-1,
        #                    flag=Instrument.FLAG_GETSET |
        #                    Instrument.FLAG_SOFTGET)
        # self.add_parameter('signal_threshold_line1', type=int,
        #                    min=-2**27, max=2**27-1,
        #                    flag=Instrument.FLAG_GETSET |
        #                    Instrument.FLAG_SOFTGET)
        # self.add_parameter('adc_offset', type=int,
        #                    min=-128, max=127,
        #                    flag=Instrument.FLAG_GETSET |
        #                    Instrument.FLAG_SOFTGET)
        # self.add_parameter('log_length', type=int,
        #                    min=0, max=8000,
        #                    flag=Instrument.FLAG_GETSET |
        #                    Instrument.FLAG_SOFTGET)

        # self.add_parameter('nr_samples', type=int,
        #                    flag=Instrument.FLAG_GETSET |
        #                    Instrument.FLAG_SOFTGET)
        # self.add_parameter('nr_averages', type=int,
        #                    flag=Instrument.FLAG_GETSET |
        #                    Instrument.FLAG_SOFTGET)
        # self.add_parameter('run_mode', type=int,
        #                    flag=Instrument.FLAG_GETSET |
        #                    Instrument.FLAG_SOFTGET)
        # self.add_parameter('measurement_timeout', type=int, units='seconds',
        #                    flag=Instrument.FLAG_GETSET)

        # self.add_parameter('sequencer_counters', type=int,
        #                    flag=Instrument.FLAG_GET)

        # self.add_parameter('tng_heartbeat_interval', type=int, units='ns',
        #                    flag=Instrument.FLAG_GETSET)
        # self.add_parameter('tng_burst_heartbeat_interval', type=int,
        #                    flag=Instrument.FLAG_GETSET)
        # self.add_parameter('tng_burst_heartbeat_n', type=int,
        #                    flag=Instrument.FLAG_GETSET)
        # self.add_parameter('tng_readout_delay', type=int, units='ns',
        #                    flag=Instrument.FLAG_GETSET)
        # self.add_parameter('tng_second_pre_rotation_delay', type=int,
        #                    units='ns', flag=Instrument.FLAG_GETSET)
        # self.add_parameter('tng_calibration_mode', type=int,
        #                    flag=Instrument.FLAG_GETSET)
        # self.add_parameter('tng_awg_mask', type=int,
        #                    flag=Instrument.FLAG_GETSET)
        # self.add_parameter('tng_readout_pulse_length', type=int, units='ns',
        #                    flag=Instrument.FLAG_GETSET)
        # self.add_parameter('tng_readout_wave_interval', type=int, units='ns',
        #                    flag=Instrument.FLAG_GETSET)
        # self.add_parameter('tng_output_trigger_delay', type=int, units='ns',
        #                    flag=Instrument.FLAG_GETSET)
        # self.add_parameter('tng_trigger_state', type=int,
        #                    flag=Instrument.FLAG_GETSET)
        # self.add_parameter('tng_feedback_mode', type=int,
        #                    flag=Instrument.FLAG_GETSET)
        # self.add_parameter('tng_feedback_code', type=int,
        #                    flag=Instrument.FLAG_GETSET)
        # self.add_parameter('tng_logging_mode', type=int,
        #                    flag=Instrument.FLAG_GETSET)

        # self.tng_heartbeat_interval = 100000
        # self.tng_burst_heartbeat_interval = 10000
        # self.tng_burst_heartbeat_n = 1
        # self.tng_readout_delay = 300
        # self.tng_calibration_mode = True
        # self.tng_awg_mask = 100
        # self.tng_readout_pulse_length = 1200
        # self.tng_readout_wave_interval = 600
        # self.tng_output_trigger_delay = 1
        # self.tng_trigger_state = 1
        # self.tng_feedback_mode = 1
        # self.tng_feedback_code = 3
        # self.tng_logging_mode = 3
        # self.tng_second_pre_rotation_delay = 0

        # self.integration_weights = [[], []]
        # self.awg_mode = [0, 0, 0]  # default values so it is gettable
        # self.dac_offsets = np.empty([3, 2])
        # self.dac_offsets[:] = np.NAN

        # self.set_measurement_timeout(360)

        # self.add_function('set_awg_lookuptable')
        # self.add_function('get_streaming_results')
        # self.add_function('get_integration_log_results')
        # self.add_function('get_avg_size')

        # self.add_function('set_averaging_parameters')
        # self.add_function('set_integration_weights')
        # self.add_function('encode_byte')
        # self.add_function('decode_byte')
        # self.add_function('enable_dac')
        # # self.add_function('awg_mode') #somehow won't wrap it in QTLab ...
        # self.add_function('set_lin_trans_coeffs')
        # self.add_function('set_dac_offset')

        # convert to string with options

        if run_tests:
            # pass the CBox to the module so it can be used in the tests
            self.c = c  # make the codec callable from the testsuite
            test_suite.CBox = self
            suite = unittest.TestLoader().loadTestsFromTestCase(test_suite.CBox_tests)
            unittest.TextTestRunner(verbosity=2).run(suite)

    def get_all(self):
        for par in self.parameters:
                        self[par].get()
        return self.snapshot()

    def _do_set_measurement_timeout(self, val):
        '''
        Sets the measurement timeout in seconds.
        This is distinct from the timeout of the read operation (5s default)
        '''
        self.timeout = val

    def _do_get_measurement_timeout(self):
        return self.timeout

    def _do_get_firmware_version(self):
        message = c.create_message(defHeaders.ReadVersion)
        (stat, mesg) = self.serial_write(message)
        if stat:
            version_msg = self.serial_read()
        # Decoding the message
        # -128 is because of MSB signifying data byte
        v_str = str(version_msg[0]-128)+'.'+str(version_msg[1]-128) + \
            '.'+str(version_msg[2]-128)
        return v_str
        return v_str

    def _do_get_sequencer_counters(self):
        '''
        Compares heartbeat counts to trigger counts in touch 'n go mode.
        To determine succes rate.
        Heartbeat counter: how many times touch n go was attempted.
        Trigger counter: how many times an external triger was given.
        '''
        message = c.create_message(defHeaders.ReadSequencerCounters)
        (stat, mesg) = self.serial_write(message)
        if stat:
            sequencer_msg = self.serial_read()
            # Decoding the message
            s_list = list(map(ord, sequencer_msg[0:6]))
            heartbeat_counter = (s_list[0]-128)*(2**14)+(s_list[1]-128)*(2**7) + \
                (s_list[2]-128)
            trigger_counter = (s_list[3]-128)*(2**14)+(s_list[4]-128)*(2**7) + \
                (s_list[5]-128)

        return heartbeat_counter, trigger_counter


    def decode_message(self, data_bytes, data_bits_per_byte=7,
                       bytes_per_value=2, signed_integer=False):
        '''
        Exists for legacy use (only used in integration streaming mode)
        recommend using the cython version otherwise.
        '''
        message_bytes = bytearray(data_bytes[:-2])
        # checksum = self.calculate_checksum(message_bytes)
        # if checksum != message_bytes[-1]:
        #     raise ValueError('Checksum does not match message')
        if type(data_bits_per_byte) == int:
            data_bits_per_byte = [data_bits_per_byte]
        if type(bytes_per_value) == int:
            bytes_per_value = [bytes_per_value]
        if type(signed_integer)==bool:
            signed_integer=[signed_integer]*len(bytes_per_value)
        assert(len(data_bits_per_byte) == len(bytes_per_value))

        bytes_per_iteration = sum(bytes_per_value)
        message_length = len(message_bytes)/bytes_per_iteration
        values = np.zeros([message_length, len(bytes_per_value)])
        cum_bytes_per_val = np.cumsum(bytes_per_value)

        for i in range(message_length):
            iteration_bytes = message_bytes[i*bytes_per_iteration:
                                            (i+1)*bytes_per_iteration]
            j = 0
            for j in range(len(bytes_per_value)):
                if j == 0:
                    byte_val = iteration_bytes[:(cum_bytes_per_val[j])]
                else:
                    byte_val = iteration_bytes[(cum_bytes_per_val[j-1]):
                                               (cum_bytes_per_val[j])]
                val = self.decode_byte(byte_val,
                                       data_bits_per_byte=data_bits_per_byte[j],
                                       signed_integer=signed_integer[j])
                values[i, j] = val
        return values

    def decode_byte(self, data_bytes, data_bits_per_byte=7,
                    signed_integer=False):
        '''
        Exists for legacy purposes, only used in integration streaming mode.
        Otherwise use the cython version of this function.

        Inverse function of encode byte. Protocol is described in docstring
        of encode_byte().

        Takes the message data bytes as input, converts them to a a BitArray
        and removes the MSB indicating it is a data byte and puts them together
        '''
        data_bit_val = BitArray()
        # loop over bytes and only add data bits to final BitArray.
        for byte in data_bytes:
            bit_val = BitArray(bin(byte))
            data_bit = bit_val[-data_bits_per_byte:]
            data_bit_val.append(data_bit)

        # Convert BitArray to value as unsigned integer
        if signed_integer:
            value = data_bit_val.int
        else:
            value = data_bit_val.uint

        return value

    def create_message(self, cmd, data_bytes=None,
                       EOM=defHeaders.EndOfMessageHeader):
        '''
        Creates a bytearray to send as a message.
        Starts with a command, then adds the data bytes and ends with EOM.
        '''
        message = bytes()
        message += cmd

        if data_bytes is None:
            pass
        elif type(data_bytes) is bytes:
            message += data_bytes
        else:
            raise TypeError
        message += EOM
        return message

    # Read Functions

    def get_integration_log_results(self):
        '''
        read the log of the master
        Corresponds to mode 2: Integration logging

        Uses fixed length for reading out the message for speedup.

        Returns integrated logs for ch0 and ch1
        '''

        log_length = self.get_log_length()
        # Information on the encoding
        bytes_per_value = 4
        data_bits_per_byte = 7

        succes = False
        t0 = time.time()
        while not succes:
            log_message = c.create_message(defHeaders.ReadLoggedResults)
            stat, log = self.serial_write(log_message)
            # print 'Got the data request stat %s' %stat
            if stat:
                # read_N +2 is for checksum and EndOfMessage
                b_log = bytearray(
                    self.serial_read(read_N=2*log_length*bytes_per_value+2))

            decoded_message = d.decode_message(
                b_log,
                data_bits_per_byte=data_bits_per_byte,
                bytes_per_value=bytes_per_value)
            ch0 = decoded_message[::2]  # take all even entries
            ch1 = decoded_message[1::2]  # take all odd entries

            if len(ch0) != 0:
                succes = True
            else:
                qt.msleep(0.01)
                sys.stdout.write('.')
            if time.time()-t0 > self.timeout:
                raise Exception('Measurement timed out')
        return ch0, ch1

    def get_input_avg_results(self):
        '''
        reads the Input Average log of the ADC input.
        Corresponds to mode 3

        @return ch0 and ch1 values
        '''
        nr_samples = self.get_nr_samples()
        # Information on the encoding
        data_bits_per_byte = 4
        bytes_per_value = 2

        succes = False
        t0 = time.time()
        # While loop is to make sure measurement finished before querying.
        while not succes:
            log_message = c.create_message(
                defHeaders.ReadInputAverageResults)
            stat, log = self.serial_write(log_message)
            if stat:
                # read_N +2 is for checksum and EndOfMessage
                b_log = bytearray(
                    self.serial_read(read_N=2*nr_samples*bytes_per_value+2))
            decoded_message = d.decode_message(
                b_log, data_bits_per_byte=data_bits_per_byte,
                bytes_per_value=bytes_per_value)
            ch0 = decoded_message[::2]
            ch1 = decoded_message[1::2]
            if len(ch0) != 0:
                succes = True
            else:
                qt.msleep(0.01)
                sys.stdout.write('.')
            if time.time()-t0 > self.timeout:
                raise Exception('Measurement timed out')
        return ch0, ch1

    def get_integrated_avg_results(self):
        '''
        read the log of the master
        Corresponds to mode 4: integrated average

        @param timeout : the timeout time in ms
        @return stat : 0 if the upload succeeded and 1 if the upload failed.
        @return mesg : the message the master returned.
        '''
        nr_samples = self.get_nr_samples()
        # Information on the encoding
        bytes_per_value = 4
        data_bits_per_byte = 7

        succes = False
        t0 = time.time()
        while not succes:
            log_message = c.create_message(
                defHeaders.ReadIntAverageResults)
            stat, log = self.serial_write(log_message)
            if stat:
                # read_N +2 is for checksum and EndOfMessage
                b_log = bytearray(
                    self.serial_read(read_N=2*nr_samples*bytes_per_value+2))
            else:
                raise ValueError('Data Request not confirmed')
            decoded_message = d.decode_message(
                b_log, data_bits_per_byte=data_bits_per_byte,
                bytes_per_value=bytes_per_value)
            ch0 = decoded_message[::2]  # take all even entries
            ch1 = decoded_message[1::2]  # take all odd entries

            if len(ch0) != 0:
                succes = True
            else:
                qt.msleep(0.01)
                sys.stdout.write('.')
            if time.time()-t0 > self.timeout:
                raise Exception('Measurement timed out')
        return ch0, ch1

    def send_stop_streaming(self):
        termination_message = c.create_message(
            defHeaders.EndOfStreamingHeader)
        stat = self.serial_write(termination_message,
                                 verify_execution=False)
        return stat

    def get_streaming_results(self, nr_samples=10000):
        succes = False
        t0 = time.time()
        termination_send = False
        message = bytearray()
        # Request the data

        log_message = c.create_message(
            defHeaders.ReadIntStreamingResults)
        stat, log = self.serial_write(log_message)

        if not stat:
            raise Exception('Requesting stream failed')
        # Taking data like crazy!
        print('Starting streaming data acquisition')
        i = 0
        while not succes:
            i += 1
            in_wait = self.visa_handle.bytes_in_buffer
            if in_wait > 0:
                message.extend(self._read_raw(in_wait))
            elif termination_send:
                if in_wait == 0:  # This is to prevent slow message check
                    if message[-1] == ord(defHeaders.EndOfMessageHeader):
                        succes = True
                        print('EOM found stopping acquisition')

            elif len(message)/10 > nr_samples:
                stat = self.send_stop_streaming()

                print('Streaming terminated, taking final data')
                termination_send = True

        t1 = time.time()
        print('Acquiring data took: %s s' % (t1-t0))

        # Has to use the slower (non cython) legacy version of the decoder
        # because of unsigned integers and different shapes of databytes
        decoded_data = self.decode_message(message,
                                           data_bits_per_byte=[7, 7, 7, 7],
                                           bytes_per_value=[4, 4, 1, 1],
                                           signed_integer=[True, True,
                                                           False, False])
        data = decoded_data.transpose()[:3, :]

        t2 = time.time()
        # print 'Decoding data took %.4f s' % (t2-t1)
        # Detect missing bytes upon decoding

        for i in range(np.shape(data)[1]):
            if not np.mod(i, 128) == data[2, i]:
                print(data[:, i])
                raise Exception('Data lost at entry %.4f' % i)
                # print  ValueError('Data lost at entry %s' %i)
        t3 = time.time()
        print('Verifying data integrity took %.4f s' % (t3-t2))

        return data

    def set_awg_lookuptable(self, awg_nr, table_nr, dac_ch, lut,
                            length=None, units='mV'):
        '''
        set the 14 bit values of a lut (V2.0)

        @param awg : the awg of the dac, (0,1,2).
        @param table_nr : the lut of the awg, (0,1,2,3,4,5,6,7).
        @param dac : the dac of the awg, 0 = Q and 1 = I channel.
        @param lut : the array of the with amplitude values,
            if units is 'mV' the range is (-1000mV, 1000mV)
            if units is 'dac' range is (-8192, 8191)
        @param length : the length in samples of the lut, (1,128)
                        can be given for test purposes, default is None


        @return stat : 0 if the upload succeeded and 1 if the upload failed.

        '''

        if units == 'mV':
            lut = lut * 8192/1000.  # dac_peak/V_peak
            # do conversion
            pass
        elif units == 'dac':
            pass
        else:
            raise ValueError('units: "%s" not understood' % units)

        # Check out of bounds
        if awg_nr < 0 or awg_nr > 2:
            raise ValueError
        if table_nr < 0 or table_nr > 7:
            raise ValueError
        if dac_ch < 0 or dac_ch > 1:
            raise ValueError

        length = len(lut)

        # Should be 128 but giving length 128 loads no pulse. - Adriaan
        if length < 1 or length > 128:
            raise ValueError('lenght "%s" not between 1 and 128' % length)
        # Makes sure the values are rounded before encoding as bytes
        lut = np.round(lut)
        cmd = defHeaders.AwgLUTHeader
        data_bytes = bytearray()
        data_bytes.extend(c.encode_byte(awg_nr, 4,
                          expected_number_of_bytes=1))
        data_bytes.extend(c.encode_byte(table_nr, 4,
                          expected_number_of_bytes=1))
        data_bytes.extend(c.encode_byte(dac_ch, 4,
                          expected_number_of_bytes=1))
        # This length is substracted by 1, because the FPGA counts from 0
        # With 1 substracted, the hardware will work properly.  -- 14-7-2015.               # With 1 substracted, the hardware will work properly.  -- 14-7-2015.
        data_bytes.extend(c.encode_byte(length-1, 7))
        data_bytes.extend(c.encode_array(lut,
                          data_bits_per_byte=7, bytes_per_value=2))
        message = c.create_message(cmd, data_bytes)

        (stat, mesg) = self.serial_write(message)
        if not stat:
            raise Exception('Failed to set AWG lookup table')
        return (stat, mesg)

    def set_awg_tape(self, awg_nr, length, tape):
        '''
        set the tape content for an awg

        @param awg : the awg of the dac, (0,1,2).
        @param length : the length in samples of the tape entries, (1,2^12-1)
        @param tape : the array of pulse numbers, (0, 7)
        @return stat : 0 if the upload succeeded and 1 if the upload failed.

        '''

        # Check out of bounds
        if awg_nr < 0 or awg_nr > 2:
            raise ValueError
        if length < 1 or length > 4095:
            raise ValueError
        if length != len(tape):
            raise ValueError
        cmd = defHeaders.AwgTapeHeader
        data_bytes = bytearray()
        data_bytes.extend(c.encode_byte(awg_nr, 4,
                          expected_number_of_bytes=1))
        data_bytes.extend(c.encode_byte(length, 7,
                          expected_number_of_bytes=2))

        data_bytes.extend(c.encode_array(tape, 4, 1))

        message = c.create_message(cmd, data_bytes)
        (stat, mesg) = self.serial_write(message)
        return (stat, mesg)

    def restart_awg_tape(self, awg_nr):
        '''
        Reset the tape pointer of specified awg to 0.

        @param awg_nr : the awg of the dac, (0,1,2).
        @return stat : True if the upload succeeded and False if the upload failed.
        '''

        cmd = defHeaders.AwgRestartTapeHeader
        data_bytes = bytearray()
        data_bytes.extend(c.encode_byte(awg_nr, 4, 1))
        message = c.create_message(cmd, data_bytes)
        (stat, mesg) = self.serial_write(message)
        if not stat:
            raise Exception('Failed to restart awg tape')
        return stat

    def enable_dac(self, awg_nr, dac_ch, enable):
        '''
        mute or enable a dac of an awg

        @param awg_nr : the awg of the dac, (0,1,2).
        @param dac_ch : the dac of the awg, 0 = Q and 1 = I channel.
        @param enable: True = enable and False = disable
        @return stat : 0 if the upload succeeded and 1 if the upload failed.
        '''
        if enable == 0:
            cmd = defHeaders.AwgDisableHeader
        else:
            cmd = defHeaders.AwgEnableHeader
        data_bytes = [c.encode_byte(awg_nr, 4, 1),
                      c.encode_byte(dac_ch, 4, 1)]
        message = c.create_message(cmd, data_bytes)
        (stat, mesg) = self.serial_write(message)
        if not stat:
            raise Exception('Failed to enable dac')
        return stat

    def set_dac_offset(self, awg_nr, dac_ch, offset):
        '''
        set the offset of 1 dac of an awg.

        @param awg : the awg of the dac, (0,1,2).
        @param dac : the dac of the awg, 0 = Q and 1 = I channel.
        @param offset : the offset in mV, range [-1000, 1000].
        @return stat : 0 if the upload succeeded and 1 if the upload failed.
        '''
        if offset > 1000 or offset < -1000:
            raise ValueError('offset out of range [-1, 1] (volts)')

        offset_dac = int(offset/1000.*2**13)
        # For 14 bit signed value, the acceptable range is -8192 to 8191.
        if offset_dac == 2**13:
            offset_dac = int(2**13-1)

        cmd = defHeaders.AwgOffsetHeader
        data_bytes = bytearray()
        data_bytes.extend(c.encode_byte(awg_nr, 4, 1))
        data_bytes.extend(c.encode_byte(dac_ch, 4, 1))
        data_bytes.extend(c.encode_byte(offset_dac,
                                        data_bits_per_byte=7,
                                        expected_number_of_bytes=2))
        message = c.create_message(cmd, data_bytes)
        (stat, mesg) = self.serial_write(message)
        if not stat:
            raise Exception('Failed to set dac_offset')
        else:
            self.dac_offsets[awg_nr, dac_ch] = offset
        return stat

    def get_dac_offset(self, awg_nr, dac_ch):
        '''
        Returns the dac offset of "awg_nr" for "dac_ch" in mV
        '''
        return self.dac_offsets[awg_nr, dac_ch]

    def set_ecc_truthtable():
        '''
        Note note implemented as Xiang indicated this will never be used.
        '''
        pass

    def set_averaging_parameters(self, nr_samples, avg_size):
        '''
        set the parameters for Input and Integrated Average functions.

        @param nr_samples : Number of samples for the input signal.
                            Range: [1 - 2000]
        @param avg_size    : For each sample, 2 ^ avg_size values will be taken
                           into the averaging calculation.
                        Range: [0 - 32].
        '''
        if nr_samples < 1 or nr_samples > 2000:  # 2**11: # max is 2000
            raise ValueError
        if avg_size < 0 or avg_size > 17:  # 32: # max is 17
            raise ValueError

        cmd = defHeaders.UpdateAverageSettings
        data_bytes = bytearray()
        data_bytes.extend(c.encode_byte(nr_samples, 7,
                          expected_number_of_bytes=2))
        data_bytes.extend(c.encode_byte(avg_size, 7,
                          expected_number_of_bytes=1))
        message = c.create_message(cmd, data_bytes)
        (stat, mesg) = self.serial_write(message)
        if stat:
            self.nr_samples = nr_samples
            self.avg_size = avg_size
            self.nr_averages = 2**avg_size
        else:
            raise Exception('Failed to set averaging parameters')
        # To ensure qtlab gui updates
        self.get_nr_averages()
        self.get_avg_size()
        self.get_nr_samples()

        return (stat, mesg)

    def _do_set_nr_samples(self, nr_samples):
        if self.get_avg_size() is not None:
            self.set_averaging_parameters(nr_samples, self.get_avg_size())
        else:
            self.set_averaging_parameters(nr_samples, 0)

    def _do_get_nr_samples(self):
        return self.nr_samples

    def get_avg_size(self):
        '''
        nr_averages = 2 ^ avg_size
        '''
        return self.avg_size

    def _do_get_nr_averages(self):
        return self.nr_averages

    def _do_set_nr_averages(self, nr_averages):

        avg_size = np.log2(nr_averages)
        Rounded_avg_size = int(avg_size)
        if avg_size % 1 != 0.0:
            logging.warning(
                'nr_averages must be power of 2, converting rounding down to 2**%d' \
                    % Rounded_avg_size)

        if self.get_nr_samples() is not None:
            self.set_averaging_parameters(self.get_nr_samples(),
                                          Rounded_avg_size)
        else:
            self.set_averaging_parameters(2, Rounded_avg_size)

        self.nr_averages = 2**Rounded_avg_size

    def set_lin_trans_coeffs(self, a11, a12, a21, a22):
        '''
        Set the coefficients for the linear transformation.

        @param a11, a12, a21, a22 : Coefficients used in the following
        transformation:
        B0 = a11*A0 + a12*A1;
        B1 = a21*A0 + a22*A1;
        The range of a11, a12, a21, a22 is from -2 to 2 - (2^-12).
        The coefficients will be transformed into fix-point binary complement
        code. The length is 14, with one bit for the sign, one bit for
        integer, and 12 bits for fraction. The 14 bits will be sent to the
        USB in two bytes, each byte is of 7 valid bits.

        @return stat : 0 if the upload succeeded and 1 if the upload failed.
        '''
        for a in [a11, a12, a21, a22]:
            if a < -2 or a >= 2:
                raise ValueError('coefficents must be between -2 and 2')
        cmd = defHeaders.UpdLinTransCoeffHeader

        # used to convert to dac value
        a11_dac = int(a11*2**12)
        a12_dac = int(a12*2**12)
        a21_dac = int(a21*2**12)
        a22_dac = int(a22*2**12)
        data_bytes = bytearray()
        data_bytes.extend(c.encode_byte(a11_dac, data_bits_per_byte=7,
                          expected_number_of_bytes=2))
        data_bytes.extend(c.encode_byte(a12_dac, data_bits_per_byte=7,
                          expected_number_of_bytes=2))
        data_bytes.extend(c.encode_byte(a21_dac, data_bits_per_byte=7,
                          expected_number_of_bytes=2))
        data_bytes.extend(c.encode_byte(a22_dac, data_bits_per_byte=7,
                          expected_number_of_bytes=2))

        message = c.create_message(cmd, data_bytes)
        (stat, mesg) = self.serial_write(message)
        if not stat:
            raise Exception('Failed to set lin_trans_coeffs')
        self.lin_trans_coeffs = np.array([a11, a12, a21, a22])
        return (stat, mesg)

    def get_lin_trans_coeffs(self):
        return self.lin_trans_coeffs

    def _do_set_log_length(self, length):
        '''
        set the number of measurements of the log in test mode.

        @param length : the number of measurements range (1, 8000)
        @return stat : 0 if the upload succeeded and 1 if the upload failed.
        '''
        if length < 1 or length > 8000:
            raise ValueError
        cmd = defHeaders.UpdateLoggerMaxCounterHeader
        data_bytes = c.encode_byte(length-1, 7,
                                      expected_number_of_bytes=2)
        message = c.create_message(cmd, data_bytes)
        (stat, mesg) = self.serial_write(message)
        if stat:
            self.log_length = length
        else:
            raise Exception('Failed to set log_length')
        return (stat, message)

    def _do_get_log_length(self):
        return self.log_length

    def _do_set_acquisition_mode(self, acquisition_mode):
        '''
        @param acquisition_mode : acquisition_mode of the fpga,
            0 = idle,
            1 = integration logging mode,
            2 = feedback mode,
            3 = input_average.
            4 = integration_averaging
            5 = integration_streaming
            6 = touch 'n go
        @return stat : True if the upload succeeded and False if the upload failed
        '''
        # Here the actual acquisition_mode is set
        cmd = defHeaders.UpdateModeHeader
        data_bytes = c.encode_byte(acquisition_mode, 7)
        message = c.create_message(cmd, data_bytes)
        (stat, mesg) = self.serial_write(message)
        if stat:
            self._acquisition_mode = acquisition_mode
        else:
            raise Exception('Failed to set acquisition_mode')
        return (stat, message)

    def _do_get_acquisition_mode(self):
        return self._acquisition_mode

    def _do_set_run_mode(self, run_mode):
        '''
        @param mode : mode of the fpga,
            0 = stop,
            1 = run,
        @return stat :True if the upload succeeded and False if the upload failed.
        '''
        if run_mode < 0 or run_mode > 1:
            raise ValueError

        # Here the actual mode is set
        cmd = defHeaders.UpdateRunModeHeader
        data_bytes = c.encode_byte(run_mode, 7)
        message = c.create_message(cmd, data_bytes)
        (stat, mesg) = self.serial_write(message)
        if stat:
            self.run_mode = run_mode
        else:
            raise Exception('Failed to set run_mode')
        return (stat, message)

    def _do_get_run_mode(self):
        return self.run_mode

    def set_awg_mode(self, awg_nr, awg_mode):
        '''
        @param awg_nr : the awg to be set mode, (0,1,2).
        @param noCodewordTrig :
            0:Codeword-trigger mode: trigger + codeword specifying lookuptable.
            1:No-codeword mode: trigger will play lookuptable 0.
            2:Tape mode: trigger will play the lut specified in the tape.

        @return stat : 0 if the upload succeeded and 1 if the upload failed.
        '''

        if awg_nr > 2 or awg_nr < 0:
            raise ValueError('awg_nr should be 0, 1 or 2')
        if awg_mode > 2 or awg_mode < 0:
            raise ValueError('awg_mode should be 0, 1 or 2')
        # Convert to No due to implementation in the box
        cmd = defHeaders.AwgModeHeader
        data_bytes = bytearray()
        data_bytes.extend(c.encode_byte(awg_nr, 7))
        data_bytes.extend(c.encode_byte(awg_mode, 7))
        message = c.create_message(cmd, data_bytes)

        (stat, mesg) = self.serial_write(message)
        if stat:
            self.awg_mode[awg_nr] = awg_mode
        return (stat, message)

    def get_awg_mode(self, awg_nr):
        return self.awg_mode[awg_nr]

    def _do_set_adc_offset(self, adc_offset):
        '''
        set the offset in  ADC levels to be subtracted from the ADCs of
        the master AWG.
        NOTE: THE SAME OFFSET IS SUBTRACTED FROM BOTH ADCs.

        @param s : the serial connection for the operation.
        @param adc_offset : a value between -127 and 128 that gets subtracted
              from the raw adc input before substraction
        @return stat : 0 if the upload succeeded and 1 if the upload failed.
        '''

        cmd = defHeaders.UpdVoffsetHeader
        data_bytes = c.encode_byte(adc_offset, data_bits_per_byte=4,
                                   signed_integer_length=8)
        message = c.create_message(cmd, data_bytes)
        (stat, mesg) = self.serial_write(message)
        if stat:
            self.adc_offset = adc_offset
        else:
            raise Exception('Failed to set adc_offset')
        return (stat, message)

    def _do_get_adc_offset(self):
        return self.adc_offset

    def _do_set_signal_delay(self, delay):
        '''
        set the samples the signal can be delayed

        @param delay : number of samples to be omitted while waiting.
        Range: (0, 255)
        @return stat : True if the upload succeeded and False
        if the upload failed.
        '''
        if delay < 0 or delay > 255:
            raise ValueError
        cmd = defHeaders.UpdIntegrationDelayHeader
        data_bytes = c.encode_byte(delay, 4, expected_number_of_bytes=2)
        message = c.create_message(cmd, data_bytes)
        (stat, mesg) = self.serial_write(message)
        if stat:
            self.signal_delay = delay
        else:
            raise Exception('Failed to set signal_delay')
        return (stat, message)

    def _do_get_signal_delay(self):
        return self.signal_delay

    def _do_set_integration_length(self, length):
        '''
        set length of the signal for integration.

        @param length : number of samples of the integration delay, (1,512)

        Warning! this is the excpetion that is one nibble (4bit/bte) and one
        5 bit/byte). Range is limited until VHDL code is updated.
        '''
        if length < 0 or length > 512:
            raise ValueError
        cmd = defHeaders.UpdIntegrationLengthHeader
        data_bytes = c.encode_byte(length, 7, expected_number_of_bytes=2)
        message = c.create_message(cmd, data_bytes)
        (stat, mesg) = self.serial_write(message)
        if stat:
            self.integration_length = length
        else:
            raise Exception('Failed to set integration length')
        return stat

    def _do_get_integration_length(self):
        return self.integration_length

    def _do_set_signal_threshold_line0(self, threshold):
        succes = self._set_signal_threshold(0, threshold)
        if succes:
            self.threshold0 = threshold
        else:
            raise Exception('Failed to set signed_threshold 0')
        return succes

    def _do_set_signal_threshold_line1(self, threshold):
        succes = self._set_signal_threshold(1, threshold)
        if succes:
            self.threshold1 = threshold
        else:
            raise Exception('Failed to set signed_threshold 1')
        return succes

    def _do_get_signal_threshold_line0(self):
        return self.threshold0

    def _do_get_signal_threshold_line1(self):
        return self.threshold1

    def _set_signal_threshold(self, line, threshold):
        '''
        Private version of command
        set the thresholds for the ancilla statusses of the integration
        results

        @param line: 0: threshold0 is going to be set.
                     1: threshold1 is going to be set.
        @param threshold : a threshold for the integration result. the range
              of this value is between -2^27 and +2^27-1
        @return stat : 0 if the upload succeeded and 1 if the upload failed.
        '''
        # the -sign is workaround for threshold problem, see note
        # Active resonator reset/depletion optimization/100 ns pulses, opt....
        threshold = threshold
        signed_threshold = threshold
        if (threshold < 0):
            signed_threshold = threshold + 2 ** 28
        if line == 0:
            cmd = defHeaders.UpdThresholdZeroHeader
        elif line == 1:
            cmd = defHeaders.UpdThresholdOneHeader
        data_bytes = c.encode_byte(signed_threshold,
                                   data_bits_per_byte=7,
                                   expected_number_of_bytes=4)
        message = c.create_message(cmd, data_bytes)
        (stat, mesg) = self.serial_write(message)
        return (stat, message)

    def set_integration_weights(self, line, weights):
        '''
        set the weights of the integregration

        @param line: 0: weight0 is going to be set.
                     1: weight1 is going to be set.
        @param weights : the weights, an array of 512 elements with a range
              between -128 and 127, (signed byte)
        @return stat : 0 if the upload succeeded and 1 if the upload failed.
        '''

        # 2 bytes per array val + cmd_header and EOM
        if max(weights) > 127:
            raise ValueError('Weights must be between -128 and 127')
        if min(weights) < -128:
            raise ValueError('Weights must be between -128 and 127')
        if len(weights) != 512:
            raise ValueError('Length of array must be 512 elements')

        if line == 0:
            cmd = defHeaders.UpdWeightsZeroHeader
        elif line == 1:
            cmd = defHeaders.UpdWeightsOneHeader
        data_bytes = []
        for i, weight in enumerate(weights):
            data_bytes.append(c.encode_byte(weight,
                                               data_bits_per_byte=4,
                                               signed_integer_length=8,
                                               expected_number_of_bytes=2))
        message = c.create_message(cmd, data_bytes)
        (stat, mesg) = self.serial_write(message)

        if not stat:
            raise Exception('Failed to set integration weights')
        self.integration_weights[line] = weights
        return (stat, mesg)

    def get_integration_weigths(self, line):
        return self.integration_weights[line]

    ########################
    #  Low Level functions #
    ########################
    # These functions are located in AuxiliaryFctn in the matlab driver

    def open_serial_port(self, nameCOM):
        '''
        Establishes serial connection with instrument.
        Requires comport as argument e.g. 'Com3'
        rest of the settings is given the arguments required for the
        QuTech_ControlBox.
        '''

        ser = serial.Serial(port=nameCOM, baudrate=7372800, timeout=2,
                            bytesize=8, parity=serial.PARITY_NONE,
                            stopbits=1, xonxoff=0, rtscts=0)
        # ser_io is used for "fast" reading by specifying a custom newline char
        newline = ('\n')
        self.ser_io = io.TextIOWrapper(io.BufferedRWPair(ser, ser, 1),
                                       newline=newline,
                                       line_buffering=True)
        # self.ser_io.write("ID\r")
        # self_id = self.ser_io.readline()

        return ser

    def calculate_checksum(self, input_command):
        '''
        Calculates checksum by taking the XOR of all elements
        in a hex string.
        '''
        checksum = 0
        for byte in bytearray(input_command):
            checksum = checksum ^ byte
        checksum = checksum | 128
        checksum = chr(checksum) # Convert int to hexs and set MSbit

        return checksum

    def _read_raw(self, size):
        '''
        Intended to replace visa_handle.read_raw
        '''
        with(self.visa_handle.ignore_warning(visa.constants.VI_SUCCESS_MAX_CNT)):
            mes = self.visa_handle.visalib.read(
                self.visa_handle.session, size)
        return mes[0]

    def serial_read(self, timeout=5, read_all=False, read_N=0):
        '''
        Reads on the serial port until EndOfMessageHeader is received.

        If read all == False and read_N = 0 it reads 1 entry.
        if read_all ==True it reads up to the EndOfMessageHeader.
        if read_N != 0 it reads a fixed number of bytes.

        Setting read_N speeds up the readout significantly.

        returns the message as a string (including the EndOfMessageHeader).
        '''
        t_start = time.time()
        end_of_message_received = False
        message = bytes()
        while not end_of_message_received:
            if read_all:
                m = self._read_raw(self.visa_handle.bytes_in_buffer)
                message += m
            elif read_N != 0:
                if self.visa_handle.bytes_in_buffer == 2:
                    # To catch all the "empty" messages (checksum +EOM)
                    m = self._read_raw(2)
                else:
                    m = self._read_raw(read_N)
                message += m
            elif self.visa_handle.bytes_in_buffer != 0:
                message += self._read_raw(1)
            if len(message) != 0:
                if message[-1:] == defHeaders.EndOfMessageHeader:
                    end_of_message_received = True

            if not end_of_message_received:
                time.sleep(.01)
                if (time.time() - t_start) > timeout:
                    raise Exception('Read timed out without EndOfMessage')
        if message[0] == defHeaders.IllegalCommandHeader:
            raise ValueError('Command not recognized')
        if message[0] == defHeaders.DataOverflowHeader:
            raise ValueError('Data overflow: too many parameters')
        if message[0] == defHeaders.IllegalDataHeader:
            raise ValueError('Illegal data sent')
        return message

    def serial_write(self, command, verify_execution=True):
        '''
        Core write function used for communicating with the Box.

        Accepts either a bytes as input
        e.g. command = b'\x5A\x00\x7F'

        Writes data to the serial port and verifies the checksum to see if the
        message was received correctly.

        Returns: succes, message
        Succes is true if the checksum matches.
        '''
        if type(command) != bytes:
            raise TypeError('command must be type bytes')
        checksum = self.calculate_checksum(command)

        in_wait = self.visa_handle.bytes_in_buffer
        if in_wait > 0:  # Clear any leftover messages in the buffer
            self.visa_handle.clear()
            print("Extra flush! Flushed %s bytes" % in_wait)
        self.visa_handle.write_raw(command)
        # Done writing , verify message executed
        if verify_execution:
            message = self.serial_read()

        #     if message[0] == checksum:
            succes = True
        #     else:
        #         raise Exception('Checksum Error, Command not executed')
            return succes, message
        else:
            return True

    def restart_awg_tape(self, awg_nr):
        '''
        Reset the tape pointer of specified awg to 0.

        @param awg_nr : the awg of the dac, (0,1,2).
        @return stat : 0 if the upload succeeded and 1 if the upload failed.
        '''
        cmd = defHeaders.AwgRestartTapeHeader
        data_bytes = bytearray()
        data_bytes.extend(c.encode_byte(awg_nr, 4, 1))
        message = c.create_message(cmd, data_bytes)
        (stat, mesg) = self.serial_write(message)
        if not stat:
            raise Exception('Failed to restart awg tape')
        return stat

    def _do_set_tng_heartbeat_interval(self, tng_heartbeat_interval):
        '''
        HeartbeatInterval  : Sets the time between two subsequent heartbeats
                             in ns as a multiple of 100 ns.
                             Range 100 ns to 1638400 ns (~1640us)
        '''
        if tng_heartbeat_interval < 100 or tng_heartbeat_interval > 1638400:
            raise ValueError
        if np.mod(tng_heartbeat_interval, 100) != 0.0:
            raise ValueError('%s is not divisble by 100 ns' %
                             tng_heartbeat_interval)
        if self.tng_burst_heartbeat_interval*self.tng_burst_heartbeat_n > tng_heartbeat_interval:
            raise ValueError('%s x %s does not fit in the heartbeatinterval %s'%(
                             self.tng_burst_heartbeat_interval,
                             self.tng_burst_heartbeat_n,
                             tng_heartbeat_interval))

        self.tng_heartbeat_interval = tng_heartbeat_interval
        self._set_touch_n_go_parameters()

    def _do_get_tng_heartbeat_interval(self):
        return self.tng_heartbeat_interval

    def _do_set_tng_burst_heartbeat_interval(self, tng_burst_heartbeat_interval):
        '''
        subHeartbeatInterval  : Sets the time between two subsequent sub heartbeats
                             in ns as a multiple of 100 ns.
                             Range 100 ns to 102400 ns. the n_subheart_beats x
                             interval_sub_heartbeats must fit in one HeartbeatInterval

        '''
        if tng_burst_heartbeat_interval < 100 or tng_burst_heartbeat_interval > 102400:
            raise ValueError('Burst hb set to "%s" must be 100ns > Burst hb < 102400ns' %
                             tng_burst_heartbeat_interval)
        if np.mod(tng_burst_heartbeat_interval, 100) != 0.0:
            raise ValueError('%s is not divisble by 100 ns' %
                             tng_burst_heartbeat_interval)
        if tng_burst_heartbeat_interval*self.tng_burst_heartbeat_n > self.tng_heartbeat_interval:
            #self.tng_burst_heartbeat_interval = self.tng_heartbeat_interval
            raise ValueError('%s x %s does not fit in the heartbeatinterval %s.'%(
                             tng_burst_heartbeat_interval,
                             self.tng_burst_heartbeat_n,
                             self.tng_heartbeat_interval))
        self.tng_burst_heartbeat_interval = tng_burst_heartbeat_interval
        self._set_touch_n_go_parameters()

    def _do_get_tng_burst_heartbeat_interval(self):
        return self.tng_burst_heartbeat_interval

    def _do_set_tng_burst_heartbeat_n(self, tng_burst_heartbeat_n):
        '''
        subHeartbeat_n  : Sets the amount of subheartbeats within a heartbeat.
                          Default is 1 meaning there is just one cycle per
                          heartbeat. the n_subheart_beats x
                          interval_sub_heartbeats must fit in one
                          HeartbeatInterval

        From the docs:  (7-bit unsigned) Sets the number of heartbeats that are
                        sent when a new burst starts (triggered by the main
                        heartbeat). Range 0 to 127 results in 1 to 1024
                        heartbeats per burst.

        '''
        if tng_burst_heartbeat_n < 1:
            raise ValueError('value smaller than 1 not possible')
        if tng_burst_heartbeat_n > 1024:
            raise ValueError('value above 1024 not possible')
        if (self.tng_burst_heartbeat_interval*tng_burst_heartbeat_n >
                self.tng_heartbeat_interval):
            raise ValueError('%s x %s does not fit in the heartbeatinterval %s'
                             % (self.tng_burst_heartbeat_interval,
                                tng_burst_heartbeat_n,
                                self.tng_heartbeat_interval))
        if tng_burst_heartbeat_n == 0:
            tng_burst_heartbeat_n = 1

        print('tng_burst_heartbeat_n', tng_burst_heartbeat_n)
        self.tng_burst_heartbeat_n = tng_burst_heartbeat_n
        self._set_touch_n_go_parameters()

    def _do_get_tng_burst_heartbeat_n(self):
        return self.tng_burst_heartbeat_n


    def _do_set_tng_readout_delay(self, tng_readout_delay):
        '''
        ReadoutDelay       : Sets the delay between the heartbeat and the
                             readout pulse during calibration mode.
                             Range 100 ns to 6300 ns.
        '''
        if tng_readout_delay < 0 or tng_readout_delay > 6300:
            raise ValueError("%s, out of range 100 to 6300 ns"
                             % tng_readout_delay)
        if np.mod(tng_readout_delay, 100) != 0.0:
            raise ValueError("%s, not multiple of 100 ns" % tng_readout_delay)

        self.tng_readout_delay = tng_readout_delay
        self._set_touch_n_go_parameters()

    def _do_get_tng_readout_delay(self):
        return self.tng_readout_delay

    def _do_set_tng_second_pre_rotation_delay(self,
                                              tng_second_pre_rotation_delay):
        '''
        2nd Prerotation delay : Sets the delay between the heartbeat and the
                               second pre-rotation pulse during calibration
                               mode as a multiple of 100ns.
                               Range 100 ns to 6300 ns
        '''
        if (tng_second_pre_rotation_delay < 0 or
                tng_second_pre_rotation_delay > 6300):
            raise ValueError("%s, out of range 100 to 6300 ns"
                             % tng_second_pre_rotation_delay)
        if np.mod(tng_second_pre_rotation_delay, 100) != 0.0:
            raise ValueError("%s, not multiple of 100 ns" %
                             tng_second_pre_rotation_delay)

        self.tng_second_pre_rotation_delay = tng_second_pre_rotation_delay
        self._set_touch_n_go_parameters()

    def _do_get_tng_second_pre_rotation_delay(self):
        return self.tng_second_pre_rotation_delay

    def _do_set_tng_calibration_mode(self, tng_calibration_mode):
        '''
        CalibrationMode   : Activates calibration mode when set to 1. In
                             calibration mode an extra delay (ReadOutDelay) is
                             added between the heartbeat pulse and the readout
                             pulse. At the same time a AWG is triggered at the
                             heartbeat. This AWG can play a rotation pulse.
                              0 = normal mode
                              1 = calibration mode
        '''
        if tng_calibration_mode < 0 or tng_calibration_mode > 1:
            raise ValueError
        self.tng_calibration_mode = tng_calibration_mode
        self._set_touch_n_go_parameters()


    def _do_get_tng_calibration_mode(self):
        return self.tng_calibration_mode

    def _do_set_tng_awg_mask(self, tng_awg_mask):
        '''
        Awgmask             : Selects AWG's to play prerotation pulse.
                             Input should be a three bit integer.
                             F.I. "101", selects awg2 and awg0
                             Feedback pulses are also played from these AWG's.
                             Readoutpulses are played from the inverted mask.
                             So, for "101", awg1 is used for readout pulses.
        '''
        if int(str(tng_awg_mask), 2) < 0 or int(str(tng_awg_mask), 2) > 7:
            raise ValueError("%s is not a three bit integer")
        self.tng_awg_mask = tng_awg_mask
        self._set_touch_n_go_parameters()


    def _do_get_tng_awg_mask(self):
        return self.tng_awg_mask

    def _do_set_tng_readout_pulse_length(self, tng_readout_pulse_length):
        '''
        ReadoutPulseLength : Sets the length of the readout pulse send to
                             the Rohde&Schwartz in multiples of 100ns.
                             Range 100 to 6300 ns.
                             In CLEAR experiment the falling edge is used
                             to trigger awg5014 so the length sets the delay
                             at which awg5014 is triggered.
        '''
        if tng_readout_pulse_length < 100 or tng_readout_pulse_length > 6300:
            raise ValueError("%s, out of range 100 to 6300 ns"
                             % tng_readout_pulse_length)
        if np.mod(tng_readout_pulse_length, 100) != 0.0:
            raise ValueError("%s, not multiple of 100 ns" %
                             tng_readout_pulse_length)

        self.tng_readout_pulse_length = tng_readout_pulse_length
        self._set_touch_n_go_parameters()


    def _do_get_tng_readout_pulse_length(self):
        return self.tng_readout_pulse_length

    def _do_set_tng_readout_wave_interval(self, tng_readout_wave_interval):
        '''
        ReadoutWaveInterval: Sets the interval of the trigger
                             that triggers the AWG used to create the Readout
                             wave (IQ). This value should be equal to the
                             Length of the pulses in the Awg lookuptable.
                             Length should be between 10 and 640 ns with steps
                             of 5 ns.
        '''
        if tng_readout_wave_interval < 10 or tng_readout_wave_interval > 640:
            raise ValueError("%s, out of range 10 to 640 ns"
                             %tng_readout_wave_interval)
        if np.mod(tng_readout_wave_interval, 5) != 0.0:
            raise ValueError("%s, not multiple of 5 ns" %tng_readout_wave_interval)

        self.tng_readout_wave_interval = tng_readout_wave_interval
        self._set_touch_n_go_parameters()


    def _do_get_tng_readout_wave_interval(self):
        return self.tng_readout_wave_interval

    def _do_set_tng_output_trigger_delay(self, tng_output_trigger_delay):
        '''
        OutputTriggerDelay : Sets the delay between the moment the Qbit state
                             is known and the start of the TriggerOut.
                             Range 0 to 6300 ns with 100 ns steps.
        '''
        if tng_output_trigger_delay < 0 or tng_output_trigger_delay > 6300:
            raise ValueError("%s, out of range 0 to 6300 ns"
                             %tng_output_trigger_delay)
        if np.mod(tng_output_trigger_delay, 100) != 0.0:
            raise ValueError("%s, not multiple of 100 ns" %tng_output_trigger_delay)

        self.tng_output_trigger_delay = tng_output_trigger_delay
        self._set_touch_n_go_parameters()


    def _do_get_tng_output_trigger_delay(self):
        return self.tng_output_trigger_delay

    def _do_set_tng_trigger_state(self, tng_trigger_state):
        '''
        TriggerState       : Defines the trigger case:
                             0 = trigger if measured value < Threshold set
                             by signal_threshold_line0
                             1 = trigger if measured value > Threshold set
                             by signal_threshold_line0
        '''
        if tng_trigger_state < 0 or tng_trigger_state > 1:
            raise ValueError
        self.tng_trigger_state = tng_trigger_state
        self._set_touch_n_go_parameters()


    def _do_get_tng_trigger_state(self):
        return self.tng_trigger_state

    def _do_set_tng_feedback_mode(self, tng_feedback_mode):
        '''
        FeedbackMode       : Defines if feedback trigger is on or off for both
                            resonator and qubit.
                            0: no conditional qubit,
                                no conditional resonator
                                actions
                            1: no conditional qubit,
                                no conditional resonator
                            2: no conditional qubit,
                                with conditional resonator
                            3: with conditional qubit,
                               with conditional resonator
        '''
        if tng_feedback_mode < 0 or tng_feedback_mode > 3:
            raise ValueError
        self.tng_feedback_mode = tng_feedback_mode
        self._set_touch_n_go_parameters()


    def _do_get_tng_feedback_mode(self):
        return self.tng_feedback_mode

    def _do_set_tng_feedback_code(self, tng_feedback_code):
        '''
        FeedbackCode       : code setting the waveform Lookuptable to be
                             played for feedback triggers. LUT entries
                             0 to 7 are accepted.
        '''
        if tng_feedback_code < 0 or tng_feedback_code > 7:
            raise ValueError
        self.tng_feedback_code = tng_feedback_code
        self._set_touch_n_go_parameters()


    def _do_get_tng_feedback_code(self):
        return self.tng_feedback_code

    def _do_set_tng_logging_mode(self, tng_logging_mode):
        '''
        logging_mode       : value setting the logging mode.
                             0: no logging
                             1: integration average logging
                             2: integration logging without averaging,
                                 i.e. normal logging.
                             3: input average logging
        '''
        if tng_logging_mode < 0 or tng_logging_mode > 3:
            raise ValueError
        self.tng_logging_mode = tng_logging_mode
        self._set_touch_n_go_parameters()


    def _do_get_tng_logging_mode(self):
        return self.tng_logging_mode

    def _set_touch_n_go_parameters(self):
        '''
        Private function used to upload touch n go settings.
        Used because it is a single function CBox.
        '''
        heartbeat_interval = self.tng_heartbeat_interval/100-1
        burst_heartbeat_interval = self.tng_burst_heartbeat_interval/100-1
        burst_heartbeat_n = self.tng_burst_heartbeat_n-1
        readout_delay = self.tng_readout_delay/100
        calibration_mode = self.tng_calibration_mode
        awg_mask = int(str(self.tng_awg_mask), 2)
        readout_pulse_length = self.tng_readout_pulse_length/100
        second_pre_rot_delay = self.tng_second_pre_rotation_delay/100
        readout_wave_interval = self.tng_readout_wave_interval/5
        output_trigger_delay = self.tng_output_trigger_delay/100
        trigger_state = self.tng_trigger_state
        feedback_mode = self.tng_feedback_mode
        feedback_code = self.tng_feedback_code
        logging_mode = self.tng_logging_mode

        if heartbeat_interval < 0 or heartbeat_interval > 16383:
            raise ValueError
        if burst_heartbeat_interval < 0 or burst_heartbeat_interval > 127:
            raise ValueError
        if burst_heartbeat_n < 0 or burst_heartbeat_n > 1023:
            raise ValueError
        if readout_delay < 0 or readout_delay > 63:
            raise ValueError
        if second_pre_rot_delay < 0 or second_pre_rot_delay > 63:
            raise ValueError
        if calibration_mode < 0 or calibration_mode > 1:
            raise ValueError
        if awg_mask < 0 or awg_mask > 7:
            raise ValueError
        if readout_pulse_length < 1 or readout_pulse_length > 63:
            raise ValueError
        if readout_wave_interval < 1 or readout_wave_interval > 128:
            raise ValueError
        if output_trigger_delay < 0 or output_trigger_delay > 63:
            raise ValueError
        if trigger_state < 0 or trigger_state > 1:
            raise ValueError
        if feedback_mode < 0 or feedback_mode > 3:
            raise ValueError
        if feedback_code < 0 or feedback_code > 7:
            raise ValueError
        if logging_mode < 0 or logging_mode > 3:
            raise ValueError

        readout_wave_interval = readout_wave_interval-1  # compensating for
        # definition in CBox
        cmd = defHeaders.UpdateSequencerParametersHeader
        data_bytes = bytearray()
        data_bytes.extend(c.encode_byte(heartbeat_interval, 7,
                          expected_number_of_bytes=2))
        data_bytes.extend(c.encode_byte(burst_heartbeat_interval, 7, 1))
        data_bytes.extend(c.encode_byte(burst_heartbeat_n, 7,
                          expected_number_of_bytes=2))
        data_bytes.extend(c.encode_byte(readout_delay, 7, 1))
        # Comment back in for v 2.12 +
        data_bytes.extend(c.encode_byte(second_pre_rot_delay, 7, 1))
        data_bytes.extend(c.encode_byte(calibration_mode, 7, 1))
        data_bytes.extend(c.encode_byte(awg_mask, 7, 1))
        data_bytes.extend(c.encode_byte(readout_pulse_length, 7, 1))
        data_bytes.extend(c.encode_byte(readout_wave_interval, 7, 1))
        data_bytes.extend(c.encode_byte(output_trigger_delay, 7, 1))
        data_bytes.extend(c.encode_byte(trigger_state, 7, 1))
        data_bytes.extend(c.encode_byte(feedback_mode, 7, 1))
        data_bytes.extend(c.encode_byte(feedback_code, 7, 1))
        data_bytes.extend(c.encode_byte(logging_mode, 7, 1))

        message = c.create_message(cmd, data_bytes)
        (stat, mesg) = self.serial_write(message)

        return stat