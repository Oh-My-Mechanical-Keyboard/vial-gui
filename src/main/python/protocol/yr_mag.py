import struct

from keycodes.keycodes import Keycode
from protocol.base_protocol import BaseProtocol
from protocol.constants import CMD_VIA_MACRO_GET_COUNT, CMD_VIA_MACRO_GET_BUFFER_SIZE, CMD_VIA_MACRO_GET_BUFFER, \
    CMD_VIA_MACRO_SET_BUFFER, BUFFER_FETCH_CHUNK, VIAL_PROTOCOL_ADVANCED_MACROS
from unlocker import Unlocker
from util import chunks

# 0x96 for screen
# 0x97 for test
# 0x98 for magnet
YR_PROTOCOL_MAG_PREFIX = 0x96

YR_PROTOCOL_MAG_GET = 0x02
YR_PROTOCOL_MAG_SET = 0x03

YR_PROTOCOL_MAG_GET_VERSION = 0
YR_PROTOCOL_MAG_RELEASE = 1
YR_PROTOCOL_MAG_PRESS = 2
YR_PROTOCOL_MAG_APC = 3
YR_PROTOCOL_MAG_RT_SW = 4
YR_PROTOCOL_MAG_RT_TH = 5
YR_PROTOCOL_MAG_RT_SET_TH = 6
YR_PROTOCOL_MAG_RT_ALL = 7
YR_PROTOCOL_MAG_ADVANCE_DKS = 8
YR_PROTOCOL_MAG_ADC_SHOW = 9
YR_PROTOCOL_MAG_TRAVEL_SHOW = 10
YR_PROTOCOL_MAG_ALL = 11

DKS_EVENT_0 = 0
DKS_EVENT_1 = 1
DKS_EVENT_2 = 2
DKS_EVENT_3 = 3

DKS_EVENT_MAX = 4
DKS_KEY_MAX = 4

