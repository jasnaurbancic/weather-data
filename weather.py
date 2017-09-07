#!/usr/bin/python

"""
ECMWF MARS archive access code.
"""

# import pdb
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


    def list(self, request):
        """Test the request and report a summary of statistics about the requested data."""
        # request has to be complete
        if not request.is_complete():
            missing = [
                param
                for param in ['target', 'date', 'time', 'step']
                if param not in request.params]
            raise RuntimeError("Request has to be complete. Missing: %s" % ', '.join(missing))

        target = request.target
        # try to create the file in order to avoid costly queries that fail in the end
        try:
            open(target, 'a').close()
        except IOError as err:
            raise IOError("Problem creating request target file: " + err.args[1])

        # build the request string
        req_str = "list,output=cost," + request.to_req_str()

        # execute the request
        #print "QUERYING WITH:", req_str
        self.service.execute(req_str, target)

        # print the stats
        with open(target) as infile:
            print "=== request info ==="
            print infile.read()
            print "===================="



class WeatherReq():
    """A weather data request."""

    def __init__(self):
        # variable parameters
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

        # fixed parameters
        self.params = {
            "class"   : "od",
            "expver"  : "1",
            "levtype" : "sfc",
            "param"   : "167.128",
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


    def to_req_str(self):
        """Transform the request into a string expected by the ECMWF service."""
        return ','.join(["%s=%s" % (param, val) for param, val in sorted(self.params.items())])


def main():
    print "ECMWF access code"

    test_req = WeatherReq()
    test_req.set_target('TEST.txt')
    test_req.set_date(date(2016, 9, 17))
    test_req.set_noon()
    test_req.set_step([0])
    serv = EcmwfServer()

    serv.list(test_req)


if __name__ == '__main__':
    main()


# EXAMPLE QUERIES:
# query = (
#     {"list" : {
#         "class"     : "od",
#         "type"      : "an",
#         "expver"    : "1",
#         "stream"    : "kwbc",
#         "date"      : "19990222",
#         "time"      : "0000/1200",
#         "levtype"   : "pl",
#         "levelist"  : "1000/850/500",
#         "param"     : "129/130"
#     }},
#     "TEST_TARGET.grib")

# query = (
#     {
#         "class"   : "od",
#         "date"    : "2017-06-29",
#         "expver"  : "1",
#         "levtype" : "sfc",
#         "param"   : "167.128",
#         "step"    : "0",
#         "stream"  : "oper",
#         "time"    : "12:00:00",
#         "type"    : "fc",
#     },
#     "TEST_TARGET.grib")


# server.retrieve({
#     'stream'    : "oper",
#     'levtype'   : "sfc",
#     'param'     : "167.128",
#     'repres'    : "gg",
#     'step'      : "0",
#     'time'      : "12",
#     'date'      : "1986-08-01/to/1986-08-31",
#     'dataset'   : "era15",
#     'type'      : "an",
#     'class'     : "er",
#     'target'    : "era15_1986-08-01to1986-08-31_12.grib"
# })