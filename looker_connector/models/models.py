# -*- coding: utf-8 -*-
import hashlib 
import logging 
import os 
import requests 
from odoo import models ,fields ,api ,_ 
from ast import literal_eval 
from odoo .exceptions import ValidationError 
class LookerWebConnectorSetting (models .TransientModel ):
      
    _inherit ='res.config.settings'
    def _get_looker_url (O00O00O0OOOOOOOO0 ):
        OO0O0O0OO00O000O0 =O00O00O0OOOOOOOO0 .env ['ir.config_parameter'].sudo ().get_param ('web.base.url')
        O00O00O0OOOOOOOO0 .env ['ir.config_parameter'].set_param ('looker_connector.looker_url',OO0O0O0OO00O000O0 )
        return OO0O0O0OO00O000O0 
    looker_url =fields .Char (string ='Connector Url',default =_get_looker_url ,readonly =True )
    looker_access_token =fields .Char (string ='Access Token',default =(' '*40 ))
    def set_values (OOO0O00OO00OOO0O0 ):
        O0OOO0OOOOO0000OO =super (LookerWebConnectorSetting ,OOO0O00OO00OOO0O0 ).set_values ()
        OOO0O00OO00OOO0O0 .env ['ir.config_parameter'].set_param ('looker_connector.looker_url',OOO0O00OO00OOO0O0 .looker_url )
        OOO0O00OO00OOO0O0 .env ['ir.config_parameter'].set_param ('looker_connector.looker_access_token',OOO0O00OO00OOO0O0 .looker_access_token )
        return O0OOO0OOOOO0000OO 
    @api .model 
    def get_values (O00O0O00OOO00OO0O ):
        O00O00O000OO0OO0O =super (LookerWebConnectorSetting ,O00O0O00OOO00OO0O ).get_values ()
        OO00O00O00O0O00OO =O00O0O00OOO00OO0O .env ['ir.config_parameter'].sudo ()
        OO000OOO0OOO0OO0O =OO00O00O00O0O00OO .get_param ('looker_connector.looker_access_token')
        OO0O0O0O00O00O000 =OO00O00O00O0O00OO .get_param ('looker_connector.looker_url')
        O00O00O000OO0OO0O .update (looker_access_token =OO000OOO0OOO0OO0O ,looker_url =OO0O0O0O00O00O000 ,)
        return O00O00O000OO0OO0O 
    def nonce (O00000000OOO0O0OO ,length =40 ,prefix =  ""):
        O00O00O000O00OOOO =os .urandom (length )
        return "{}_{}".format (prefix ,str (hashlib .sha1 (O00O00O000O00OOOO ).hexdigest ()))
    def looker_generate_token (OO000OO00O0OOOO00 ):
        OOOO00O000OOO00O0 =OO000OO00O0OOOO00 .env ['ir.config_parameter'].sudo ()
        OO000OO00O0OOOO00 .env ['ir.config_parameter'].set_param ('looker_connector.looker_access_token',OO000OO00O0OOOO00 .nonce ())
class TestCase (models .Model ):
      
    _name ='test.case'
    _description ='dummy table for testing pagination data related to non-primary key tables '
    num1 =fields .Integer (primary_key =True )
