# -*- coding: utf-8 -*-
"""
    __init__.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool
from .gift_card import GiftCard
from sale import SaleLine


def register():
    Pool.register(
        GiftCard,
        SaleLine,
        module='gift_card', type_='model'
    )
