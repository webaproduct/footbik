# -*- coding: utf-8 -*-
import json
import logging
import datetime
import sys
import re

from odoo import http
from odoo.http import request, Response
from odoo.tools import date_utils
from odoo.addons.looker_connector.controllers.validate_token import validate_token
from math import ceil
from itertools import groupby


# SAFE SQL composition for identifiers (table names)
from psycopg2 import sql

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<\s*(p|br)\b", re.IGNORECASE)


class LookerConnector(http.Controller):

    @validate_token
    @http.route(
        ['/looker/connector/<string:model>', '/looker/connector/<string:model>/'],
        type='http', auth="none", methods=['GET', 'OPTIONS'],
        website=True, csrf=False, cors='*'
    )
    def get_model_data(self, model, **kwargs):

        logger.info(f'Getting data of {model}')
        status_code = 200
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')

        try:
            model_obj = request.env[model]
            table_name = model_obj._table
        except Exception as e:
            logger.error(f"Invalid model '{model}': {e}")
            return Response(
                json.dumps({'error': f"Unknown model '{model}'"}, default=date_utils.json_default),
                content_type='application/json', status=404
            )

        # ---- pagination params (clamped) ----
        try:
            count = int(kwargs.get('count', 18500))
        except Exception:
            count = 18500
        try:
            current = int(kwargs.get('current', 1))
        except Exception:
            current = 1

        # hard clamps to avoid runaway payloads but preserves variable names/schema
        if count < 1:
            count = 1
        if count > 100000:
            count = 100000
        if current < 1:
            current = 1

        # ---- get exact size (COUNT(*)) using safe SQL ----
        try:
            request.env.cr.execute(
                sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table_name))
            )
            model_size = int(request.env.cr.fetchone()[0] or 0)
        except Exception as e:
            logger.error(f"Counting rows for {table_name} failed: {e}")
            return Response(
                json.dumps({'error': str(e)}, default=date_utils.json_default),
                content_type='application/json', status=500
            )

        response_data = {
            "size": model_size,
            "count": count,
            "prev": None,
            "current": current,
            "next": None,
            "total_pages": None,
            "data": [],

        }

        # ---- total pages & nav urls ----
        response_data['total_pages'] = ceil(model_size / response_data['count']) if response_data['count'] else 0

        if response_data['total_pages'] and response_data['current'] > response_data['total_pages']:
            # clamp current to last page if caller overshoots
            response_data['current'] = response_data['total_pages']

        if response_data['total_pages'] > 0 and response_data['current'] < response_data['total_pages']:
            response_data['next'] = (
                f"{base_url}/looker/connector/{model}?current={response_data['current'] + 1}"
            )
        if response_data['current'] > 1:
            response_data['prev'] = (
                f"{base_url}/looker/connector/{model}?current={response_data['current'] - 1}"
            )

        if not response_data.get('prev'):
            response_data.pop('prev')
        if not response_data.get('next'):
            response_data.pop('next')

        offset = (response_data['current'] - 1) * response_data['count'] if response_data['current'] > 0 else 0

        # ---- data page (safe SQL, stable ordering on PK 'id') ----
        try:
            with request.env.cr.savepoint():
                query = sql.SQL("""
                    SELECT * FROM {} ORDER BY id LIMIT %s OFFSET %s
                """).format(sql.Identifier(table_name))
                request.env.cr.execute(query, (response_data['count'], offset))
                result = request.env.cr.dictfetchall()

                # tight in-place normalization: dict -> first value, date formatting same as before
                for row in result:
                    for key, value in list(row.items()):
                        if isinstance(value, dict):
                            # preserve prior behavior: take first dict value
                            try:
                                row[key] = next(iter(value.values()))
                            except Exception:
                                row[key] = None
                            continue

                        if isinstance(value, datetime.datetime):
                            row[key] = value.strftime("%Y%m%d%H%M%S")
                        elif isinstance(value, datetime.date):
                            row[key] = value.strftime("%Y%m%d")

                response_data['data'] = result

        except Exception as e:
            logger.error(f"Fetching data for {table_name} failed: {e}")
            response_data['data'] = []
            status_code = 200  # preserve prior behavior

        # ---- size guard / HTML tag nullification (optimized) ----
        data = self.size_data(response_data)
        page=data['current']
        logger.info(f'Looker data transfer for {model} page- {page}')

        return Response(
            json.dumps(data, default=date_utils.json_default, separators=(',', ':')),
            content_type='application/json', status=status_code
        )

    def size_data(self, response):
        """
        Keeps exact same outward behavior (nullify HTML-ish fields, then nullify columns >10MB).
        Optimizations:
        - One pass to clean + accumulate sizes (reduces regex calls dramatically)
        - Uses logger instead of prints
        - Returns original response on error (never 'null' body)
        """
        try:
            data = response
            rows = data.get("data") or []
            if not isinstance(rows, list):
                logger.warning("Expected 'data' to be a list of dictionaries.")
                return data

            column_sizes = {}

            # pass 1: clean HTML-like values and accumulate approximate sizes
            for row in rows:
                for key, value in list(row.items()):
                    if isinstance(value, str):
                        # quick guard before regex
                        if '<' in value and _TAG_RE.search(value):
                            row[key] = None
                            value = None
                    # keep same sizing approach (sys.getsizeof) to preserve the logic
                    column_sizes[key] = column_sizes.get(key, 0) + sys.getsizeof(value)

            # columns over 10MB -> nullify
            TOO_BIG = 10 * 1024 * 1024
            large_columns = [col for col, sz in column_sizes.items() if sz > TOO_BIG]

            if large_columns:
                logger.info("Columns >10MB will be nullified: %s", ", ".join(large_columns))
                for row in rows:
                    for col in large_columns:
                        if col in row:
                            row[col] = None

            return data

        except Exception as e:
            logger.error(f"size_data failed: {e}")
            # Never break the schema; return the original payload
            return response

    @validate_token
    @http.route('/looker/schemas/', type='http', auth="none", methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def get_schema(self, **kwargs):
        logger.info('Getting database tables with their schema')
        schema_dict = {}
        try:
            with request.env.cr.savepoint():
                query = '''
                       SELECT
                           column_name, data_type AS column_type, table_name
                       FROM
                           information_schema.columns
                       WHERE
                           table_schema = 'public'
                       ORDER BY table_name
                   '''
                request.env.cr.execute(query)
                result = request.env.cr.dictfetchall()
                for table_name, columns in groupby(result, lambda x: x['table_name']):
                    columns_list = list(columns)
                    schema_dict[table_name.replace('_', '.')] = [
                        {"column_name": col["column_name"], "column_type": col["column_type"]} for col in columns_list
                    ]
        except Exception as e:
            logger.error(str(e))
            return Response(json.dumps({'error': str(e)}, default=date_utils.json_default),
                            content_type='application/json', status=500)

        logger.info('Schema collection done')
        return Response(json.dumps(schema_dict, default=date_utils.json_default),
                        content_type='application/json', status=200)

    @validate_token
    @http.route('/looker/tablenames/', type='http', auth="none", methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def get_model_names(self, **kwargs):
        logger.info('Getting database tables')
        table_names = []
        try:
            with request.env.cr.savepoint():
                query = '''
                       SELECT
                           relname AS table
                       FROM
                           pg_stat_user_tables
                       ORDER BY relname
                   '''
                request.env.cr.execute(query)
                result = request.env.cr.dictfetchall()
                for row in result:
                    table_names.append(row['table'].replace('_', '.'))
        except Exception as e:
            logger.error(str(e))
            return Response(json.dumps({'error': str(e)}, default=date_utils.json_default),
                            content_type='application/json', status=500)

        logger.info('Tables collection done')
        return Response(json.dumps(table_names, default=date_utils.json_default),
                        content_type='application/json', status=200)