class DksKey:
    def __init__(self):
        self.down_events = ([0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0])
        self.up_events = ([0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0])
        self.keys = ["KC_NO","KC_NO","KC_NO","KC_NO"]
        self.dirty = False

    def is_dirty(self):
        return self.dirty
    
    def is_valid(self):
        for k in self.keys:
            if k != "KC_NO":
                return True
        for t in self.down_events:
            for e in t:
                if e != 0:
                    return True
        for t in self.up_events:
            for e in t:
                if e != 0:
                    return True
        return False
    
    def set_dirty(self, dirty):
        self.dirty = dirty

    def update_inner_key(self, index, key):
        if index >= DKS_KEY_MAX:
            return

        if not Keycode.is_basic(key):
            return

        if not Keycode.is_mask(self.keys[index]):
            return

        kc = Keycode.find_outer_keycode(self.keys[index])
        if kc is None:
            return
        
        keycode = kc.qmk_id.replace("(kc)", "({})".format(key))
        self.keys[index] = keycode
        self.dirty = True

        print("DKS keys: index={}, code={}".format(index, keycode))

    def add_key(self, index, key):
        if index < DKS_KEY_MAX:
            if self.keys[index] != key:
                self.keys[index] = key
                self.dirty = True
            return True
        else:
            print("DKS failed to add key: index ={}, key={}".format(index, key))
            return False
    
    def del_key(self, index):
        if self.keys[index] != "KC_NO":
            self.keys[index] = "KC_NO"
            self.dirty = True

    def add_event(self, event, key, down):
        if event >= DKS_EVENT_MAX:
            print("DKS failed to set event: index={}, key={}, down={}".format(event, key, down))
            return False

        evts = self.down_events if down else self.up_events
        if evts[event][key] == 0:
            evts[event][key] = 1
            self.dirty = True
        return True

    def del_event(self, event, key, down):
        if event >= DKS_EVENT_MAX:
            print("DKS failed to clear event: index={}, key={}, down={}".format(event, key, down))
            return False

        evts = self.down_events if down else self.up_events
        if evts[event][key] == 1:
            evts[event][key] = 0
            self.dirty = True
        return True

    def pack_dks(self):
        evts = [0,0,0,0]
        for i in range(DKS_EVENT_MAX):
            for j in range(4):
                if self.down_events[i][j] > 0:
                    evts[i] |= 1 << j
                if self.up_events[i][j] > 0:
                    evts[i] |= 1 << (j+4)
        
        keys = [0,0,0,0]
        for i in range(len(self.keys)):
            keys[i] = Keycode.resolve(self.keys[i])
        
        data = struct.pack(">BBBBHHHH", 
                        evts[0], evts[1], evts[2], evts[3],
                        keys[0], keys[1], keys[2], keys[3])
        return data
    
    def save(self):
        dks = {}
        dks["down"] = self.down_events
        dks["up"] = self.up_events
        dks["codes"] = self.keys
        return dks

    def load(self, dks):
        for i in range(len(self.down_events)):
            for j in range(len(self.down_events[i])):
                self.down_events[i][j] = dks["down"][i][j]

        for i in range(len(self.up_events)):
            for j in range(len(self.up_events[i])):
                self.down_events[i][j] = dks["up"][i][j]

        for i in range(len(self.keys)):
            self.keys[i] = dks["codes"][i]

    def is_same(self, dks):
        for i in range(len(self.down_events)):
            for j in range(len(self.down_events[i])):
                if self.down_events[i][j] != dks["down"][i][j]:
                    return False

        for i in range(len(self.up_events)):
            for j in range(len(self.up_events[i])):
                if self.down_events[i][j] != dks["up"][i][j]:
                    return False

        for i in range(len(self.keys)):
            if self.keys[i] != dks["codes"][i]:
                return False

        return True

    def parse(self, data):
        print("Parse DKS")
        for i in range(4):
            print("Event:{:b}".format(data[i]))
            for j in range(4):
                if data[i] & (1<<j) > 0:
                    self.down_events[i][j] = 1
                else:
                    self.down_events[i][j] = 0

                if data[i] & (1<<(j+4)) > 0:
                    self.up_events[i][j] = 1
                else:
                    self.up_events[i][j] = 0

        keys = struct.unpack(">HHHH", data[4:13])
        for i in range(4):
            self.keys[i] = Keycode.serialize(keys[i])
            print("Keys", self.keys[i])


    def clear(self):
        for i in range(len(self.keys)):
            self.keys[i] = "KC_NO"

        for i in range(DKS_EVENT_MAX):
            for j in range(4):
                self.down_events[i][j] = 0
                self.up_events[i][j] = 0

        self.dirty = True
    
    def get_key(self, index):
        if index < len(self.keys):
            return self.keys[index]

        return 0
    
    def is_event_on(self, event, index, down):
        if event < DKS_EVENT_MAX:
            if down:
                if index < 4:
                    return self.down_events[event][index] > 0
            else:
                if index < 4:
                    return self.up_events[event][index] > 0

        return False

    def dump(self):
        return
        print("Dump DKSKey")
        for i in range(4):
            print("Key({}) is {}".format(i, self.keys[i]))

        for i in range(DKS_EVENT_MAX):
            for j in range(4):
                print("Event({}), Down({}) is {:b}".format(i, j, self.down_events[i][j]))
                print("Event({}), Up({}) is {:b}".format(i, j, self.up_events[i][j]))


