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