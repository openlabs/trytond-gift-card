# -*- coding: utf-8 -*-
"""
    __init__.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool
from .gift_card import GiftCard, GiftCardSaleLine, GiftCardReport
from sale import SaleLine, Sale
from configuration import Configuration
from invoice import Invoice, InvoiceLine
from gateway import PaymentGateway, PaymentTransaction


def register():
    Pool.register(
        Configuration,
        GiftCard,
        GiftCardSaleLine,
        SaleLine,
        Sale,
        Invoice,
        InvoiceLine,
        PaymentGateway,
        PaymentTransaction,
        module='gift_card', type_='model'
    )
    Pool.register(
        GiftCardReport,
        module='gift_card', type_='report'
    )
