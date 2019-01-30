import sys
import socket
import copy
import os

from easyzone import easyzone


host = ''
port = 5353
dns_port = 53
buffer_size = 2048
type_values = {1: 'A', 28: 'AAAA', 2: 'NS', 5: 'CNAME', 6: 'SOA', 15: 'MX', 16: 'TXT'}
dns_server_ips = ['198.41.0.4', '192.228.79.201', '192.33.4.12', '199.7.91.13', 
'192.203.230.10', '192.5.5.241', '192.112.36.4', '128.63.2.53', '192.36.148.17',
'192.58.128.30', '193.0.14.129', '199.7.83.42', '202.12.27.33']
FIRST_TWO_BITS = 2**15 + 2**14
cache = {}

def get_ip(data):
	ip = ''
	for i in range(len(data)):
		ip += str(data[i]) + '.'
	return ip[: -1]

def get_name_bytes(name):
	labels = name.split('.')
	ans = bytes()
	for label in labels:
		ans += bytes([len(label)]) + bytes(label, 'ascii')
	ans += bytes([0])
	return ans

def get_name(data, l, key, key1, j, query, data_len=-1):
	if data[l] == 0 or len(query[key][j][key1]) == data_len-1:
		return l+1

	is_ptr = False;
	while data[l] & (1<<7) > 0 and data[l] & (1<<6) > 0:
		if not is_ptr:
			res = l+2
		l = int.from_bytes(data[l: l+2], byteorder='big') - FIRST_TWO_BITS
		is_ptr = True
	for i in range(data[l]):
		query[key][j][key1] += chr(data[l+i+1])
	l += data[l] + 1
	if data[l] != 0:
		query[key][j][key1] += '.'
	l = get_name(data, l, key, key1, j, query)
	if not is_ptr:
		res = l
	return res

def parse_data(response, new_data, i, key):
	if response[key][i]['type'] not in type_values:
		return None
	res = ''
	if type_values[response[key][i]['type']] == 'A':
		res = get_ip(response[key][i]['data'])
	elif type_values[response[key][i]['type']] == 'AAAA':
		for j in range(0, len(response[key][i]['data']), 2):
			b = int.from_bytes(new_data[response[key][i]['data_offs']+j: response[key][i]['data_offs']+j+2], byteorder='big')

			res += '{:02x}'.format(b) + ':'
		res = res[:-1]
	elif type_values[response[key][i]['type']] == 'CNAME' or type_values[response[key][i]['type']] == 'TXT' or type_values[response[key][i]['type']] == 'NS':
		response[key][i]['data_name'] = ''
		get_name(new_data, response[key][i]['data_offs'], key, 'data_name', i, response, response[key][i]['data_len'])
		res += response[key][i]['data_name']
	elif type_values[response[key][i]['type']] == 'MX':
		pref = int.from_bytes(response[key][i]['data'][:2], byteorder='big')
		res += str(pref) + ' '
		response[key][i]['data_name'] = ''
		get_name(new_data, response[key][i]['data_offs'], key, 'data_name', i, response, response[key][i]['data_len'])
		res += response[key][i]['data_name']
	elif type_values[response[key][i]['type']] == 'SOA':
		response[key][i]['data_name'] = ''
		l = get_name(new_data, response[key][i]['data_offs'], key, 'data_name', i, response, response[key][i]['data_len'])
		res += response[key][i]['data_name'] + ' '
		response[key][i]['data_name'] = ''
		l = get_name(new_data, l, key, 'data_name', i, response, response[key][i]['data_len'])
		res += response[key][i]['data_name'] + ' '
		for j in range(5):
			res += str(int.from_bytes(new_data[l: l+4], byteorder='big')) + ' '
			l += 4
	return res

def parse_answers(data, l, key, n, query):
	query[key] = []
	for j in range(n):
		query[key].append({})

		query[key][j]['name'] = ''
		l = get_name(data, l, key, 'name', j, query)
		query[key][j]['type'] = int.from_bytes(data[l: l+2], byteorder='big')
		query[key][j]['class'] = int.from_bytes(data[l+2: l+4], byteorder='big')
		query[key][j]['ttl'] = int.from_bytes(data[l+4: l+8], byteorder='big')
		query[key][j]['data_len'] = int.from_bytes(data[l+8: l+10], byteorder='big')
		query[key][j]['data_offs'] = l+10
		query[key][j]['data'] = data[l+10: l+10+query[key][j]['data_len']]

		query[key][j]['parsed_data'] = parse_data(query, data, j, key)

		l += 10 + query[key][j]['data_len']
	return l

