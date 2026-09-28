"""Same region objective with explicitly budgeted finger corrections."""
from paired_finger_fit import FingerHandActor
from paired_palm_region import install_region


class FingerRegionActor(FingerHandActor):
    def __init__(self,*args,patch,**kwargs):
        super().__init__(*args,**kwargs)
        install_region(self,patch,args[4])
