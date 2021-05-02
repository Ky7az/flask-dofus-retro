# -*- encoding: utf-8 -*-
""" PACKETS.PY """

from kamene.all import * # scapy
import struct

from dr.snf.constants import CMSG, SMSG


# GENERAL

class StrStopField(StrStopField):
    """ Remove stop field (last character) """

    def i2repr(self, pkt, x):
        return x[:-1]

    def i2h(self, pkt, x):
        return x[:-1]

# CLIENT

class CLIENT_MSG(Packet):
    name = "CMSG"
    fields_desc = [
        ByteField("type", 0),
        ByteField("action", 0),
        ByteField("error", 0)
    ]

    @classmethod
    def add_ConditionalPacketField(cls, name, inst):
        cond_pck_field = ConditionalField(PacketField(name, "", inst), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == inst.name)
        cls.fields_desc.append(cond_pck_field)

client_pkt_fields = CMSG.values()
for cpf in client_pkt_fields:
    inst = getattr(sys.modules[__name__], "CMSG_" + cpf)
    CLIENT_MSG.add_ConditionalPacketField(cpf, inst)


# SERVER

class SERVER_MSG(Packet):
    name = "SMSG"
    fields_desc = [
        ByteField("type", 0),
        ByteField("action", 0),
        ByteField("error", 0)
    ]

    @classmethod
    def add_ConditionalPacketField(cls, name, inst):
        lmbd = lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == inst.name
        if len(inst.name) == 3:
            lmbd = lambda pkt: '{}{}{}'.format(chr(pkt.type), chr(pkt.action), chr(pkt.error)) == inst.name

        cond_pck_field = ConditionalField(PacketField(name, None, inst), lmbd)
        cls.fields_desc.append(cond_pck_field)

class SMSG_Fights_onCount(Packet):
    name = 'fC'
    fields_desc = [
        StrNullField("count", 0)
    ]

class SMSG_Basics_onReferenceTime(Packet):
    name = 'BT'
    fields_desc = [
        StrNullField("time", 0),
        ByteField("type", 0),
        ByteField("action", 0),
        ConditionalField(PacketField("SMSG_Fights_onCount", None, SMSG_Fights_onCount), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_Fights_onCount.name)
    ]

class SMSG_Game_onMapData(Packet):
    name = 'GDM'
    fields_desc = [
        ByteField("|", ""),
        StrStopField("map_id", 0, b"|"),
        StrStopField("create_date", 0, b"|"),
        StrNullField("private_key", 0),
        ByteField("type", 0),
        ByteField("action", 0),
        ConditionalField(PacketField("SMSG_Basics_onReferenceTime", None, SMSG_Basics_onReferenceTime), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_Basics_onReferenceTime.name)    
    ]

class SMSG_Job_onXP(Packet):
    name = 'JX'
    fields_desc = [
        StrStopField("unknown", 0, b";"),
        StrStopField("lvl", 0, b";"),
        StrStopField("xp_min", 0, b";"),
        StrStopField("xp", 0, b";"),
        StrNullField("xp_max", 0),
        ByteField("type", 0),
        ByteField("action", 0)
    ]

class SMSG_Infos_onQuantity(Packet):
    name = 'IQ'
    fields_desc = [
        StrStopField("entity_id", 0, b"|"),
        StrNullField("quantity", 0),
        ByteField("type", 0),
        ByteField("action", 0),
        ByteField("error", 0),
        ConditionalField(PacketField("SMSG_Job_onXP", None, SMSG_Job_onXP), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_Job_onXP.name)
    ]

class SMSG_Items_onWeight(Packet):
    name = 'Ow'
    fields_desc = [
        StrStopField("current_weight", 0, b"|"),
        StrNullField("max_weight", 0),
        ByteField("type", 0),
        ByteField("action", 0),
        ConditionalField(PacketField("SMSG_Infos_onQuantity", None, SMSG_Infos_onQuantity), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_Infos_onQuantity.name),
        ConditionalField(PacketField("SMSG_Job_onXP", None, SMSG_Job_onXP), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_Job_onXP.name)
    ]

class SMSG_Items_onQuantity(Packet):
    name = 'OQ'
    fields_desc = [
        StrStopField("item_id", 0, b"|"),
        StrNullField("quantity", 0),
        ByteField("type", 0),
        ByteField("action", 0),
        ConditionalField(PacketField("SMSG_Items_onWeight", None, SMSG_Items_onWeight), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_Items_onWeight.name)
    ]

class SMSG_Exchange_onList(Packet):
    name = 'EL'
    fields_desc = [
        StrNullField("data", "")
    ]

class SMSG_Exchange_onCreate(Packet):
    name = 'EC'
    fields_desc = [
        StrNullField("data", ""),
        ByteField("type", 0),
        ByteField("action", 0),
        ConditionalField(PacketField("SMSG_Exchange_onList", None, SMSG_Exchange_onList), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_Exchange_onList.name)
    ]

