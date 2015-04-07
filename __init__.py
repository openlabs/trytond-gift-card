# -*- coding: utf-8 -*-
"""
    __init__.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool
from gift_card import (
    GiftCard, GiftCardReport, GiftCardRedeemStart, GiftCardRedeemDone,
    GiftCardRedeemWizard
)
from sale import SaleLine, Sale, AddSalePaymentView, Payment, AddSalePayment
from configuration import Configuration, SaleConfiguration
from gateway import PaymentGateway, PaymentTransaction
from product import Product, GiftCardPrice


def register():
    Pool.register(
        Configuration,
        GiftCard,
        GiftCardPrice,
        GiftCardRedeemStart,
        GiftCardRedeemDone,
        SaleConfiguration,
        SaleLine,
        Sale,
        AddSalePaymentView,
        Payment,
        PaymentGateway,
        PaymentTransaction,
        Product,
        module='gift_card', type_='model'
    )
    Pool.register(
        GiftCardReport,
        module='gift_card', type_='report'
    )
    Pool.register(
        GiftCardRedeemWizard,
        AddSalePayment,
        module='gift_card', type_='wizard'
    )
