#!/usr/bin/python3

# http://stackoverflow.com/questions/315362/properly-formatted-example-for-python-imap-email-access
# http://stackoverflow.com/questions/3180891/imap-deleting-messages

import os, sys, argparse, imaplib, re, email
from io import StringIO

PasswordRegex = r"Password: (\w+)"

def fetch(server, username, password, hostname):
	mailbox = imaplib.IMAP4_SSL(server)
	mailbox.login(username, password)
	mailbox.select('inbox')

	_, found = mailbox.search(None, '(SUBJECT "Your new Droplet is created!")')
	for num in found[0].split():
		_, data = mailbox.fetch(num, '(RFC822)') # data = [ (a, b), c ]
		# contents = data[0][1].decode(encoding='UTF-8')
		msg = email.message_from_bytes(data[0][1])
		subject = msg['subject']
		
		if subject == 'Your new Droplet is created! (%s) - DigitalOcean' % hostname:
			body = msg.get_payload()

			# temp. password
			mp = re.search(PasswordRegex, body)
			if mp:
				tempPassword = mp.group(1).strip()
			else:
				raise ValueError("Invalid temp. password")

			print(tempPassword)
			mailbox.store(num, '+FLAGS', '\\Deleted')

	mailbox.close()
	mailbox.logout()

	return 0

def main():
	parser = argparse.ArgumentParser(description='')
	parser.add_argument('-s', '--server', type=str, required=True, help='')
	parser.add_argument('-u', '--username', type=str, required=True, help='')
	parser.add_argument('-p', '--password', type=str, required=True, help='')
	parser.add_argument('-n', '--hostname', type=str, required=True, help='')

	parsed = parser.parse_args(sys.argv[1:])

	args = vars(parsed)

	try:
		fetch(args['server'], args['username'], args['password'], args['hostname'])

	except Exception as e:
		print(e)
		return 1

	return 0

if __name__ == '__main__':
	sys.exit(main())
