# -*- coding: utf-8 -*-
"""
    product.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import PoolMeta

__all__ = ['Template']
__metaclass__ = PoolMeta


class Template:
    "Product Template"
    __name__ = 'product.template'

    @classmethod
    def __setup__(cls):
        super(Template, cls).__setup__()

        gift_card = ('gift_card', 'Gift Card')

        if gift_card not in cls.type.selection:
            cls.type.selection.append(gift_card)
