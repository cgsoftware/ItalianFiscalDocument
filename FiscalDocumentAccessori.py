# -*- encoding: utf-8 -*-

import netsvc
import pooler, tools
import math
from tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time


from osv import fields, osv

def _ListaTipiDocumento(self, cr, uid, context={}):
    return [("DT", "Documento di Trasporto"), ('FA', 'Fattura Accompagnatoria'), ('FI', 'Fattura Immediata'), ('FD', 'Fattura Differita'), ('ND', 'Nota di Addebito'), ('NC', 'Nota di Credito'), ('FC', 'Fattura/Ricevuta Fiscale'), ('RF', 'Ricevuta Fiscale'),('PF','Fattura Proforma')]



    



class fiscaldoc_tipoprogressivi(osv.osv):
    
   _name = "fiscaldoc.tipoprogressivi"
   _description = "Numerazioni Fiscali Documenti"
   
   _columns = {
             'name':fields.char('Codice', size=5, required=True, translate=True),
             'descr_progr':fields.char('Descrizione', size=25, translate=True),
             'tipo_doc_progr':fields.selection(_ListaTipiDocumento, 'Tipo Documento'),
             'registro_iva':fields.char('Registro Iva', size=20),
             'ids_ultimi_numeri': fields.one2many('fiscaldoc.numeriprogressivi', 'id_tipo_prog', 'Ultimi Numeri'),

               } 
     
   def _get_ult_progr(self, cr, uid, ids, progr, anno):
        #import pdb;pdb.set_trace()
        vals = {}
        if progr:
         riga = self.pool.get('fiscaldoc.numeriprogressivi').search(cr, uid, [('anno', '=', anno), ('id_tipo_prog', "=", progr)])
         if riga:
             righe_dict = self.pool.get('fiscaldoc.numeriprogressivi').read(cr, uid, riga, ['ultimo_numero', 'data_ultimo_numero'])
             riga_dict = righe_dict[0]
         else:
             # CREA LA RIGA CON L'ANNO
             riga_dict = {
                        "anno":anno,
                        "id_tipo_prog":progr,
                        "ultimo_numero":0,
                        "data_ultimo_numero": time.strftime('%Y-%m-%d'),
                        }
             riga = self.pool.get('fiscaldoc.numeriprogressivi').create(cr, uid, riga_dict, context=None)
         vals = {
               "ultimo_numero":riga_dict["ultimo_numero"],
               'data_ultimo_numero':riga_dict["data_ultimo_numero"],
               }
        return vals
     
 
fiscaldoc_tipoprogressivi()

class fiscaldoc_numeriprogressivi(osv.osv):
    
   _name = "fiscaldoc.numeriprogressivi"
   _description = "Ultimi Numeri Fiscali Documenti"
   
   _columns = {
             'anno':fields.char('Anno', size=4, required=True),
             'id_tipo_prog':fields.many2one('fiscaldoc.tipoprogressivi', 'Tipo Progressivi', required=True, help="Inserisci il tipo progressivo"),
             'ultimo_numero':fields.integer('Ultimo Numero'),
             'data_ultimo_numero':fields.date('Data Ultimo Numero'),
               } 
   
   def  _aggiorna_progr(self, cr, uid, progr, data_doc, numdoc):
       anno = data_doc[0:4]
       riga = {}
       id_prog = riga = self.pool.get('fiscaldoc.numeriprogressivi').search(cr, uid, [('anno', '=', anno), ('id_tipo_prog', "=", progr)])
       if id_prog:
           riga = {
                          'ultimo_numero':numdoc,
                          'data_ultimo_numero':data_doc
                          }
           res = self.pool.get('fiscaldoc.numeriprogressivi').write(cr, uid, id_prog, riga)
       else:
            res = False
       return res

fiscaldoc_numeriprogressivi()

