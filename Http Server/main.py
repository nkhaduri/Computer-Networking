import sys
import json
import socket
import os
import magic
import urllib
import time
import selectors
from time import mktime
from hashlib import sha256
from datetime import datetime
from wsgiref.handlers import format_date_time
from multiprocessing import Process
from threading import Thread
from pathlib import Path

backlog = 1024
buffer_size = 2048
not_found_text = bytes("REQUESTED DOMAIN NOT FOUND", "utf-8")

class ClientHandler(Thread):
	def __init__(self, sock, buffer_size, servers, log_path):
		super().__init__()
		self.sock = sock
		self.buffer_size = buffer_size
		self.servers = servers
		self.log_path = log_path
		self.sel = selectors.DefaultSelector()
		self.sock.setblocking(False)
		self.sel.register(self.sock, selectors.EVENT_READ, self.read)

	def read(self):
		try:
			request = self.sock.recv(self.buffer_size)
		except ConnectionResetError:
			self.sock.close()
			return
		request_str = str(request, "utf8")
		if request:
			lines = request_str.split("\r\n")
			method, url, http_v = lines[0].split(" ") 
			url = urllib.parse.unquote(url)
			header_fields = {}
			for line in lines[1:]:
				s = line.split(":", 1)
				if len(s) == 2:
					header_fields[s[0].strip().lower()] = s[1].strip() 
			
			date = format_date_time(mktime(datetime.now().timetuple()))
			response = http_v + " "
			headers = "Server: http_serv\r\nCache-Control: max-age=5\r\nAccept-Ranges: bytes\r\nDate: " + date + "\r\n"
			if 'connection' in header_fields and header_fields['connection'].lower() == 'keep-alive':
				headers += "Connection: keep-alive\r\nKeep-Alive: timeout=5\r\n\r\n"
			else:
				headers += "Connection: close\r\n\r\n"
			status_code = "404"
			cont_len = "0"
			documentroot = ''
			for server in self.servers:
				if server['vhost'] == header_fields['host'].split(':')[0]:
					documentroot = server['documentroot']
					break;

			if documentroot != '' and Path(documentroot + url).is_file():
				file = open(documentroot + url, "rb")
				is_partial = False
				if 'range' in header_fields:
					byte_range = header_fields['range'].split('=')[1].strip()
					start = int(byte_range.split('-')[0].strip())
					file.seek(start)
					if byte_range[-1] != '-':
						length = int(byte_range.split('-')[1].strip()) - start + 1
						if length < 0:
							response += "416 Requested Range Not Satisfiable\r\nContent-Length: 0\r\n" 
							status_code = "416"
							response += headers
							response = bytes(response, "utf-8")
							self.sock.send(response)
							return

						content = file.read(length)
						is_partial = True
					else: 
						content = file.read()
					if start != 0:
						is_partial = True
				else:
					content = file.read()
				file.close()

				h = sha256()
				h.update(content);
				file_hash = h.hexdigest()
				is_modified = True
				if 'if-none-match' in header_fields:
					if file_hash == header_fields['if-none-match']:
						response += "304 OK\r\n"
						status_code = "304"
						is_modified = False
				if is_partial:
					response += "206 Partial Content\r\n"
					status_code = "206"
				elif is_modified and not is_partial:
					response += "200 OK\r\n"
					status_code = "200"
				mime = magic.Magic(mime=True)
				response += "Content-Type: " + mime.from_file(documentroot + url) + "\r\n"
				cont_len = str(len(content))
				response += "Content-Length: " + cont_len + "\r\n"
				response += "ETag: " + file_hash + "\r\n"
				response += headers
				response = bytes(response, "utf-8")
				if method == "GET" and is_modified:
					response += content
			else: 
				response += "404 Not Found\r\n" 
				cont_len = str(len(not_found_text))
				response += "Content-Length: " + cont_len + "\r\n" 
				response += headers
				response = bytes(response, "utf-8") + not_found_text
			self.sock.send(response)
			log_msg = "[" + time.strftime("%c") + "] " + self.sock.getpeername()[0] + " " + header_fields['host'] + " " + url + " " +\
									status_code + " " + cont_len + " " + '"' + header_fields['user-agent'] + '"\n'
			if documentroot != '':
				with open(self.log_path + '/' + header_fields['host'].split(':')[0] + '.log', "a") as log_file:
					log_file.write(log_msg)
			else:
				with open(self.log_path + '/error.log', "a") as log_file:
					log_file.write(log_msg)
			if 'connection' in header_fields and header_fields['connection'].lower() == 'keep-alive':	
				for x in self.sel.select(timeout=5):
					self.read()
		try:
			self.sel.unregister(self.sock)
			self.sock.close()
		except:
			pass

	def run(self):
		for x in self.sel.select(timeout=1):
			self.read()

class VhostHandler(Thread):
	def __init__(self, servers, ip, port, log_path):
		super().__init__()
		self.servers = servers
		self.ip = ip
		self.port = port
		self.log_path = log_path

	def run(self):
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			sock.bind((self.ip, self.port))

			sock.listen(backlog)
			while True:
				conn, addr = sock.accept()
				ClientHandler(conn, buffer_size, self.servers, self.log_path,).start()

def create_log_files(config_data):
	for server in config_data['server']:
		with open(config_data['log'] + '/' + server['vhost'] + '.log', 'w') as file:
			pass

if __name__ == '__main__':
	conf_path = sys.argv[1]
	config_file = open(conf_path, 'r')
	config_data = json.loads(config_file.read())
	create_log_files(config_data)

	ip_ports = []
	for server in config_data['server']:
		ip_port = server['ip']+':'+str(server['port'])
		if ip_port not in ip_ports:
			ip_ports.append(ip_port)
			VhostHandler(config_data['server'], server['ip'], int(server['port']), config_data['log']).start()