# FlaskDofusRetro
Dofus Retro Hacks & Helpers

*Based on Flask*  
*Packet sniffing with Scapy*

## Features
* Bank/Inventory Management
* Craft Management
* Market Analysis
* Gathering Bot

## Libz
Python3  
pip install -r requirements.txt

## Env
set FLASK_APP=dr/app.py   
set FLASK_ENV=development  
set FLASK_DEBUG=1  

## Config
Edit Param SQLALCHEMY_DATABASE_URI  
Edit Constants RESOLUTION, PLAYERS, MAP_PLAYER

## Database
Create User  
Grant SELECT, UPDATE, DELETE and INSERT  
Create MySQL database 'dr'

python -m flask db_manager create

## Config
Edit Constants NETWORK_INTERFACE, RESOLUTION, ENTITY_PLAYER, MAP_PLAYER

## Commands
python -m flask cmd_manager load-items  
python -m flask cmd_manager load-barbok-data  
python -m flask cmd_manager load-maps  

python -m flask snf_manager check-coord X  

python -m flask snf_manager start  
python -m flask snf_manager process  