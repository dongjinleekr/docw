#!/usr/bin/python3

# http://stackoverflow.com/questions/315362/properly-formatted-example-for-python-imap-email-access
# http://stackoverflow.com/questions/3180891/imap-deleting-messages

import os, sys, imaplib, re, email
from io import StringIO
from dopy.manager import DoManager

PasswordRegex = r"Password: (\w+)"

def is_active(client_id, api_key, hostname):
	do = DoManager(client_id, api_key)
	droplet = next((d for d in do.all_active_droplets() if d['name'] == hostname), None)
	
	return droplet

def fetch(server, username, password, hostname):
	mailbox = imaplib.IMAP4_SSL(server)
	mailbox.login(username, password)
	mailbox.select('inbox')

	_, found = mailbox.search(None, '(SUBJECT "Your new Droplet is created! (%s) - DigitalOcean")' % hostname)
	
	msgIds = found[0].split()
	if 1 == len(msgIds):
		_, data = mailbox.fetch(msgIds[0], '(RFC822)')  # data = [ (a, b), c ]
		# contents = data[0][1].decode(encoding='UTF-8')
		msg = email.message_from_bytes(data[0][1])
		body = msg.get_payload()

		# temp. password
		mp = re.search(PasswordRegex, body)
		if mp:
			tempPassword = mp.group(1).strip()
		else:
			raise ValueError("Invalid temp. password")

		print(tempPassword)
		mailbox.store(msgIds[0], '+FLAGS', '\\Deleted')
		
	else:
		raise ValueError("Invalid temp. password")

	mailbox.close()
	mailbox.logout()

	return 0

def main():
	try:
		if is_active(sys.argv[1], sys.argv[2], sys.argv[6]):
			fetch(sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
		else:
			raise ValueError("No active host")

	except Exception as e:
		return 1

	return 0

if __name__ == '__main__':
	sys.exit(main())
