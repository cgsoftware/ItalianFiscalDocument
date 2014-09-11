# -*- encoding: utf-8 -*-


import decimal_precision as dp
import pooler
import time
from tools.translate import _
from osv import osv, fields
from tools.translate import _


def doc_id_create(self, cr, uid,tipo_doc,data_doc,progr,numdoc):
    # import pdb;pdb.set_trace()
    name_tipo = self.pool.get('fiscaldoc.causalidoc').read(cr,uid,[tipo_doc],["name"])
    anno = data_doc[0:4]
    name_progr = self.pool.get('fiscaldoc.tipoprogressivi').read(cr,uid,[progr],["name"])
    return name_tipo[0]['name']+"-"+anno+"-"+name_progr[0]['name']+"-"+'%%0%sd' % 8 %  numdoc

def doc_prog_create(self, cr, uid, tipo_doc, data_doc, progr, numdoc):
    # import pdb;pdb.set_trace()
    name_tipo = self.pool.get('fiscaldoc.causalidoc').read(cr, uid, [tipo_doc], ["name"])
    anno = data_doc[0:4]
    name_progr = self.pool.get('fiscaldoc.tipoprogressivi').read(cr, uid, [progr], ["name"])
    return  anno + "-" + name_progr[0]['name'] + "-" + '%%0%sd' % 8 % numdoc



