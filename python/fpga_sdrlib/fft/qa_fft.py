# Copyright (c) 2012 Ben Reynwar
# Released under MIT License (see LICENSE.txt)

import os
import random
import unittest
import logging
import shutil

from fpga_sdrlib.message import msg_utils
from fpga_sdrlib.conversions import f_to_int
from fpga_sdrlib.generate import logceil
from fpga_sdrlib import config, b100, buildutils
from fpga_sdrlib.testbench import TestBenchB100, TestBenchIcarusInner, TestBenchIcarusOuter

logger = logging.getLogger(__name__)

def prune_zeros(xs):
    start_index = None
    stop_index = None
    for i, x in enumerate(xs):
        if x != 0:
            if start_index is None:
                start_index = i
            stop_index = i
    if start_index is None:
        return []
    else:
        return xs[start_index:stop_index+1]

class TestDIT(unittest.TestCase):

    def test_one(self):
        """
        Test the dit module.
        """
        width = config.default_width
        sendnth = config.default_sendnth
        # Changing N will require resynthesis.
        N = 8
        # Arguments used for producing verilog from templates.
        extraargs = {}
        # Amount of data to send.
        n_data = 10
        # Define the input
        in_samples = [random.random()*2-1 + random.random()*2j-1j for i in range(n_data)]
        steps_rqd = len(in_samples)*sendnth + 100
        # Define meta data
        mwidth = 1
        in_ms = [random.randint(0, pow(2,mwidth)-1) for d in in_samples]
        expected = in_samples
        steps_rqd = n_data * sendnth * 2 + 1000
        filter_id = 123
        # Create, setup and simulate the test bench.
        defines = config.updated_defines(
            {'WIDTH': width,
             'FFT_LEN': N
             })
        executable_inner = buildutils.generate_icarus_executable(
            'fft', 'dit_inner', '-{0}'.format(N), defines=defines,
            extraargs=extraargs)
        executable_outer = buildutils.generate_icarus_executable(
            'fft', 'dit', '-{0}'.format(N), defines=defines,
            extraargs=extraargs)
        #fpgaimage = buildutils.generate_B100_image(
        #    'flter', 'filter', '-{0}'.format(N), defines=defines,
        #    extraargs=extraargs)
        tb_icarus_inner = TestBenchIcarusInner(executable_inner, in_samples, in_ms)
        tb_icarus_outer = TestBenchIcarusOuter(executable_outer, in_samples)
        #tb_b100 = TestBenchB100(fpgaimage, in_samples)
        for tb, steps in (
                (tb_icarus_inner, steps_rqd),
                (tb_icarus_outer, steps_rqd),
        #        (tb_b100, 100000), 
                ):
            tb.run(steps)
            # Confirm that our data is correct.
            self.assertEqual(len(tb.out_samples), len(expected))
            for r, e in zip(tb.out_samples, expected):
                self.assertAlmostEqual(e, r, 3)

class TestStage(unittest.TestCase):

    def test_one(self):
        """
        Test the dit module.
        """
        width = config.default_width
        sendnth = config.default_sendnth
        # Changing N will require resynthesis.
        N = 8
        # Arguments used for producing verilog from templates.
        extraargs = {}
        # Amount of data to send.
        n_data = 2*N
        # Define the input
        in_samples = [random.random()*2-1 + random.random()*2j-1j for i in range(n_data)]
        steps_rqd = len(in_samples)*sendnth + 100
        # Define meta data
        mwidth = 1
        in_ms = [random.randint(0, pow(2,mwidth)-1) for d in in_samples]
        expected = in_samples
        steps_rqd = n_data * sendnth * 2 + 1000
        # Create, setup and simulate the test bench.
        defines = config.updated_defines(
            {'WIDTH': width,
             'N': N
             })
        executable_inner = buildutils.generate_icarus_executable(
            'fft', 'stage_inner', '-{0}'.format(N), defines=defines,
            extraargs=extraargs)
        executable_outer = buildutils.generate_icarus_executable(
            'fft', 'stage', '-{0}'.format(N), defines=defines,
            extraargs=extraargs)
        fpgaimage = buildutils.generate_B100_image(
            'fft', 'stage', '-{0}'.format(N), defines=defines,
            extraargs=extraargs)
        tb_icarus_inner = TestBenchIcarusInner(executable_inner, in_samples, in_ms)
        tb_icarus_outer = TestBenchIcarusOuter(executable_outer, in_samples)
        tb_b100 = TestBenchB100(fpgaimage, in_samples)
        for tb, steps in (
                (tb_icarus_inner, steps_rqd),
                (tb_icarus_outer, steps_rqd),
                (tb_b100, 100000), 
                ):
            tb.run(steps)
            # Confirm that our data is correct.
            self.assertEqual(len(tb.out_samples), len(expected))
            for r, e in zip(tb.out_samples, expected):
                self.assertAlmostEqual(e, r, 3)

if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStage)
    unittest.TextTestRunner(verbosity=2).run(suite)
    #unittest.main()
