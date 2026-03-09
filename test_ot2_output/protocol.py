
from opentrons import protocol_api

# metadata
metadata = {
    'protocolName': 'Test Assembly Protocol', 'author': 'ProtoGen', 'robotType': 'OT-2'
}

requirements = {'robotType': 'OT-2', 'apiLevel': '2.17'}


def run(protocol: protocol_api.ProtocolContext):
    # labware_load
    Stocking_plate_1 = protocol.load_labware('corning_96_wellplate_360ul_flat', 1)
    Stocking_plate_2 = protocol.load_labware('corning_96_wellplate_360ul_flat', 2)
    destination = protocol.load_labware('corning_96_wellplate_360ul_flat', 3)
    
    tiprack = protocol.load_labware('opentrons_96_tiprack_300ul', 4)
    p300 = protocol.load_instrument('p300_single', 'left', tip_racks=[tiprack])
    

    # Assembly design 1
    p300.pick_up_tip()
    p300.aspirate(1.0, Stocking_plate_1['A1'])  # (P)TDH
    p300.dispense(1.0, destination['A1'])
    p300.drop_tip()
    
    p300.pick_up_tip()
    p300.aspirate(1.0, Stocking_plate_2['A1'])  # (C)mTurquiose2
    p300.dispense(1.0, destination['A1'])
    p300.drop_tip()
    
    p300.pick_up_tip()
    p300.aspirate(1.0, Stocking_plate_1['A4'])  # (T)ENO1
    p300.dispense(1.0, destination['A1'])
    p300.drop_tip()
    
    p300.pick_up_tip()
    p300.aspirate(1.0, Stocking_plate_1['A6'])  # (N)s|1
    p300.dispense(1.0, destination['A1'])
    p300.drop_tip()
    
    p300.pick_up_tip()
    p300.aspirate(2.0, Stocking_plate_2['A8'])  # GGAmix
    p300.dispense(2.0, destination['A1'])
    p300.drop_tip()
    

    # Assembly design 2
    p300.pick_up_tip()
    p300.aspirate(1.0, Stocking_plate_1['B1'])  # (P)CCW12
    p300.dispense(1.0, destination['A2'])
    p300.drop_tip()
    
    p300.pick_up_tip()
    p300.aspirate(1.0, Stocking_plate_2['A1'])  # (C)mTurquiose2
    p300.dispense(1.0, destination['A2'])
    p300.drop_tip()
    
    p300.pick_up_tip()
    p300.aspirate(1.0, Stocking_plate_1['A4'])  # (T)ENO1
    p300.dispense(1.0, destination['A2'])
    p300.drop_tip()
    
    p300.pick_up_tip()
    p300.aspirate(1.0, Stocking_plate_1['A6'])  # (N)s|1
    p300.dispense(1.0, destination['A2'])
    p300.drop_tip()
    
    p300.pick_up_tip()
    p300.aspirate(2.0, Stocking_plate_2['A8'])  # GGAmix
    p300.dispense(2.0, destination['A2'])
    p300.drop_tip()
    

    # Assembly design 3
    p300.pick_up_tip()
    p300.aspirate(1.0, Stocking_plate_1['A2'])  # (P)RPL18B
    p300.dispense(1.0, destination['A3'])
    p300.drop_tip()
    
    p300.pick_up_tip()
    p300.aspirate(1.0, Stocking_plate_2['B1'])  # (C)Venus
    p300.dispense(1.0, destination['A3'])
    p300.drop_tip()
    
    p300.pick_up_tip()
    p300.aspirate(1.0, Stocking_plate_1['B4'])  # (T)ISSA1
    p300.dispense(1.0, destination['A3'])
    p300.drop_tip()
    
    p300.pick_up_tip()
    p300.aspirate(1.0, Stocking_plate_1['A5'])  # (N)1|2
    p300.dispense(1.0, destination['A3'])
    p300.drop_tip()
    
    p300.pick_up_tip()
    p300.aspirate(2.0, Stocking_plate_2['A8'])  # GGAmix
    p300.dispense(2.0, destination['A3'])
    p300.drop_tip()
    

    # Assembly design 4
    p300.pick_up_tip()
    p300.aspirate(1.0, Stocking_plate_1['A2'])  # (P)RPL18B
    p300.dispense(1.0, destination['A4'])
    p300.drop_tip()
    
    p300.pick_up_tip()
    p300.aspirate(1.0, Stocking_plate_2['C1'])  # (C)mRuby2
    p300.dispense(1.0, destination['A4'])
    p300.drop_tip()
    
    p300.pick_up_tip()
    p300.aspirate(1.0, Stocking_plate_1['B4'])  # (T)ISSA1
    p300.dispense(1.0, destination['A4'])
    p300.drop_tip()
    
    p300.pick_up_tip()
    p300.aspirate(1.0, Stocking_plate_1['A5'])  # (N)1|2
    p300.dispense(1.0, destination['A4'])
    p300.drop_tip()
    
    p300.pick_up_tip()
    p300.aspirate(2.0, Stocking_plate_2['A8'])  # GGAmix
    p300.dispense(2.0, destination['A4'])
    p300.drop_tip()
    