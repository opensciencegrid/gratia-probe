#===============================================================================
# VM Probe Configuration
#===============================================================================
from gratia.common.GratiaCore import ProbeConfiguration
class VMGratiaProbeConfig(ProbeConfiguration):
    def __init__( self,customConfig='ProbeConfig' ):
        # Just call the parent class to read in the file.
        # We just add some extra name/value readouts.
        ProbeConfiguration.__init__(self,customConfig)
        
