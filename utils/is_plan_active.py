'''
is_plan_active.py
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

def is_plan_active(plan, first_date_str):
    if plan == "fam":
        return  True
    elif plan in ['free']:
        try:
           first_date = datetime.fromisoformat(first_date_str)
           today = datetime.now()
           trial_duration = timedelta(days=7)  # 7 days
           trial_end_date = first_date + trial_duration
           days_left = (trial_end_date - today).days
           trial_status = True if days_left > 0 else False
           return trial_status
        except ValueError:
           return False
    else:
        try:
            first_date = datetime.fromisoformat(first_date_str)
            today = datetime.now()
            trial_duration = timedelta(days=30)   # 30 days
            trial_end_date = first_date + trial_duration
            days_left = (trial_end_date - today).days
            trial_status = True if days_left > 0 else False
            return trial_status
        except ValueError:
            return False