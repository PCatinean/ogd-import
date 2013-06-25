import ConfigParser
import argparse
import os
import logging
import ogd_logging 
import gdata.spreadsheet.service
import gdata.service
import xmlrpclib

class GoogleSpreadsheet:
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

        self.uid = xmlrpclib.ServerProxy(login_addr).login(database, username, password)
        self.execute = lambda *a: s.execute(database, self.uid, password, *a)


class OGDParser():

    def __init__(self):
        #Parse CLI arguments
        parser = argparse.ArgumentParser()
        group = parser.add_mutually_exclusive_group(required=True)

        group.add_argument("-l",'--list', action="store_true", help="List spreadsheets and their ids")
        group.add_argument("-r","--resources", nargs="+", help="Resources to import, *NOTE: Priority is taken into consideration*")

        parser.add_argument("-e","--env", required=True, help="OpenERP environment")
        parser.add_argument("-m","--magento", action="store_true", help="Add magento fields to import")
        parser.add_argument("-u","--update", nargs="+", default=[], help="Update the following resources"),

        args = parser.parse_args()

        #Load configuration file

        if not os.path.isfile('ogd_config.ini'):
            logging.error("No such file 'ogd_config.ini'")

        config = ConfigParser.ConfigParser()
        config.read('ogd_config.ini')

        try:
            oerp_host = config.get(args.env, 'openerp_host')
            oerp_port = config.get(args.env, 'openerp_port')
            oerp_database = config.get(args.env, 'openerp_database')
            oerp_username = config.get(args.env, 'openerp_username')
            oerp_password = config.get(args.env, 'openerp_password')

            drive_email = config.get(args.env, 'drive_email')
            drive_password = config.get(args.env, 'drive_password')

        except Exception, e:
            logging.error("Config file error (%s)" % e)

        #OpenERP login

        try:
            import pdb;pdb.set_trace()
            xmlrpc_addr = 'http://%s:%s/xmlrpc/object'%(oerp_host,oerp_port)
            logging.info("Attempting login to OpenERP server at '%s'..." % xmlrpc_addr)
            OpenERP = OpenERP(oerp_username, oerp_password, oerp_host, oerp_database, oerp_port)
        except Exception, e:
            logging.error(e.strerror)

        logging.info("Login to OpenERP server successful!")

        #Login to Drive

        try:
            logging.info("Attempting login to Google Drive with email '%s'..."%drive_email)
            GDrive = GoogleSpreadsheet(drive_email,drive_password)
        except Exception, e:
            logging.error("Google Drive: %s" % e.message)

        logging.info("Login to Google Drive successful!")


        #Print spreadsheetlist if requested by the -l option
        if args.list:
            logging.info("Retreiving Spreadsheet info...")
            spreadsheet_data = GDrive.listSpreadsheets()
            for ss_name, ss_info in spreadsheet_data.items():
                print "%s: %s" % (ss_name, ss_info[0])
                for ws_data in ss_info[1]:
                    print "    %s: %s" % (ws_data[0], ws_data[1])
                print "\n"
        #Load resources otherwise
        else:
            for res in args.resources:
                try:
                    res_data = config.get(args.env, res).split(',')
                    #Retreive spreadhseet and worksheet of resource to import
                    spreadhseet_id = res_data[0]
                    worksheet_id = res_data[1] if len(res_data) > 1 else None
                    rows = GDrive.getRows(spreadhseet_id, worksheet_id)
                    
                    #Get data from spreadsheet
                    #Register function to handle data
                    #Prase it
                except Exception, e:
                    logging.error(e)