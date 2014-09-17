# -*- coding: utf-8 -*-
"""
    configuration.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.model import ModelView, ModelSQL, ModelSingleton, fields

__all__ = ['Configuration']


class Configuration(ModelSingleton, ModelSQL, ModelView):
    "Configuration"
    __name__ = 'gift_card.configuration'

    liability_account = fields.Property(
        fields.Many2One(
            'account.account', 'Liability Account', required=True,
            domain=[('kind', '=', 'revenue')]
        )
    )
