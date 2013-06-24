import gdata.spreadsheet.service
import gdata.service

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
	
	def listSpreadsheets(self, query=None):
		"Return a dictionary with SpreadSheet names and Ids as key: val pair"
		feed = self.gd_client.GetSpreadsheetsFeed(query).entry
		spreadsheet_ids = {entry.title.text: entry.id.text.rsplit('/',1)[1] for entry in feed}
		return spreadsheet_ids