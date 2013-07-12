import ogdimport 
import ogd_logging 
import logging
import os

class CustomImport(ogdimport.OGDParser):


    PREFIXES = {
        'product.category': 'aluart_product_category_',
        'product.product': 'aluart_product_',
        'res.partner': 'aluart_partner_'
    }

    def import_categories(self, model, resource, rows, prefix=''):

        for row in rows:
            res_id = self.open_erp.get_res_id(model,'%s' % (self.PREFIXES[model]+row['externalid']))

            #Prepare values for writing to DB
            vals = {'name': row['namede']}

            if row['parentcategory']:
                paret_category = self.open_erp.get_res_id(model, self.PREFIXES[model] + row['parentcategory'])
                if paret_category:
                    vals.update({'parent_id': paret_category})

            if res_id:
                if 'all' in self.args.update or resource in self.args.update:
                    self.open_erp.execute('product.category','write',res_id,vals)
                    logging.info("Updated product category %s"%row['namede'])
                else:
                    logging.warning("Category already imported in database '%s'"%row['namede'])

            else:
                #Create a new category if there is none with the specified external_id
                categ_id = self.open_erp.execute(model,'create',vals)
                self.open_erp.create_external_id('product.category', self.PREFIXES[model]+row['externalid'], categ_id, 'aluart')

                logging.info("Created new product category '%s'"%row['namede'])

                #Add translations
                #logger().info("Adding translations...\n")
                #self.open_erp('product.category','write',categ_id,{'name': row['namede']},{'lang': 'de_DE'})
                #self.open_erp('product.category','write',categ_id,{'name': row['nameit']},{'lang': 'it_IT'}) 
                #self.open_erp('product.category','write',categ_id,{'name': row['namees']},{'lang': 'es_ES'}) 
                #self.open_erp('product.category','write',categ_id,{'name': row['namefr']},{'lang': 'fr_FR'})   

    def import_products(self, model, resource, rows,  prefix=''):

        def get_categ_id(external_id):
            res_id = self.open_erp.get_res_id('product.category',external_id)      
            if not res_id:
                logging.warning("Product category with external id (%s) not found"%external_id)
            return res_id

        def get_product_img(path,reference):
            #Returns base64 encoded images for upload in openERP database
            images = os.listdir(path) 
            for img in images:
                name = img.split('.')[0]
                if row['reference'] == name:
                    img_file = open(path+img) 
                    product_img = base64.b64encode(img_file.read())    
                    return product_img
            return False

           
        img_path = '/home/wiz/Dropbox/Projects/Aluart/Shared Docs/JPG/'

        for row in rows:
            res_id = self.open_erp.get_res_id(model,'%s' % (self.PREFIXES[model]+row['reference']))
            procurement_method = 'make_to_stock' if row['supplymethod'] == 'buy' else 'make_to_order'
            uom_id = self.open_erp.get_uom_id(row['uom'])

            if not uom_id:
                continue

            img_bit64 = get_product_img(img_path,row['reference'])

            if img_bit64:
                product_img = {
                    'name': row['reference'],
                    'file': img_bit64,
                    }

            get_categ_id(self.PREFIXES['product.category']+row['productcategoryexternalid'])

            vals = {'name': row['nameen'],
                    'type': 'product',
                    'procure_method': procurement_method,
                    'purchase_ok': 1 if procurement_method == 'make_to_stock' else 0,
                    'categ_id': get_categ_id(self.PREFIXES['product.category']+row['productcategoryexternalid']) or 1,
                    'defaultcode': row['reference'],
                    'weight': row['weight'] or '',
                    'supply_method': row['supplymethod'],
                    'uom_id': uom_id,
                    'uom_po_id': uom_id, 
                    'description': row['descriptionde'] or '',
                    'image_ids': [(0, 0, product_img)] if img_bit64 else '',
                    }

            if res_id:
                if 'all' in self.args.update or resource in self.args.update:
                    image_ids = self.open_erp.execute('product.images','search',[('product_id','=',res_id)])

                    #Remove all images if the product must be updated to the latest info
                    if image_ids:
                        openERP('product.images','unlink',image_ids)

                    self.open_erp.execute('product.product','write',res_id,vals)
                    logging.info("Updated product [%s] %s" % (row['reference'], row['namede']) )
                else:
                    logging.warning("Product already imported in database (%s)" % row['namede'])

            else:
                res_id = self.open_erp.execute('product.product','create',vals)
                self.open_erp.create_external_id(model,self.PREFIXES[model]+row['reference'],res_id,'aluart')
                logging.info("Added product [%s] %s (%i images)" % (row['reference'],row['namede'], len(vals['image_ids'])))
            
            logging.error("Break!")



    def import_partners(self, model, resource, rows, prefix=''):

        PARTNER_IDS = {}

        def get_country(countrycode):
            country_id = self.open_erp.execute('res.country','search',[('code','=',countrycode)])
            return country_id[0] if country_id else ''

        def get_title_id(title, title_dict={}):
            if title in title_dict:
                return title_dict[title]

            title_id = self.open_erp.execute('res.partner.title','search',[('name','=',title)],1,False,False,{'lang': 'de_DE'})
            if title_id:
                title_dict[title] = title_id[0]
                return title_id[0]
            return ''

        for row in rows:

            #Determine wether the partner is a contact or a company
            partner_sequence = row['partnercode'].split('.')
            partner_type = 'company' if partner_sequence[1] == '01' else 'contact'
            external_id = 'aluart_%s_%s' % (partner_type, row['partnercode']) 

            #Check external id for partner
            res_id = self.open_erp.get_res_id(model,external_id)
            
            vals = {
                'email': row['email'] or '',
                'phone': row['phone'] or '',
                'mobile': row['mobile'] or '',
                'fax': row['fax'] or '',
                'lang': 'de_DE',
            }

            if partner_type == 'company' and row['companyname']:
                #If it's a company add it to the partner_ids list for parent_id reference of contacts
                if res_id:
                    PARTNER_IDS[partner_sequence[0]] = res_id    

                #Prepare values for possible update or creation
                vals.update({
                    'is_company': 1,
                    'name': row['companyname'],
                    'street': row['street'] or '',
                    'country_id': get_country(row['countrycode']) or '',
                    'zip': row['zipcode'] or '',
                    'city': row['city'] or '',
                    'customer': row['iscustomer'] or 0,
                    'supplier': row['issupplier'] or 0
                    })


                if row['contactname']:
                    contact_vals = {
                        'name': row['contactname'],
                        'title': get_title_id(row['contacttitle']) if row['contacttitle'] else '',
                        'mobile': row['mobile'] or '',
                        'fax': row['fax'] or '',
                        'phone': row['phone'] or '',
                        'use_parent_address': 1,
                    }
                    
            elif partner_type == 'contact' and row['contactname']:
                vals.update({
                        'name': row['contactname'],
                        'parent_id': PARTNER_IDS[partner_sequence[0]],
                        'contact_title': get_title_id(row['contacttitle']) if row['contacttitle'] else '',
                    })

            else:
                logging.warning("[%s] %s has an error and has been skipped from import!" % (row['partnercode'], row['companyname']) )
                continue


            if res_id:
                if 'all' in self.args.update or resource in self.args.update:
                    
                    self.open_erp.execute(model,'write',res_id,vals)
                    logging.info("Updated %s [%s] %s" % (partner_type, row['partnercode'], vals['name']))

                    if row['contactname']:
                        contact_id = self.open_erp.get_res_id(model, 'aluart_contact_%s' % row['partnercode'])
                        if contact_id:
                            self.open_erp.execute(model,'write',contact_id, contact_vals)
                            logging.info("Updated contact [%s] %s" % (row['partnercode'], contact_vals['name']))
                        else:
                            logging.warning("No such contact with partner code [%s]" %row['partnercode'])
                else:
                    logging.warning("%s already imported in database ([%s] %s )" % (partner_type, row['partnercode'], row['companyname'] if partner_sequence[1] == '01' else row['contactname']) )              

            else:
                partner_id = self.open_erp.execute(model, 'create', vals)
                self.open_erp.create_external_id(model, external_id, partner_id, 'aluart')
                logging.info("Created new %s [%s] %s" % (partner_type, row['partnercode'], vals['name']))
                
                if partner_type == 'company':
                    PARTNER_IDS[partner_sequence[0]] = partner_id

                    if row['contactname']:
                        contact_vals.update({'parent_id': partner_id})
                        contact_id = self.open_erp.execute(model, 'create', contact_vals)
                        self.open_erp.create_external_id(model, 'aluart_contact_' + row['partnercode'], contact_id, 'aluart')
                        logging.info("Created new contact [%s] %s" % (row['partnercode'], contact_vals['name']))
        print "\n"                    
        logging.info("[FINISHED IMPORTING\UPDATING PARTNERS]\n")

    def parse_resource(self, resource, rows):
        
        if resource == 'products':
            self.import_products('product.product', resource, rows, prefix='aluart_product_')
        elif resource == 'categories':
            self.import_categories('product.category', resource, rows, prefix='aluart_product_category_')
        elif resource == 'partners':
            self.import_partners('res.partner', resource, rows)

custom_import = CustomImport()

custom_import.parse_arguments()