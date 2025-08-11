import logging
import datetime
import json
import ast

import werkzeug.wrappers

_logger = logging.getLogger(__name__)


def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    if isinstance(o, bytes):
        return str(o)


def valid_response(data, status=200,check_json=None):
    """Valid Response
    This will be return when the http request was successfully processed."""
    data = {"count": len(data) if not isinstance(data, str) else 1, "data": data}
    response = werkzeug.wrappers.Response(
        status=status,
        headers=[('Access-Control-Allow-Methods', 'GET,POST,PUT,PATCH,DELETE,OPTIONS'),("Access-Control-Allow-Origin", "*")], 
        content_type="application/json; charset=utf-8", 
        response=json.dumps(data, default=default),
    )
    if check_json:
        return response.response
    return response


def invalid_response(typ,message=None, status=401,check_json = None):
    """Invalid Response
    This will be the return value whenever the server runs into an error
    either from the client or the server."""
    response = werkzeug.wrappers.Response(
        content_type = "application/json; charset=utf-8",
        headers = [('Access-Control-Allow-Methods', 'GET,POST,PUT,PATCH,DELETE,OPTIONS'),("Access-Control-Allow-Origin", "*"
)],
        response = json.dumps(
            {"type": typ, "message": str(message) if str(message) else "wrong arguments (missing validation)",},
            default=datetime.datetime.isoformat,
        ),
    )
    if check_json:
        response.status = str(status)
        return response.response
    response.status = str(status)
    return response

def datefields_extracter(values):
    for obj in values:
        date_filed_dict = {}
        pop_keys = []
        for key,value in obj.items():
            if isinstance(value,(datetime.date,datetime.datetime)):
                date_filed_dict.update({key:value})
                pop_keys.append(key)
        for key in pop_keys:
            obj.pop(key)
        obj.update({'date_fields':date_filed_dict})
    return values