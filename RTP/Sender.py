import sys
import getopt
import random
import time

import Checksum
import BasicSender

'''
This is a skeleton sender class. Create a fantastic transport protocol here.
'''
data_size = 1400
window_size = 7
acks_to_retransmit = 4
max_timeout = 0.5
class Sender(BasicSender.BasicSender):
	def __init__(self, dest, port, filename, debug=False, sackMode=False):
		super(Sender, self).__init__(dest, port, filename, debug)
		self.sackMode = sackMode
		self.debug = debug

	def send_packet(self, data_chunks, seq_num):
		msg_type = 'dat'
		if seq_num == len(data_chunks):
			msg_type = 'fin'
		self.send(self.make_packet(msg_type, seq_num, data_chunks[seq_num-1]))

	# Main sending loop.
	def start(self):
		seq_num = 0
		self.send(self.make_packet('syn', seq_num, None))
		ack = self.receive(max_timeout)
		while not Checksum.validate_checksum(ack) or int(self.split_packet(ack)[1].split(';')[0]) != seq_num+1:
			# print ack
			self.send(self.make_packet('syn', seq_num, None))
			ack = self.receive(max_timeout)
		data = self.infile.read()
		data_chunks = [data[i: i+data_size] for i in range(0, len(data), data_size)]
		l = 0
		r = 0
		same = 0
		last = 1
		send_times = [float('inf')] * window_size
		if not self.sackMode:
			while l != len(data_chunks):
				for i in range(r, min(l + window_size, len(data_chunks))):
					self.send_packet(data_chunks, i+1)
					send_times[i-l] = time.time()
				r = min(l + window_size, len(data_chunks))
				start = time.time()
				timeout = max_timeout - (time.time() - min(send_times))
				ind = send_times.index(min(send_times))
				while time.time() - start <= timeout:
					ack = self.receive(max(0, timeout - (time.time() - start)))
					if not Checksum.validate_checksum(ack) or self.split_packet(ack)[0] != 'ack' or\
								not l+1 <= int(self.split_packet(ack)[1]) <= r+1:
						continue
					msg_type, seqno, data, checksum = self.split_packet(ack)
					seqno = int(seqno)
					if seqno == len(data_chunks)+1:
						return
					if seqno == last:
						same += 1
					else:
						same = 1
						last = seqno
					if same == acks_to_retransmit:
						self.send_packet(data_chunks, last)
						send_times[last-1-l] = time.time()
					if seqno > l+1:
						break
				if last <= l+ind+1:
					self.send_packet(data_chunks, l+ind+1)
					send_times[ind] = time.time()
				send_times = send_times[-window_size+(last-1-l): ] + [float('inf')] * (last-1-l)
				l = last-1
		else:
			received = [False] * window_size
			while l != len(data_chunks):
				for i in range(r, min(l + window_size, len(data_chunks))):
					if not received[i-l]:
						self.send_packet(data_chunks, i+1)
						send_times[i-l] = time.time()
				r = min(l + window_size, len(data_chunks))
				start = time.time()
				minn = send_times[0]
				ind = 0
				for i in range(1, window_size):
					if not received[i] and minn > send_times[i]:
						minn = send_times[i]
						ind = i
				timeout = max_timeout - (time.time() - minn)
				while time.time() - start <= timeout:
					ack = self.receive(timeout - (time.time() - start))
					if not Checksum.validate_checksum(ack) or self.split_packet(ack)[0] != 'sack' or\
								not l+1 <= int(self.split_packet(ack)[1].split(';')[0]) <= r+1:
						continue
					msg_type, seqno, data, checksum = self.split_packet(ack)
					seqno_split = seqno.split(';')
					seqno = int(seqno_split[0])
					if seqno == len(data_chunks)+1:
						return
					for x in seqno_split[1].split(','):
						if x != '':
							received[int(x)-1-l] = True
					if seqno == last:
						same += 1
					else:
						same = 1
						last = seqno
					if same == acks_to_retransmit:
						self.send_packet(data_chunks, last)
						send_times[last-1-l] = time.time()
					if seqno > l+1:
						break
				if last <= l+ind+1 and not received[ind]:
					self.send_packet(data_chunks, l+ind+1)
					send_times[ind] = time.time()
				send_times = send_times[-window_size+(last-1-l): ] + [float('inf')] * (last-1-l)
				received = received[-window_size+(last-1-l):] + [False] * (last-1-l)
				l = last-1

        
'''
This will be run if you run this script from the command line. You should not
change any of this; the grader may rely on the behavior here to test your
submission.
'''
if __name__ == "__main__":
	def usage():
		print "BEARS-TP Sender"
		print "-f FILE | --file=FILE The file to transfer; if empty reads from STDIN"
		print "-p PORT | --port=PORT The destination port, defaults to 33122"
		print "-a ADDRESS | --address=ADDRESS The receiver address or hostname, defaults to localhost"
		print "-d | --debug Print debug messages"
		print "-h | --help Print this usage message"
		print "-k | --sack Enable selective acknowledgement mode"

	try:
		opts, args = getopt.getopt(sys.argv[1:],
								"f:p:a:dk", ["file=", "port=", "address=", "debug=", "sack="])
	except:
		usage()
		exit()

	port = 33122
	dest = "localhost"
	filename = None
	debug = False
	sackMode = False

	for o,a in opts:
		if o in ("-f", "--file="):
			filename = a
		elif o in ("-p", "--port="):
			port = int(a)
		elif o in ("-a", "--address="):
			dest = a
		elif o in ("-d", "--debug="):
			debug = True
		elif o in ("-k", "--sack="):
			sackMode = True

	s = Sender(dest,port,filename,debug, sackMode)
	try:
		s.start()
	except (KeyboardInterrupt, SystemExit):
		exit()
