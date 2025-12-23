'''
get_plan_status.py
----------------
Subscription service module for managing user subscriptions and trial periods.

expects
    plan (str): The subscription plan type. {'free', 'fam', 'pro', 'starter','ultra'}.
    first_date_str (str): The start date of the subscription in ISO format.

outputs
    trial_status (bool): 1 if the trial is active, 0 if expired.
    remaining_days (int): The number of days remaining in the trial period, or 0 if expired.
'''

from datetime import datetime, timedelta

def compute_plan_status(plan, first_date_str):
    if plan == "fam":
        return  True, 0
    elif plan in ['free']:
        try:
           first_date = datetime.fromisoformat(first_date_str)
           today = datetime.now()
           trial_duration = timedelta(days=7)  # 7 days
           trial_end_date = first_date + trial_duration
           days_left = (trial_end_date - today).days
           trial_status = True if days_left > 0 else False
           return trial_status , days_left
        except ValueError:
           return False , 0
    else:
        try:
            first_date = datetime.fromisoformat(first_date_str)
            today = datetime.now()
            trial_duration = timedelta(days=30)   # 30 days
            trial_end_date = first_date + trial_duration
            days_left = (trial_end_date - today).days
            trial_status = True if days_left > 0 else False
            return trial_status, days_left
        except ValueError:
            return False , 0
        
    
def get_plan_data(service):
    data = service._binder.adapter.get_user(service._binder.domain,service._binder.current_user)

    meta =data.get("metadata")
    if meta:
        date = meta.get("plan_started_at")
        if not date:
            user = service._binder.adapter.get_user(service._binder.domain,service._binder.current_user)
            date = user.get("created_at")
        plan = meta.get("plan","free")
    else:
        date = datetime.now().isoformat()
        plan = "free"
    return plan , date