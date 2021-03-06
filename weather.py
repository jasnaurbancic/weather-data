#!/usr/bin/python

"""
ECMWF MARS archive access code.
"""

import pdb
import ecmwfapi

from datetime import date

# the set of allowed steps in a query
ALLOWED_STEPS = set(range(0, 90) + range(90, 144, 3) + range(144, 246, 6))

# def ecmwf_server_login():
#     """
#     Establish a connection to ECMWF data server.
#     Assumes a valid .ecmwfapirc file is present in the same folder as the code.
#     """
#     server = ecmwfapi.ECMWFDataServer()
#     return server


class EcmwfServer():
    """
    Connection to the ECMWF server.
    Assumes a valid .ecmwfapirc file is present in the same folder as the code.
    """

    def __init__(self):
        # set up a connection to the MARS data service
        self.service = ecmwfapi.ECMWFService('mars')


    def _check_request(self, request):
        """Test if request is ok for execution."""
        # request has to be complete
        if not request.is_complete():
            missing = [
                param
                for param in ['target', 'date', 'time', 'step']
                if param not in request.params]
            raise RuntimeError("Request has to be complete. Missing: %s" % ', '.join(missing))


    def _check_target(self, target):
        """Check if target file is ok."""
        # try to create the file in order to avoid costly queries that fail in the end
        try:
            open(target, 'a').close()
        except IOError as err:
            raise IOError("Problem creating request target file: " + err.args[1])


    def list(self, request):
        """Test the request and report a summary of statistics about the requested data."""
        self._check_request(request)

        target = request.target
        self._check_target(target)

        # build the request string
        req_str = "list,output=cost," + request.to_req_str()

        # execute the request
        # print "QUERYING WITH:", req_str
        self.service.execute(req_str, target)

        # print the stats
        with open(target) as infile:
            print "=== request info ==="
            print infile.read()
            print "===================="


    def retrieve(self, request):
        """Test the request and report a summary of statistics about the requested data."""
        self._check_request(request)

        target = request.target
        self._check_target(target)

        # build the request string
        req_str = "retreive," + request.to_req_str()

        # execute the request
        # print "QUERYING WITH:", req_str
        self.service.execute(req_str, target)


class WeatherReq():
    """A weather data request."""

    def __init__(self):
        # VARIABLE PARAMETERS
        # ===================

        # mandatory params
        # ----------------

        # target:
        #   * filename where the requested data is dumped
        self.target = None

        # date:
        #   * "YYYY-MM-DD" or "YYYY-MM-DD/to/YYYY-MM-DD"
        #   * date or date range of the data
        self.date = None
        self.end_date = None

        # time:
        #   * "00:00:00" or "12:00:00"
        #   * the time (GMT) of the weather state on each day (at step 0)
        self.time = None

        # step:
        #   * in [0,1,2,...,89] u [90,93,96,...,141] u [144,150,156,...,240]
        #   * time in hours for which the data is returned
        #   * step 0 is current weather state, step X is the forecasted weather state in X hours
        self.step = None


        # optional params
        # ----------------

        # area:
        #   * a lat/lon bounding box specifying the area for the data
        #   * format is [north, west, south, east] or differently [maxLat, minLon, minLat, maxLon]
        self.area = None

        # grid:
        #   * a lat/lon resolution of the data
        #   * format is [latRes, lonRes] (e.g. [1.5, 1.5])
        self.grid = None


        # FIXED PARAMETERS
        self.params = {
            "class"   : "od",
            "expver"  : "1",
            "levtype" : "sfc",
            "param"   : "20.3/23.228/121.128/122.128/123.128/134.128/137.128/141.128/144.128/164.128/167.128/224.228/225.228/228.128/260015",
            "stream"  : "oper",
            "type"    : "fc"}


    def __str__(self):
        """Strig representation of the request is simply the representation of its parameters."""
        max_k = max(len(key) for key in self.params.keys())
        template = "{:%d} : {}" % max_k

        ret = "ECMWF MARS API request:\n"
        ret += '\n'.join(template.format(param, val) for param, val in self.params.iteritems())
        return ret


    def is_complete(self):
        """Does the request have all the parameters needed for execution."""
        return self.target is not None and self.date is not None and \
            self.time is not None and self.step is not None


    def set_target(self, target):
        """Set the target filename to dump the requested data."""
        assert isinstance(target, str), "string expected as target filename, not %s" % repr(target)

        self.target = target
        self.params['target'] = target


    def set_date(self, req_date, end_date = None):
        """Set the date (range) of the data."""
        assert isinstance(req_date, date), "date object expected as input, not %s" % repr(req_date)
        if end_date is not None:
            assert isinstance(end_date, date), "date object expected as input, not %s" % repr(end_date)
            assert req_date < end_date, "start date should be before end date"

        self.date = req_date
        # ECMWF API expects date info serialized as YYYY-MM-DD which is Python default
        self.params['date'] = str(req_date)

        if end_date is not None:
            self.end_date = end_date
            self.params['date'] += '/to/%s' % str(end_date)


    def set_midnight(self):
        """Set measurement time to midnight (00:00:00)."""
        self.time = "00:00:00"
        self.params['time'] = "00:00:00"


    def set_noon(self):
        """Set measurement time to noon (12:00:00)."""
        self.time = "12:00:00"
        self.params['time'] = "12:00:00"


    def set_step(self, step):
        """Set the steps for which you want the weather state."""
        assert isinstance(step, (list, tuple)), "Expectiong a list or tuple"
        assert len(step) > 0, "Expecting at least some steps."
        for s in step:
            assert isinstance(s, int), "Each step should be an int."
        assert set(step).issubset(ALLOWED_STEPS), \
            "Steps %s not possible. Step values can be: %s" % (sorted(set(step)-ALLOWED_STEPS), ALLOWED_STEPS)

        self.step = list(sorted(step))
        self.params['step'] = '/'.join(str(s) for s in self.step)


    def set_area(self, area):
        """Set the area for which you want the data. [N,W,S,E]"""
        assert isinstance(area, (list, tuple)), "Expectiong a list or tuple"
        assert len(area) == 4, "Expecting 4 values for area."
        for res in area:
            assert isinstance(res, (int, float)), "Each area value should be an int or float."

        assert check_area_ranges(area), "Expecting sane area borders."

        self.area = area
        self.params['area'] = '/'.join(str(x) for x in self.area)


    def set_grid(self, grid):
        """Set the lat/lon grid resolution of the data."""
        assert isinstance(grid, (list, tuple)), "Expectiong a list or tuple"
        assert len(grid) == 2, "Expecting 2 values for grid.."
        for res in grid:
            assert isinstance(res, float), "Each grid resolution value should be a float."

        self.grid = grid
        latRes = ('%f' % grid[0]).rstrip('0').rstrip('.')
        lonRes = ('%f' % grid[1]).rstrip('0').rstrip('.')
        self.params['grid'] = '%s/%s' % (latRes, lonRes)


    def to_req_str(self):
        """Transform the request into a string expected by the ECMWF service."""
        return ','.join(["%s=%s" % (param, val) for param, val in sorted(self.params.items())])


def check_area_ranges(area):
    """Check if given list/tuple holds a set of sane area values."""
    # unpack values
    N, W, S, E = area
    # check ranges and ordering
    return -90 <= S < N <= 90  and -180 <= W < E <= 180


def main():
    print "ECMWF access code"


if __name__ == '__main__':
    main()