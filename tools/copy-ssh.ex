#!/usr/bin/expect -f

set pub_file_path [lindex $argv 0]
set remote_hostname [lindex $argv 1]
set remote_user [lindex $argv 2]
set remote_password [lindex $argv 3]

set timeout -1

spawn ssh-copy-id -i $pub_file_path $remote_user@$remote_hostname
expect "password:"
send "$remote_password\r"
expect eof
