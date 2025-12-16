"""
payments_routes.py
-----------------
Flask blueprint for handling payments and subscriptions API routes.

- Controller layer only.
- Delegates all business logic to services.
"""

from flask import Blueprint, request,session
from services.subscription_service import SubscriptionService
from services.payment_service import PaymentService
from payments.stripe_provider import StripePaymentProvider
from services.user_service import UserService
from binder import FirebaseCrudAdapter
from config import STRIPE_API_KEY,PLANS
from utils.make_res import make_response

payments_blueprint = Blueprint("payments", __name__)
adapter = FirebaseCrudAdapter()
stripe_provider = StripePaymentProvider(api_key=STRIPE_API_KEY)
payment_service = PaymentService(stripe_provider)
subscription_service = SubscriptionService(adapter, payment_service)
user_service = UserService(adapter)


@payments_blueprint.route("/subscribe", methods=["POST"])
def subscribe():
    """
    POST /api/payments/subscribe
    Subscribes a user to a plan.
    """
    payload = request.get_json()
    domain = payload.get("domain", session.get("domain", session.get("binder", "business")))
    user_id = payload.get("user_id")
    plan = payload.get("plan")
    payment_data = payload.get("payment_data")

    if not all([user_id, plan, payment_data]):
        return make_response(None, "Missing parameters.", "error")

    result = subscription_service.subscribe_user(domain,user_id, plan, payment_data)
    return make_response({"result":result}, "Subscription processed.")


@payments_blueprint.route("/cancel", methods=["POST"])
def cancel_subscription():
    """
    POST /api/payments/cancel
    Cancels the user's subscription.
    """
    payload = request.get_json()
    domain = payload.get("domain", session.get("domain", session.get("binder", "business")))
    user_id = payload.get("user_id")
    if not user_id:
        return make_response(None, "Missing user_id.", "error")

    subscription_service.cancel_subscription(domain,user_id)
    return make_response(None, "Subscription canceled.")


@payments_blueprint.route("/plans", methods=["GET"])
def get_plans():
    """
    GET /api/payments/plans
    Returns available subscription plans and pricing.
    """
    return make_response({"plans":PLANS}, "Available plans fetched.")
