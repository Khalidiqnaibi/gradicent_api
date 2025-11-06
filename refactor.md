- services
- auth
- authirization 
- controllers 


files:
``` ts
gradicent-api/
├── app.py                       # bootstrap + blueprint registration
├── config.py                    # configuration (secrets, env)
├── requirements.txt
├── binder/
│   ├── __init__.py
│   ├── adapters/
│   │   ├── storage_adapter.py        # StorageAdapter interface
│   │   ├── firebase_crud_adapter.py
│   │   └── inmemory_adapter.py
│   ├── models/
│   │   └── models.py
│   ├── services/
│   │   ├── user_service.py
│   │   ├── client_service.py
│   │   └── subscription_service.py
│   └── binder_business.py
│
├── gaia/
│   └── (existing engine + metrics)
│
├── core/
│   ├── auth/
│   │   ├── auth_service.py           # AuthService (Google OAuth, session)
│   │   └── oauth_blueprint.py
│   ├── payments/
│   │   ├── payment_provider.py       # Payment provider interface + factory
│   │   ├── paypal_provider.py
│   │   ├── paddle_provider.py
│   │   └── stripe_provider.py
│   ├── utils/
│   │   ├── crypto.py                 # create_fernet, encrypt, decrypt
│   │   └── timeutils.py              # parse/format helpers
│   └── controllers/
│       ├── binder_controller.py
│       └── gaia_controller.py
│
├── routes/
│   ├── binder_routes.py
│   ├── gaia_routes.py
│   ├── payments_routes.py
│   └── web_routes.py                 # html template rendering routes
│
├── templates/
│   └── base.html, index.html, plans.html, ...
└── tests/
    ├── test_auth.py
    └── test_payment_provider.py
```