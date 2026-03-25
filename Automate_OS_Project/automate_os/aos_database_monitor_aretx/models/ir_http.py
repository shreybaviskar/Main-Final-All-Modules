# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request
from odoo.exceptions import AccessError
from werkzeug.utils import redirect
import logging
import psycopg2

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _dispatch(cls, endpoint):
        """Override dispatch to check storage limit before processing any request"""

        # Get request path first
        path = request.httprequest.path if hasattr(request, 'httprequest') else ''

        # Skip check for essential static resources and login pages
        SKIP_PATHS = [
            '/web/static/',
            '/web/assets/',
            '/web/image/',
            '/web/content/',
            '/longpolling/',
            '/web/webclient/',
            '/storage/exceeded',
            '/web/login',
            '/web/session/',
            '/web/signup',
            '/web/reset_password',
        ]

        # Allow essential paths
        if any(path.startswith(p) for p in SKIP_PATHS):
            return super(IrHttp, cls)._dispatch(endpoint)

        # Check storage limit
        try:
            if hasattr(request, 'env') and request.env:
                env = request.env

                # Search for monitor record
                monitor = env['database.monitor'].sudo().search(
                    [('name', '=', env.cr.dbname)],
                    limit=1
                )

                # If no monitor exists, skip check
                if not monitor:
                    _logger.info("No storage monitor found - skipping check")
                    return super(IrHttp, cls)._dispatch(endpoint)

                try:
                    limit_exceeded = env['database.monitor'].sudo().is_storage_limit_exceeded()
                except Exception as e:
                    _logger.debug(f"Could not determine storage limit via lightweight check: {e}")
                    limit_exceeded = False

                # Check if limit exceeded
                if monitor.storage_percent >= 100.0:
                    _logger.warning(f"🚫 Storage limit exceeded: {monitor.storage_percent:.2f}%")

                    # Check if user is logged in
                    is_logged_in = hasattr(request, 'session') and request.session.uid

                    if not is_logged_in:
                        # User is not logged in - allow normal flow (will go to login page)
                        _logger.info("ℹ️ User not logged in - allowing normal flow")
                        return super(IrHttp, cls)._dispatch(endpoint)

                    # Check if current user has Super Role - skip redirect for them
                    is_super_role = False
                    try:
                        uid = request.session.uid

                        # Search for "Super Role" group
                        super_role_group = env['res.groups'].sudo().search([
                            ('name', '=', 'Super Role')
                        ], limit=1)

                        if super_role_group:
                            # Check if user is in this group using SQL query to avoid attribute issues
                            env.cr.execute("""
                                           SELECT 1
                                           FROM res_groups_users_rel
                                           WHERE gid = %s
                                             AND uid = %s LIMIT 1
                                           """, (super_role_group.id, uid))

                            if env.cr.fetchone():
                                is_super_role = True
                                user = env['res.users'].sudo().browse(uid)
                                _logger.info(
                                    f"✅ User {user.login if user.exists() else uid} is in Super Role - NO REDIRECT (banner will still show)")
                    except Exception as e:
                        _logger.error(f"Error checking super role: {e}", exc_info=True)

                    # Redirect to storage exceeded page ONLY if user is NOT Super Role
                    if not is_super_role and not path.startswith('/storage/exceeded'):
                        _logger.info(f"🔄 Redirecting to /storage/exceeded")
                        return redirect('/storage/exceeded', code=302)

        except AccessError:
            # Re-raise AccessError to show user
            raise
        except Exception as e:
            # Log other errors but don't block request
            _logger.error(f"Error in storage check: {e}", exc_info=True)
            # Continue with normal request processing

        # Process request normally
        return super(IrHttp, cls)._dispatch(endpoint)