class fiscaldoc_causalidoc(osv.osv):
    _name = "fiscaldoc.causalidoc"
    _description = "Causali dei Fiscali Documenti"
    _columns = {
             'name':fields.char('Codice', size=10, required=True),
             'descrizione':fields.char('Descrizione', size=50, required=True),
             'tipo_operazione':fields.selection((('C', 'Cliente'), ('F', 'Fornitore'), ('A', 'Altro')), 'Tipo Operazione'),
             'tipo_azione':fields.selection((('VE', 'Vendita'), ('AC', 'Acquisto'), ('CV', 'Conto/Visone'),('NS', 'Non Specificato'),('RE', 'Resi')), 'Tipo Azione'),
             'tipo_documento':fields.selection(_ListaTipiDocumento, 'Tipo Documento'),
             'flag_magazzino':fields.boolean('Movimenta Magazzino'),
             'flag_fatturabile':fields.boolean('Fatturabile',help="Se attivo questa Causale non è Fatturabile"),
             'progr_id_default':fields.many2one('fiscaldoc.tipoprogressivi', 'Progressivo di Default', help="Inserisci l'eventuale Progressivo di Default"),
             'causale_del_trasporto_id': fields.many2one('stock.picking.transportation_reason', 'Reason for transportation'),
             'flag_contabile':fields.boolean('Documento da Contabilizzabile'),
             'tipo_modulo_stampa':fields.many2one('ir.actions.report.xml', 'Modulo di Stampa'),
             'numero_copie_in_stampa':fields.integer('N.Copie'),
             'deposito_default':fields.many2one('stock.location', 'Deposito di partenza', help="Inserisci l'eventuale Deposito di Default",required=True),
             'deposito_destinazione_default':fields.many2one('stock.location', 'Deposito di Destinazione', help="Inserisci il Deposito di destinazione di Default",required=True),
               } 
fiscaldoc_causalidoc()
    
    
class fiscaldoc_spedizioni(osv.osv):
    _name = "fiscaldoc.spedizioni"
    _description = "Metodo di Consegna"
    _columns = {
             'name':fields.char('Descrizione', size=40, required=False),
             }                
fiscaldoc_spedizioni()