def parse_message(data):
	query = {}
	query['transaction_id'] = data[:2]
	query['flags'] = int.from_bytes(data[2: 4], byteorder='big')
	query['num_q'] = int.from_bytes(data[4: 6], byteorder='big')
	query['num_ans'] = int.from_bytes(data[6: 8], byteorder='big')
	query['auth_rrs'] = int.from_bytes(data[8: 10], byteorder='big')
	query['add_rrs'] = int.from_bytes(data[10: 12], byteorder='big')

	l = 12
	query['name'] = ''
	while True:
		for i in range(data[l]):
			query['name'] += chr(data[l+i+1])
		l += data[l] + 1
		if data[l] == 0:
			break
		query['name'] += '.'
	query['type'] = int.from_bytes(data[l+1: l+3], byteorder='big')
	query['class'] = int.from_bytes(data[l+3: l+5], byteorder='big')

	l += 5
	l = parse_answers(data, l, 'answers', query['num_ans'], query)
	l = parse_answers(data, l, 'authority', query['auth_rrs'], query)
	parse_answers(data, l, 'additional', query['add_rrs'], query)

	return query

def log_message(query, response, data, new_data, ip):
	print(";; QUERY SECTION:")
	print('Standart query', '0x' + query['transaction_id'].hex(), type_values[query['type']], 'IN', query['name'])
	print('TO: ', ip)
	print('\n;; ANSWERS SECTION')
	for i in range(response['num_ans']):
		if response['answers'][i]['type'] not in type_values:
			continue
		print(response['answers'][i]['name'] + '.     ', response['answers'][i]['ttl'], 'IN', 
			type_values[response['answers'][i]['type']], response['answers'][i]['parsed_data'])
	print('\n;; AUTHORITY SECTION')
	for i in range(response['auth_rrs']):
		if response['authority'][i]['type'] not in type_values:
			continue
		print(response['authority'][i]['name'] + '.     ', response['authority'][i]['ttl'], 'IN', 
			type_values[response['authority'][i]['type']], response['authority'][i]['parsed_data'])
	print('\n;; ADDITIONAL SECTION')
	for i in range(response['add_rrs']):
		if response['additional'][i]['type'] not in type_values:
			continue
		print(response['additional'][i]['name'] + '.     ', response['additional'][i]['ttl'], 'IN', 
			type_values[response['additional'][i]['type']], response['additional'][i]['parsed_data'])

	print('\n\n\n')

def find_in_cache(query):
	name_parts = query['name'].split('.')
	curr = cache
	til_end = True
	for i in range(len(name_parts)-1, -1, -1):
		if name_parts[i] in curr:
			curr = curr[name_parts[i]]
		else:
			til_end = False
			break
	if til_end and ('answer', query['type']) in curr:
		return curr[('answer', query['type'])]
	return (curr['response'] if 'response' in curr else None)

def add_to_cache(name, response, data=None):
	name_parts = name.split('.')
	curr = cache
	for i in range(len(name_parts)-1, -1, -1):
		curr = curr.setdefault(name_parts[i], {})
	if data:
		curr[('answer', response['type'])] = data
	else:
		curr.setdefault('response', [])
		curr['response'].append(response)