class evasione_ordini(osv.osv_memory):
    _name = 'evasione.ordini'
    _description = 'Testata con info da chiedere per emettere il documento di uscita'
    _columns = {
         'name':fields.many2one('fiscaldoc.causalidoc', 'Tipo Documento',required=True),
         'data_doc':fields.date('Data Documento', required=True, readonly=False),
         'righe_da_evadere': fields.one2many('evasione.ordini.righe', 'testa', 'Righe Articoli in Evasione'),
 
         
    }
  
  
  
    def view_init(self, cr, uid, fields_list, context=None):
        #~ import pdb;pdb.set_trace()
        res = super(evasione_ordini, self).view_init(cr, uid, fields_list, context=context)
        
        move_obj = self.pool.get('stock.move')  
        first = True
        if context is None:
            context = {}
        for move in move_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            if move.state in ('done', 'cancel'):
                raise osv.except_osv(_('Invalid action !'), _('Non puoi Evadere righe già evase !'))
            if first:
              first = False
              old_partner = move.partner_id
            if move.partner_id <> old_partner:
              raise osv.except_osv(_('Invalid action !'), _('Non puoi Evadere righe da partner diversi !'))
            if move.origin==False:
               raise osv.except_osv(_('Invalid action !'), _('Non puoi Evadere righe che non hanno documenti(ordini) sorgenti !'))
            
        return res
    
    
    def __get_caudoc(self,cr, uid, context=None):
        move_obj = self.pool.get('stock.move')  
        if context is None:
            context = {}
        First = True
        for riga in move_obj.browse(cr, uid, context.get('active_ids', []), context=context):
          if First:
            # è il primo record deve inserire prima una testata
            res = riga.company_id.caudoc_evao.id
                   
        #import pdb;pdb.set_trace()
        return res 
      
      
    def __create_partial_move_memory(self, riga):
        
                if riga.partner_id.bloccato:
                    #import pdb;pdb.set_trace() 
                    raise osv.except_osv(_('Invalid action !'), _('CLIENTE BLOCCATO PER MOTIVI AMMINISTRATIVI !'))
                    rg_eva={}
                else:
                    rg_eva = {
                          'name':riga.name,
                          'product_id':riga.product_id.id,
                          'product_qty':riga.product_qty,
                          'qty_ship':riga.product_qty,
                          'picking_id':riga.picking_id.id,
                          'company_id':riga.company_id.id,
                          'partner_id':riga.partner_id.id,
                          'origin':riga.origin,
                          'riga_mov_id':riga.id,
                          'sale_line_id':riga.sale_line_id.id,
                          }
                 #import pdb;pdb.set_trace()
                return rg_eva
     
    def __get_active_stock_moves(self,cr, uid, context=None):
        #import pdb;pdb.set_trace()
        move_obj = self.pool.get('stock.move')
        if context is None:
            context = {}
               
        res = []
        for move in move_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            if move.state in ('done', 'cancel'):
                continue           
            res.append(self.__create_partial_move_memory(move))
            
        return res
      
    def calcola_spese_inc(self, cr, uid, ids,pagamento_id):
            spese = 0
            #import pdb;pdb.set_trace()  
            if pagamento_id:
                lines = self.pool.get('account.payment.term.line').search(cr,uid,[('payment_id',"=",pagamento_id)])
                spese = 0
                for riga in self.pool.get('account.payment.term.line').browse(cr, uid, lines):
                    spese = spese +riga['costo_scadenza']
            return spese   
             
    def check_move_state(self, cr, uid,riga, ids, context=None):
 
      if riga.qty_ship >= riga.product_qty:
        # sta evadendo tutto quindi restituisce la  lo stesso id
        return riga.riga_mov_id
      else:
        # l'evasione è parziale
        mov_riga = self.pool.get('stock.move').read(cr,uid,[riga.riga_mov_id])[0]
        #import pdb;pdb.set_trace()
        new_mov = {
                        'name': mov_riga['name'],
                        'picking_id': mov_riga['picking_id'][0],
                        'product_id': mov_riga['product_id'][0],
                        'product_qty': riga.qty_ship,
                        'product_uom': mov_riga['product_uom'][0],
                        'product_uos_qty': riga.qty_ship,
                        'product_uos': mov_riga['product_uos'][0],
                        'address_id':  mov_riga['address_id'][0],
                        'location_id': mov_riga['location_id'][0],
                        'location_dest_id': mov_riga['location_dest_id'][0],
                        'tracking_id': False,
                        'state': 'done',
                        #'state': 'waiting',
                        'company_id': mov_riga['company_id'][0],
                        }
              
        id_new_mov = self.pool.get('stock.move').create(cr,uid,new_mov)
        if not id_new_mov:
            # c'è stato un errore di scrittura
            raise osv.except_osv(_('Invalid action !'), _('IMPOSSIBILE SCRIVERE IL MOVIMENTO DI MAGAZZINO COLLEGATO !'))
        else:
            # aggiorna la qta da evadere ancora
            old_mov = {
                       'product_qty':riga.product_qty-riga.qty_ship,
                       'product_uos_qty':riga.product_qty-riga.qty_ship,
                       }
            wr = self.pool.get('stock.move').write(cr,uid,[riga.riga_mov_id],old_mov)
            return id_new_mov
     
    def check_sottoscorta(self,cr, uid, ids,context=None):
        ok = True
        #import pdb;pdb.set_trace() 
        if not context:
            context={}           
        if ids:
            testa = self.pool.get('evasione.ordini').browse(cr,uid,ids)
            testa = testa[0]
            mov_riga = self.pool.get('stock.move')
            riga1= testa.righe_da_evadere[0]
            company_id = riga1.partner_id.company_id
            if company_id.flag_no_neg: 
                for riga in testa.righe_da_evadere:
                    if riga.product_id.type=='product':
                        context['location']= mov_riga.browse(cr,uid,riga.riga_mov_id).location_id.id
                        if riga.product_id.qty_available-riga.qty_ship <0:
                            ok=False
        return ok
  
    def genera(self, cr, uid, ids, context=None):
     #import pdb;pdb.set_trace()
     if self.check_sottoscorta(cr, uid, ids, context):
      
      #prepara i dati di testata
      Doc_obj = self.pool.get('fiscaldoc.header')
      Riga_obj = self.pool.get('fiscaldoc.righe')
      Order_obj= self.pool.get('sale.order')
      testa = self.pool.get('evasione.ordini').browse(cr,uid,ids)
      testa = testa[0]
      righe= testa.righe_da_evadere
      riga1 = righe[0]
      part= riga1.partner_id
      TestaOrdine = riga1.sale_line_id.order_id
      part= TestaOrdine.partner_id
      #addr = self.pool.get('res.partner').address_get(cr, uid, [part.id], ['delivery', 'invoice', 'contact'])
      pricelist = TestaOrdine.pricelist_id.id
      # part.property_product_pricelist and part.property_product_pricelist.id or False      
      pagamento_id = TestaOrdine.payment_term.id
      # part.property_payment_term and part.property_payment_term.id or False
      agente = part.user_id and part.user_id.id or uid 
          
      if part.bank_ids:
            banca_cliente = part.bank_ids[0].bank.id
      else:
            banca_cliente = False
      #import pdb;pdb.set_trace()
      tipo = testa.name
      progr = tipo.progr_id_default.id
      numdoc = Doc_obj.trova_numdoc(cr,uid,ids,tipo.id,testa.data_doc,progr)
      doc_id= doc_id_create(self,cr, uid,tipo.id,testa.data_doc,progr,numdoc) 
      doc_prog= doc_prog_create(self, cr, uid, tipo.id,testa.data_doc,progr,numdoc)
      record_doc={
                  'data_documento':testa.data_doc,
                  'partner_id':part.id,
                  'progr':progr,
                  'partner_indfat_id': TestaOrdine.partner_invoice_id.id,
                  'partner_indcons_id': TestaOrdine.partner_shipping_id.id,
                  'pagamento_id':pagamento_id,
                  'sconto_pagamento':TestaOrdine.payment_term.sconto,
                  'agente':agente,
                  'str_sconto_partner':part.str_sconto_partner,
                  'sconto_partner':part.sconto_partner,
                  'spedizione':part.spedizione.id,
                  'vettore':part.property_delivery_carrier.id,
                  'porto_id':part.carriage_condition_id.id,
                  'aspetto_esteriore_id':part.goods_description_id.id,
                  'banca_patner':banca_cliente,
                  'valuta':False,
                  'ora_trasporto':False,
                  'spese_imballo':False,
                  'spese_trasporto':TestaOrdine.spese_di_trasporto,
                  'totale_peso':False,
                  'data_trasporto':False,
                  'banca_azienda':False,
                  'note_di_trasporto':False,
                  'totale_bolli':False,
                  'tipo_doc':testa.name.id,
                  'totale_colli':0,
                  'magazzino_id':tipo.deposito_default.id,
                  'numdoc':numdoc,
                  'causale_del_trasporto_id':tipo.causale_del_trasporto_id.id,
                  'magazzino_destinazione_id':tipo.deposito_destinazione_default.id,
                  'name':doc_id,
                  'doc_prog':doc_prog,
                  'totale_acconti':False,
                  'spese_incasso':self.calcola_spese_inc(cr,uid,ids,pagamento_id)
                  }
      ese_iva = False
      if 'cod_esenzione_iva' in Doc_obj._columns:
          if part.scad_esenzione_iva >= testa.data_doc:
            record_doc['cod_esenzione_iva'] = part.cod_esenzione_iva.id
            record_doc['scad_esenzione_iva'] = part.scad_esenzione_iva
            ese_iva = True
            codice_ese = part.cod_esenzione_iva.id
      if 'esenzione_conai' in Doc_obj._columns:
          if part.scad_esenzione >= testa.data_doc:
            record_doc['esenzione_conai'] = part.esenzione.id
            record_doc['scad_esenzione_conai'] = part.scad_esenzione
      
      if pricelist:
            record_doc['listino_id'] = pricelist  
      righe_articoli = []  
      
      #PREPARTO LA PRIMA RIGA CHE RIPORTA I NUMERI DEGLI ORDINI EVASI
      riga_doc ={}
      lista_ordini= []
      for riga in righe:
        lista_ordini.append((riga.origin))
        art_ddt = self.pool.get('res.company').read(cr, uid,[riga.company_id.id],(['art_des_ddt']))
        art_ord = self.pool.get('res.company').read(cr, uid,[riga.company_id.id],(['art_des_ord']))
      #ELIMINO I DUPLICATI
      #~ import pdb; pdb.set_trace()
      listanew = [h for h in set(lista_ordini)]
      #CONVERTO IN STRINGA
      import string
      ordini_evasi = string.join(listanew)
      #PREPARO LA PRIMA RIGA CHE RIPORTA I DATI DI EVASIONE 
      #~ import pdb; pdb.set_trace()
      art_ord_id = art_ord[0]['art_des_ord'][0]
      
      art = self.pool.get('product.product').browse(cr,uid,[art_ord_id])[0]
      codice = art.taxes_id[0].id
      if ese_iva:
        codice = codice_ese
      des = art.name +' '+str(ordini_evasi)
      riga_doc={
                    'product_id': art_ord_id,
                    'product_uom_qty':1,
                    'product_uom':art.product_tmpl_id.uom_id.id,
                    'contropartita':art.categ_id.property_account_income_categ.id,
                    'descrizione_riga':des,
                    'codice_iva':codice
                    }
      riga_det = (0,0,riga_doc)
      righe_articoli.append(riga_det) 
      
      # prepara le righe del documento
      #~ import pdb; pdb.set_trace()
      for riga in righe:
        #import pdb; pdb.set_trace()
        riga_doc ={}
        riga_ord = riga.sale_line_id
        righe_tasse_articolo = self.pool.get('account.fiscal.position').map_tax(cr, uid, False, riga.product_id.taxes_id)
        if righe_tasse_articolo:
          codice_iva = righe_tasse_articolo[0]
          
        else:
          codice_iva = False
        if ese_iva:
          codice_iva = codice_ese
        riga_doc={
                    'product_id':riga.product_id.id,
                    'product_uom_qty':riga.qty_ship,
                    'discount_riga':riga_ord.discount,
                    'totale_riga':riga_ord.price_subtotal,
                    'product_prezzo_unitario':riga_ord.price_unit,
                    'product_uom':riga_ord.product_uom.id,
                    'contropartita':riga.product_id.categ_id.property_account_income_categ.id,
                    'prezzo_netto':riga_ord.price_unit-(riga_ord.price_unit*riga_ord.discount/100),
                    'codice_iva':codice_iva,
                    'flag_omaggi':False,
                    'sconti_riga':riga_ord.string_discount,
                    'descrizione_riga':riga_ord.name,
                    'move_ids':self.check_move_state(cr, uid,riga, ids, context),# riga.riga_mov_id,
                    'order_line_id':riga.sale_line_id.id
                    }
        
        if 'flag_multi_creato' in Riga_obj._columns:
            riga_doc['flag_multi_creato']=True   
        if 'commission_rate' in self.pool.get('sale.order.line')._columns:           
            riga_doc['perc_provv']=riga_ord.commission_rate        
        else:
            riga_doc['perc_provv']=False
        #~ import pdb; pdb.set_trace()
        if 'conai' in riga_ord.product_id._columns:
            art_obj = riga_ord.product_id
            if art_obj.product_tmpl_id.conai.id:
              riga_doc['cod_conai'] = art_obj.product_tmpl_id.conai.id
              riga_doc['peso_conai'] =  art_obj.production_conai_peso * riga.qty_ship
              riga_doc['prezzo_conai'] = art_obj.product_tmpl_id.conai.valore
              riga_doc['totale_conai'] = riga_doc['peso_conai']*  riga_doc['prezzo_conai']
        if 'extra_price_variant' in Riga_obj._columns:
            riga_doc['extra_price_variant'] = riga_ord.extra_price_variant
            
        riga_det = (0,0,riga_doc)
        righe_articoli.append(riga_det)
      record_doc.update({'righe_articoli':righe_articoli})
      #import pdb;pdb.set_trace()
      id_doc = Doc_obj.create(cr,uid,record_doc)
      context.update({'doc_id':[id_doc]})
      
      return {
            'name': 'Apri Documento',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'open.fiscaldoc',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }
     else:
           raise osv.except_osv(_('Invalid action !'), _('IMPOSSIBILE SCRIVERE IL MOVIMENTO PRESENZA DI ARTICOLI IN SOTTOSCORTA !'))       
    
    _defaults = {

                 'righe_da_evadere' : __get_active_stock_moves,
                 'name':__get_caudoc,
                 'data_doc' : lambda *a : time.strftime('%Y-%m-%d %H:%M:%S'),
                 }
    
