# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class StorageExceededController(http.Controller):

    @http.route('/storage/exceeded', type='http', auth='none', csrf=False)
    def storage_exceeded_page(self, **kwargs):
        """
        Storage Exceeded Page
        Simple standalone page showing storage exceeded message
        """
        # Check if user has Super Role - if yes, redirect to normal Odoo
        try:
            if hasattr(request, 'env') and request.env and request.env.user:
                user = request.env.user

                # Skip for public users
                if not user._is_public():
                    # Check all groups - if user is in "Super Role" group, redirect to /web
                    for group in user.groups_id:
                        group_name = (group.name or '').strip()
                        # Exact match for "Super Role" group
                        if group_name.lower() == 'Role / Administrator':
                            _logger.info(f"✅ User {user.login} is in Super Role group - redirecting to /web")
                            return request.redirect('/web', code=302)

        except Exception as e:
            _logger.debug(f"Could not check user role in controller: {e}")

        html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Storage Exceeded</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        html, body {
            height: 100%;
            width: 100%;
            overflow: hidden;
        }
        .storage-wrapper {
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            font-family: 'Inter', sans-serif;
        }

        .storage-card {
            background: #ffffff;
            padding: 40px;
            border-radius: 16px;
            max-width: 480px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
            animation: fadeIn 0.6s ease-in-out;
        }

        .storage-card h1 {
            font-size: 24px;
            margin-bottom: 12px;
            color: #d32f2f;
        }

        .storage-card p {
            font-size: 15px;
            color: #555;
            margin-bottom: 30px;
            line-height: 1.6;
        }

        .support-btn {
            display: inline-block;
            padding: 14px 28px;
            background: linear-gradient(135deg, #1976d2, #42a5f5);
            color: #fff;
            text-decoration: none;
            font-weight: 600;
            border-radius: 30px;
            transition: all 0.3s ease;
        }

        .support-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(25, 118, 210, 0.4);
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(15px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    </style>
</head>
<body>
   <div class="storage-wrapper">
    <div class="storage-card">
        <h1>Storage Limit Reached 🚫</h1>
        <p>
            You've exceeded your allocated storage space.  
            To continue uninterrupted service, please contact our support team to upgrade your plan.
        </p>

        <a href="https://www.areterix.com/contactus" 
           target="_blank" 
           class="support-btn">
            Contact Support
        </a>
    </div>
</div>

</body>
</html>"""

        return request.make_response(
            html_content,
            headers=[('Content-Type', 'text/html; charset=utf-8')]
        )