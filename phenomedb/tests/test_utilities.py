#import sys, os
#if os.environ['PHENOMEDB_PATH'] not in sys.path:
#    sys.path.append( os.environ['PHENOMEDB_PATH'])
from phenomedb.config import config
import phenomedb.utilities as utils
import math
import re
class TestCache:
    """TestCache class. Tests the output of the cache task classes with test configurations
    """

    def test_float_round(self):

        test_strings = ['0.0000002345',
                        '0.0000023450002',
                        '1.265e-17',
                        '-1.265e-17',
                        '-1.265000002e-17',

                        '0.00012650000002e-13']
        for test_string in test_strings:
            regex = r'[1-9]+(0|9)(0|9)(0|9)(0|9)[1-9]'
            final_string = float(test_string)
            test_split_one = test_string.split('e')
            test_split_two = test_split_one[0].split('.')
            decimal_string = test_split_two[1]
            search = re.search(regex, decimal_string)
            match_pos = None
            substring = None
            if search:
                match_pos = search.end()
                if match_pos is not None:
                    substring = decimal_string[0:(match_pos-5)]
                    reconstructed_string = test_split_two[0] + "." + substring
                    if len(test_split_one) > 1:
                        reconstructed_string = reconstructed_string + "e" + test_split_one[1]

                    final_string = float(reconstructed_string)
            print("%s %s %s %s" % (test_string, match_pos,substring, final_string))


    def test_round_precision(self):
        test_numbers = [4.33734343434e-24,
                        4.3370000000000004e-24,
                        3.6070000000000003e-25,
                        39.60799999999993e-25,
                        0.00000023452324,
                       0.0000023452,
                       1.265e-17,
                       -1.265e-17,
                       -1.265000002e-17,
                       0.00012650000002e-13]

        for number in test_numbers:
            rounded_float = utils.precision_round(number)
            rounded_str = utils.precision_round(number,type='str')
            print("%s %s %s" % (number,rounded_float, rounded_str))

    def test_parse_intensity_metabolights(self):

        assert utils.parse_intensity_metabolights(1) == 1.0
        assert utils.parse_intensity_metabolights('1') == 1.0
        assert utils.parse_intensity_metabolights('1,2') == 1.2
        assert utils.parse_intensity_metabolights('111,111,111') == 111111111.0