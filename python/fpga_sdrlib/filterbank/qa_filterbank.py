# Copyright (c) 2012 Ben Reynwar
# Released under MIT License (see LICENSE.txt)

"""
MyHDL Test Bench to check the vericode filterbank.
"""

import os
import random
import unittest
import math
import logging

from myhdl import always

from fpga_sdrlib.conversions import c_to_int, cs_to_int, int_to_c, int_to_cs
from fpga_sdrlib.filterbank.build import generate
from fpga_sdrlib.testbench import TestBench
from fpga_sdrlib import config

def convolve(data, taps):
    out = []
    data = [0]*(len(taps)-1) + data
    for i in range(len(taps)-1, len(data)):
        v = 0
        for j in range(len(taps)):
            v += data[i-j]*taps[j]
        out.append(v)
    return out

class FilterbankTestBench(TestBench):
    """
    Helper class for doing testing.
    
    Args:
        name: A name to use for generated files.
        width: Bit width of a complex number.
        sendnth: Send an input on every `sendnth` clock cycle.
        data: A list of complex points to send.
        chantaps: The taps to use for channelizing.
    """

    extra_signal_names = ['first_filter']

    def __init__(self, name, width, mwidth, sendnth, data, ms, chantaps):
        self.width = width
        self.chantaps = chantaps
        TestBench.__init__(self, sendnth, data, ms, self.width, self.width)
        outputdir = os.path.join(config.builddir, 'filterbank')
        self.executable, inputfiles = generate(name, chantaps, width, mwidth)
        self.out_ff = []
        self.drivers.append(self.get_first_filter)

    def get_first_filter(self):
        @always(self.clk.posedge)
        def run():
            if self.out_nd:
                self.out_ff.append(int(self.first_filter))
        return run

def scale_taps(tapss):
    """
    Scales a list of lists of taps.
    """
    scaledtaps = []
    maxabsintegral = 0
    for taps in tapss:
        absintegral = sum([abs(x) for x in taps])
        if absintegral > maxabsintegral:
            maxabsintegral = absintegral
    scaledtaps = [[t/maxabsintegral for t in taps] for taps in tapss]
    return scaledtaps, maxabsintegral 
    

class TestFilterbank(unittest.TestCase):
    """
    Test the verilog filterbank.
    """

    def setUp(self):
        # Random number generator
        rg = random.Random(0)
        self.myrand = rg.random
        self.myrandint = rg.randint

    def tearDown(self):
        pass

    def test_simple(self):
        """
        Test with some simple input and taps.
        """
        taps = [
            [1, 0, 0, 0], 
            [0, 1, 0, 0], 
            [0.5, 0.5, 0, 0], 
            [0, 0, 0.5, 0.5], 
            ]
        n_filters = len(taps)
        # Amount of data to send to every filter.
        n_data = 10
        # Define the input
        data = []
        for i in range(n_data):
            data += [float(i)/n_data]*len(taps)
        width = 32
        sendnth = 2
        steps_rqd = len(data)*sendnth + 100
        # Define meta data
        mwidth = 1
        ms = [self.myrandint(0, pow(2,mwidth)-1) for d in data]
        # Expected first filter signals
        ffs = ([1] + [0]*(n_filters-1))*n_data
        # Create the test bench
        tb = FilterbankTestBench('simpletaps', width, mwidth, sendnth, data, ms, taps)
        tb.simulate(steps_rqd)
        # Compare to expected output
        input_streams = [data[i::n_filters] for i in range(n_filters)]
        received = [tb.output[i::n_filters] for i in range(n_filters)]
        expected = [convolve(d,t) for d,t in zip(input_streams, taps)]
        for rs, es in zip(received, expected):
            for r, e in zip(rs, es):
                self.assertAlmostEqual(r, e, 3)
        # Compare ms
        self.assertEqual(len(tb.out_ms), len(ms))
        for r, e in zip(tb.out_ms, ms):
            self.assertEqual(r, e)
        # Compare first_filter signals
        self.assertEqual(len(tb.out_ff), len(ffs))
        for r, e in zip(tb.out_ff, ffs):
            self.assertEqual(r, e)
        

    def atest_medium(self):
        """
        Test with some simple input and taps.
        """
        # Generate some random input.
        data =  [self.myrand()*2-1 + self.myrand()*2j-1j
                 for x in range(20)]
        # sends random ms between 0 and 7
        mwidth = 3
        ms = [self.myrandint(0, 7) for d in data]
        # get expected first_filter signal
        ffs = [1, 0] * (len(data)/2)
        # Some slightly more complicated taps.
        taps = [
            [0.4, 0.4, 0.1], 
            [0, 0.7, 0.3], 
            ]
        width = 32
        sendnth = 2
        steps_rqd = 20 * sendnth + 1000
        # Create the test bench
        tb = FilterbankTestBench('mediumtaps', width, mwidth, sendnth, data, ms, taps)
        tb.simulate(steps_rqd)
        # Compare to expected output
        n_filters = len(taps)
        received = [tb.output[i::n_filters] for i in range(n_filters)]
        input_streams = [data[i::n_filters] for i in range(n_filters)]
        expected = [convolve(d,t) for d,t in zip(input_streams, taps)]
        for rs, es in zip(received, expected):
            for r, e in zip(rs, es):
                self.assertAlmostEqual(r, e, 3)
        # Compare ms
        self.assertEqual(len(tb.out_ms), len(ms))
        for r, e in zip(tb.out_ms, ms):
            self.assertEqual(r, e)
        # Compare first_filter signals
        self.assertEqual(len(tb.out_ff), len(ffs))
        for r, e in zip(tb.out_ff, ffs):
            self.assertEqual(r, e)

    def atest_randominput(self):
        """
        Test a filterbank with random data and taps.
        """
        n_filters = 5
        n_taps = 10
        # Amount of data to send to every filter.
        n_data = 50
        # Send a new input every sendnth clock cycles.
        sendnth = 2
        # Width of a complex number
        width = 32
        # get expected first_filter signal
        ffs = ([1] + [0]*(n_filters-1)) * n_data
        # Generate some random input.
        data =  [self.myrand()*2-1 + (self.myrand()*2j-1j)
                 for x in range(n_data*n_filters)]
        mwidth = 7
        ms = [self.myrandint(0, pow(2,mwidth)-1) for d in data]
        # Generate some random taps.
        taps = [[self.myrand()*2-1 for x in range(n_taps)] for i in range(n_filters)]
        # Scale taps to prevent overflow
        chantaps, tapsscalefactor = scale_taps(taps)
        steps_rqd = n_data * n_filters * sendnth + 1000
        # Create the test bench
        tb = FilterbankTestBench('randomtaps', width, mwidth, sendnth, data, ms, chantaps)
        tb.simulate(steps_rqd)
        received = [tb.output[i::n_filters] for i in range(n_filters)]
        input_streams = [data[i::n_filters] for i in range(n_filters)]
        expected = [convolve(d,t) for d,t in zip(input_streams, chantaps)]
        for rs, es in zip(received, expected):
            for r, e in zip(rs, es):
                self.assertAlmostEqual(r, e, 3)
        # Compare ms
        self.assertEqual(len(tb.out_ms), len(ms))
        for r, e in zip(tb.out_ms, ms):
            self.assertEqual(r, e)
        # Compare first_filter signals
        self.assertEqual(len(tb.out_ff), len(ffs))
        for r, e in zip(tb.out_ff, ffs):
            self.assertEqual(r, e)

if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    unittest.main()
