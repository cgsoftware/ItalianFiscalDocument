# -*- encoding: utf-8 -*-

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import decimal_precision as dp
import time
import netsvc
import pooler, tools
import math
from tools.translate import _

from osv import fields, osv
import logging
    
logger = netsvc.Logger()


def doc_id_create(self, cr, uid, tipo_doc, data_doc, progr, numdoc):
    # import pdb;pdb.set_trace()
    name_tipo = self.pool.get('fiscaldoc.causalidoc').read(cr, uid, [tipo_doc], ["name"])
    anno = data_doc[0:4]
    name_progr = self.pool.get('fiscaldoc.tipoprogressivi').read(cr, uid, [progr], ["name"])
    return name_tipo[0]['name'] + "-" + anno + "-" + name_progr[0]['name'] + "-" + '%%0%sd' % 8 % numdoc

def doc_prog_create(self, cr, uid, tipo_doc, data_doc, progr, numdoc):
    # import pdb;pdb.set_trace()
    name_tipo = self.pool.get('fiscaldoc.causalidoc').read(cr, uid, [tipo_doc], ["name"])
    anno = data_doc[0:4]
    name_progr = self.pool.get('fiscaldoc.tipoprogressivi').read(cr, uid, [progr], ["name"])
    return  anno + "-" + name_progr[0]['name'] + "-" + '%%0%sd' % 8 % numdoc


def arrot(cr,uid,valore,decimali):
    #import pdb;pdb.set_trace()
    return round(valore,decimali(cr)[1])

