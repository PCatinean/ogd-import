import ConfigParser
import argparse
import os
import logging
import ogd_logging 
import gdata.spreadsheet.service
import gdata.service
import xmlrpclib

class GoogleSpreadsheet():
    ''' An iterable google spreadsheet object.  Each row is a dictionary with an entry for each field, keyed by the header'''
    
    def __init__(self, drive_email, drive_password):
        gd_client = gdata.spreadsheet.service.SpreadsheetsService()
        gd_client.email = drive_email
        gd_client.password = drive_password
        gd_client.ProgrammaticLogin()
        
        self.gd_client = gd_client
        
    def formRows(self, ListFeed):
        rows = []
        for entry in ListFeed.entry:
            d = {}
            for key in entry.custom.keys():
                d[key] = entry.custom[key].text
            rows.append(d)
        return rows

    def getRows(self, spreadsheet_id, worksheet_id=None):
        if worksheet_id:
            rows = self.gd_client.GetListFeed(spreadsheet_id, worksheet_id)
        else:
            rows = self.gd_client.GetListFeed(spreadsheet_id)
        return self.formRows(rows)
    
    def listSpreadsheets(self, query=None):
        "Return a dictionary with tuples representing SpreadSheet names, their ids and child worksheet ids and names"
        spreadsheet_data = {}       
        feed = self.gd_client.GetSpreadsheetsFeed(query).entry
        for spreadsheet in feed:
            spreadsheet_id = spreadsheet.id.text.rsplit('/',1)[1]
            spreadsheet_name = spreadsheet.title.text

            spreadsheet_data[spreadsheet_name] = (spreadsheet_id, [])

            worksheets = self.gd_client.GetWorksheetsFeed(spreadsheet_id).entry

            for worksheet in worksheets:
                worksheet_id = worksheet.id.text.rsplit('/',1)[1]
                worksheet_name = worksheet.title.text
                spreadsheet_data[spreadsheet_name][1].append((worksheet_name, worksheet_id))

        return spreadsheet_data



class OpenERP():

    def __init__(self, username, password, host, database, port=8069):

        xmlrpc_addr = 'http://%s:%s/xmlrpc/object'%(host,port)
        login_addr = 'http://%s:%s/xmlrpc/common'%(host,port)
        
        s = xmlrpclib.ServerProxy(xmlrpc_addr)

        self.username = username
        self.database = database
        self.xmlrpc_addr = xmlrpc_addr
        self.uid = xmlrpclib.ServerProxy(login_addr).login(database, username, password)
        self.execute = lambda *a: s.execute(database, self.uid, password, *a)

    def get_res_id(self, obj_model, external_id):
        """Verifies if there is a resource in the database using the external_id provided and returns the database_id"""

        domain = [('name','=',external_id),('model','=',obj_model)]
        data_id = self.execute('ir.model.data','search',domain)
        if data_id:
            res_dict = self.execute('ir.model.data','read',data_id[0],['res_id'])
            return res_dict['res_id'] if res_dict else False
        return False

    def get_option_id(self, dimension_id,label,code):
        #Get option database id by using unqieu code field
        option_id = self.execute('product.variant.dimension.option','search',[('code','=',code),('name','=',label),('dimension_id','=',dimension_id)])
        return option_id[0] if option_id else False          

    def create_external_id(self, obj_model, external_id, res_id, module=None):
        """Creates a external id in ir.model.data"""
        vals = {'name': external_id,
                'model': obj_model,
                'module': module,
                'res_id': res_id,
                'noupdate': 1}
        self.execute('ir.model.data','create',vals)
        return True

    def get_uom_id(self, name, uoms={}):
        """Returns the unit of measure id by using the same as search cryteria"""
        if name not in uoms:
            uom_id = self.execute('product.uom','search',[('name','=',name)])
            if uom_id:
                uoms[name] = uom_id[0]
            else:
                logging.warning("Unit of Measure ('%s') not found"%name)
                return False
        return uoms[name]   

    def get_country_id(self, country_code):
        """Returns the Country ID by using the country code (e.g 'de_DE','en_EN' etc)"""
        country_id = self.execute('res.country','search',[('code','=',country_code)])
        return country_id[0] if country_id else False             


class OGDParser():

    def __init__(self):
        #Parse CLI arguments
        self.parser = argparse.ArgumentParser()
        group = self.parser.add_mutually_exclusive_group(required=True)

        group.add_argument("-l",'--list', action="store_true", help="List spreadsheets and ids")
        group.add_argument("-r","--resources", nargs="+", help="Resources to import")

        self.parser.add_argument("-e","--env", required=True, help="OpenERP environment")
        self.parser.add_argument("-m","--magento", action="store_true", help="Magento fields included")
        self.parser.add_argument("-u","--update", nargs="+", default=[], help="Update resources"),
        self.parser.add_argument("-i","--update-inventory", action="store_true", help="Update products inventory"),

        self.args = self.parser.parse_args()

    def read_config(self, config_file):
        if not os.path.isfile(config_file):
            logging.error("No such file '%s'" % config_file)

        self.config = ConfigParser.ConfigParser()
        self.config.read(config_file)

        try:
            self.oerp_host = self.config.get(self.args.env, 'openerp_host')
            self.oerp_port = self.config.get(self.args.env, 'openerp_port')
            self.oerp_database = self.config.get(self.args.env, 'openerp_database')
            self.oerp_username = self.config.get(self.args.env, 'openerp_username')
            self.oerp_password = self.config.get(self.args.env, 'openerp_password')

            self.drive_email = self.config.get(self.args.env, 'drive_email')
            self.drive_password = self.config.get(self.args.env, 'drive_password')

        except Exception, e:
            logging.error("Config file error (%s)" % e)        

    def parse_arguments(self):
        #Load configuration file

        self.read_config('ogd_config.ini')

        #OpenERP login

        try:
            xmlrpc_addr = 'http://%s:%s/xmlrpc/object'%(self.oerp_host,self.oerp_port)
            logging.info("Attempting login to OpenERP server at '%s'..." % xmlrpc_addr)
            self.open_erp = OpenERP(self.oerp_username, self.oerp_password, self.oerp_host, self.oerp_database, self.oerp_port)
        except Exception, e:
            logging.error(e.strerror)

        logging.info("Login to OpenERP server successful!")

        #Login to Drive

        try:
            logging.info("Attempting login to Google Drive with email '%s'..."%self.drive_email)
            self.google_drive = GoogleSpreadsheet(self.drive_email,self.drive_password)
        except Exception, e:
            logging.error("Google Drive: %s" % e.message)

        logging.info("Login to Google Drive successful!")


        #Print spreadsheetlist if requested by the -l option
        if self.args.list:
            logging.info("Retreiving Spreadsheet info...")
            spreadsheet_data = self.google_drive.listSpreadsheets()
            for ss_name, ss_info in spreadsheet_data.items():
                print "%s: %s" % (ss_name, ss_info[0])
                for ws_data in ss_info[1]:
                    print "    %s: %s" % (ws_data[0], ws_data[1])
                print "\n"

        #Load resources otherwise
        else:
            for res in self.args.resources:
                res_data = [x.strip() for x in self.config.get(self.args.env, res).split(',')]
                #Retreive spreadhseet and worksheet of resource to import
                spreadsheet_id = res_data[0]
                worksheet_id = res_data[1] if len(res_data) > 1 else None
                rows = self.google_drive.getRows(spreadsheet_id, worksheet_id)

                self.parse_resource(res, rows)

    def parse_resource(self, resource, rows):
        """Function hook to be overriden by subclass to handle resource data and import"""
        pass