
from __future__ import print_function

import gratia.common.GratiaCore as GratiaCore
import gratia.common.send as send
import gratia.metric.Metric as Metric

if __name__ == '__main__':
        GratiaCore.Initialize()
        r = Metric.MetricRecord()

        r.MetricName("LFC-READ")
        r.MetricStatus("OK")
        r.Timestamp("2009-01-02T15:48:39Z") # Or could enter it as seconds since epoch

        print(send.Send(r))