class account_payment_term(osv.osv):
    _inherit = "account.payment.term"
    _columns = {
             'conto_cassa_banca':fields.many2one('account.account', "Conto Cassa o Banca",  required=False, select=False),   
             'sconto':fields.float('Sconto Pagamento', digits=(7, 3)),
               } 
    
    def get_data_scad(self, cr, uid, id, data_par, ngg, tipscad,context=None):
        if not context:
            context={}
        #import pdb;pdb.set_trace()      
        if tipscad < 0:
          tip_sca = "FM" # fine mee
        elif tipscad > 0:
          tip_sca = "GF"  #giorno fisso del mese esempio 15
        else:
          tip_sca = "DF" # data fattura documento
          
        data_sca = datetime.strptime(data_par, '%Y-%m-%d')
        nmesi = ngg / 30.0
        #import pdb;pdb.set_trace()
        if nmesi == int(nmesi):
          giorno = data_sca.day
          mese = data_sca.month + int(nmesi)
          anno = data_sca.year
        else:
          giorno = (data_sca + relativedelta(days=ngg)).day
          mese = (data_sca + relativedelta(days=ngg)).month
          anno = (data_sca + relativedelta(days=ngg)).year
        if tip_sca == "GF": 
          #Se Giorno Fisso cambia giorno (ev.te sposta avanti di un mese)
          if tip_sca == "FM":
            mese += 1
          else:
            if tipscad < giorno:
              mese += 1
          giorno = tipscad
        # controlla l'anno
        while mese > 12:
          anno += 1
          mese -= 12
        # controlli per le giuste date del fine mese 
        giornos = str(giorno).zfill(2)
        meses = str(mese).zfill(2)
        annos = str(anno)
        mese_succ = str(mese + 1).zfill(2)
        if meses in "02-04-06-09-11" and  giorno > 28:
          # controlla dal mese successivo il giono giusto
          ggfm = (datetime.strptime(annos + "-" + mese_succ + "-01", '%Y-%m-%d') + relativedelta(days= -1)).day
          if giorno > ggfm:
            giornos = str(ggfm).zfill(2)
          else:
            giornos = str(giorno).zfill(2)
            
        if tip_sca == 'FM':
          # la modalità di pagamento prevede il fine mese
          giornos = self.check_fm(meses, annos, giornos)

        # finiti i controlli di fine mese
        data_sca = annos + "-" + meses + "-" + giornos
        #import pdb;pdb.set_trace()
        # ORA SI FA I CONTROLLI DEL MESE ESCLUSO
        if context.get('partner_id',False):
	    #import pdb;pdb.set_trace()
            partner = self.pool.get('res.partner').browse(cr,uid,context['partner_id'])
            if (partner.meseprimoescluso>0 or partner.mesesecondoescluso>0):
                
                if ( partner.meseprimoescluso>0 and partner.meseprimoescluso<13) and partner.meseprimoescluso==int(meses):
                    # è uguale al primo mese escluso                    
                    if int(meses) + 1 > 12:
                        appo = str(int(annos) + 1)
                    else:
                        appo = annos
                    if int(meses) + 1 > 12:
                        appo1 = "01"
                    else:
                        appo1 = str(int(meses) + 1).zfill(2)
		    appo2 = str(int(appo1) + 1).zfill(2)
                    giornos = str((datetime.strptime(appo + "-" + appo2 + "-01", '%Y-%m-%d') + relativedelta(days= -1)).day).zfill(2)
                    if partner.giornoescluso and partner.giornoescluso>0:
                        giornos = str(partner.giornoescluso).zfill(2)
                    data_sca = appo + "-" + appo1 + "-" + giornos

                if ( partner.mesesecondoescluso>0 and partner.mesesecondoescluso<13) and partner.mesesecondoescluso==int(meses):
                    # è uguale al primo mese escluso                    
                    if int(meses) + 1 > 12:
                        appo = str(int(annos) + 1)
                    else:
                        appo = annos
                    if int(meses) + 1 > 12:
                        appo1 = "01"
                    else:
                        appo1 = str(int(meses) + 1).zfill(2)
		    appo2 = str(int(appo1) + 1).zfill(2)
                    giornos = str((datetime.strptime(appo + "-" + appo2 + "-01", '%Y-%m-%d') + relativedelta(days= -1)).day).zfill(2)
                    if partner.giornoescluso and partner.giornoescluso>0:
                        giornos = str(partner.giornoescluso).zfill(2)
                    data_sca = appo + "-" + appo1 + "-" + giornos
                        
                    
        return data_sca
 
    def check_fm(self,meses,annos,giornos):   
        if int(meses) + 1 > 12:
            appo = str(int(annos) + 1)
        else:
           appo = annos
        if int(meses) + 1 > 12:
            appo1 = "01"
        else:
            appo1 = str(int(meses) + 1).zfill(2)
        giornos = str((datetime.strptime(appo + "-" + appo1 + "-01", '%Y-%m-%d') + relativedelta(days= -1)).day).zfill(2)
        return giornos
   
    def compute(self, cr, uid, id, value, date_ref=False, context=None):
      
                # import pdb;pdb.set_trace()
        if not date_ref:
            date_ref = datetime.now().strftime('%Y-%m-%d')
        pt = self.browse(cr, uid, id, context=context)
        amount = value
        result = []
        obj_precision = self.pool.get('decimal.precision')
        for line in pt.line_ids:
            prec = obj_precision.precision_get(cr, uid, 'Account')
            if line.value == 'fixed':
                amt = round(line.value_amount, prec)
            elif line.value == 'procent':
                amt = round(value * line.value_amount, prec)
            elif line.value == 'balance':
                amt = round(amount, prec)
            if amt:
              #  next_date = datetime.strptime(date_ref, '%Y-%m-%d')
              #  if line.days2 < 0:
              #      next_first_date = next_date + relativedelta(day=1,months=1) #Getting 1st of next month
              #      next_date = next_first_date + relativedelta(days=line.days2)
              #      next_date = (datetime.strptime(date_ref, '%Y-%m-%d') + relativedelta(days=line.days))
              #  if line.days2 > 0:
              #      next_date = (datetime.strptime(date_ref, '%Y-%m-%d') + relativedelta(days=line.days))
                #import pdb;pdb.set_trace()
                next_date = self.get_data_scad(cr, uid, id, date_ref, line.days, line.days2,context)
               # next_date = datetime.strftime(self.get_data_scad(cr, uid, id, date_ref, line.days, line.days2), '%Y-%m-%d')
                result.append((next_date, amt, line.tipo_scadenza))
                amount -= amt
        return result