class ProtocolYrMag(BaseProtocol):

    def yr_mag_protocol_version(self):
        """ Get the version of YR Magnet protocol """
        data = self.usb_send(self.dev, struct.pack("BBB", YR_PROTOCOL_MAG_GET, YR_PROTOCOL_MAG_PREFIX, YR_PROTOCOL_MAG_GET_VERSION), retries=20)
        print("Magment Version:", data[5])
        return data[5]

    def reload_apc(self):
        """ Reload APC information from keyboard """
        for row, col in self.rowcol.keys():
            data = self.usb_send(self.dev, 
                                struct.pack("BBBBB", YR_PROTOCOL_MAG_GET, YR_PROTOCOL_MAG_PREFIX, YR_PROTOCOL_MAG_APC, row, col),
                                retries=20)
            data = data[5] & 0xff
            self.mag_apc[(row, col)] = data

    def reload_rt(self):
        """ Reload RT information from keyboard """
        for row, col in self.rowcol.keys():
            data = self.usb_send(self.dev, 
                                struct.pack("BBBBB", YR_PROTOCOL_MAG_GET, YR_PROTOCOL_MAG_PREFIX, YR_PROTOCOL_MAG_RT_ALL, row, col),
                                retries=20)
            # rt_sw, rt_th, rt_set_th
            self.mag_rt[(row, col)] = [data[5]&0xff, data[6]&0xff, data[7]&0xff]
            
    def reload_dks(self):
        pass
        # """ Reload DKS information from keyboard """
        # for row, col in self.rowcol.keys():
        #     data = self.usb_send(self.dev, 
        #                         struct.pack("BBBB", YR_PROTOCOL_MAG_GET, YR_PROTOCOL_MAG_PREFIX, row, col),
        #                         retries=20)
        #     print("DKS:")
        #     print(data)
            # dks_data = data[3:15]
            # dks = DksKey()
            # dks.parse(dks_data)
            # self.amk_dks[(row, col)] = dks 
            # print("AMK protocol: DKS={}, row={}, col={}".format(dks.pack_dks(), row, col))

    def apply_dks(self, row, col, dks=None):
        pass
        # if dks is not None:
        #     if self.amk_dks[(row, col)].is_same(dks):
        #         return
        #     self.amk_dks[(row,col)].load(dks)

        # #self.amk_dks[(row,col)].dump()
        # data = struct.pack("BBBB", AMK_PROTOCOL_PREFIX, AMK_PROTOCOL_SET_DKS, row, col) + self.amk_dks[(row,col)].pack_dks()
        # data = self.usb_send(self.dev, data, retries=20)

    def apply_apc(self, row, col, val):
        if self.mag_apc[(row,col)] == val:
            return
        print("Update APC at({},{}), old({}), new({})".format(row, col, self.mag_apc[(row,col)], val))
        self.mag_apc[(row,col)] = val
        data = struct.pack("BBBBBB", YR_PROTOCOL_MAG_SET, YR_PROTOCOL_MAG_PREFIX, YR_PROTOCOL_MAG_APC, row, col, val)
        data = self.usb_send(self.dev, data, retries=20)

    def apply_rt(self, row, col, val):
        ori_val = self.mag_rt[(row,col)]
        if len(val) != 3 or len(ori_val) != 3:
            return
        if ori_val[0] == val[0] and ori_val[1] == val[1] and ori_val[2] == val[2] :
            return
        print("Update RT at({},{}), old({}), new({})".format(row, col, self.mag_rt[(row,col)], val))
        self.mag_rt[(row,col)] = val
        data = struct.pack("BBBBBBBB", YR_PROTOCOL_MAG_SET, YR_PROTOCOL_MAG_PREFIX, YR_PROTOCOL_MAG_RT_ALL, row, col, val[0], val[1], val[2])
        data = self.usb_send(self.dev, data, retries=20)

    def get_adc(self, row, col):
        data = struct.pack("BBBBB", YR_PROTOCOL_MAG_GET, YR_PROTOCOL_MAG_PREFIX, YR_PROTOCOL_MAG_ADC_SHOW, row, col)
        data = self.usb_send(self.dev, data, retries=20)
        adc = (data[5] << 8) | (data[6] & 0xff)
        return adc
    def get_travel(self, row, col):
        data = struct.pack("BBBBB", YR_PROTOCOL_MAG_GET, YR_PROTOCOL_MAG_PREFIX, YR_PROTOCOL_MAG_TRAVEL_SHOW, row, col)
        data = self.usb_send(self.dev, data, retries=20)
        travel = (data[5] & 0xff)
        return travel
