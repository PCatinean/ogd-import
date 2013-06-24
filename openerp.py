import xmlrpclib

class OpenERP():

	def __init__(self, username, password, host, database, port=8069):

		xmlrpc_addr = 'http://%s:%s/xmlrpc/object'%(host,port)
		login_addr = 'http://%s:%s/xmlrpc/common'%(host,port)
		
		s = xmlrpclib.ServerProxy(xmlrpc_addr)

		self.uid = xmlrpclib.ServerProxy(login_addr).login(database, username, password)
		self.execute = lambda *a: s.execute(database, self.uid, password, *a)

