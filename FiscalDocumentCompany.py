# -*- encoding: utf-8 -*-

import netsvc
import pooler, tools
import math
from tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time


from osv import fields, osv

class res_company(osv.osv):
    _inherit = 'res.company'
    _columns={
              'civa_spe_inc':fields.many2one('account.tax', 'Codice Iva Spese Incasso', readonly=False),
              'civa_spe_imb':fields.many2one('account.tax', 'Codice Iva Spese Imballo', readonly=False),
              'civa_spe_tra':fields.many2one('account.tax', 'Codice Iva Spese Trasporto', readonly=False),
              'civa_bolli':fields.many2one('account.tax', 'Codice Iva Bolli', readonly=False),

              'civa_fc':fields.many2one('account.tax', 'Codice Iva Fuori Campo Iva', readonly=False),
              'caudoc_evao':fields.many2one('fiscaldoc.causalidoc', 'Tipo Documento Default Evasione Ordini'),
              'civa_product_sale':fields.many2one('account.tax', 'Codice Iva Vendite Articoli', readonly=False),
              'civa_product_purchase':fields.many2one('account.tax', 'Codice Iva Acquisti Articolo', readonly=False),
              'art_des_ddt':fields.many2one('product.product','Articolo per descrizione DDT',readonly=False),
              'art_des_ord':fields.many2one('product.product','Articolo per descrizione Ordini/Conferme',readonly=False),
              'flag_no_neg':fields.boolean('No Negativi',help="Se attivo le Giacenze Articoli sui documenti non potranno andare a negativo  "),
               }

res_company()
