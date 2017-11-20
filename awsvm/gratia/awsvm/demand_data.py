#!/usr/bin/python

import re
import urllib2
import json
from gratia.common.Gratia import DebugPrint, Error



class AwsDemandData(object):
    def __init__(self):
        self.data=dict()

    def load_url(self, url="http://a0.awsstatic.com/pricing/1/ec2/linux-od.min.js"):
        """
        Load AWS on-demand pricing data from unodcumented API used for AWS website.

        Format:

        callback({vers:0.01,config:{rate:"perhr",valueColumns:["vCPU","ECU","memoryGiB","storageGB","linux"],currencies:["USD"],regions:[{region:"us-east-1",instanceTypes:[{type:"generalCurrentGen",sizes:[{size:"t2.micro",vCPU:"1",ECU:"variable",memoryGiB:"1",storageGB:"ebsonly",valueColumns:[{name:"linux",prices:{USD:"0.013"}}]},{size:"t2.small",vCPU:"1",ECU:"variable",memoryGiB:"2",storageGB:"ebsonly",valueColumns:[{name:"linux",prices:{USD:"0.026"}}]},
        ...
        {size:"i2.8xlarge",vCPU:"32",ECU:"104",memoryGiB:"244",storageGB:"8 x 800 SSD",valueColumns:[{name:"linux",prices:{USD:"8.184"}}]}]}]}]}});
        """
        f = urllib2.urlopen(url).read()
        f = re.sub("/\\*[^\x00]+\\*/", "", f, 0, re.M)
        f = re.sub("([a-zA-Z0-9]+):", "\"\\1\":", f)
        f = re.sub(";", "\n", f)
        f = re.sub("callback\(", "", f)
        f = re.sub("\)$", "", f)
        r = json.loads(f)

        for region in r["config"]["regions"]:
            region_name = region["region"]
            region_prices = {}
            for t in region["instanceTypes"]:
                for s in t['sizes']:
                    price = -1
                    for c in s["valueColumns"]:
                        if c["name"] == "linux":
                            price = c["prices"]["USD"]
                            break
                    if price == -1:
                        DebugPrint(1,"trouble getting price for image %s in region %s"%(s["size"],region_name))
                        raise IOError
                    region_prices[s["size"]] = {
                            "name": s["size"],
                            "cpu": s["vCPU"],
                            "memory": s["memoryGiB"],
                            "storage": s["storageGB"],
                            "price": price,
                            }
            self.data[region_name]=region_prices

    def load_file(self, filename):
        """
        Load AWS on-demand pricing data from JSON file. 
        (run this script standalone to generate this file from the AWS site)
        """
        f = open(filename)
        self.data = json.load(f)
    
    def instance_data(self, region, instance):
        return self.data[region][instance]

    def instance_price(self, region, instance):
        return self.instance_data(region,instance).price


if __name__=="__main__":
    a = AwsDemandData()
    a.load_url()
    print json.dumps(a.data, sort_keys=True, indent=4)