def search_rec(sock, addr, data, query, queried_ips, ip, flag, searching_for_ns, cname_val=None):
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.settimeout(0.3)
	try:
		s.sendto(data, (ip, dns_port))
		new_data, new_addr = s.recvfrom(buffer_size)
	except socket.timeout as e:
		s.close()
		return None
	s.close()
	if (int.from_bytes(new_data[2: 4], byteorder='big') & 1) > 0 and (int.from_bytes(new_data[2: 4], byteorder='big') & 2) > 0:
		new_data = new_data[:2] + (int.from_bytes(new_data[2: 4], byteorder='big') | 2**7).to_bytes(2, byteorder='big') + new_data[4:]
		sock.sendto(new_data, addr) 
		if len(new_data) > 12:
			response = parse_message(new_data)
			log_message(query, response, data, new_data, ip)
		add_to_cache(response['name'], response, new_data)
		return ip
	if len(new_data) <= 12:
		return None
	response = parse_message(new_data)
	log_message(query, response, data, new_data, ip)
	datas = []
	queries = []
	cname_vals = []
	flags = []
	if response['num_ans'] > 0:
		cnames = {}
		for i in range(response['num_ans']):
			if response['answers'][i]['type'] == query['type']:
				cnames.clear()
				break
			if response['answers'][i]['type'] in type_values and type_values[response['answers'][i]['type']] == 'CNAME':
				cnames[response['answers'][i]['parsed_data']] = dict(response['answers'][i]) 
		if len(cnames) == 0:
			if not searching_for_ns:			
				my_resp = data[:2] + (response['flags'] | 2**7).to_bytes(2, byteorder='big')
				if flag:
					add_to_cache(response['name'], response, new_data)
					my_resp += new_data[4: 6] + (response['num_ans'] + 1).to_bytes(2, byteorder='big') + (0).to_bytes(4, byteorder='big') #new_data[8: 12]
					my_resp += get_name_bytes(cname_val['name']) + query['type'].to_bytes(2, byteorder='big') + query['class'].to_bytes(2, byteorder='big')
					my_resp += get_name_bytes(cname_val['name']) + cname_val['type'].to_bytes(2, byteorder='big')
					my_resp += cname_val['class'].to_bytes(2, byteorder='big') + cname_val['ttl'].to_bytes(4, byteorder='big')
					my_resp += (len(response['name']) + 2).to_bytes(2, byteorder='big') + get_name_bytes(response['name'])
					for i in range(response['num_ans']):
						my_resp += get_name_bytes(response['answers'][i]['name']) + response['answers'][i]['type'].to_bytes(2, byteorder='big')
						my_resp += response['answers'][i]['class'].to_bytes(2, byteorder='big') + response['answers'][i]['ttl'].to_bytes(4, byteorder='big')
						my_resp += response['answers'][i]['data_len'].to_bytes(2, byteorder='big') + response['answers'][i]['data']
				else: 
					my_resp += new_data[4:]
				sock.sendto(my_resp, addr)
				parsed_my_resp = parse_message(my_resp)
				add_to_cache(parsed_my_resp['name'], parsed_my_resp, my_resp)
			else:
				add_to_cache(response['name'], response, new_data)

			return response['answers'][response['num_ans']-1]['data']
		else:
			tmp_resp = copy.deepcopy(response)
			tmp_resp['type'] = 5
			add_to_cache(response['name'], tmp_resp, 
				new_data[:14+len(response['name'])] + (5).to_bytes(2, byteorder='big') + new_data[16+len(response['name']):])
			for cname in cnames:
				datas.append(data[:12] + get_name_bytes(cname) + data[len(query['name']) + 14:])
				new_query = copy.deepcopy(query)
				new_query['name'] = cname
				queries.append(new_query)
				cname_vals.append(cnames[cname])
				flags.append(True)
	else:
		add_to_cache(response['authority'][0]['name'], response)

	datas.append(data)
	queries.append(query)
	cname_vals.append(cname_val)
	flags.append(flag)

	for i in range(len(datas)):
		data = datas[i]
		query = queries[i]
		cname_val = cname_vals[i]
		flag = flags[i]

		nss = set()
		for i in range(response['auth_rrs']):
			if response['authority'][i]['type'] in type_values and type_values[response['authority'][i]['type']] == 'NS':
				nss.add(response['authority'][i]['parsed_data'])
		for i in range(response['add_rrs']):
			if response['additional'][i]['type'] in type_values and type_values[response['additional'][i]['type']] == 'A':
				nss.remove(response['additional'][i]['name'])
				next_ip = get_ip(response['additional'][i]['data'])
				if next_ip in queried_ips:
					continue 
				queried_ips.add(next_ip)
				res = search_rec(sock, addr, data, query, queried_ips, next_ip, flag, searching_for_ns, cname_val)
				if res:
					return res
		next_ips = set()
		for ns in nss:
			new_request = data[:12] + get_name_bytes(ns) + (1).to_bytes(2, byteorder='big') + data[len(query['name']) + 16:]
			new_query = copy.deepcopy(query)
			new_query['name'] = ns
			new_query['type'] = 1
			res = search_wrap(sock, addr, new_request, new_query, True)
			if res:
				next_ips.add(get_ip(res))
		for next_ip in next_ips:
			if next_ip in queried_ips:
				continue 
			queried_ips.add(next_ip)
			res = search_rec(sock, addr, data, query, queried_ips, next_ip, flag, searching_for_ns, cname_val)
			if res:
				return res

	return None

