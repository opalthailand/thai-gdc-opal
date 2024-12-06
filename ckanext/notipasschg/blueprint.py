# encoding: utf-8


from flask import Blueprint, request
from flask.views import MethodView
from datetime import datetime
import logging

log = logging.getLogger(__name__)
ext_route = Blueprint('notipasschg', __name__)

class EditView(MethodView):
    def _prepare(self, id):
        """Prepare context for user editing."""
        # Debug: Log ID being prepared
        log.info(f"Preparing context for user ID: {id}")
        if id is None:
            return None, 400  # Debugging response
        return {"user_id": id}, 200

    def post(self, id=None):
        """Handle POST request for editing user."""
        try:
            context, status = self._prepare(id)
            if status != 200:
                return f"Error in context preparation: {status}", status

            # Debug: Log context and request form
            log.info(f"Context prepared: {context}")
            log.info(f"Request data: {request.form}")

            # Simulate processing user data
            log.info(f"Processing data for user ID: {id}")
            return f"User {id} updated successfully", 200

        except Exception as e:
            log.error(f"Error processing request: {e}")
            return "Internal Server Error", 500

    def get(self, id=None):
        """Handle GET request to fetch user details."""
        try:
            context, status = self._prepare(id)
            if status != 200:
                return f"Error in context preparation: {status}", status

            # Simulate fetching user details
            log.info(f"Fetching details for user ID: {id}")
            return f"User details for {id}", 200

        except Exception as e:
            log.error(f"Error fetching user details: {e}")
            return "Internal Server Error", 500


# Add URL rules
_edit_view = EditView.as_view("edit")
ext_route.add_url_rule("/user/edit", view_func=_edit_view, methods=["GET", "POST"])
ext_route.add_url_rule("/user/edit/<id>", view_func=_edit_view, methods=["GET", "POST"])