class FiscalDocHeader(osv.osv):
   _name = "fiscaldoc.header"
   _description = "Testata Documenti"


   def _totgen_doc(self, cr, uid, ids, field_name, arg, context=None):
     #  PER CALCOLARE QUESTI DATI DEVE PRIMA ACCERTARSI CHE IL CASSTELLETTO IVA SIA CORRETTO
     #import pdb;pdb.set_trace()

     ok= self.pool.get('fiscaldoc.righe').calcola_netto_merce(cr, uid, ids, context)
     res_iva = self.pool.get('fiscaldoc.iva').agg_righe_iva(cr, uid, ids, context)
     cur_obj = self.pool.get('res.currency')
     #import pdb;pdb.set_trace()
     res = {}
     if len(ids) == 1:
         for document in self.browse(cr, uid, ids, context=context):
             #lines = self.pool.get('fiscaldoc.iva').search(cr, uid, [('name', '=', ids)])
             res[document.id] = {'totale_documento': 0.0,
                                 'totale_imposta':0.0,
                                 'totale_imponibile':0.0,
                                 }
             imponibile = imposta = 0.0

             # Calcola il totale merce
             res[document.id] = {'totale_merce':0.0, 'totale_netto_merce':0.0, }
             valore = 0
             cur = False
             tot_merce = 0
             tot_netto = 0
             if document.righe_articoli:
              for riga in document.righe_articoli:
                 #import pdb;pdb.set_trace()
                 tot_merce += riga.totale_riga
                 if riga.name.sconto_partner or riga.name.sconto_pagamento:
                    netto = riga.totale_riga
                    if riga.name.sconto_partner:
                        netto = netto-(netto*riga.name.sconto_partner/100)
                        netto = arrot(cr,uid,netto,dp.get_precision('Account'))
                    if riga.name.sconto_pagamento:
                        netto = netto-(netto*riga.name.sconto_pagamento/100)
                        netto = arrot(cr,uid,netto,dp.get_precision('Account'))
                    tot_netto += netto
                 else:
                    netto = riga.totale_riga
                    tot_netto += netto


              cur = document.listino_id.currency_id

              res[document.id]['totale_merce'] = cur_obj.round(cr, uid, cur, tot_merce)
              res[document.id]['totale_netto_merce'] = cur_obj.round(cr, uid, cur, tot_netto)

             # calcola il totale imposta e totali documento
              for riga_iva in document.righe_totali_iva:
             #self.pool.get('fiscaldoc.iva').browse(cr, uid, lines, context=context):
                 imponibile += riga_iva.imponibile
                 imposta += riga_iva.imposta
              cur = document.listino_id.currency_id
              res[document.id]['totale_documento'] = cur_obj.round(cr, uid, cur, imposta) + cur_obj.round(cr, uid, cur, imponibile)
              res[document.id]['totale_imponibile'] = cur_obj.round(cr, uid, cur, imponibile)
              res[document.id]['totale_imposta'] = cur_obj.round(cr, uid, cur, imposta)
              #import pdb;pdb.set_trace()
              #CALCOLO DEL TOTALE DA PAGARE - IMPORTANTE PER LA GESTIONE DEL FLAG OMAGGIO
              # 24/02/2012 DA RIVEDERE XCHE' SE C'È LO SCONTO IN TESTATA SBAGLIA TUTTO
             # if res[document.id]['totale_merce'] <> res[document.id]['totale_imponibile']:
             #    dif = res[document.id]['totale_merce'] - res[document.id]['totale_imponibile']
             #     res[document.id]['totale_pagare'] = res[document.id]['totale_documento'] + dif
             # else:
             #     res[document.id]['totale_pagare'] = res[document.id]['totale_documento']
              res[document.id]['totale_pagare'] = res[document.id]['totale_documento']+document.totale_abbuoni-document.totale_acconti
         #
     return res


   _columns = {
             'data_documento': fields.date('Data Documento', required=True, readonly=False),
             'tipo_doc':fields.many2one('fiscaldoc.causalidoc', 'Tipo', required=True,),
             'progr':fields.many2one('fiscaldoc.tipoprogressivi', 'Progressivo', required=True,),
             'numdoc':fields.integer('Numero ', required=True),
             'name':fields.char('Codice Documento', size=30, required=True),
             'doc_prog':fields.char('Codice progressivo Annuale', size=30, required=True),
             'magazzino_id':fields.many2one('stock.location', 'Magazzino', required=True),
             'company_id': fields.many2one('res.company', 'Company', ),
             'magazzino_destinazione_id':fields.many2one('stock.location', 'Altro Magazzino',required=True),
             'partner_id': fields.many2one('res.partner', 'Cliente', select=True, required=True),
             'partner_indfat_id': fields.many2one('res.partner.address', 'Indirizzo di Fattura'),
             'partner_indcons_id': fields.many2one('res.partner.address', 'indirizzo di Consegna'),
             'comment': fields.text('Note Partner'),
             'listino_id': fields.many2one('product.pricelist', 'Pricelist', required=True, help="Pricelist for current sales order."),
             'pagamento_id':fields.many2one('account.payment.term', 'Pagamento', required=True, help="Pricelist for current sales order."),
             'sconto_pagamento':fields.float('Sconto Pagamento', digits=(9, 3)),
             'str_sconto_partner':fields.char('Sconto', size=20),
             'sconto_partner':fields.float('Sconto Partner', digits=(9, 3)),
             'banca_patner':fields.many2one('res.bank', 'Banca ', required=False, help="Banca del partner "),
             'banca_azienda':fields.many2one('res.bank', 'Banca ', required=False, help="Banca del Azienda "),
             'valuta':fields.many2one('res.currency', 'Valuta ', required=False, help="Valuta del Documento "),
             'agente':fields.many2one('res.users', 'Salesman', help='The internal user that is in charge of communicating with this partner if any.'),
             'spedizione':fields.many2one('fiscaldoc.spedizioni', 'Modalità di Consegna/Spedizione ', required=False, help="Consegna "),
             'vettore':fields.many2one('delivery.carrier', 'Vettore ', required=False, help="Vettore "),
             'porto_id': fields.many2one('stock.picking.carriage_condition', 'Carriage condition'),
             'aspetto_esteriore_id': fields.many2one('stock.picking.goods_description', 'Description of goods'),
             'causale_del_trasporto_id': fields.many2one('stock.picking.transportation_reason', 'Reason for transportation'),
             'totale_colli':fields.integer('Numero Colli Totale'),
             'totale_peso':fields.float('Totale Peso Merce', digits=(12, 3)),
             'data_trasporto':fields.date('Data Inizio Trasporto', required=False, readonly=False),
             'ora_trasporto':fields.datetime('Data Inizio Trasporto', required=False, readonly=False),
             'note_di_trasporto': fields.text('Note di Trasporto'),
             'righe_articoli': fields.one2many('fiscaldoc.righe', 'name', 'Righe Articoli', required=True),
             'righe_scadenze':fields.one2many('fiscaldoc.scadenze', 'name', 'Scadenze'),
             'righe_totali_iva':fields.one2many('fiscaldoc.iva', 'name', 'Castelletto Iva', readonly=True),
             'spese_incasso':fields.float('Spese Incasso', digits_compute=dp.get_precision('Account')),
             'spese_imballo':fields.float('Spese Imballo', digits_compute=dp.get_precision('Account')),
             'spese_trasporto':fields.float('Spese Trasporto', digits_compute=dp.get_precision('Account')),
             'totale_merce':fields.function(_totgen_doc, method=True, digits_compute=dp.get_precision('Account'), string='Totale Merce', store=True, help="Totale Merce", multi='sums'),
             'totale_netto_merce':fields.function(_totgen_doc, method=True, digits_compute=dp.get_precision('Account'), string='Totale Netto Merce', store=True, help="Totale Merce", multi='sums'),
             'totale_imponibile':fields.function(_totgen_doc, method=True, digits_compute=dp.get_precision('Account'), string='Totale Imponibile', store=True, multi='sums'),
             'totale_imposta':fields.function(_totgen_doc, method=True, digits_compute=dp.get_precision('Account'), string='Totale Imposta', store=True, multi='sums'),
             'totale_bolli':fields.float('Bolli', digits=(12, 2)),
             'totale_acconti':fields.float('Totale Acconti', digits=(12, 2)),
             'totale_abbuoni':fields.float('Abbuoni', digits=(12, 2)),
             'totale_documento':fields.function(_totgen_doc, method=True, digits_compute=dp.get_precision('Account'), string='Totale Documento', store=True, multi='sums'),
             'picking_ids': fields.many2one('stock.picking', 'Ordine di Prelievo', readonly=True, help="Lista di Prelievo merce"),
             'differita_id':fields.many2one('fiscaldoc.header', 'Fattura Differita', readonly=True),
             'totale_pagare':fields.function(_totgen_doc, method=True, digits_compute=dp.get_precision('Account'), string='Netto da Pagare', store=True, multi='sums'),
             }

   _defaults = {
              'data_documento': lambda * a: time.strftime('%Y-%m-%d'),
              'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'res.partner', context=c),
              }

   _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Il Codice Documento deve essere unico !'),
        ('doc_prog_uniq', 'unique(doc_prog)', 'Il Numero Progressivo deve essere unico !'),
    ]
   _order = 'doc_prog desc'




   def ricrea_scad(self, cr, uid, ids, context=None):
        #import pdb;pdb.set_trace()
        testata = self.browse(cr, uid, ids)[0]
        #~ if 'generato_effetto' in self.pool.get('fiscaldoc.scadenze')._columns:
            #~ lines = self.pool.get('fiscaldoc.scadenze').search(cr, uid, [("name", "=", testata.id),('generato_effetto','=',False)])
        #~ else:
	lines = self.pool.get('fiscaldoc.scadenze').search(cr, uid, [("name", "=", testata.id)])
        #~ if lines:
            #~ ok = self.pool.get('fiscaldoc.scadenze').unlink(cr, uid, lines)
	ok = self.pool.get('fiscaldoc.scadenze').unlink(cr, uid, lines) # mettere in rem questa se si usano le righe di sopra
        ok = self.pool.get('fiscaldoc.scadenze').agg_righe_scad(cr, uid, ids, testata.totale_documento, context)
        return True


   def agg_magazzino(self, cr, uid, ids, context={}):

       testata = self.browse(cr, uid, ids)[0]
       causale = testata.tipo_doc
       output_id = testata.magazzino_id.id
       destination_id = testata.magazzino_destinazione_id.id

       if causale.flag_magazzino:
           # SE FALSE IL DOC NON CREA MOVIMENTI DI MAGAZZINO
           if ids:
               righe_ids = self.pool.get('fiscaldoc.righe').search(cr, uid, [('name', "=", ids)])
               # import pdb;pdb.set_trace()
               date_planned = testata.data_documento # datetime.now()
               # date_planned = (date_planned - timedelta(days=testata.company_id.security_lead)).strftime('%Y-%m-%d %H:%M:%S')
               #import pdb;pdb.set_trace()
               company_id = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id
               first_line = True
               if testata.picking_ids:
                   #import pdb;pdb.set_trace()
                   OK = self.pool.get('stock.picking').write(cr, uid, [testata.picking_ids.id], {'address_id': testata.partner_indcons_id.id, })

               for riga_art in self.pool.get('fiscaldoc.righe').browse(cr, uid, righe_ids, context=context):

                   if riga_art.move_ids:
                       #si tratta di una modifica dei dati
                        #import pdb;pdb.set_trace()
                        OK = self.pool.get('stock.move').write(cr, uid, [riga_art.move_ids.id], {
                        'name': "Documento " + riga_art.name.name,
                        'product_id': riga_art.product_id.id,
                        'date': date_planned,
                        'date_expected': date_planned,
                        'product_qty': riga_art.product_uom_qty,
                        'product_uom': riga_art.product_uom.id,
                        'product_uos_qty': riga_art.product_uos_qty,
                        'product_uos': (riga_art.product_uos and riga_art.product_uos.id)\
                                or riga_art.product_uom.id,
                        'address_id':  testata.partner_indcons_id.id,
                        'location_id': output_id,
                        'location_dest_id': destination_id,
                        'tracking_id': False,
                        'state': 'done',
                        #'state': 'waiting',
                        'company_id': company_id,
                    })


                   else:
                        #crEate PRIMA IL PICKING E POI IN MOVIMENTO E POI AGGIORNA TESTATA E RIGA

                        if first_line:
                            # prima riga scrive il picking la testata
                            first_line = False
                            pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
                            picking_id = self.pool.get('stock.picking').create(cr, uid, {
                                                                                         'name': pick_name,
                                                                                         'origin': testata.name,
                                                                                         'type': 'out',
                                                                                         'state': 'done',
                                                                                         'move_type':'direct',
                                                                                         'doc_id': testata.id,
                                                                                         'address_id': testata.partner_indcons_id.id,
                                                                                         'invoice_state': 'none',
                                                                                         'company_id':company_id,
                                                                                         })
                            stringa_update = " update fiscaldoc_header set picking_ids =" + str(picking_id) + " where id = " + str(testata.id)
                            ok = cr.execute(stringa_update)
                        move_id = self.pool.get('stock.move').create(cr, uid, {
                        'name': "Documento " + riga_art.name.name,
                        'picking_id': picking_id,
                        'product_id': riga_art.product_id.id,
                        'date': date_planned,
                        'date_expected': date_planned,
                        'product_qty': riga_art.product_uom_qty,
                        'product_uom': riga_art.product_uom.id,
                        'product_uos_qty': riga_art.product_uos_qty,
                        'product_uos': (riga_art.product_uos and riga_art.product_uos.id)\
                                or riga_art.product_uom.id,
                        'address_id':  testata.partner_indcons_id.id,
                        'location_id': output_id,
                        'location_dest_id': destination_id,
                        'tracking_id': False,
                        'state': 'done',
                        #'state': 'waiting',
                        'company_id': company_id,
                    })
                        stringa_update = " update fiscaldoc_righe set move_ids =" + str(move_id) + " where id = " + str(riga_art.id)
                        ok = cr.execute(stringa_update)



       return True





   def _get_document_lines(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('fiscaldoc.righe').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

   def write(self, cr, uid, ids, vals, context=None):
        # prima scrive i record così come sono poi si preoccupa di ricalcolare  le tasse e i campi calcolati
        #import pdb;pdb.set_trace()

        res = super(FiscalDocHeader, self).write(cr, uid, ids, vals, context=context)
        # ricalcola le scadenze
        totaledoc = self.browse(cr, uid, ids)[0].totale_documento
        ok = self.agg_magazzino(cr, uid, ids, context)
        ok = self.ricrea_scad(cr, uid, ids, context)
        
        #MODIFICA PER 6.1 IN CASO DI CAMBIO DI CAUSALE NON VENIVANO AGGIORNATI I PROGRESSIVI
        #NON FUNZIONA RISCRIVE IL PROGRESSIVO ANCHE IN FASE DI MODIFICA DI UN DOCUMENTO VECCHIO
        #~ if not 'data_documento' in vals:
            #~ data = self.browse(cr, uid, ids)[0].data_documento
        #~ else:
            #~ data=vals['data_documento']
        #~ if not 'progr' in vals:
            #~ prog = self.browse(cr, uid, ids)[0].progr.id
        #~ else:
            #~ prog = vals['prog']
        #~ if not 'numdoc' in vals:
            #~ numdoc = self.browse(cr, uid, ids)[0].numdoc
        #~ else:
            #~ numdoc = vals['numdoc']
        #~ res = self.pool.get('fiscaldoc.numeriprogressivi')._aggiorna_progr(cr, uid, prog, data, numdoc)
        
        # totale_merce = self.pool.get('fiscaldoc.righe').calcola_netto_merce(cr, uid, ids,context)
        # res_iva = self.pool.get('fiscaldoc.iva').agg_righe_iva(cr, uid, ids,context)
        return res

   def create(self, cr, uid, vals, context=None):
        #
     res = 0
     def riassegna_doc(self, cr, uid, vals):
            #import pdb;pdb.set_trace()
            # cicla fino a che non becca un numero libero
            doc = self.pool.get('fiscaldoc.header')
            doc_id = vals['name']
            numdoc = vals['numdoc']
            doc_prog = vals['doc_prog']
            while doc.search(cr, uid, [('doc_prog', "=", doc_prog)]):
                numdoc += 1
                doc_id = doc_id_create(self, cr, uid, vals['tipo_doc'], vals['data_documento'], vals['progr'], numdoc)
                doc_prog = doc_prog_create(self, cr, uid, vals['tipo_doc'], vals['data_documento'], vals['progr'], numdoc)
            return {'name':doc_id, 'numdoc':numdoc,'doc_prog':doc_prog}

     if vals:
        #import pdb;pdb.set_trace()

       #if vals.get('righe_articoli', False): # or len(vals['righe_articoli']) == 0:
          # pass
      # non accetta che ci siano documenti senza corpo righe
          #raise osv.except_osv(_('ERRORE !'), _('NON HAI INSERITO ALCUNA RIGA ARTICOLO'))

        doc = self.pool.get('fiscaldoc.header')
        #ids_docs = doc.search(cr, uid, [('doc_prog', "=", vals['doc_prog'])])
        #if ids_docs:
            # CI SONO DEI DOCUMENTI CON LO STESSO NUMERO, SE + IN LA SI AGGIUNGE L'ANNO SUI DOCUMENTI LA RICERCA E + DIRETTA
            # ORA INVECE DEVE CICLARE
        #    for doc_ob in doc.browse(cr,uid,ids_docs):
        #        anno = vals['data_documento'][0:4]
        #        if doc_ob.data_documento[0:4]=='anno':
                    #ESISTE GIA IL PROGRESSIVO DELL'ANNO
        #            res = riassegna_doc(self, cr, uid, vals)
        #            vals['name'] = res['name']
        #            vals['numdoc'] = res['numdoc']

        if doc.search(cr, uid, [('doc_prog', "=", vals['doc_prog'])]):
            #TROVATO GIA UN DOCUMENTO IDENTICO DEVE RIASSEGNARE
            res = riassegna_doc(self, cr, uid, vals)
            vals['name'] = res['name']
            vals['numdoc'] = res['numdoc']
            vals['doc_prog']= res['doc_prog']
        else:
            #tutto  ok
            pass
      # AGGIORNA IL PROGRESSIVO
        #import pdb;pdb.set_trace()
        res = self.pool.get('fiscaldoc.numeriprogressivi')._aggiorna_progr(cr, uid, vals['progr'], vals['data_documento'], vals['numdoc'])
        if not res:
            raise osv.except_osv(_('ERRORE !'), _('NON È STATO POSSIBILE AGGIORNARE IL PROGRESSIVO DOCUMENTO NON SALVATO'))
        res = super(FiscalDocHeader, self).create(cr, uid, vals, context=context)
        #import pdb;pdb.set_trace()
        ok = self.agg_magazzino(cr, uid, [res], context)
        ok = self.ricrea_scad(cr, uid, [res], context)
     return res


   def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        """Controlli se è possibile cancellare ed esegue le operazioni preparatorie"""
        for rec in self.browse(cr, uid, ids, context=context):
          if rec.tipo_doc.tipo_documento == "FD": #il doc è una fattura differita va ad eliminare il legame con i ddt in modo che possano essere rifatturati
            ids_ddt = self.search(cr, uid, [('differita_id', '=', rec.id)])
            for id in ids_ddt:
              ok = self.write(cr, uid, [id], {'differita_id':0})
              # raise osv.except_osv(_('Invalid action !'), _('Cannot delete a sales order line which is %s !') %(rec.state,))
          #import pdb;pdb.set_trace()
          for riga_art in rec.righe_articoli:
            if  riga_art.order_line_id and  riga_art.name.tipo_doc.tipo_documento<>'FD':
              # ci sono righe con  movimento di magazzino legato se il movimento ha come origine il documento stesso cancella
              # altrimenti segnala la necessità di effettuare un reso merce che è un wizard sul documento
            #raise osv.except_osv(_('Invalid action !'), _('NON PUOI CANCELLARE UN DOCUMENTO LEGATO AD UN ORDINE, PUOI MODIFICARE IL DOCUMENTO O FARE UN RIENTRO  !'))
              print " CANCELLAZIONE DEL DOCUMENTO CON ORDINE "+rec.name
          for riga_art in rec.righe_articoli:
            if  riga_art.move_ids and rec.tipo_doc.tipo_documento <> "FD":
              context['document'] = True
              ok = self.pool.get('stock.move').unlink(cr, uid, [riga_art.move_ids.id], context=context)
          if rec.picking_ids and rec.tipo_doc.tipo_documento <> "FD":
            context['document'] = True
            ok = self.pool.get('stock.picking').unlink(cr, uid, [rec.picking_ids.id], context=context)

        return super(FiscalDocHeader, self).unlink(cr, uid, ids, context=context)

   def check_data_doc(self, ult_numdoc_e_data, data_doc):
        #import pdb;pdb.set_trace()
        if ult_numdoc_e_data['data_ultimo_numero']:
            if ult_numdoc_e_data['data_ultimo_numero'] <= data_doc:
                res = True
            else:
                res = False
        else:
            res = True
        return res

   def trova_numdoc(self, cr, uid, ids, tipo_doc, data_doc, progr):
        #import pdb;pdb.set_trace()
      val = 0
      if tipo_doc:
        anno = data_doc[0:4]
        if progr:
            progressivo = self.pool.get('fiscaldoc.tipoprogressivi')
            numdoc_e_data = progressivo._get_ult_progr(cr, uid, ids, progr, anno)
            if  self.check_data_doc(numdoc_e_data, data_doc):
                val = numdoc_e_data["ultimo_numero"] + 1
            else:
                val = 0
                raise osv.except_osv(_('ERRORE !'), _("DATA DOCUMENTO INFERIORE ALL' ULTIMO DOCUMENTO MA N° SUPERIORE"))
      return val



   def onchange_tipo_doc(self, cr, uid, ids, tipo_doc, data_doc,context):
            #import pdb;pdb.set_trace()
            v = {}
            if tipo_doc:
                tipo = self.pool.get('fiscaldoc.causalidoc').browse(cr, uid, tipo_doc)
                if tipo.progr_id_default.id:
                    v['tipo_doc'] = tipo_doc
                    v['progr'] = tipo.progr_id_default.id
                    v['numdoc'] = self.trova_numdoc(cr, uid, ids, tipo_doc, data_doc, v['progr'])
                    v['name'] = doc_id_create(self, cr, uid, tipo_doc, data_doc, v['progr'], v['numdoc'])
                    v['doc_prog']=  doc_prog_create(self, cr, uid, tipo_doc, data_doc, v['progr'], v['numdoc'])
                    v['magazzino_id'] = tipo.deposito_default.id
                    v['magazzino_destinazione_id'] = tipo.deposito_destinazione_default.id
                    context.update({'location':tipo.deposito_default.id} )
                    v['causale_del_trasporto_id'] = tipo.causale_del_trasporto_id.id
            #import pdb;pdb.set_trace()
            return {'value': v}

   def calcola_spese_inc(self, cr, uid, ids, pagamento_id):
            #import pdb;pdb.set_trace()
            v = {}
            if pagamento_id:
                lines = self.pool.get('account.payment.term.line').search(cr, uid, [('payment_id', "=", pagamento_id)])
                spese = 0
                for riga in self.pool.get('account.payment.term.line').browse(cr, uid, lines):
                    spese = spese + riga['costo_scadenza']
                v['spese_incasso'] = spese

            return {'value': v}

   def onchange_datadoc(self, cr, uid, ids, tipo_doc, data_doc, progr):

            v = {}
            if progr:
                v['numdoc'] = self.trova_numdoc(cr, uid, ids, tipo_doc, data_doc, progr)
            else:
                v['numdoc'] = 0
            return {'value': v}



   def onchange_numdoc(self, cr, uid, ids, tipo_doc, data_doc, progr, numdoc):
        # SE È STATO CAMBIATO IL NUMERO PROPOSTO ALLORA VERIFICA I VINCOLI, SE SI TRATTA DI UN NUMERO PRECEDENTE
        # IL DOCUMENTO NON DEVE ESISTERE, E DEVE ESSERE NEL RANGE DI DATE TRA IL DOC PRECEDENTE E SUCCESSIVO
        # SE FORZA UN NUMERO IN AVANTI INVECE FA LE VERIFICHE NORMALI
        v = {}

        progressivo = self.pool.get('fiscaldoc.tipoprogressivi')
        anno = data_doc[0:4]
        numdoc_e_data = progressivo._get_ult_progr(cr, uid, ids, progr, anno)
        if numdoc_e_data:
         num_norm = numdoc_e_data["ultimo_numero"]
         v = {}
         if num_norm >= numdoc:
            # il numero è inferiore o uguale all'ultimo lancia la ricerca per vedere se esiste
            doc = self.pool.get('fiscaldoc.header')
            name = doc_id_create(self, cr, uid, tipo_doc, data_doc, progr, numdoc)
            doc_prog=doc_prog_create(self, cr, uid, tipo_doc, data_doc,progr, numdoc)
            if doc.search(cr, uid, [('doc_prog', "=", doc_prog)]):
                # Esiste già il record quindi gli da Errore
                raise osv.except_osv(_('ERRORE !'), _("IL DOCUMENTO ESISTE GIA'"))
            else:
                if numdoc_e_data['data_ultimo_numero'] < data_doc and num_norm < numdoc:
                    raise osv.except_osv(_('ERRORE !'), _("NUMERO DOC. INFERIORE MA DATA DOC. SUPERIORE ALL'ULTIMO DOCUMENTO !!"))
                else:
                    name = doc_id_create(self, cr, uid, tipo_doc, data_doc, progr, numdoc)
                    doc_prog=doc_prog_create(self, cr, uid, tipo_doc, data_doc,progr, numdoc)
                    v['name'] = name
                    v['doc_prog'] = doc_prog
         else:
            name = doc_id_create(self, cr, uid, tipo_doc, data_doc, progr, numdoc)
            doc_prog=doc_prog_create(self, cr, uid, tipo_doc, data_doc,progr, numdoc)
            v['name'] = name
            v['doc_prog'] = doc_prog

        return {'value': v}


   def onchange_partner_id(self, cr, uid, ids, part, context):
        #import pdb;pdb.set_trace()
        # cerca il cliente e poi riporta i dati che servono di default
        if not part:
            return {'value': {'partner_indfat_id': False, 'partner_indcons_id': False}}
        addr = self.pool.get('res.partner').address_get(cr, uid, [part], ['delivery', 'invoice', 'contact'])
        part = self.pool.get('res.partner').browse(cr, uid, part)
        pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
        pagamento_id = part.property_payment_term and part.property_payment_term.id or False
#       fiscal_position = part.property_account_position and part.property_account_position.id or False
        agente = part.user_id and part.user_id.id or uid
        if part.bank_ids:
            banca_cliente = part.bank_ids[0].bank.id
        else:
            banca_cliente = False
        val = {
            'partner_indfat_id': addr['invoice'],
            'partner_indcons_id': addr['delivery'],
            'pagamento_id':pagamento_id,
            'sconto_pagamento':part.property_payment_term.sconto,
            'agente':agente,
            'str_sconto_partner':part.str_sconto_partner,
            'sconto_partner':part.sconto_partner,
            'spedizione':part.spedizione.id,
            'vettore':part.property_delivery_carrier.id,
            'porto_id':part.carriage_condition_id.id,
            'aspetto_esteriore_id':part.goods_description_id.id,
            'banca_patner':banca_cliente

        }
        if pricelist:
            val['listino_id'] = pricelist

        warning = {}

        if part.comment:
           # raise 'ATTENZIONE !', part.comment
            # raise osv.except_osv(_('ATTENZIONE !'), _(part.comment))
             warning = {
                                    'title': 'ATTENZIONE !',
                                    'message':part.comment,

            }

        if part.bloccato:
            #import pdb;pdb.set_trace()
            val = {
            'partner_id':False,
            'partner_indfat_id': False,
            'partner_indcons_id': False,
            'pagamento_id':False,
            }
            if part.comment:
                    warning = {
                                    'title': 'ATTENZIONE !',
                                    'message':'PARTNER BLOCCATO '+part.comment,

                                    }
            else:
                    warning = {
                                    'title': 'ATTENZIONE !',
                                    'message':'PARTNER BLOCCATO ',

                                    }

        #import pdb;pdb.set_trace()
        return {'value': val, 'warning': warning}



FiscalDocHeader()

class FiscalDocRighe(osv.osv):
   
   _name = "fiscaldoc.righe"
   _description = "Righe Documenti"
  # dp.get_precision('Account')
   
   __logger = logging.getLogger(_name)
   _columns = {
             'order_line_id': fields.many2one('sale.order.line', 'Righe Ordine', required=False, ondelete='cascade', select=True, readonly=True),
             'name': fields.many2one('fiscaldoc.header', 'Numero Documento', required=True, ondelete='cascade', select=True, readonly=True),
             'descrizione_riga':fields.text("Descrizione", required=True),
             'product_id': fields.many2one('product.product', 'Articolo', required=True, ondelete='cascade', select=True),
             'product_uom_qty': fields.float('Quantity (UoM)', digits=(16, 2), required=True, readonly=False , Traslate=True),
             'product_uom': fields.many2one('product.uom', 'Unit of Measure ', required=True, readonly=False, Traslate=True),
             'product_uos_qty': fields.float('Quantity (UoS)', readonly=False, Traslate=True),
             'product_uos': fields.many2one('product.uom', 'Product UoS', Traslate=True),
             'product_prezzo_unitario':fields.float('Prezzo di Vendita',digits_compute=dp.get_precision('Sale Price')),
             'sconti_riga':fields.char("Sconti", size=20),
             'discount_riga':fields.float('Sconto Totale di Riga', digits=(12, 3)),
             'prezzo_netto':fields.float('Prezzo Netto di Riga', digits_compute=dp.get_precision('Sale Price')),
             'totale_riga':fields.float('Totale di Riga',digits_compute=dp.get_precision('Account')),
             #'tot_merce_riga':fields.float('Totale Netto di Riga', digits_compute=dp.get_precision('Account')),
             #'netto_riga': fields.function(_amount_line, method=True, string='Netto Riga', digits_compute=dp.get_precision('Sale Price')),
             'flag_omaggi':fields.selection((('M', 'Sconto Merce'), ('O', 'Omaggio Imponibile'), ('T', 'Omaggio di Imponibile e Iva'), ('N', 'Annulla Omaggio')), 'OMAGGI'),
             'perc_provv':fields.float('% Provvigioni', digits=(7, 3)),
             'contropartita':fields.many2one('account.account', "Contropartita", required=True),
             'codice_iva':fields.many2one('account.tax', 'Codice Iva', required=True, readonly=False),
             'move_ids': fields.many2one('stock.move', 'Movimeti di Magazzino', readonly=True),


               }
   _defaults = {
              'product_uom_qty': 1,
              #'flag_omaggi': 'N'
              }

   def copy_data(self, cr, uid, id, default=None, context=None):
        #import pdb;pdb.set_trace()
        if not default:
            default = {}
        #default.update({'state': 'draft', 'move_ids': [], 'invoiced': False, 'invoice_lines': []})
        return super(FiscalDocRighe, self).copy_data(cr, uid, id, default, context=context)

   def unlink(self, cr, uid, ids, context=None):
        #import pdb;pdb.set_trace()
        if context is None:
            context = {}
        if ids:
          for riga_art in self.browse(cr,uid,ids):
            if  riga_art.order_line_id and  riga_art.name.tipo_doc.tipo_documento<>'FD':
              # ci sono righe con  movimento di magazzino legato se il movimento ha come origine il documento stesso cancella
              # altrimenti segnala la necessità di effettuare un reso merce che è un wizard sul documento
              #raise osv.except_osv(_('Invalid action !'), _('NON PUOI CANCELLARE UN DOCUMENTO LEGATO AD UN ORDINE, PUOI MODIFICARE IL DOCUMENTO O FARE UN RIENTRO  !'))
              print " CANCELLAZIONE DEL DOCUMENTO CON ORDINE "+riga_art.product_id.default_code
          for riga_art in self.browse(cr,uid,ids):
            if  riga_art.move_ids and riga_art.name.tipo_doc.tipo_documento <> "FD":
              context['document'] = True
              ok = self.pool.get('stock.move').unlink(cr, uid, [riga_art.move_ids.id], context=context)
        return super(FiscalDocRighe, self).unlink(cr, uid, ids, context=context)

   def write(self, cr, uid, ids, vals, context=None):
        #import pdb;pdb.set_trace()
        #lines = self.pool.get('fiscaldoc.righe').search(cr, uid, [('name', '=', ids)])

        return super(FiscalDocRighe, self).write(cr, uid, ids, vals, context=context)

   def create(self, cr, uid, vals, context=None):
        # import pdb;pdb.set_trace()
        return super(FiscalDocRighe, self).create(cr, uid, vals, context=context)

   def calcola_netto_merce(self, cr, uid, ids, context):
       # Ricalcola per sicurezza il totale delle righe
        lines = self.pool.get('fiscaldoc.righe').search(cr, uid, [('name', '=', ids)])
        tot_merce = 0
        #import pdb;pdb.set_trace()
        for riga in self.pool.get('fiscaldoc.righe').browse(cr, uid, lines, context=context):
            tot_merce= riga.prezzo_netto*riga.product_uom_qty
            tot_merce = arrot(cr,uid,tot_merce,dp.get_precision('Account'))
 #           netto_merce = riga.prezzo_netto*riga.product_uom_qty
 #           if riga.name.sconto_partner:
 #               tot_merce= tot_merce-(tot_merce*riga.name.sconto_partner/100)
 #           if riga.name.sconto_pagamento:
 #               tot_merce = tot_merce-(tot_merce*riga.name.sconto_pagamento/100)

            #tot_merce = tot_merce + riga['totale_riga']
            ok = self.pool.get('fiscaldoc.righe').write(cr,uid,riga.id,{'totale_riga':tot_merce})
        return True

   def calcola_netto(self,cr, uid, ids, prezzo, sconto):
       # sta calcolando il prezzo unitario  netto della riga
       netto = prezzo - (prezzo * sconto / 100)
       netto = arrot(cr,uid,netto,dp.get_precision('Sale Price'))
       return netto

   def totale_riga(self,cr,uid, qty, netto):
       tot = qty * netto
       tot = arrot(cr,uid,tot,dp.get_precision('Account'))
       #import pdb;pdb.set_trace()
       return tot

   def get_string_discount(self, cr, uid, ids, res_dict):
            # VA A CERCARE LE RIGHE CON SCONTO PERSONALIZZATO
            #import pdb;pdb.set_trace()
            item_obj = self.pool.get('product.pricelist.item')
            if res_dict.get('price_item_id', False):
                    item = res_dict.get('price_item_id', False)
                    item_String_Discount = item_obj.read(cr, uid, [item], ['string_discount'])[0]['string_discount']
            else:
                item_String_Discount = ""
            return item_String_Discount

   def get_real_price(self, cr, uid, ids, res_dict, product_id, qty, uom, pricelist):

            # CERCA IL PREZZO DELL'ARTICOLO E GLI EVENTUALI SCONTI
            item_obj = self.pool.get('product.pricelist.item')
            price_type_obj = self.pool.get('product.price.type')
            product_obj = self.pool.get('product.product')
            template_obj = self.pool.get('product.template')
            field_name = 'list_price'
            if res_dict.get('item_id', False) and res_dict['item_id'].get(pricelist, False):
                if res_dict.get('price_item_id', False):
                    item = res_dict.get('price_item_id', False)
                else:
                    item = res_dict['item_id'].get(pricelist, False)
                item_base = item_obj.read(cr, uid, [item], ['base'])[0]['base']
                if item_base > 0:
                    field_name = price_type_obj.browse(cr, uid, item_base).field

            product = product_obj.browse(cr, uid, product_id)
            product_tmpl_id = product.product_tmpl_id.id

            product_read = template_obj.read(cr, uid, product_tmpl_id, [field_name])

            factor = 1.0
            if uom and uom != product.uom_id.id:
                product_uom_obj = self.pool.get('product.uom')
                uom_data = product_uom_obj.browse(cr, uid, product.uom_id.id)
                factor = uom_data.factor
            return product_read[field_name] * factor

   def get_prezzo(self, cr, uid, ids, product_id, listino_id, qty, partner_id):
            # CERCA IL PREZZO DI LISTINO
            price = 0
            if not listino_id:
             warning = {
                'title': 'No Pricelist !',
                'message':
                    'You have to select a pricelist or a customer in the sales form !\n'
                    'Please set one before choosing a product.'
                }
            else:
                price = self.pool.get('product.pricelist').price_get(cr, uid, [listino_id],product_id, qty or 1.0 , partner_id)[listino_id]

            if price is False:
                warning = {
                    'title': 'No valid pricelist line found !',
                    'message':
                        "Couldn't find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist."
                    }
            return price

   def get_prezzo_netto(self, cr, uid, res_dict):
            item_obj = self.pool.get('product.pricelist.item')
            if res_dict.get('price_item_id', False):
                    item = res_dict.get('price_item_id', False)
                    item_String_Discount = item_obj.read(cr, uid, [item], ['price_surcharge'])[0]['price_surcharge']
            else:
                item_String_Discount = 0
            return item_String_Discount

   def determina_prezzo_sconti(self, cr, uid, ids, product_id, listino_id, qty, partner_id, uom, data_doc):
            # determina il prezzo
                pricelist_obj = self.pool.get('product.pricelist')
                #import pdb;pdb.set_trace()
                price = self.get_prezzo(cr, uid, ids, product_id, listino_id, partner_id, qty)
                list_price = pricelist_obj.price_get(cr, uid, [listino_id], product_id, qty or 1.0, partner_id, {'uom': uom, 'date': data_doc })
                pricelists = pricelist_obj.read(cr, uid, [listino_id], ['visible_discount'])
                #old_uom = riga_art.uos_id or riga_art.uom_id
                new_list_price = self.get_real_price(cr, uid, ids, list_price, product_id, qty, uom, listino_id)
                if(len(pricelists) > 0 and pricelists[0]['visible_discount'] and list_price[listino_id] != 0):
                    if new_list_price<> 0.0:
                        discount = (new_list_price - price) / new_list_price * 100
                    else:
                        discount = 0.0
                else:
                    new_list_price = 0
                    discount = 0
                #import pdb;pdb.set_trace()
                item_String_Discount = self.get_string_discount(cr, uid, ids, list_price)
                if item_String_Discount:
                    lista_sconti = item_String_Discount.split("+")
                    sconto = float(100)
                    for scontoStr in lista_sconti:
                        if scontoStr <> "+":
                            sconto = sconto - (sconto * float(scontoStr) / 100)
                    sconto = (100 - sconto)
                else:
                    sconto = 0
                #import pdb;pdb.set_trace()
                if sconto == 100:
                    # prezzo netto senza sconti
                    new_list_price = self.get_prezzo_netto(cr, uid, list_price)
                    sconto = 0.0
                    item_String_Discount = ''
                if list_price[listino_id] != new_list_price and  sconto == 0:
                    new_list_price = list_price[listino_id]

                return {'prezzo':new_list_price, 'sconto':sconto, 'StringaSconto':item_String_Discount}

   def check_giac(self,cr,uid,ids,product_id,qty,company_id,context):
       # controlla se l'articolo va in negativo con questa qta se si azzera la lista e blocca lo scarico
       #import pdb;pdb.set_trace()
       
       #questo controllo evita il check dei negativi nel caso in cui si movimenti il magazzino
       #clienti ad. esempio per una fattura proforma
       flag = True
       if context:
           if 'location' in context:
               mag = self.pool.get('stock.location').browse(cr, uid, context['location'])
               if mag.name == "Customers":
                   flag = False 
       if company_id.flag_no_neg and flag:
           if product_id and qty:
               product_obj = self.pool.get('product.product').browse(cr,uid,[product_id],context=context)[0]
               if product_obj.type =='product': # il contollo è solo sugli stoccabili
                   #~ import pdb; pdb.set_trace()
                   
                   #self.__logger.info('Codice Articolo %s', str(product_obj.default_code))
                   #self.__logger.info('Qta Available %s', str(product_obj.qty_available))
                   ##self.__logger.info('Qta venduta %s', str(qty))
                   #self.__logger.info('Differenza %s', str(product_obj.qty_available-qty))
                   if (round(product_obj.qty_available)-round(qty)) < 0 :
                       self.__logger.info('Valore di CHECK_GIAC')
                       self.__logger.info('Differenza %s', str(int(product_obj.qty_available-qty)))
                       flag = True
                      
                   else:
                       flag = False
               else:
                    flag = False
           else:
               flag = False
       else:
           flag = False
       return flag

   def onchange_articolo(self, cr, uid, ids, product_id, listino_id, qty, partner_id, data_doc, uom,context):
    v = {}
    domain={}
    warning = {}
    #import pdb;pdb.set_trace()
    if context:
        location = context
        context={'location':location}
    else:
        location = context
    if product_id:
        #import pdb;pdb.set_trace()
        partner_obj = self.pool.get("res.partner")

        if partner_id:
            lang = partner_obj.browse(cr, uid, partner_id).lang
            company_id = partner_obj.browse(cr, uid, partner_id).company_id
        context = {'lang': lang, 'partner_id': partner_id}
        v = {}
        if product_id:
            product_obj = self.pool.get('product.product')
            riga_art = product_obj.browse(cr, uid, product_id)
            if riga_art:
                # import pdb;pdb.set_trace()
                if riga_art.description_sale:
                    if riga_art.variants:
                      v['descrizione_riga'] = riga_art.name + " - " + riga_art.variants
                     #+ " - " + riga_art.description_sale
                    else:
                       v['descrizione_riga'] = riga_art.name
                      #+ " - " + riga_art.description_sale
                else:
                   if riga_art.variants:
                      v['descrizione_riga'] = riga_art.name + " - " + riga_art.variants
                   else:
                     v['descrizione_riga'] = riga_art.name
                v['product_uom'] = riga_art.uom_id.id
                #import pdb;pdb.set_trace()
                if riga_art.property_account_income:
                    v['contropartita'] = riga_art.property_account_income.id
                else:
                    v['contropartita'] = riga_art.categ_id.property_account_income_categ.id
                righe_tasse_articolo = self.pool.get('account.fiscal.position').map_tax(cr, uid, False, riga_art.taxes_id)
                if righe_tasse_articolo:
                    v['codice_iva'] = righe_tasse_articolo[0]

                # determina il prezzo

                dati_prz = self.determina_prezzo_sconti(cr, uid, ids, product_id, listino_id, qty, partner_id, uom, data_doc)

                v['product_prezzo_unitario'] = dati_prz['prezzo']
                v['discount_riga'] = dati_prz['sconto']
                #import pdb;pdb.set_trace()
                v['sconti_riga'] = dati_prz['StringaSconto']
            else:
                v['discount_riga'] = 0.0
            v['prezzo_netto'] = self.calcola_netto(cr, uid, ids,v['product_prezzo_unitario'], v['discount_riga'])

            v['totale_riga'] = self.totale_riga(cr,uid,qty, v['prezzo_netto'])
            #import pdb;pdb.set_trace()
            context['location'] = location
            if self.check_giac(cr,uid,ids,product_id,qty,company_id,context):
                # sottoscorta non permesso
                self.__logger.info('Codice Articolo %s', str(riga_art.default_code))
                self.__logger.info('Qta Available %s', str(riga_art.qty_available))
                self.__logger.info('Qta venduta %s', str(qty))
                self.__logger.info('Differenza %s', str(riga_art.qty_available-qty))
                self.__logger.info('Uscira il warning')
                v = {'product_uom_qty':False,
                     'codice_iva':False
                     }
                warning = {
                    'title': _('Errore di Giacenza !'),
                    'message': 'Sottoscorta non permesso sullarticolo !'
                    }
                return {'value': v, 'domain': domain, 'warning': warning}
                #raise osv.except_osv(_('Errore'), _('Sottoscorta non permesso sullarticolo !') )

    return {'value': v, 'domain': domain, 'warning': warning}

   def on_change_qty(self, cr, uid, ids, product_id, listino_id, qty, partner_id, uom, data_doc,context):
         v = {}
         domain={}
         warning = {}
         if context:
             location = context
             context={'location':location}
         else:
            location = context

         partner_obj = self.pool.get("res.partner")
         if partner_id:
            company_id = partner_obj.browse(cr, uid, partner_id).company_id

         if qty and product_id and listino_id:
             dati_prz = self.determina_prezzo_sconti(cr, uid, ids, product_id, listino_id, qty, partner_id, uom, data_doc)
             v['product_prezzo_unitario'] = dati_prz['prezzo']
             v['discount_riga'] = dati_prz['sconto']
             v['sconti_riga'] = dati_prz['StringaSconto']
             v['prezzo_netto'] = self.calcola_netto(cr, uid, ids,v['product_prezzo_unitario'], v['discount_riga'])
             v['totale_riga'] = self.totale_riga(cr,uid,qty, v['prezzo_netto'])
             #import pdb;pdb.set_trace()
             context['location'] = location
             if self.check_giac(cr,uid,ids,product_id,qty,company_id,context):
                # sottoscorta non permesso
                riga_art = self.pool.get('product.product').browse(cr, uid, product_id)
                self.__logger.info('Context %s', str(context))
                self.__logger.info('Codice Articolo %s', str(riga_art.default_code))
                self.__logger.info('Qta Available %s', str(riga_art.qty_available))
                self.__logger.info('Qta venduta %s', str(qty))
                self.__logger.info('Differenza %s', str(riga_art.qty_available-qty))
                self.__logger.info('Uscira il warning')
                v = {'product_uom_qty':False,
                     'codice_iva':False}
                warning = {
                    'title': _('Errore di Giacenza !'),
                    'message': 'Sottoscorta non permesso sullarticolo !'
                    }
                return {'value': v, 'domain': domain, 'warning': warning}
                #raise osv.except_osv(_('Errore'), _('Sottoscorta non permesso sullarticolo !') )
         return {'value': v, 'domain': domain, 'warning': warning}

   def on_change_prezzo(self, cr, uid, ids, prezzo, sconto, qty):
       v = {}
       if prezzo:

            v['prezzo_netto'] = self.calcola_netto(cr, uid, ids,prezzo, float(sconto))
            v['totale_riga'] = self.totale_riga(cr,uid, qty, v['prezzo_netto'])
       return {'value':v}

   def on_change_strSconti(self, cr, uid, ids, value, prezzo, qty):
       #import pdb;pdb.set_trace()
        v = {}
        if value and prezzo and qty:
            lista_sconti = value.split("+")
            sconto = float(100)
            for scontoStr in lista_sconti:
                if scontoStr <> "+":
                    sconto = sconto - (sconto * float(scontoStr) / 100)
            sconto = (100 - sconto)
            v['discount_riga'] = sconto
            v['prezzo_netto'] = self.calcola_netto(cr, uid, ids,prezzo, sconto)
            v['totale_riga'] = self.totale_riga(cr,uid,qty, v['prezzo_netto'])
        else:
            sconto = 0

        return  {'value': v}

   def onchange_flag(self, cr, uid, ids, product_id, listino_id, qty, partner_id, data_doc, uom, flag_omaggi):
        v = {}
        if flag_omaggi:
            v={}

        #CALCOLO DELL'OMAGGIO COME SCONTO MERCE
        # DEVE FARE IN MODO DA ESCLUDERE LA RIGA DAL CALCOLO DEL CASTELLETTO
        # E' DA OGNI ALTRO AUTOMATISMO AUTOMATIZZATO DI CALCOLO NEL DOCUMENTO

            if flag_omaggi == 'M':
                #import pdb;pdb.set_trace()
                product_obj = self.pool.get('product.product')
                riga_art = product_obj.browse(cr, uid, product_id)
                v['codice_iva'] = 0
                v['descrizione_riga'] = riga_art.name + " - " + riga_art.variants + " * SCONTO MERCE * "
                dati_prz = self.determina_prezzo_sconti(cr, uid, ids, product_id, listino_id, qty, partner_id, uom, data_doc)
                v['product_prezzo_unitario'] = dati_prz['prezzo']
                v['discount_riga'] = 0 # dati_prz['sconto']
                v['prezzo_netto'] = 0 # self.calcola_netto(cr, uid, ids,v['product_prezzo_unitario'], v['discount_riga']) * -1
                v['totale_riga'] = 0 #self.totale_riga(cr,uid, qty, v['prezzo_netto'])
                if riga_art.property_account_income:
                    v['contropartita'] = riga_art.property_account_income
                else:
                    v['contropartita'] = riga_art.categ_id.property_account_income_categ.id
                return {'value':v}
            else:
            #CALCOLO DELL'OMAGGIO IMPONIBILE
            # DA RIVEDERE
                if flag_omaggi == 'O':
                    #import pdb;pdb.set_trace()
                    product_obj = self.pool.get('product.product')
                    riga_art = product_obj.browse(cr, uid, product_id)
                    v['descrizione_riga'] = riga_art.name + " - " + riga_art.variants + " * OMAGGIO IMPONIBILE * "


                    dati_prz = self.determina_prezzo_sconti(cr, uid, ids, product_id, listino_id, qty, partner_id, uom, data_doc)
                    v['product_prezzo_unitario'] = dati_prz['prezzo']
                    v['discount_riga'] = dati_prz['sconto']
                    v['prezzo_netto'] = self.calcola_netto(cr, uid, ids,v['product_prezzo_unitario'], v['discount_riga']) * -1
                    v['totale_riga'] = self.totale_riga(cr,uid,qty, v['prezzo_netto'])

                    #import pdb;pdb.set_trace()
                    v['sconti_riga'] = dati_prz['StringaSconto']

                    righe_tasse_articolo = self.pool.get('account.fiscal.position').map_tax(cr, uid, False, riga_art.taxes_id)

                    if righe_tasse_articolo:
                        v['codice_iva'] = righe_tasse_articolo[0]
                    if riga_art.property_account_income:
                        v['contropartita'] = riga_art.property_account_income
                    else:
                        v['contropartita'] = riga_art.categ_id.property_account_income_categ.id

                    return {'value': v}
                else:
                    if flag_omaggi == 'N':
                        product_obj = self.pool.get('product.product')
                    riga_art = product_obj.browse(cr, uid, product_id)
                    v['descrizione_riga'] = riga_art.name + " - " + riga_art.variants
                    dati_prz = self.determina_prezzo_sconti(cr, uid, ids, product_id, listino_id, qty, partner_id, uom, data_doc)
                    v['product_prezzo_unitario'] = dati_prz['prezzo']
                    v['discount_riga'] = dati_prz['sconto']
                    v['prezzo_netto'] = self.calcola_netto(cr, uid, ids,v['product_prezzo_unitario'], v['discount_riga'])
                    v['totale_riga'] = self.totale_riga(cr,uid,qty, v['prezzo_netto'])
                    v['sconti_riga'] = dati_prz['StringaSconto']
                    righe_tasse_articolo = self.pool.get('account.fiscal.position').map_tax(cr, uid, False, riga_art.taxes_id)
                    if righe_tasse_articolo:
                        v['codice_iva'] = righe_tasse_articolo[0]
                    if riga_art.property_account_income:
                        v['contropartita'] = riga_art.property_account_income
                    else:
                        v['contropartita'] = riga_art.categ_id.property_account_income_categ.id

                    return {'value': v}
        return {'value': v}

FiscalDocRighe()

class FiscalDocScadenze(osv.osv):
   _name = "fiscaldoc.scadenze"
   _description = "Scadenze Documenti"
   _columns = {
             'name': fields.many2one('fiscaldoc.header', 'Numero Documento', required=True, ondelete='cascade', select=True, readonly=True),
             'tipo_scadenza':fields.selection((('RB', 'Ri.Ba.'), ('BO', 'Bonifico'), ('CO', 'Contanti/Cash'), ('RD', 'Rimessa Diretta'),('RI', 'R.I.D.')), 'Tipo Scadenza', required=True),
             'data_scadenza':fields.date('Data Scadenza', required=True, select=True),
             'importo_scadenza':fields.float('Importo',digits_compute=dp.get_precision('Account'), select=True),
               }

   def agg_righe_scad(self, cr, uid, ids, importo, context):
       if context is None:
	 context = {}
       for testata in self.pool.get('fiscaldoc.header').browse(cr, uid, ids):
           if testata.tipo_doc.tipo_documento <> 'DT':
            if testata.pagamento_id.id:
                lines = self.pool.get('account.payment.term.line').search(cr, uid, [('payment_id', "=", testata.pagamento_id.id)])
                if testata.partner_id.id:
		  context['partner_id']= testata.partner_id.id
		#import pdb;pdb.set_trace()
                scadenze = self.pool.get('account.payment.term').compute(cr, uid, testata.pagamento_id.id, importo, testata.data_documento, context)
                if scadenze:
                    for scadenza in scadenze:
                        riga_scad = {
                                    'name':ids[0],
                                    'tipo_scadenza':scadenza[2],
                                    'data_scadenza':scadenza[0],
                                    'importo_scadenza':arrot(cr,uid,scadenza[1],dp.get_precision('Account')),
                                    #'generato_effetto':False,
                                }
                        #~ print scadenza[0] +' '+testata.name +' '+testata.partner_id.name
                        res = self.create(cr, uid, riga_scad)

       return True


FiscalDocScadenze()

class FiscalDocIva(osv.osv):
    _name = "fiscaldoc.iva"
    _description = "Castelleto Iva Documenti"
    _columns = {
             'name': fields.many2one('fiscaldoc.header', 'Numero Documento', required=True, ondelete='cascade', select=True, readonly=True),
             'codice_iva':fields.many2one('account.tax', 'Codice Iva', readonly=False, required=True),
             'imponibile':fields.float("Totale Imponibile",digits_compute=dp.get_precision('Account')),
             'imposta':fields.float("Totale Imponibile", digits_compute=dp.get_precision('Account')),
               }
    _rec_name = 'name'


    def agg_righe_iva(self, cr, uid, ids, context):

        def get_perc_iva(self, cr, uid, ids, idiva, context):
            dati = self.pool.get('account.tax').read(cr, uid, [idiva], (['amount', 'type']), context=context)
            return dati[0]['amount']



        #import pdb;pdb.set_trace()
        # PRIMA SCORRE TUTTE LE RIGHE DI ARTICOLI
        lines = self.pool.get('fiscaldoc.righe').search(cr, uid, [('name', '=', ids)])
        righe_iva = {}
        for riga in self.pool.get('fiscaldoc.righe').browse(cr, uid, lines, context=context):
          #import pdb;pdb.set_trace()
          if riga.codice_iva.id:
            if riga.name.sconto_partner or riga.name.sconto_pagamento:
                    netto = riga.totale_riga
                    if riga.name.sconto_partner:
                        netto = netto-(netto*riga.name.sconto_partner/100)
                        netto = arrot(cr,uid,netto,dp.get_precision('Account'))
                    if riga.name.sconto_pagamento:
                        netto = netto-(netto*riga.name.sconto_pagamento/100)
                        netto = arrot(cr,uid,netto,dp.get_precision('Account'))
            else:
                    netto = riga.totale_riga
            netto = arrot(cr,uid,netto,dp.get_precision('Account'))

            if righe_iva.get(riga.codice_iva.id, False):
                # esiste gia la riga con questo codice
                dati_iva = righe_iva[riga.codice_iva.id]
                #import pdb;pdb.set_trace()
                dati_iva['imponibile'] = dati_iva['imponibile'] + netto
                righe_iva[riga.codice_iva.id] = dati_iva
            else:
                dati_iva = {'imponibile':arrot(cr,uid,netto,dp.get_precision('Account'))}
                righe_iva.update({riga.codice_iva.id:dati_iva})
        # QUI DEVE CALCOLARE LE POSIZIONI IVA DI TUTTE LE SPESE ACCESSORIE
        id = ids[0]
        testata = self.pool.get('fiscaldoc.header').browse(cr, uid, id)
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.id
        codici_iva_accessori = self.pool.get('res.company').read(cr, uid, company_id , (['civa_spe_inc', 'civa_spe_imb', 'civa_spe_tra', 'civa_fc']), context=context)
        if testata._columns.get('cod_esenzione_iva',False):
            esenzione = testata.cod_esenzione_iva
        else:
            esenzione = False
        if testata.spese_incasso:
          if codici_iva_accessori['civa_spe_inc'][0] or esenzione:
            #import pdb;pdb.set_trace()
            if esenzione:
             if righe_iva.get(esenzione.id, False):
                # esiste gia la riga con questo codice
                dati_iva = righe_iva[esenzione.id]
                dati_iva['imponibile'] = dati_iva['imponibile'] + testata.spese_incasso
                righe_iva[esenzione.id] = dati_iva
             else:
                dati_iva = {'imponibile':testata.spese_incasso}
                righe_iva.update({esenzione.id:dati_iva})


            else:
             if righe_iva.get(codici_iva_accessori['civa_spe_inc'][0], False):
                # esiste gia la riga con questo codice
                dati_iva = righe_iva[codici_iva_accessori['civa_spe_inc'][0]]
                dati_iva['imponibile'] = dati_iva['imponibile'] + testata.spese_incasso
                righe_iva[codici_iva_accessori['civa_spe_inc'][0]] = dati_iva
             else:
                dati_iva = {'imponibile':testata.spese_incasso}
                righe_iva.update({codici_iva_accessori['civa_spe_inc'][0]:dati_iva})

        if testata.spese_imballo:
          if codici_iva_accessori['civa_spe_imb'][0] or esenzione :
            if esenzione:
             if righe_iva.get(esenzione.id, False):
                # esiste gia la riga con questo codice
                dati_iva = righe_iva[esenzione.id]
                dati_iva['imponibile'] = dati_iva['imponibile'] + testata.spese_iballo
                righe_iva[esenzione.id] = dati_iva
             else:
                dati_iva = {'imponibile':testata.spese_imballo}
                righe_iva.update({esenzione.id:dati_iva})

            else:


             if righe_iva.get(codici_iva_accessori['civa_spe_imb'][0], False):
                # esiste gia la riga con questo codice
                dati_iva = righe_iva[codici_iva_accessori['civa_spe_imb'][0]]
                dati_iva['imponibile'] = dati_iva['imponibile'] + testata.spese_imballo
                righe_iva[codici_iva_accessori['civa_spe_imb'][0]] = dati_iva
             else:
                dati_iva = {'imponibile':testata.spese_imballo}
                righe_iva.update({codici_iva_accessori['civa_spe_imb'][0]:dati_iva})

        if testata.spese_trasporto:

          if codici_iva_accessori['civa_spe_tra'][0] or esenzione:
            if esenzione:
             if righe_iva.get(esenzione.id, False):
                # esiste gia la riga con questo codice
                dati_iva = righe_iva[esenzione.id]
                dati_iva['imponibile'] = dati_iva['imponibile'] + testata.spese_trasporto
                righe_iva[esenzione.id] = dati_iva
             else:
                dati_iva = {'imponibile':testata.spese_trasporto}
                righe_iva.update({esenzione.id:dati_iva})


            else:


             if righe_iva.get(codici_iva_accessori['civa_spe_tra'][0], False):
                # esiste gia la riga con questo codice
                dati_iva = righe_iva[codici_iva_accessori['civa_spe_tra'][0]]
                dati_iva['imponibile'] = dati_iva['imponibile'] + testata.spese_trasporto
                righe_iva[codici_iva_accessori['civa_spe_tra'][0]] = dati_iva
             else:
                dati_iva = {'imponibile':testata.spese_trasporto}
                righe_iva.update({codici_iva_accessori['civa_spe_tra'][0]:dati_iva})

        # HA FINITO DI CALCOLARE GLI IMPONIBILI ORA CALCOLA L'IMPOSTA RIGA PER RIGA
        for rg_iva in righe_iva:
            perc_iva = get_perc_iva(self, cr, uid, ids, rg_iva, context)
            dati_iva = righe_iva[rg_iva]
            #Andre@
            #AGGIUNTO PER LA GESTIONE DEL FLAG OMAGGI

            if dati_iva['imponibile'] < 0:
                dati_iva.update({'imposta':dati_iva['imponibile'] * perc_iva * -1})
                dati_iva['imposta']= arrot(cr,uid, dati_iva['imposta'],dp.get_precision('Account'))
                righe_iva[rg_iva] = dati_iva
            else:
                dati_iva.update({'imposta':dati_iva['imponibile'] * perc_iva})
                dati_iva['imposta']= arrot(cr,uid, dati_iva['imposta'],dp.get_precision('Account'))
                righe_iva[rg_iva] = dati_iva

        # ORA SCRIVE I RECORD CANCELLA COMUNQUE TUTTE LE REGHE E POI LE RICREA AGGIORNATE QUESTO SALVA LA CONDIZIONE IN CUI SCOMPAIA COMPLETAMENTE
        # UNA RIGA DI ALIQUOTA IVA
        lines = self.pool.get('fiscaldoc.iva').search(cr, uid, [('name', '=', ids)])
        if lines:
            res = self.pool.get('fiscaldoc.iva').unlink(cr, uid, lines, context)
        else:
            # E' LA CREATE QUINDI CREA LE SCADENZE
            totaledoc = 0
            for riga in righe_iva:
                totaledoc += righe_iva[riga]['imponibile'] + righe_iva[riga]['imposta']

            ok = self.pool.get('fiscaldoc.scadenze').agg_righe_scad(cr, uid, ids, totaledoc, context)

        for riga in righe_iva:

            record = {
                    'name':ids[0],
                    'codice_iva':riga,
                    'imponibile':righe_iva[riga]['imponibile'],
                    'imposta':righe_iva[riga]['imposta'],
                    }
            res = self.pool.get('fiscaldoc.iva').create(cr, uid, record)
        #import pdb;pdb.set_trace()
        return True

FiscalDocIva()

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
                'str_sconto_partner':fields.char('Stringa Sconto', size=20),
                'sconto_partner':fields.float('Sconto Partner', digits=(9, 3)),
                'spedizione':fields.many2one('fiscaldoc.spedizioni', 'Modalità di Consegna/Spedizione ', required=False, help="Consegna "),
                'meseprimoescluso': fields.integer('1 Mese Escluso'),
                'mesesecondoescluso': fields.integer('2 Mese Escluso'),
                'giornoescluso': fields.integer('Giorno Escluso'),
                'credagenti':fields.char('Crediti Agenti',size=1),
                'bloccato':fields.boolean('Partner Bloccato'),
                'moratoria':fields.boolean('Partner in Contenzioso'),
                'fatt_once':fields.boolean('Fatturazione singola', help="Se selezionato in fase di fatturazione differita sara' generata una fattura per ogni DDT"),

                }

