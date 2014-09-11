# -*- encoding: utf-8 -*-


import decimal_precision as dp
import pooler
import time
from tools.translate import _
from osv import osv, fields
from tools.translate import _
import unicodedata


def _ListaTipiDocumento(self, cr, uid, context={}):
    return [("DT", "Documento di Trasporto")]
             #('FA', 'Fattura Accompagnatoria'), ('FI', 'Fattura Immediata'), ('FD', 'Fattura Differita'), ('ND', 'Nota di Addebito'), ('NC', 'Nota di Credito'), ('FC', 'Fattura/Ricevuta Fiscale'), ('RF', 'Ricevuta Fiscale')]


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



class generazione_differite(osv.osv_memory):
    _name = 'generazione.differite'
    _description = 'Genera fatture differite '
    _columns = {
         'cauddt':fields.selection(_ListaTipiDocumento, 'Tipo DDT',required=True),
         'tipo_operazione':fields.selection((('C', 'Cliente'), ('F', 'Fornitore'), ('A', 'Altro')), 'Tipo Operazione',required=True),
         'tipo_azione':fields.selection((('VE', 'Vendita'), ('AC', 'Acquisto'), ('CV', 'Conto/Visone'),('NS', 'Non Specificato'),('RE', 'Resi')), 'Tipo Azione',required=True),
         'caufd':fields.many2one('fiscaldoc.causalidoc', 'Tipo Fattura Differita',required=True),
         'prog_fd':fields.many2one('fiscaldoc.tipoprogressivi', 'Tipo Progressivo Fattura Differita',required=True),
         'data_comp_ddt':fields.date('Data Competenza Iva DDT', required=True, readonly=False),
         'data_doc':fields.date('Data Documento da Generare', required=True, readonly=False),
         'primo_num_doc':fields.integer('Numero Documento', required=True, readonly=False),
         'flag_raggruppa': fields.boolean('Raggruppa Per Articolo', help="Se attivo nella fattura saranno sommati gli articoli con lo stesso prezzo di vendita"),
         'da_dataddt':fields.date('Da Data  DDT', required=True, readonly=False),
         'a_dataddt':fields.date('A Data DDT', required=True, readonly=False),
         'da_numddt':fields.integer('Da DDT Num.', required=True, readonly=False),
         'a_numddt':fields.integer('A DDT Num.', required=True, readonly=False),
         'da_partner':fields.many2one('res.partner', 'Da Partner',required=True),
         'a_partner':fields.many2one('res.partner', 'A Partner',required=True),
         }



    def view_init(self, cr, uid, fields_list, context=None):
        # import pdb;pdb.set_trace()
        res = super(generazione_differite, self).view_init(cr, uid, fields_list, context=context)

        return res


    def _get_cauddt(self,cr, uid, context=None):
        cau_obj = self.pool.get('fiscaldoc.causalidoc')

        #import pdb;pdb.set_trace()
        return cau_obj.search(cr, uid, [('tipo_documento','=','DT')])[0]

    def _get_caufd(self,cr, uid, context=None):
        cau_obj = self.pool.get('fiscaldoc.causalidoc')

        #import pdb;pdb.set_trace()
        return cau_obj.search(cr, uid, [('tipo_documento','=','FD')])[0]


    def _get_prog(self,cr, uid, context=None):
        FdId = self._get_caufd(cr, uid, context)
        cau_obj = self.pool.get('fiscaldoc.causalidoc')

        #import pdb;pdb.set_trace()
        return cau_obj.browse(cr, uid, [FdId], context=context)[0].progr_id_default.id

    def _get_num_prog(self,cr, uid, context=None):
        prog_id = self._get_prog(cr, uid, context)
        prog_rec = self.pool.get('fiscaldoc.tipoprogressivi')
        #import pdb;pdb.set_trace()
        data_doc =  time.strftime('%Y-%m-%d %H:%M:%S')
        anno=data_doc[0:4]
        ultimo = prog_rec._get_ult_progr(cr,uid,[prog_id],prog_id,anno)


        return ultimo['ultimo_numero']+1

    def _get_da_ddt(self,cr, uid, context=None):
       data_doc =  time.strftime('%Y-%m-%d %H:%M:%S')
       return data_doc[0:4]+"-01-01"+data_doc[10:]

    def _get_da_partner(self,cr, uid, context=None):
       lista =self.pool.get('res.partner').search(cr, uid, [])
       return lista[0]

    def _get_a_partner(self,cr, uid, context=None):
         lista =self.pool.get('res.partner').search(cr, uid, [])
         lunghezza = len(lista)
         return lista[lunghezza-1]


    def calcola_spese_inc(self, cr, uid, ids,pagamento_id):
            spese = 0
            #import pdb;pdb.set_trace()
            if pagamento_id:
                lines = self.pool.get('account.payment.term.line').search(cr,uid,[('payment_id',"=",pagamento_id)])
                spese = 0
                for riga in self.pool.get('account.payment.term.line').browse(cr, uid, lines):
                    spese = spese +riga['costo_scadenza']
            return spese


    def allinea(self, cr, uid, ids, context=None):
	obj_fat= self.pool.get('fiscaldoc.header')
	cr.execute("""
	    SELECT target.id, address.openupgrade_7_migrated_to_partner_id
	    FROM %s as target,
		 res_partner_address as address
	    WHERE address.id = target.%s""" % ('fiscaldoc_header', 'partner_indfat_id'))
	for row in cr.fetchall():
	    cr.execute("""UPDATE  fiscaldoc_header  SET  partner_indfat_id =%s  where id =%s """%(row[1],row[0]))
	    #~ obj_fat.write(cr, uid, row[0], {'partner_indfat_id': row[1]})
	    print row

	cr.execute("""
	    SELECT target.id, address.openupgrade_7_migrated_to_partner_id
	    FROM %s as target,
		 res_partner_address as address
	    WHERE address.id = target.%s""" % ('fiscaldoc_header', 'partner_indcons_id'))
	for row in cr.fetchall():
	    cr.execute("""UPDATE  fiscaldoc_header  SET  partner_indcons_id =%s  where id =%s """%(row[1],row[0]))
	    #~ obj_fat.write(cr, uid, row[0], {'partner_indcons_id': row[1]})
	    print row
	    
        return {'type': 'ir.actions.act_window_close',}


    def genera(self, cr, uid, ids, context=None):
      #~ cod_iva = False
      #Verifica se ci sono DDT che soddisfano la Selezione
      selezione_obj=self.pool.get('generazione.differite').browse(cr,uid,ids)[0]
      ddt_obj = self.pool.get('fiscaldoc.header')
      ddt_obj_line= self.pool.get("fiscaldoc.righe")
      fattura_obj = self.pool.get('fiscaldoc.header')
      testa_ddt_ids = ddt_obj.search(cr,uid,[('differita_id',"=",False),
                                         #('tipo_doc','=',selezione_obj.cauddt.id),
                                         ('data_documento','>=',selezione_obj.da_dataddt),
                                         ('data_documento','<=',selezione_obj.a_dataddt),
                                         ('numdoc','>=',selezione_obj.da_numddt),
                                         ('numdoc','<=',selezione_obj.a_numddt),
                                       #  ('partner_id','>=',selezione_obj.da_partner), non funziona xchè lancia una sql e quindi paragona gli id non interpreta la browse
                                       #  ('partner_id','<=',selezione_obj.a_partner),
                                          ],order='partner_id,pagamento_id,data_documento,numdoc')
      ddt_ids = []
      # controlla la selezione sui partner
      #import pdb;pdb.set_trace()
      for testa in ddt_obj.browse(cr,uid,testa_ddt_ids):
          # questa replace('.','z') sostituisce il punto con la zeta al fine di ottenere lo stesso
          # ordinamento del database
        if testa.partner_id.name.lower().replace('.','z') >= selezione_obj.da_partner.name.lower().replace('.','z') and \
             testa.partner_id.name.lower().replace('.','z') <= selezione_obj.a_partner.name.lower().replace('.','z') \
             and testa.tipo_doc.tipo_documento == selezione_obj.cauddt  \
             and testa.tipo_doc.tipo_operazione == selezione_obj.tipo_operazione \
             and  testa.tipo_doc.tipo_azione==selezione_obj.tipo_azione and testa.tipo_doc.flag_fatturabile:
          ddt_ids.append(testa.id)
      if ddt_ids:         # trovati record
        # ELEMENTI DI ROTTURA SU NUOVA FATTURA SONO, PARTNER, INDIRIZZO DI FATTURAZIONE, IL PAGAMENTO, LA BANCA SE CAMBIA UNO DI QUESTI DATI DEVE CREARE UN NUOVO DOCUMENTO
        partner_corrente_id = 0
        indirizzo_corrente_id = 0
        pagamento_corrente_id = 0
        banca_corrente_id = 0
        testata_fattura={}
        ids_ddt_da_aggiornare=[]
        ids_fatture = []
        righe_articoli = []
        Primo = True
