import ConfigParser
import argparse
import os
import logging
import ogd_logging 

from openerp import OpenERP
from googlespreadsheet import GoogleSpreadsheet


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
    logger.error(e.message)

logging.info("Login to OpenERP server successful!")

#Login to Drive

try:
    logging.info("Attempting login to Google Drive with email '%s'..."%drive_email)
    ogd_spreadsheet = GoogleSpreadsheet(drive_email,drive_password)
except Exception, e:
    logging.error("Google Drive: %s" % e.message)

logging.info("Login to Google Drive successful!")


#Print spreadsheetlist if requested by the -l option
if args.list:
    spreadsheet_list = ogd_spreadsheet.listSpreadsheets().iteritems()
    print "\n".join( ("'%s': %s" % (k, v) for k, v in spreadsheet_list) )

#Load resources otherwise
else:
    for res in args.resources:
        try:
            config.get(args.env, res)
        except Exception, e:
            logging.error(e)

