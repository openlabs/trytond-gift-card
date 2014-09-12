# -*- coding: utf-8 -*-
"""
    sale.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import PoolMeta
import copy

__all__ = ['SaleLine']
__metaclass__ = PoolMeta


class SaleLine:
    "SaleLine"
    __name__ = 'sale.line'

    @classmethod
    def __setup__(cls):
        super(SaleLine, cls).__setup__()

        cls.type = copy.copy(cls.type)
        cls.type.selection = copy.copy(cls.type.selection)
        cls.type.selection.append(('gift_card', 'Gift Card'))
