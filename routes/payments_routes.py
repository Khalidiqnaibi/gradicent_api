'''
billing_routes.py
----------------
Billing routes for payment processing.
'''
from flask import Blueprint, request, current_app, make_response
from ..decorators.req_login import login_required

billing_blueprint = Blueprint("billing", __name__)

@billing_blueprint.route("/create", methods=["POST"])
@login_required
def create_payment():
    '''
    Create a payment checkout session.
    Expects JSON payload with:
    {
        "provider": "paddle" | "paypal",
        "amount": float,
        "return_url": str,
        "cancel_url": str
    }
    outputs:
    {
        "checkout_url": str
    }
    '''
    payload = request.json
    provider = payload.get("provider","paddle")
    amount = float(payload["amount"])
    return_url = payload["return_url"]
    cancel_url = payload["cancel_url"]
    checkout = current_app.config["PAYMENT"].checkout(provider, amount=amount, return_url=return_url, cancel_url=cancel_url)
    return make_response({"checkout_url": checkout["url"]}, "Redirect to checkout")
