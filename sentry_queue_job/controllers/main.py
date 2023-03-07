from odoo import _
from odoo.exceptions import ValidationError
from odoo.addons.queue_job.controllers.main import RunJobController
try:
    from sentry_sdk.hub import Hub
except ImportError:
    raise ValidationError(_("sentry_sdk not installed, please complete this command: 'pip install sentry-sdk'"))

class SentryRunJobController(RunJobController):

    def _try_perform_job(self, env, job):

        """
        Change to new module
        ====================
        See: https://github.com/OCA/server-tools/pull/2490/files#r1090656357
        ORIGINAL CODE
        -------------
        try:
            from odoo.addons.queue_job.controllers.main import RunJobController

            _ori_try_perform_job = RunJobController._try_perform_job

            def _try_perform_job(self, env, job):
                hub = Hub.current
                with hub.configure_scope() as scope:
                    scope.set_tag("odoo.job.model", job.model_name)
                    scope.set_tag("odoo.job.method", job.method_name)

                return _ori_try_perform_job(self, env, job)

            RunJobController._try_perform_job = _try_perform_job
        except ImportError:
            _logger.debug("Queue Job not install skip instrumentation")
        """
        hub = Hub.current
        with hub.configure_scope() as scope:
            scope.set_tag("odoo.job.model", job.model_name)
            scope.set_tag("odoo.job.method", job.method_name)
            return super()._try_perform_job(env, job)
