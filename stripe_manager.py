import os
import stripe
from dotenv import load_dotenv

load_dotenv('.env.local')
if not os.getenv('STRIPE_SECRET_KEY'):
    load_dotenv('.env')

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def create_checkout_session(price_id, success_url, cancel_url, quantity=1):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': quantity,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session
    except Exception as e:
        print(f"Stripe error: {e}")
        return None

def create_payment_intent(amount, currency='usd', metadata=None):
    """
    Create a Stripe PaymentIntent.
    :param amount: Amount in the smallest currency unit (e.g., cents)
    :param currency: Currency code (default: 'usd')
    :param metadata: Optional dict of metadata
    :return: PaymentIntent object or None
    """
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            metadata=metadata or {}
        )
        return payment_intent
    except Exception as e:
        print(f"Stripe error: {e}")
        return None
