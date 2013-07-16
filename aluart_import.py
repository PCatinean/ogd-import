import ogdimport 
import ogd_logging 
import logging
import os
import base64

class CustomImport(ogdimport.OGDParser):


    PREFIXES = {
        'product.category': 'aluart_product_category_',
        'product.product': 'aluart_product_',
        'res.partner': 'aluart_company_',
    }

    def import_categories(self, model, resource, rows, prefix=''):

        for row in rows:
            res_id = self.open_erp.execute.get_res_id(model,'%s' % (self.PREFIXES[model]+row['externalid']))

            #Prepare values for writing to DB
            vals = {'name': row['namede'], 'parent_id': 1}

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
                #logging().info("Adding translations...\n")
                #self.open_erp('product.category','write',categ_id,{'name': row['namede']},{'lang': 'de_DE'})
                #self.open_erp('product.category','write',categ_id,{'name': row['nameit']},{'lang': 'it_IT'}) 
                #self.open_erp('product.category','write',categ_id,{'name': row['namees']},{'lang': 'es_ES'}) 
                #self.open_erp('product.category','write',categ_id,{'name': row['namefr']},{'lang': 'fr_FR'})   

        print "\n"
        logging.info("[FINISHED IMPORTING/UPDATING PRODUCT CATEGORIES]\n")                

    def import_partners(self, model, resource, rows, prefix=''):

        PARTNER_IDS = {}

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
                    'country_id': self.open_erp.get_country_id(row['countrycode']) or '',
                    'zip': row['zipcode'] or '',
                    'city': row['city'] or '',
                    'customer': int(row['iscustomer'] or 0),
                    'supplier': int(row['issupplier'] or 0)
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

                    if row['contactname'] and partner_type == 'company':
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

    def import_products(self, model, resource, rows,  prefix=''):

        def get_categ_id(external_id):
            res_id = self.open_erp.get_res_id('product.category',external_id)      
            if not res_id:
                logging.warning("Product category with external id (%s) not found"%external_id)
            return res_id

        def get_product_img(path,reference):
            #Returns base64 encoded images for upload in self.open_erp.execute database
            images = os.listdir(path) 
            for img in images:
                name = img.split('.')[0]
                if row['reference'] == name:
                    img_file = open(path+img) 
                    product_img = base64.b64encode(img_file.read())    
                    return product_img
            return False

        def update_translations(row, res_id):
            #Add translations to product
            if row['namede']:
                self.open_erp.execute('product.product', 'write', res_id, {'name': row['namede']},{'lang': 'de_DE'})
            if row['nameit']:                
                self.open_erp.execute('product.product', 'write', res_id, {'name': row['nameit']},{'lang': 'it_IT'})
            if row['namees']:                
                self.open_erp.execute('product.product', 'write', res_id, {'name': row['namees']},{'lang': 'es_ES'})
            if row['namefr']:                        
                self.open_erp.execute('product.product', 'write', res_id, {'name': row['namefr']},{'lang': 'fr_FR'})

        def update_inventory(product_ids, qty=1000):
            inventory_id = self.open_erp.get_res_id('stock.inventory','aluart_initial_stock_inventory')
            if inventory_id:
                logging.warning("There is already a inventory created for startup [ID: %d]" % inventory_id)
                return 0
                
            inventory_lines = []
            stock_location_id = self.open_erp.get_res_id('stock.location','stock_location_stock')
            for product in product_ids:
                uom_id = self.open_erp.execute('product.product','read', res_id,['uom_id'])['uom_id'][0]    
                inventory_lines.append((0, 0, {'location_id': stock_location_id,
                                               'product_id': product,
                                               'product_qty': qty,
                                               'product_uom': uom_id}))

            inventory_id = self.open_erp.execute('stock.inventory','create',{'name': "Startup Inventory", 
                                                                            'inventory_line_id': inventory_lines})

            self.open_erp.create_external_id('stock.inventory','aluart_initial_stock_inventory',inventory_id,'aluart')
            return inventory_id

        def update_orderpoints(row, res_id):
            #Update minimum orderpoints for make-to-stock/buy products
            if row['minqty'] and row['orderqty']:
                op_id = self.open_erp.execute('stock.warehouse.orderpoint','search',[('product_id','=',res_id)])
                uom_id = self.open_erp.execute('product.product','read', res_id,['uom_id'])['uom_id'][0]

                vals = {'product_id': res_id,
                        'product_min_qty': row['minqty'],
                        'product_max_qty': row['orderqty'],
                        'product_uom': uom_id,
                        }

                if op_id:
                    self.open_erp.execute('stock.warehouse.orderpoint', 'write', op_id, vals)
                else:
                    self.open_erp.execute('stock.warehouse.orderpoint', 'create', vals)
            else:
                logging.warning("There is no minimum or maximum order qty set for product [%s] %s" % (row['reference'], row['nameen']) )
            return True
           

        #Get the main supplier for minimum order points
        sisale_external_id = self.PREFIXES['res.partner'] + '101180.01'

        sisale_id = self.open_erp.get_res_id('res.partner',sisale_external_id)

        if not sisale_id:
            logging.error("Could not retreive id of Sisale supplier for minimum orderpoint [%s]" % sisale_external_id)

        img_path = '/home/wiz/Dropbox/Projects/Aluart/Shared Docs/JPG/'
        product_inventory_ids = []

        for row in rows:
            external_id = self.PREFIXES[model] + row['reference']
            res_id = self.open_erp.get_res_id(model,'%s' % (external_id))
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
                    'default_code': row['reference'],
                    'weight': row['weight'] or '',
                    'supply_method': row['supplymethod'],
                    'uom_id': uom_id,
                    'uom_po_id': uom_id, 
                    'description': row['descriptionde'] or '',
                    'image_medium': img_bit64 or ''
                    }

            if procurement_method == 'make_to_stock':
                vals.update({'seller_ids': [(0, 0, {'name': sisale_id, 'min_qty': 0})]})                

            if res_id:
                if 'all' in self.args.update or resource in self.args.update:
                    seller_ids = self.open_erp.execute('product.supplierinfo','search',[('product_id','=',res_id)])

                    #Remove all suppliers if the product must be updated to the latest info
                    if seller_ids:
                        self.open_erp.execute('product.supplierinfo','unlink',seller_ids)

                    self.open_erp.execute('product.product','write',res_id,vals)
                    logging.info("Updated product [%s] %s" % (row['reference'], row['nameen']) )
                    update_translations(row, res_id)  

                    if procurement_method == 'make_to_stock' and vals['supply_method'] == 'buy':
                        update_orderpoints(row, res_id)
                                    
                else:
                    logging.warning("Product already imported in database (%s)" % row['nameen'])


            else:
                res_id = self.open_erp.execute('product.product','create',vals)
                self.open_erp.create_external_id(model, external_id, res_id,'aluart')

                update_translations(row, res_id)

                if procurement_method == 'make_to_stock' and vals['supply_method'] == 'buy':
                    update_orderpoints(row, res_id)
                
                logging.info("Added product [%s] %s (%d images)" % (row['reference'], row['nameen'], 1 if vals['image_medium'] else 0))

            #Add product ids for inventory updated if requested
            if self.args.update_inventory and vals['procure_method'] == 'make_to_stock':
                product_inventory_ids.append(res_id)
        
        if self.args.update_inventory:
            logging.info("[UPDATING PRODUCT INVENTORY]\n")
            inventory_id = update_inventory(product_inventory_ids)
            if inventory_id:
                self.open_erp.execute('stock.inventory','action_confirm',[inventory_id])
                logging.info("[INVENTORY UPDATED]")

        print "\n"
        logging.info("[FINISHED IMPORTING/UPDATING PRODUCTS]\n")        

    def import_dimensions(self, resource, rows):


        def get_dimension_id(prefix):
            #Get dimension database id by using unique prefix field
            dim_id = self.open_erp.execute('product.variant.dimension.type','search',[('prefix','=',prefix)])
            return dim_id[0] if dim_id else False  

        def get_template_id(prefix):
            dim_id = self.open_erp.execute('product.template','search',[('prefix','=',prefix)])
            return dim_id[0] if dim_id else False    

        def get_option_ids(codes):
            option_ids = self.open_erp.execute('product.variant.dimension.option','search',[('code','in',codes)])
            return option_ids

        def import_dependencies(template_id,dependencies,vals):
            value_ids = self.open_erp.execute('product.variant.dimension.value','search',[('product_tmpl_id','=',template_id)])
            template_values = self.open_erp.execute('product.variant.dimension.value','read',value_ids,['option_id'])
            template_options = {value['option_id'][0]: value['id'] for value in template_values}
            for option in template_options:
                #Loop through template options (that have value mapping)
                if option in dependencies:
                    #If the option is in the dependency tree from the drive document
                    dep_type = vals['prefix'] if vals['prefix'] in dependencies[option] else 'default'
                    dep_dict = {'dependency_ids': [(4, template_options[option_id]) for option_id in dependencies[option][dep_type] if option_id in template_options]}  
                    self.open_erp.execute('product.variant.dimension.value','write',template_options[option],dep_dict)                      
                    logging().info("Updated dependency for template '%s'"%vals['name']) 
            return True                

        dim_id = 0
        for row in rows:
            #Add a dimension type if needed
            if row['option']:
                if not row['prefix']:
                    logging.error("There is no prefix set for option %s" % row['option'])
                if not row['sequence']:
                    logging.warning("There is no sequence set for option %s" % row['option'])
                
                res_id = get_dimension_id(row['prefix'])

                vals = {'name': row['option'],
                        'description': row['option'],
                        'prefix': row['prefix'],
                        'sequence': row['sequence'] or 0,
                        'depends_on': get_dimension_id(row['dependson']) if row['dependson'] else '',
                    }   

                translation = {'description': row['optionde']}    

                if res_id:
                    if 'all' in self.args.update or resource in self.args.update:
                        self.open_erp.execute('product.variant.dimension.type', 'write', res_id, vals)
                        logging.info("Updated dimension %s" % row['option'])
                        self.open_erp.execute('product.variant.dimension.type', 'write', res_id, translation, {'lang': 'de_DE'})
                    else:
                        logging.warning("Dimension already imported in database '%s'" % row['option'])                

                else:
                    res_id = self.open_erp.execute('product.variant.dimension.type','create',vals)
                    logging.info("Created new dimension '%s'" % row['option'])   
                    self.open_erp.execute('product.variant.dimension.type','write',res_id,translation, {'lang': 'de_DE'})             

                dim_id = res_id

            #Add dimension options using the parent dimension_type variable
            if row['label'] and row['value']:

                res_id = self.open_erp.get_option_id(dim_id, row['label'], row['value'])

                vals = {'dimension_id': dim_id,
                        'name': row['label'],
                        'code': row['value'],
                        }

                if row['value'] == 'custom':
                    vals.update({'allow_custom_value': True})

                elif row['value'] == 'custom_send':
                    vals.update({
                        'allow_custom_value': True,
                        'send_value': True
                        })
                else:
                    vals.update({'code': row['value']})

                if res_id:
                    if 'all' in self.args.update or resource in self.args.update:
                        self.open_erp.execute('product.variant.dimension.option', 'write', res_id,vals)
                        logging.info("Updated option %s" % row['value'])
                    else:
                        logging.warning("Option already imported in database '%s'" % row['value'])                

                else:
                    res_id = self.open_erp.execute('product.variant.dimension.option', 'create', vals)
                    logging.info("Created new option '%s'" % row['label']) 

    def import_templates(resource, rows, prefix=None):

        options = {}
        dependencies = {}

        #Get options to templates mapping

        for row in rows:

            if row['option']:

                if not row['prefix']:
                    logging.error("There is no prefix set for option %s" % row['option'])
                if not row['sequence']:
                    logging.warning("There is no sequence set for option %s" % row['option'])
                
                dim_id = get_dimension_id(row['prefix'])
                prefix = row['prefix'].upper()
                
                if not dim_id:
                    logging.error("No such dimension %s" % row['option'])

            if row['label'] and row['value']:
                res_id = self.open_erp.get_option_id(dim_id, row['label'], row['value'])

                if not res_id:
                    logging.error("No such option %s" % row['label'])

                #Fill compatibilities dictionary
                categories = row['compatibility'].split('_')
                for category in categories:
                    category = category.upper()
                    if prefix not in options:
                        options[prefix] = {category: (dim_id, [res_id])}
                    else:
                        if category not in options[prefix]:
                            options[prefix][category] = (dim_id, [res_id])
                        else:
                            options[prefix][category][1].append(res_id)

                #Fill dependencies dictionary
                if res_id not in dependencies:
                    default_options = row['defaultdependentoptions']
                    option_ids = []
                    if default_options:
                        option_ids = self.open_erp.get_option_ids(default_options.split(','))
                    dependencies[res_id] = {'default': option_ids}

                for product_type in row:
                    #Really messy workaround because there is no sorting by column in gdata.SpreadSheetService
                    if len(product_type) <= 3:                    
                        if row[product_type]:
                            option_ids = self.open_erp.get_option_ids(row[product_type].split(','))
                            dependencies[res_id][product_type.upper()] = option_ids
        

        #Import templates
        worksheet_id = feed.entry[1].id.rsplit('/',1)[1]
        rows = gd_client.GetListFeed(spreadsheet_id, worksheet_id).entry

        for row in rows:

            tmpl_prefix = row['prefix'].upper()
            value_ids = []
            dimension_type_ids = []

            for dim in row:
                if dim.upper() in options:
                    category = row[dim].upper()
                    if category in options[dim.upper()]:
                        #Add dimension_id to template
                        dimension_type_ids.append( (4,options[dim.upper()][category][0]) )
                        #Add dimension values to template
                        for val in options[dim.upper()][category][1]:
                            value_ids.append( (0, 0, {'option_id': val}) )
                        if row['type'] == "Standard Mast":
                            pass
                            #import pdb;pdb.set_trace()
                    elif category == 'N/A':
                        pass
                    else:
                        logging.warning("There is no such compatibility category '%s'"%category)

            vals = {'name': row['type'],
                    'prefix': row['prefix'].upper(),
                    'is_multi_variants': True,
                    'dimension_type_ids': dimension_type_ids,
                    'value_ids': value_ids}

            res_id = get_template_id(row['prefix'])
            if res_id:
                if 'all' in self.args.update or resource in args.update:
                    #Remove active dependencies
                    value_ids = self.open_erp.execute('product.variant.dimension.value','search',[('product_tmpl_id','=',res_id)])
                    for val in value_ids:
                        option_dependencies = self.open_erp.execute('product.variant.dimension.value','read',val,['dependency_ids'])
                        reset_dep = [(3, dep_id) for dep_id in option_dependencies['dependency_ids']]
                        self.open_erp.execute('product.variant.dimension.value','write',val,{"dependency_ids": reset_dep})

                    import_dependencies(res_id,dependencies,vals)
                else:
                    logging.warning("Template already imported in database '%s'" % row['type'])

            else:
                res_id = self.open_erp.execute('product.template','create',vals)
                logging().info("Created new template '%s'"%row['type']) 
                import_dependencies(res_id,dependencies,vals)                                

    def parse_resource(self, resource, rows):
        
        if resource == 'products':
            self.import_products('product.product', resource, rows, prefix='aluart_product_')
        elif resource == 'categories':
            self.import_categories('product.category', resource, rows, prefix='aluart_product_category_')
        elif resource == 'partners':
            self.import_partners('res.partner', resource, rows)
        elif resource == 'dimensions':
            self.import_dimensions(resource, rows)

custom_import = CustomImport()

custom_import.parse_arguments()