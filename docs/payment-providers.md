# Payment provider integration

Premium access is managed by `Subscription`, independently of any payment provider. An active subscription grants access until `expires_at`; cancellation changes its status to `canceled` but does not end the existing access period. There is no automatic renewal.

`PaymentProvider` defines the provider-neutral `create_checkout(subscription)` and `handle_webhook(request)` operations. A future Payme or Click adapter can implement this interface and be selected through server-side configuration. Adapters must validate provider signatures, amount, currency, subscription reference, and event idempotency before activating or extending a subscription.

For now, `POST /api/payments/checkout/` and `POST /api/payments/<provider>/webhook/` are deliberate HTTP 501 stubs. They do not create payment requests or change subscriptions. Administrators can create or extend subscriptions in Django admin.

Before enabling a provider, add an auditable payment transaction model, verify callbacks using provider-specific cryptographic rules, make webhook processing idempotent, and test duplicate, invalid, delayed, and out-of-order events. Do not trust client-submitted payment confirmations.
