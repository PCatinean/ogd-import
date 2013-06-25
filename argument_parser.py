import ConfigParser
import argparse
import os
import logging
import ogd_logging 

from openerp import OpenERP
from googlespreadsheet import GoogleSpreadsheet

_resmap = {}

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
            import pdb;pdb.set_trace()

            #Get data from spreadsheet
            #Register function to handle data
            #Parse it
        except Exception, e:
            logging.error(e)


