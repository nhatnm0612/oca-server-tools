# Copyright 2022 Akretion (https://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


# Monkey patch odoo method in order to track all database


import logging

import psycopg2

import odoo.http
from odoo.sql_db import Cursor

# from odoo.addons.base.models.ir_cron import ir_cron
from odoo import api, models

_logger = logging.getLogger(__name__)
HAS_SENTRY_SDK = True

try:
    from sentry_sdk import start_transaction
    from sentry_sdk.hub import Hub
    from sentry_sdk.tracing_utils import record_sql_queries
except ImportError:
    HAS_SENTRY_SDK = False
    _logger.debug(
        "Cannot import 'sentry-sdk'.\
                        Please make sure it is installed."
    )


if HAS_SENTRY_SDK:

    _ori_execute = Cursor.execute

    def execute(self, query, params=None, log_exceptions=None):
        with record_sql_queries(
            Hub.current, self, query, params, psycopg2.paramstyle, executemany=False
        ):
            return _ori_execute(
                self, query, params=params, log_exceptions=log_exceptions
            )

    Cursor.execute = execute


    class IrCron(models.Model):
        _inherit = "ir.cron"

        @api.model
        def _callback(self, cron_name, server_action_id, job_id):
            """
            Odooic patching method
            ======================
            ORIGINAL FUNCTION
            -----------------
            _ori_process_job = ir_cron._process_job

            @classmethod
            def _process_job(cls, db, cron_cr, job):
                with start_transaction(
                    op="cron", name=f"Cron {job['cron_name']}".replace(" ", "_")
                ) as transaction:
                    transaction.set_tag("odoo.db", db.dbname)
                    return _ori_process_job(db, cron_cr, job)

            ir_cron._process_job = _process_job
            
            ORIGINAL ERROR
            --------------
            [UTC_TIME] WARNING [DB_NAME] odoo.addons.base.models.ir_cron: Exception in cron: 
            Traceback (most recent call last):
            File ".../odoo/odoo/addons/base/models/ir_cron.py", line 115, in _process_jobs
                registry[cls._name]._process_job(db, cron_cr, job)
            File ".../server-tools/sentry/patch.py", line 74, in _process_job
                return _ori_process_job(db, cron_cr, job)
            File ".../odoo/odoo/addons/base/models/ir_cron.py", line 291, in _process_job
                with cls.pool.cursor() as job_cr:
            AttributeError: type object 'ir_cron' has no attribute 'pool'
            """
            with start_transaction(op="cron", name=cron_name.replace(" ", "_")) as transaction:
                transaction.set_tag("odoo.db", self.env.cr.dbname)
                return super()._callback(cron_name, server_action_id, job_id)

    class SentryRoot(odoo.http.Root):

        def get_request(self, httprequest):
            '''
            Odooic patching method
            ======================
            ORIGINAL FUNCTION
            -----------------
            _ori_get_request = odoo.http.Root.get_request

            def get_request(self, httprequest):
                request = _ori_get_request(self, httprequest)
                hub = Hub.current
                with hub.configure_scope() as scope:
                    # Extract some params of the request to give a better name
                    # to the transaction and also add tag to improve filtering
                    # experience on sentry
                    scope.set_transaction_name(httprequest.environ.get("PATH_INFO"))
                    scope.set_user({"id": httprequest.session.get("uid")})
                    for key in ["model", "method"]:
                        if key in request.params:
                            scope.set_tag(f"odoo.{key}", request.params[key])
                    scope.set_tag("odoo.db", request.db)
                return request

            odoo.http.Root.get_request = get_request

            ORIGINAL ERROR
            --------------
            [UTC_TIME] ERROR [DB_NAME] werkzeug: Error on request:
            Traceback (most recent call last):
            File ".../.venv/lib/python3.9/site-packages/werkzeug/serving.py", line 306, in run_wsgi
                execute(self.server.app)
            File ".../.venv/lib/python3.9/site-packages/werkzeug/serving.py", line 294, in execute
                application_iter = app(environ, start_response)
            File ".../odoo/custom/src/odoo/odoo/service/server.py", line 482, in app
                return self.app(e, s)
            File ".../odoo/custom/src/odoo/odoo/service/wsgi_server.py", line 112, in application
                return application_unproxied(environ, start_response)
            File ".../odoo/custom/src/odoo/odoo/service/wsgi_server.py", line 87, in application_unproxied
                result = odoo.http.root(environ, start_response)
            File ".../odoo/custom/src/odoo/odoo/http.py", line 1341, in __call__
                return self.dispatch(environ, start_response)
            File ".../odoo/custom/src/odoo/odoo/http.py", line 1307, in __call__
                return self.app(environ, start_wrapped)
            File ".../.venv/lib/python3.9/site-packages/werkzeug/middleware/shared_data.py", line 220, in __call__
                return self.app(environ, start_response)
            File ".../odoo/custom/src/odoo/odoo/http.py", line 1496, in dispatch
                request = self.get_request(httprequest)
            File ".../odoo/custom/src/server-tools/sentry/patch.py", line 39, in get_request
                request = _ori_get_request(self, httprequest)
            File ".../odoo/custom/src/rest-framework/base_rest/http.py", line 234, in get_request
                return ori_get_request(self, httprequest)
            File ".../odoo/custom/src/server-tools/sentry/patch.py", line 39, in get_request
                request = _ori_get_request(self, httprequest)
            File ".../odoo/custom/src/rest-framework/base_rest/http.py", line 230, in get_request
                """ :class:`~collections.abc.Mapping` of context values for the current request """
            NameError: name '_rest_services_routes' is not defined - - -
            '''
            request = super().get_request(httprequest)
            hub = Hub.current
            with hub.configure_scope() as scope:
                scope.set_transaction_name(httprequest.environ.get("PATH_INFO"))
                scope.set_user({"id": httprequest.session.get("uid")})
                for key in ["model", "method"]:
                    if key in request.params:
                        scope.set_tag(f"odoo.{key}", request.params[key])
                scope.set_tag("odoo.db", request.db)
                return request

    # See: https://github.com/odoo/odoo/blob/e90fce6495c0cd2bef22938d5ff31d8846b84452/addons/hw_drivers/http.py#L22
    # patching method using re-set pointer to methods and functions like this can only use once.
    # because it not calling super, every other part except the pointer is not returned
    # E.g:
    # file_1.py
    # import requests
    # def func_1():
    #     return requests.post(...)
    #
    # file_2.py
    # import file_1
    # pointer = file_1.func_1
    # def func_2():
    #     print(...)
    #     return pointer
    # file_1.func_1 = func_2
    #
    # On this code above, since requests is imported outside of scope for func_1, return
    # pointer here will raise NameError, because requests is not defined in file_2.py scope
    # this is how aggressive patching error was raised.

    odoo.http.Root = SentryRoot
    odoo.http.root = SentryRoot()
