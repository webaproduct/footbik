import re 
import ast 
import functools 
import logging 
import requests 
import json 
from odoo .exceptions import AccessError 
from odoo import http 
from odoo .addons .looker_connector .common import (invalid_response ,valid_response ,)
from odoo .http import request 
def validate_token (OOOOO000O00OO000O ):
     
    @functools .wraps (OOOOO000O00OO000O )
    def OO0OOOOO000OO0O0O (OO00O0O0OO000O0OO ,*O0OOOO0OOO00OOO0O ,**OO000OOO0OOOO0000 ):
         
        OO00OO0O0O0O0O0O0 =request .env ['ir.config_parameter'].sudo ()
        O0OOOOOOOO0OOOO0O =request .httprequest .headers .get ("authorization")
        if not O0OOOOOOOO0OOOO0O :
            return invalid_response ("access_token_not_found","missing access token in request header",401 ,check_json =request .__dict__ .get ('jsonrequest',None ))
        O000OOOOO0000O000 =(OO00OO0O0O0O0O0O0 .get_param ('looker_connector.looker_access_token'))
        if O000OOOOO0000O000 !=O0OOOOOOOO0OOOO0O or O0OOOOOOOO0OOOO0O =='*'*40 :
            return invalid_response ("access_token","Token seems to have expired or invalid",401 ,check_json =request .__dict__ .get ('jsonrequest',None ))
        return OOOOO000O00OO000O (OO00O0O0OO000O0OO ,*O0OOOO0OOO00OOO0O ,**OO000OOO0OOOO0000 )
    return OO0OOOOO000OO0O0O 