def search_wrap(sock, addr, data, query, searching_for_ns):
	queried_ips = set()
	responses = find_in_cache(query)
	if responses and type(responses) is not list:
		if not searching_for_ns:
			response = data[:2] + responses[2:]
			sock.sendto(response, addr)
		r = parse_message(responses)
		return r['answers'][r['num_ans']-1]['data']
	
	ips = set()
	nss = set()
	if not responses:
		ips = set(dns_server_ips)
	else:
		for response in responses:
			for i in range(response['auth_rrs']):
				if response['authority'][i]['type'] in type_values and type_values[response['authority'][i]['type']] == 'NS':
					nss.add(response['authority'][i]['parsed_data'])
			for i in range(response['add_rrs']):
				if response['additional'][i]['type'] in type_values and type_values[response['additional'][i]['type']] == 'A':
					nss.remove(response['additional'][i]['name'])
					ips.add(get_ip(response['additional'][i]['data']))
	for ip in ips:
		res = search_rec(sock, addr, data, query, queried_ips, ip, False, searching_for_ns)
		if res:
			return res
	next_ips = set()	
	for ns in nss:
		new_request = data[:12] + get_name_bytes(ns) + (1).to_bytes(2, byteorder='big') + data[len(query['name']) + 16:]
		new_query = copy.deepcopy(query)
		new_query['name'] = ns
		new_query['type'] = 1
		res = search_wrap(sock, addr, new_request, new_query, True)
		if res:
			next_ips.add(get_ip(res))
	for next_ip in next_ips:
		if next_ip in queried_ips:
			continue 
		queried_ips.add(next_ip)
		res = search_rec(sock, addr, data, query, queried_ips, next_ip, False, searching_for_ns)
		if res:
			return res


def run_dns_server(configpath):
	# your code here
	with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		sock.bind((host, port))

		while True:
			data, addr = sock.recvfrom(buffer_size)
			query = parse_message(data)
			if query['type'] not in type_values:
				continue
			
			name_list = query['name'].split('.')[-2:]
			name = name_list[0] + '.' + name_list[1]

			from_zone = False
			if os.path.isfile(configpath + name + '.conf'):
				z = easyzone.zone_from_file(name, configpath + name + '.conf')
				item_list = z.names[query['name'] + '.'].records(type_values[query['type']])
				if item_list:
					from_zone = True
					item_list = item_list.items
					flags = 2**15 + 2**10 + (2**8 & query['flags']) + 2**7
					my_resp = data[:2] + flags.to_bytes(2, byteorder='big') + data[4:6]
					my_resp += (len(item_list)).to_bytes(2, byteorder='big') + (0).to_bytes(4, byteorder='big') 
					my_resp += get_name_bytes(query['name']) + data[len(query['name']) + 14: len(query['name']) + 18]
					for item in item_list:
						my_resp += get_name_bytes(query['name']) + query['type'].to_bytes(2, byteorder='big')
						my_resp += query['class'].to_bytes(2, byteorder='big') + (300000).to_bytes(4, byteorder='big')  
						if type_values[query['type']] == 'A':
							my_resp += (4).to_bytes(2, byteorder='big')
							parts = item.split('.')
							for i in range(4):
								my_resp += bytes([int(parts[i])])
						elif type_values[query['type']] == 'AAAA':
							my_resp += (16).to_bytes(2, byteorder='big')
							parts = item.split(':')
							for i in range(len(parts)):
								if parts[i] == '':
									my_resp += (0).to_bytes(2*(8-len(parts)), byteorder='big')
								else:
									my_resp += bytearray.fromhex(parts[i])
						elif type_values[query['type']] == 'MX':
							name = get_name_bytes(item[1]) if item[1][-1] != '.' else get_name_bytes(item[1][:-1])
							my_resp += (len(name) + 2).to_bytes(2, byteorder='big') + item[0].to_bytes(2, byteorder='big') + name
						elif type_values[query['type']] == 'NS' or type_values[query['type']] == 'CNAME':
							name = get_name_bytes(item) if item[-1] != '.' else get_name_bytes(item[:-1])
							print(name)
							my_resp += len(name).to_bytes(2, byteorder='big') + name
						elif type_values[query['type']] == 'TXT':
							if item[0] == '"':
								item = item[1:]
							if item[-1] == '"':
								item = item[:-1]
							name = get_name_bytes(item)[:-1]
							my_resp += len(name).to_bytes(2, byteorder='big') + name
						else:
							parts = item.split(' ')
							name1 = get_name_bytes(parts[0][:-1])
							name2 = get_name_bytes(parts[0][:-1])
							my_resp += (20 + len(name1) + len(name2)).to_bytes(2, byteorder='big') + name1 + name2
							for i in range(2, len(parts)):
								my_resp += int(parts[i]).to_bytes(4, byteorder='big')
					sock.sendto(my_resp, addr)

			if not from_zone:
				search_wrap(sock, addr, data, query, False)

# do not change!
if __name__ == '__main__':
	configpath = sys.argv[1]
	run_dns_server(configpath)