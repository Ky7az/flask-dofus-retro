# -*- encoding: utf-8 -*-
""" CONSTANTS.PY """

import win32gui


DOFUS_AUTH_IP = ["34.251.172.139"]
DOFUS_GAME_IP = ["52.19.56.159"]

is_CMSG = lambda p: p["IP"].dst in DOFUS_AUTH_IP + DOFUS_GAME_IP
is_SMSG = lambda p: p["IP"].src in DOFUS_AUTH_IP + DOFUS_GAME_IP

version = '1.30.14'
win_title_fmt = '{} - Dofus Retro v%s' % version

CMSG = {
}

SMSG = {
    'GDF': 'Game_onFrameObject2',
    'GA': 'GameActions_onActions',
    'GC': 'Game_onCreate',
    'GD': 'Game_GD',
    'Im': 'Infos_onMessage',
    'EHP': 'Exchange_onItemMiddlePriceInBigStore',
    'EHl': 'Exchange_onBigStoreItemsList'
}

NETWORK_INTERFACE = 'Intel(R) Dual Band Wireless-AC 3165'

RESOLUTION =  {
    'min_x': 270,
    'max_x': 1650,
    'min_y': 20,
    'max_y': 850
}

SCAN_ON_LOADING_MAP = False

ACTIONS = [
    'nothing',
    'wait',
    'move_random',
    'move_center'
]

RESOURCE_IDS = [
    # Bûcheron
    3404, # Frêne
    3405, # Chataignier
    3406, # Noyer
    3407, # Chêne
    3408, # Erable
    3445, # Bombu
    # Mineur
    3426, # Cuivre
    3427, # Bronze
    3428, # Manganèse
    3429 # Kobalte
]

# PLAYER_ID: PLAYER_NAME
ENTITY_PLAYER = {
}

# PLAYER_ID: [MAP_IDS]
PLAYER_MAPS = {
}

# MAP_ID : {
#     'bot': MAP_ID,
#     'top': MAP_ID,
#     'left': MAP_ID,
#     'right': MAP_ID
# }
MAP_PATH = {
}