res_partner()

class stock_picking(osv.osv):
    _inherit = "stock.picking"
    _columns = {
              'doc_id': fields.many2one('fiscaldoc.header', 'Documento', ondelete='set null', select=True),
               }

    def unlink(self, cr, uid, ids, context=None):
        move_obj = self.pool.get('stock.move')
        if context is None:
            context = {}
        for pick in self.browse(cr, uid, ids, context=context):
          if not context.get('document', False): # verifica se è stato lanciato da un documento

            if pick.state in ['done', 'cancel']:
                raise osv.except_osv(_('Error'), _('You cannot remove the picking which is in %s state !') % (pick.state,))
            elif pick.state in ['confirmed', 'assigned', 'draft']:
                ids2 = [move.id for move in pick.move_lines]
                ctx = context.copy()
                ctx.update({'call_unlink':True})
                if pick.state != 'draft':
                    #Cancelling the move in order to affect Virtual stock of product
                    move_obj.action_cancel(cr, uid, ids2, ctx)
                #Removing the move
                move_obj.unlink(cr, uid, ids2, ctx)
          else:
            # è stato lanciato da un documento deve eseguire il controllo se ci sono altri movimenti non annullati pqr qualche motivo
            ids2 = [move.id for move in pick.move_lines]
            if ids2:
              raise osv.except_osv(_('Error'), _('Ci sono righe non rimosse nel picking  %s !') % (pick.name,))
            stato = {'state':'draft'}
            ok = self.pool.get('stock.picking').write(cr, uid, [pick.id], stato)
        return super(stock_picking, self).unlink(cr, uid, ids, context=context)




