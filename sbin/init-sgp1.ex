#!/usr/bin/expect -f
# wrapper to make passwd(1) be non-interactive
# username is passed as 1st arg, passwd as 2nd

set hostip [lindex $argv 0]
set password [lindex $argv 1]
set newpassword [lindex $argv 2]

set timeout -1

spawn ssh root@$hostip

expect "(yes/no)?"
send "yes\r"
expect "assword:"
send "$password\r"
expect "UNIX password:"
send "$password\r"
expect "password:"
send "$newpassword\r"
expect "password:"
send "$newpassword\r"
expect "\#"
send "exit\r"
expect eof