#        import pdb;pdb.set_trace()
        for testa_ddt_corrente in ddt_obj.browse(cr,uid,ddt_ids):
            #~ import pdb; pdb.set_trace()
          # CONTROLLO DELL'ESENZIONE IVA
          part = testa_ddt_corrente.partner_id
          scad_iva = False
          cod_iva = False
          if part.__contains__('cod_esenzione_iva'):
                #~ import pdb; pdb.set_trace()
                if part.cod_esenzione_iva:
                    if part.scad_esenzione_iva:
                        if part.cod_esenzione_iva and part.scad_esenzione_iva >= selezione_obj.data_doc or testa_ddt_corrente.data_documento <= part.scad_esenzione_iva:
                            cod_iva = part.cod_esenzione_iva.id
                            scad_iva = part.scad_esenzione_iva
                    else:
                        #~ import pdb; pdb.set_trace()
                        raise osv.except_osv(_('Errore'), _('NON É IMPOSTATA LA DATA DI SCADENZA ESENZIONE IVA SUL PARTNER '
                                   +(unicodedata.normalize('NFKD',  part.name)).encode('ascii','ignore') or '' ))

          if (partner_corrente_id<> testa_ddt_corrente.partner_id.id
              # or indirizzo_corrente_id<>testa_ddt_corrente.partner_indfat_id.id
              or pagamento_corrente_id<>testa_ddt_corrente.pagamento_id.id) or testa_ddt_corrente.partner_id.fatt_once:
              #or banca_corrente_id <> testa_ddt_corrente.banca_patner.id):
              # è nuovo documento chiude il vecchio e prepara il nuovo
              #~ import pdb; pdb.set_trace()
            if not Primo:
              # chiude il vecchio documento, in pratica lo scrive
              # prima di scrivere il documento si ricalcola le spese di trasporto partendo dai ddt
              tottraspo = 0
              for ddt_o in ddt_obj.browse(cr,uid,ids_ddt_da_aggiornare):

                   tottraspo += ddt_o.spese_trasporto
              testata_fattura['spese_trasporto']=tottraspo
              testata_fattura['righe_articoli']=righe_articoli
              #import pdb;pdb.set_trace()
              testata_fattura['spese_incasso']=self.calcola_spese_inc(cr, uid, ids, testata_fattura['pagamento_id'])
              id_fat = fattura_obj.create(cr,uid,testata_fattura)
              ids_fatture.append(id_fat)
              []
              for ddt_id in ids_ddt_da_aggiornare: # scrive id della fatura su ddt
               ok =  ddt_obj.write(cr,uid,[ddt_id],{'differita_id':id_fat})
              ids_ddt_da_aggiornare=[] # prima di azzerare questa lista deve aver scritto l'id della fattura differita sui ddt presenti in quel documento.
              righe_articoli = []
            # prepara la nuova testata del documento
            Primo = False
            partner_corrente_id = testa_ddt_corrente.partner_id.id
            indirizzo_corrente_id = testa_ddt_corrente.partner_indfat_id.id
            pagamento_corrente_id = testa_ddt_corrente.pagamento_id.id
            banca_corrente_id = testa_ddt_corrente.banca_patner.id
            default = {}
            testata_fattura = ddt_obj.copy_data(cr, uid, testa_ddt_corrente.id,default=None, context=None)
            # mi ha preparato una testata come il ddt ora imposto le diversità
            testatafd_obj = self.pool.get('fiscaldoc.header')
            #import pdb;pdb.set_trace()
            testata_fattura['data_documento'] = selezione_obj.data_doc
            testata_fattura['tipo_doc']= selezione_obj.caufd.id
            testata_fattura['progr'] =  selezione_obj.caufd.progr_id_default.id
            testata_fattura['numdoc']= testatafd_obj.trova_numdoc(cr, uid, ids, testata_fattura['tipo_doc'],testata_fattura['data_documento'],testata_fattura['progr'])
            testata_fattura['name']= doc_id_create(self, cr, uid,testata_fattura['tipo_doc'],testata_fattura['data_documento'],testata_fattura['progr'],testata_fattura['numdoc'])
            testata_fattura['doc_prog']= doc_prog_create(self, cr, uid,testata_fattura['tipo_doc'],testata_fattura['data_documento'],testata_fattura['progr'],testata_fattura['numdoc'])
            testata_fattura['righe_articoli']=[]
            testata_fattura['righe_scadenze']=[]
            testata_fattura['righe_totali_iva']=[]

            testata_fattura['cod_esenzione_iva'] = cod_iva
            testata_fattura['scad_esenzione_iva'] = scad_iva
          righeddt = testa_ddt_corrente.righe_articoli
          nuova_riga = {}


          art_ddt = self.pool.get('res.company').read(cr, uid,[testa_ddt_corrente.company_id.id],(['art_des_ddt']))
                      #import pdb;pdb.set_trace()
          art_ddt_id = art_ddt[0]['art_des_ddt'][0]
          art = self.pool.get('product.product').browse(cr,uid,[art_ddt_id])[0]
          data_doc =  testa_ddt_corrente.data_documento[8:]+testa_ddt_corrente.data_documento[4:8]+testa_ddt_corrente.data_documento[:4]
          des_ddt = 'DA DDT N° '+str(testa_ddt_corrente.numdoc)+" DEL "+ data_doc
          ids_ddt_da_aggiornare.append(testa_ddt_corrente.id) # si salva l'id del ddt che sta per scrivere
          if cod_iva:
              iva_art = cod_iva
          else:
              iva_art = art.taxes_id[0].id
          nuova_riga={
                    'product_id': art_ddt_id,
                    'product_uom_qty':1,
                    'product_uom':art.product_tmpl_id.uom_id.id,
                    'contropartita':art.categ_id.property_account_income_categ.id,
                    'descrizione_riga':des_ddt,
                    'codice_iva':iva_art,
                    }
          riga_det = (0,0,nuova_riga)
          righe_articoli.append(riga_det) # ha inserito la riga di intestazione di un ddt
          #import pdb;pdb.set_trace()
          for riga_ddt in righeddt:
	    #import pdb;pdb.set_trace()
            # copia le righe del ddt sulla fattura
            default = {}
            nuova_riga = ddt_obj_line.copy_data(cr, uid,riga_ddt.id,default=None, context=None)
            if cod_iva and testa_ddt_corrente.data_documento <= part.scad_esenzione_iva:
                nuova_riga['codice_iva'] = cod_iva
            else:
		print riga_ddt.product_id.default_code
		if riga_ddt.product_id.taxes_id:
		    iva = riga_ddt.product_id.taxes_id[0].id
		else:
		    iva = riga_ddt.codice_iva.id
                nuova_riga['codice_iva'] = iva
            dati = ddt_obj_line.read(cr, uid, riga_ddt.id,[])
            nuova_riga['name']= testata_fattura['name']
            riga_det = (0,0,nuova_riga)
            #
            righe_articoli.append(riga_det)
        #import pdb;pdb.set_trace()
        tottraspo = 0
        for ddt_o in ddt_obj.browse(cr,uid,ids_ddt_da_aggiornare):
            tottraspo += ddt_o.spese_trasporto
            testata_fattura['spese_trasporto']=tottraspo

        if ids_ddt_da_aggiornare:
             # chiude il l'ultimo documento se c'è, in pratica lo scrive
