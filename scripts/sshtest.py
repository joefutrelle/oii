import sys
import paramiko
import os
from binascii import hexlify

ssh = paramiko.SSHClient()

server, username, key = sys.argv[1:]

ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(server, username=username, key_filename=key)

sftp = paramiko.SFTPClient.from_transport(ssh.get_transport())

path='this_is_an_sftp_test'
temp='tempywempy201305_%s' % hexlify(os.urandom(32))
sftp.put(path,temp)
try:
    sftp.rename(temp,path)
except:
    print 'rename failed, removing first'
    try:
        sftp.remove(path)
        sftp.rename(temp,path)
    except:
        print 'attempt to delete existing failed, removing temp'
        try:
            sftp.remove(temp)
        except:
            print 'even removing temp failed'

for f in sftp.listdir():
    print f

ssh.close()