account_payment_term()  
  
class account_payment_term_line(osv.osv):
    _inherit = "account.payment.term.line"       
    _columns = {
              'tipo_scadenza':fields.selection([('RB', 'Ri.Ba.'), ('BO', 'Bonifico'), ('CO', 'Contanti/Cash'), ('RD', 'Rimessa Diretta'),('RI', 'R.I.D.')], 'Tipo Scadenza', required=True),
              'costo_scadenza':fields.float('Costo Scadenza', digits=(12, 2)),
               } 
    


account_payment_term_line()


class Bank(osv.osv):
    _inherit = 'res.bank'  
    _columns = {
              'codice_abi':fields.char('ABI', size=5),
              'codice_cab':fields.char('CAB', size=5),
              'province': fields.many2one('res.province', string='Provincia'),
              'region': fields.many2one('res.region', string='Regione'),
               }       

Bank()    

class res_partner_bank(osv.osv):
    _inherit = 'res.partner.bank'     
    
    def _calc_iban(self, cr, uid, ids, field_name, arg, context=None):
     #  PER CALCOLARE QUESTI DATI DEVE PRIMA ACCERTARSI CHE IL CASSTELLETTO IVA SIA CORRETTO
     #import pdb;pdb.set_trace()
     res = {}
     if ids:
         for bank_part in self.browse(cr,uid,ids):
             res[bank_part.id]=''
             if bank_part.codice_iban and bank_part.codice_cin and bank_part.acc_number and bank_part.bank:
                 if bank_part.bank.codice_abi and bank_part.bank.codice_cab:                    
                     res[bank_part.id] = bank_part.codice_iban+bank_part.codice_cin+bank_part.bank.codice_abi+bank_part.bank.codice_cab+bank_part.acc_number
         #
     return res
    
    
    
    _columns = {
              'codice_iban':fields.char('Codice IBAN', size=4),
              'codice_cin':fields.char('CIN', size=1),
              'iban': fields.function(_calc_iban, method=True, string='IBAN', store=False,type='char' ),
              #multi='sums'
              
               }       

res_partner_bank()



class product_category(osv.osv):
    _inherit = "product.category"
    
    def mappa_categoria(self, cr, uid, categoria,context=False,lista_id = False):
        # cerca in maniera ricorsiva tutti gli id figli di una categoria assegnata
        # il parametro lista_id deve essere
        #import pdb;pdb.set_trace()
        if not lista_id:
            lista_id=[]
                  
        lista_id.append(categoria.id)
            #import pdb;pdb.set_trace()
        if categoria.child_id:
                for child in categoria.child_id:
                    #lista_id.append(child.id)
                    if child.child_id:
                        self.mappa_categoria(cr, uid, child,context,lista_id=lista_id)
                    else:
                        lista_id.append(child.id)
        #import pdb;pdb.set_trace()
        return lista_id

      

product_category()

class res_partner_category(osv.osv):
    _inherit = "res.partner.category"
    
    def mappa_categoria(self, cr, uid, categoria,context=False,lista_id = False):
        # cerca in maniera ricorsiva tutti gli id figli di una categoria assegnata
        # il parametro lista_id deve essere
        #import pdb;pdb.set_trace()
        if not lista_id:
            lista_id=[]
                  
        lista_id.append(categoria.id)
            #import pdb;pdb.set_trace()
        if categoria.child_id:
                for child in categoria.child_id:
                    #lista_id.append(child.id)
                    if child.child_id:
                        self.mappa_categoria(cr, uid, child,context,lista_id=lista_id)
                    else:
                        lista_id.append(child.id)
        #import pdb;pdb.set_trace()
        return lista_id

      

res_partner_category()


class res_country(osv.osv):
    _inherit = "res.country"
    _columns = {
		'flag_ue':fields.boolean('Flag Paese Ue'),
	       }

res_country()