evasione_ordini()  

class evasione_ordini_righe(osv.osv_memory):
    _name = 'evasione.ordini.righe'
    _description = 'Legge tutte le righe di un cliente da evadere'
    _columns = {
         'name': fields.char('Name', size=64, required=True, select=True),
         'testa': fields.many2one('evasione.ordini', 'Tipo Documento', required=True, ondelete='cascade', select=True,),
         'product_id': fields.many2one('product.product', 'Articolo', required=True, select=True, domain=[('type','<>','service')]),
         'product_qty': fields.float('Qta Prevista', digits_compute=dp.get_precision('Product UoM'), required=True,),
         'qty_ship':fields.float(("in Consegna"),digits_compute=dp.get_precision('Product UoM'),required=True),
         'picking_id': fields.many2one('stock.picking', 'Referimeti', select=True),        
         'company_id': fields.many2one('res.company', 'Azienda', required=True, select=True),
         'partner_id': fields.related('picking_id','partner_id',type='many2one', relation="res.partner", string="Cli/For", store=True, select=True),
         'backorder_id': fields.related('picking_id','backorder_id',type='many2one', relation="stock.picking", string="Back Order", select=True),
         'origin': fields.related('picking_id','origin',type='char', size=64, relation="stock.picking", string="Origine", store=True),
         'riga_mov_id':fields.float("id riga mov"),
         'sale_line_id': fields.many2one('sale.order.line', 'Sales Order Line', ondelete='set null', select=True),
         
    }
    
    
     
evasione_ordini_righe()    




class open_fiscaldoc(osv.osv_memory):
    _name = "open.fiscaldoc"
    _description = "Apre il Documento Generato"

    def open_doc(self, cr, uid, ids, context=None):

        """
             To open invoice.
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs if we want more than one
             @param context: A standard dictionary
             @return:

        """
 #       if context is None:
 #           context = {}
 #       mod_obj = self.pool.get('ir.model.data')
 #       for advance_pay in self.browse(cr, uid, ids, context=context):
 #           form_res = mod_obj.get_object_reference(cr, uid, 'fiscaldoc.header', 'invoice_form')
 #           form_id = form_res and form_res[1] or False
 #           tree_res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_tree')
 #           tree_id = tree_res and tree_res[1] or False

        return {
            'name': _('Documenti di Vendita'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'fiscaldoc.header',
            'res_id': int(context['doc_id'][0]),
            'view_id': False,
            'context': context,
            'type': 'ir.actions.act_window',
         }

#          'views': [(form_id, 'form'), (tree_id, 'tree')],

open_fiscaldoc()
