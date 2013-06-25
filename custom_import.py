import ogdimport 

class CustomImport(ogdimport.OGDParser):

	def import_categories(self, model, rows, prefix=''):
				
	    for row in rows:
	        res_id = self.open_erp.get_res_id(model,'%s' % (prefix+row['externalid']))
	        #Prepare values for writing to DB
	        vals = {'name': row['namede'],
	                'parent_id': self.open_erp.get_res_id(model, prefix + row['parentcategory'])
	                }

	        if args.magento:
	            add_magento_vals('product.category',vals)

	        if res_id:
	            #FIXME! Please find a better, dynamic solution to this!
	            if 'all' in args.update or 'product-categories' in args.update:
	                openERP('product.category','write',res_id,vals)
	                logger().info("Updated product category %s"%row.custom['namede'].text)
	            else:
	                logger().warning("Category already imported in database '%s'"%row.custom['namede'].text)

	        else:
	            #Crete a new category if there is none with the specified external_id
	            

	            categ_id = openERP('product.category','create',vals)
	            create_external_ref(prefix+row.custom['externalid'].text,'product.category',categ_id)

	            logger().info("Created new product category '%s'"%row.custom['namede'].text)

	            #Add translations
	            #openERP('product.category','write',categ_id,{'name': row.custom['namede'].text},{'lang': 'de_DE'})
	            #openERP('product.category','write',categ_id,{'name': row.custom['nameit'].text},{'lang': 'it_IT'}) 
	            #openERP('product.category','write',categ_id,{'name': row.custom['namees'].text},{'lang': 'es_ES'}) 
	            #openERP('product.category','write',categ_id,{'name': row.custom['namefr'].text},{'lang': 'fr_FR'}) 	

	def parse_resource(self, resource, rows):
		
		if resource == 'products':
			self.import_products(rows)
		elif resource == 'categories':
			self.import_categories('product.category', rows)


CustomImport()