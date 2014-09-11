# -*- encoding: utf-8 -*-

import wizard
import decimal_precision as dp
import pooler
import time
from tools.translate import _
from osv import osv, fields
from tools.translate import _



class stampa_fiscaldoc(osv.osv_memory):
    _name = 'stampa.fiscaldoc'
    _description = 'funzioni necessarie alla stampa documenti'
    _columns = {
                'dadata': fields.date('Da Data Documento', required=True ),
                'adata': fields.date('A Data Documento', required=True),
                'danrv': fields.char('Da Documento',size=30,required=True),
                'anrv': fields.char('A Documento',size=30,required=True),
                'sconto': fields.boolean('Stampo gli sconti sul documento?', required=True),
                'prezzi': fields.boolean('Stampo i prezzi sul documento?', required=True ),
                'agente':fields.many2one('sale.agent', 'Agente', select=True),
                #'sub': fields.char('numero documento per sub_report')
    }
        
    def _build_contexts(self, cr, uid, ids, data, context=None):
        #import pdb;pdb.set_trace()
        if context is None:
            context = {}
        result = {}
        sub = data['form']['danrv']
        result = {'danr':data['form']['danrv'],'anr':data['form']['anrv'],'dadata':data['form']['dadata'],
                  'adata':data['form']['adata'], 'sconto':data['form']['sconto'], 'prezzi':data['form']['prezzi'], 'name':sub,
                  'agente':data['form']['agente']}
        var = data['form']['prezzi']
        #import pdb;pdb.set_trace()
        parametri = self.browse(cr,uid,ids)[0]
        if data['form']['agente']==0 or data['form']['agente']==False :
            spazio = '%'
            data['form']['agente'] = spazio
        else:
            data['form']['agente']=parametri.agente.name
        if var == True or var == 1:
            result = {'danr':data['form']['danrv'],'anr':data['form']['anrv'],'agente':data['form']['agente'],'dadata':data['form']['dadata'],
                  'adata':data['form']['adata'], 'sconto':data['form']['sconto'], 'prezzi':1,'name':sub}
        else:
            result = {'danr':data['form']['danrv'],'anr':data['form']['anrv'],'agente':data['form']['agente'],'dadata':data['form']['dadata'],
                  'adata':data['form']['adata'], 'sconto':data['form']['sconto'], 'prezzi':0,'name':sub}
        return result
  
    def _print_report(self, cr, uid, ids, data, context=None):
        #import pdb;pdb.set_trace()
        if context is None:
            context = {}
        pool = pooler.get_pool(cr.dbname)
        fatture = pool.get('fiscaldoc.header')
        active_ids = context and context.get('active_ids', [])
        Primo = True
        if active_ids:
            for doc in fatture.browse(cr, uid, active_ids, context=context):
                if Primo:
                    Primo = False
                    IdTipoSta = doc.tipo_doc.id
                    TipoStampa = doc.tipo_doc.tipo_modulo_stampa.report_name
                #import pdb;pdb.set_trace()
                else:
                  if IdTipoSta <> doc.tipo_doc.id:
                      raise osv.except_osv(_('ERRORE !'),_('Devi Selezionare documenti con la stessa Causale Documento'))

        return {
                'type': 'ir.actions.report.xml',
                'report_name': TipoStampa,
                'datas': data,
            }
 

    def check_report(self, cr, uid, ids, context=None):
        #import pdb;pdb.set_trace()
        if context is None:
            context = {}
            
        data = {}
        data['ids'] = context.get('active_ids', [])
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(cr, uid, ids, ['dadata',  'adata',  'danrv', 'anrv','sconto','agente','prezzi'])[0]
        used_context = self._build_contexts(cr, uid, ids, data, context=context)
        data['form']['parameters'] = used_context
        return self._print_report(cr, uid, ids, data, context=context)
  
    def view_init(self, cr, uid, fields_list, context=None):
        # import pdb;pdb.set_trace()
        res = super(stampa_fiscaldoc, self).view_init(cr, uid, fields_list, context=context)

        return res
    
             
    def  default_get(self, cr, uid, fields, context=None):
        #import pdb;pdb.set_trace()
        pool = pooler.get_pool(cr.dbname)
        fatture = pool.get('fiscaldoc.header')
        active_ids = context and context.get('active_ids', [])
        Primo = True
        if active_ids:
            for doc in fatture.browse(cr, uid, active_ids, context=context):
                if Primo:
                    Primo = False
                    DtIni = doc['data_documento']
                    NrIni = doc['name']
                    danr = doc['id']
                  #import pdb;pdb.set_trace()
                DtFin = doc['data_documento']
                NrFin = doc['name']
                anr = doc['id']

                
        
        return{'dadata':DtIni,'adata':DtFin,'danrv':NrIni,'anrv':NrFin}

    

    
stampa_fiscaldoc()  