stock_picking()

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
              'doc_line_id': fields.many2one('fiscaldoc.righe', 'Riga Documento', ondelete='set null', select=True, readonly=True),
               }

    def write(self, cr, uid, ids, vals, context=None):
        # ho riscritto la write xchè fa un controllo che se administrator non è = ad id 1 il controllo non va che cazzata
        if False : #uid != 1 :
            frozen_fields = set(['product_qty', 'product_uom', 'product_uos_qty', 'product_uos', 'location_id', 'location_dest_id', 'product_id'])
            for move in self.browse(cr, uid, ids, context=context):
                if move.state == 'done':
                    if frozen_fields.intersection(vals):
                        raise osv.except_osv(_('Operation forbidden'),
                                             _('Quantities, UoMs, Products and Locations cannot be modified on stock moves that have already been processed (except by the Administrator)'))
        return  super(stock_move, self).write(cr, uid, ids, vals, context=context)


    def unlink(self, cr, uid, ids, context=None):
        #import pdb;pdb.set_trace()
        if context is None:
            context = {}
        ctx = context.copy()
        for move in self.browse(cr, uid, ids, context=context):
          # controlla il context se lo lancia un documento lo cancella
           if not context.get('document', False):
            if move.state != 'draft' and not ctx.get('call_unlink', False):
                raise osv.except_osv(_('UserError'),
                        _('You can only delete draft moves.'))
           else: # passa in draft il record prima di cancellarlo
              stato = {'state':'draft'}
              ok = self.pool.get('stock.move').write(cr, uid, [move.id], stato)
        return super(stock_move, self).unlink(
            cr, uid, ids, context=ctx)
