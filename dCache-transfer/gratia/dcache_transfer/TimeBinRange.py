
"""
This module provides an implementation of time binning

The TimeBinRange class represents a single time step, and will do the work of
aggregating (summing) common keys of dictionaries given to the class
"""

RANGE_SIZE_SECS=3600

class DictRecordAggregator:

    """
    This class can be used to add two dictionaries with like keys together
    """

    def __init__(self, aggFields, sumFields):
        """
        @param aggFields: A list of keys used to determine if two
            dictionaries are equal to each other.
        @param sumFields: A list of keys used to add two dictionaries together.
        """
        self.aggFields = aggFields
        self.sumFields = sumFields

    def equal(self, item1, item2):
        """
        Test to see if two dictionaries are equal to each other.

        Equal iff the value of item1[key] == item2[key] for each key in
        aggFields

        @param item1: The first input dictionary
        @param item2: The second input dictionary
        @return: 1 if we consider the dictionaries equivalent; 0 otherwise
        """
        try:
            for aggField in self.aggFields:
                if ( item1[aggField] != item2[aggField] ):
                    return 0
            return 1
        except KeyError as ex:
            pass
        return 0

    def add(self, item1, item2):
        """
        Add dictionary item1 to dictionary item2, saving the results to item1.

        Only keys in self.sumFields are summed.  Keys in item1 that are not in
        self.sumFields are ignored.

        @return: Nothing.  item1 is altered.
        """
        for sumField in self.sumFields:
            item1[sumField] = item1[sumField] + item2[sumField]

class Bin:

    """
    A container object to hold aggregated items at a certain time bin.
    """

    def __init__(self, tm, aggregator):
        self.tracks = []
        self.aggregator = aggregator
        self.tm = tm

    def add(self,item):
        item["tm"] = self.tm
        for t in self.tracks:
            # can be optimized to use hash keys for specific field names, etc. not critical here
            if self.aggregator.equal(t,item):
                t = self.aggregator.add(t,item)
                return
        self.tracks.append(item)

    def list(self):
        return self.tracks

class TimeBinRange:

    """
    Class that holds (and ultimately aggregates) a range of time bins

    Timebins are aligned to the global RANGE_SIZE_SECS
    """

    def __init__(self, agg):
        """
        @param agg: An object that can be used to add two dictionaries and
           determine if they are equal.  Usually a DictRecordAggregator.
        """
        self.agg = agg
        self.bins = {}

    def add(self, tm, item):
       """
       Add item to timebin for tm.

       @param tm: Unix timestamp
       @param item: Dictionary to add to the TimeBin.
       """
       alignedTm = int(tm/RANGE_SIZE_SECS)*RANGE_SIZE_SECS
       b = self.bins.setdefault(alignedTm, Bin(alignedTm, self.agg))
       b.add(item)

    def list(self):
        """
        Returns a list of the aggregated rows held by this object.
        """
        result = []
        for tm in sorted(self.bins):
            result += self.bins[tm].list()
        return result

####
# Remainder of this module is for testing
####

def test():

    r1 = { 'status': 1 , 'source' : 'a', 'jobs' : 1 , 'transferred' : 1 }
    r2 = { 'status': 1 , 'source' : 'a', 'jobs' : 1 , 'transferred' : 2 }

    r3 = { 'status': 0 ,  'source' : 'a', 'jobs' : 1 , 'transferred' : 0 }
    r4 = { 'status': 0 ,  'source' : 'a', 'jobs' : 1 , 'transferred' : 0 }

    r5 = { 'status': 0 ,  'source' : 'a', 'jobs' : 1 , 'transferred' : 0 }
    r6 = { 'status': 0 ,  'source' : 'b', 'jobs' : 1 , 'transferred' : 0 }

    tr = TimeBinRange(DictRecordAggregator(['status','source'],['jobs','transferred']))

    tr.add(0,r1)
    tr.add(0,r2)
    tr.add(0,r3)
    tr.add(0,r4)
    tr.add(10000,r5)
    tr.add(10000,r6)


    for l in tr.list():
       print(l)

if __name__ == '__main__':
    test()