#              import pdb;pdb.set_trace()
#              tottraspo = 0
#              for ddt_o in ddt_obj.browse(cr,uid,ids_ddt_da_aggiornare):
#
#                   tottraspo += ddt_o.spese_trasporto
#              testata_fattura['spese_trasporto']=tottraspo
              testata_fattura['righe_articoli']=righe_articoli
              #~ import pdb;pdb.set_trace()

              testata_fattura['spese_incasso']=self.calcola_spese_inc(cr, uid, ids, testata_fattura['pagamento_id'])

              id_fat = fattura_obj.create(cr,uid,testata_fattura)
              ids_fatture.append(id_fat)
              #import pdb;pdb.set_trace()
              for ddt_id in ids_ddt_da_aggiornare:
               ok =  ddt_obj.write(cr,uid,[ddt_id],{'differita_id':id_fat})
              ids_ddt_da_aggiornare=[] # prima di azzerare questa lista deve aver scritto l'id della fattura differita sui ddt presenti in quel documento.
              righe_articoli = []

      else:
        raise osv.except_osv(_('Invalid action !'), _('Non ci sono DDT da Fatturare !'))


      #import pdb;pdb.set_trace()
      context.update({'doc_id':ids_fatture})
      return {
            'name': 'Apri Documento',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'open.fiscaldoc.differite',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
            }





    _defaults = {
                 'data_doc' : lambda *a : time.strftime('%Y-%m-%d %H:%M:%S'),
                 'data_comp_ddt' : lambda *a : time.strftime('%Y-%m-%d %H:%M:%S'),
            #     'cauddt':_get_cauddt,
                 'caufd':_get_caufd,
                 'prog_fd':_get_prog,
                 'primo_num_doc':_get_num_prog,
                 'a_numddt':999999,
                 'a_dataddt':lambda *a : time.strftime('%Y-%m-%d %H:%M:%S'),
                 'da_dataddt':_get_da_ddt,
                 'da_partner':_get_da_partner,
                 'a_partner':_get_a_partner,

                 }

generazione_differite()






class open_fiscaldoc_differite(osv.osv_memory):
    _name = "open.fiscaldoc.differite"
    _description = "Apre i Documenti Generati"

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
            'view_mode': 'tree,form',
            'res_model': 'fiscaldoc.header',
            'res_id':context['doc_id'],
            'view_id': False,
            'context': context,
            'type': 'ir.actions.act_window',
         }

#          'views': [(form_id, 'form'), (tree_id, 'tree')],

open_fiscaldoc_differite()