stock_move()


class sale_order(osv.osv):
    _inherit = "sale.order"

    _columns = {
              'spese_di_trasporto': fields.float('Spese di Trasporto', required=False, digits_compute=dp.get_precision('Sale Price'), readonly=True, states={'draft': [('readonly', False)]}),
               }

    def onchange_partner_id(self, cr, uid, ids, part):
        res = super(sale_order,self).onchange_partner_id(cr, uid, ids, part)
        if not part:
             return {'value': {'partner_invoice_id': False, 'partner_shipping_id': False, 'partner_order_id': False, 'payment_term': False, 'fiscal_position': False}}
        val = res.get('value',False)
        if val:
            part_obj = self.pool.get('res.partner').browse(cr,uid,part)
            if part_obj.str_sconto_partner: #IL PARTNER HA UNA STRINGA DI SCONTO
                val['str_sconto_partner']=part_obj.str_sconto_partner
            if part_obj.sconto_partner: #IL PARTNER HA UNA PERCENTUALE DI SCONTO NUMERICA
                val['sconto_partner']=part_obj.sconto_partner
            if part_obj.bloccato:
                                    warning = {
                                    'title': 'ATTENZIONE !',
                                    'message':'PARTNER BLOCCATO ',}
                                    val =  {'partner_id':False,'partner_invoice_id': False, 'partner_shipping_id': False, 'partner_order_id': False, 'payment_term': False, 'fiscal_position': False}
            else:
                warning = {}
        return {'value': val,'warning':warning}

sale_order()
