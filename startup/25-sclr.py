from ophyd.scaler import ScalerCH
from ophyd.device import (Component as C, DynamicDeviceComponent as DDC,
                          kind_context, Device)
from ophyd.status import StatusBase
from ophyd import EpicsSignal


class ScalerMCA(Device):
    _default_read_attrs = ('channels', 'current_channel')
    _default_configuration_attrs = ('nuse', 'prescale')

    # things to be read as data
    channels = DDC({f'mca{k:02d}': (EpicsSignal, f"mca{k}", {})
                    for k in range(1, 21)})
    current_channel = C(EpicsSignal, 'CurrentChannel')
    # configuration details
    nuse = C(EpicsSignal, 'NuseAll', kind='config')
    prescale = C(EpicsSignal, 'Prescale', kind='config')
    channel_advance = C(EpicsSignal, 'ChannelAdvance')
    
    # control PVs

    # high is acquiring
    with kind_context('omitted') as Co:
        status = Co(EpicsSignal, 'Acquiring', string=True,)
        startall = Co(EpicsSignal, 'StartAll', string=True)
        stopall = Co(EpicsSignal, 'StopAll', string=True)
        eraseall = Co(EpicsSignal, 'EraseAll', string=True)
        erasestart = Co(EpicsSignal, 'EraseStart', string=True)

    def stage(self):
        super().stage()
        self.eraseall.put('Erase')

    def stop(self):
        self.stopall.put('Stop')

    def trigger(self):
        self.erasestart.put('Erase')

        return StatusBase(done=True, success=True)

    def read(self):
        # TODO handle file writing and document generation
        return super().read()


class FixedScalerCH(ScalerCH):
    def __init__(self, *args, **kwargs):
        Device.__init__(self, *args, **kwargs)


class Scaler(Device):
    # MCAs
    mcas = C(ScalerMCA, '')
    # TODO maybe an issue with the timing around the triggering?
    cnts = C(FixedScalerCH, 'scaler1')

    def __init__(self, *args, mode='counting', **kwargs):
        super().__init__(*args, **kwargs)
        self.set_mode(mode)

    def match_names(self, N=20):
        self.cnts.match_names()
        for j in range(1, N+1):
            mca_ch = getattr(self.mcas.channels, f"mca{j:02d}")
            ct_ch = getattr(self.cnts.channels, f"chan{j:02d}")
            mca_ch.name = ct_ch.chname.get()

    # TODO put a soft signal around this so we can stage it
    def set_mode(self, mode):
        if mode == 'counting':
            self.read_attrs = ['cnts']
            self.configuration_attrs = ['cnts']
        elif mode == 'flying':
            self.read_attrs = ['mcas']
            self.configuration_attrs = ['mcas']
        else:
            raise ValueError

        self._mode = mode

    def trigger(self):
        if self._mode == 'counting':
            return self.cnts.trigger()
        elif self._mode == 'flying':
            return self.mcas.trigger()
        else:
            raise ValueError

    def stage(self):
        self.match_names()
        if self._mode == 'counting':
            return self.cnts.stage()
        elif self._mode == 'flying':
            return self.mcas.stage()
        else:
            raise ValueError

    def unstage(self):
        if self._mode == 'counting':
            return self.cnts.unstage()
        elif self._mode == 'flying':
            return self.mcas.unstage()
        else:
            raise ValueError


sclr = Scaler('XF:08BM-ES:1{Sclr:1}', name='sclr')
sclr.cnts.channels.read_attrs = [f"chan{j:02d}" for j in range(1, 21)]
sclr.mcas.channels.read_attrs = [f"mca{j:02d}" for j in range(1, 21)]
sclr.mcas.stage_sigs['channel_advance'] = 'External'
sclr.match_names(20)
sclr.set_mode('counting')