class SMSG_Account_onStats(Packet):
    name = 'As'
    fields_desc = [
        StrNullField("data", ""),
        ByteField("type", 0),
        ByteField("action", 0),
        ConditionalField(PacketField("SMSG_Exchange_onCreate", None, SMSG_Exchange_onCreate), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_Exchange_onCreate.name)
    ]

class SMSG_Infos_onMessage(Packet):
    name = 'Im'
    fields_desc = [
        StrNullField("data", ""),
        ByteField("type", 0),
        ByteField("action", 0),
        ConditionalField(PacketField("SMSG_Account_onStats", None, SMSG_Account_onStats), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_Account_onStats.name),
    ]

class SMSG_Dialog_DR(Packet):
    name = 'DR'
    fields_desc = [
        StrNullField("data", ""),
        ByteField("type", 0),
        ByteField("action", 0),
        ConditionalField(PacketField("SMSG_Infos_onMessage", None, SMSG_Infos_onMessage), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_Infos_onMessage.name),
    ]

class SMSG_Game_onFrameObject2(Packet):
    name = 'GDF'
    fields_desc = [
        StrNullField("data", ""),
        ByteField("type", 0),
        ByteField("action", 0),
        ConditionalField(PacketField("SMSG_Items_onQuantity", None, SMSG_Items_onQuantity), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_Items_onQuantity.name),
        ConditionalField(PacketField("SMSG_Infos_onMessage", None, SMSG_Infos_onMessage), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_Infos_onMessage.name)
    ]

class SMSG_Game_onJoin(Packet):
    name = 'GJ'
    fields_desc = [
        StrNullField("unknown", "")
    ]

class SMSG_Game_onMovement(Packet):
    name = 'GM'
    fields_desc = [
        StrNullField("unknown", ""), 
        ByteField("type", 0),
        ByteField("action", 0),
        ConditionalField(PacketField("SMSG_Game_onJoin", None, SMSG_Game_onJoin), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_Game_onJoin.name)
    ]

class SMSG_GameActions_onActions(Packet):
    name = 'GA'
    fields_desc = [
        StrNullField("data", ""),
        ByteField("type", 0),
        ByteField("action", 0),
        ByteField("error", 0),
        ConditionalField(PacketField("SMSG_Game_onMapData", None, SMSG_Game_onMapData), lambda pkt: '{}{}{}'.format(chr(pkt.type), chr(pkt.action), chr(pkt.error)) == SMSG_Game_onMapData.name),
        ConditionalField(PacketField("SMSG_Game_onFrameObject2", None, SMSG_Game_onFrameObject2), lambda pkt: '{}{}{}'.format(chr(pkt.type), chr(pkt.action), chr(pkt.error)) == SMSG_Game_onFrameObject2.name),
        ConditionalField(PacketField("SMSG_Game_onMovement", None, SMSG_Game_onMovement), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_Game_onMovement.name),
        ConditionalField(PacketField("SMSG_Game_onJoin", None, SMSG_Game_onJoin), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_Game_onJoin.name)
    ]

class SMSG_Game_onCreate(Packet):
    name = 'GC'
    fields_desc = [
        StrNullField("data", ""),
        ByteField("type", 0),
        ByteField("action", 0),
        ConditionalField(PacketField("SMSG_Account_onStats", None, SMSG_Account_onStats), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_Account_onStats.name)
    ]

class SMSG_Game_GD(Packet):
    name = 'GD'
    fields_desc = [
        ByteField("type", 0),
        ByteField("action", 0),
        ByteField("error", 0),
        ConditionalField(PacketField("SMSG_Game_onFrameObject2", None, SMSG_Game_onFrameObject2), lambda pkt: '{}{}{}'.format(chr(pkt.type), chr(pkt.action), chr(pkt.error)) == SMSG_Game_onFrameObject2.name)
    ]

class SMSG_Exchange_onItemMiddlePriceInBigStore(Packet):
    name = 'EHP'
    fields_desc = [
        StrStopField("item_id", 0, b"|"),
        StrNullField("avg_price", 0)
    ]

class SMSG_Exchange_onBigStoreItemsList(Packet):
    name = 'EHl'
    fields_desc = [
        StrStopField("item_id", 0, b"|"),
        StrNullField("data", "")
    ]

SMSG_Job_onXP.fields_desc.append(ConditionalField(PacketField("SMSG_GameActions_onActions", None, SMSG_GameActions_onActions), lambda pkt: '{}{}'.format(chr(pkt.type), chr(pkt.action)) == SMSG_GameActions_onActions.name))

server_pkt_fields = SMSG.values()
for spf in server_pkt_fields:
    inst = getattr(sys.modules[__name__], "SMSG_" + spf)
    SERVER_MSG.add_ConditionalPacketField(spf, inst)