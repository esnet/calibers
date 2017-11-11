#!/bin/bash


# create junk files, start servers
for i in 111 112 113 114 115 116
do
	echo "*******First contact to $i"
    ssh rootnh@192.168.120.$i << EOF
ifconfig eth1 mtu 9000
tc qdisc del dev eth1 root
tc qdisc show dev eth1
globus-gridftp-server -S -p 8$i -data-interface 192.168.200.$i -aa -anonymous-user 'nhanford' -home-dir / -Z ~/$i.log -log-level all
ps aux | grep gridftp
EOF
done
globus-gridftp-server -S -p 8$i -data-interface 192.168.200.$i -aa -anonymous-user 'nhanford' -home-dir / -Z ~/$i.log -log-level all
# AMST
ssh rootnh@192.168.120.111 << EOF
if [ ! -e "/storage/zero.img" ]
then
	dd if=/dev/zero of=/storage/zero.img bs=1M count=2145
	chmod +r /storage/zero.img
fi
ls /storage | grep img
EOF
# CERN
ssh rootnh@192.168.120.112 << EOF
if [ ! -e "/storage/zero.img" ]
then
	dd if=/dev/zero of=/storage/zero.img bs=1M count=1609
	chmod +r /storage/zero.img
fi
ls /storage | grep img
EOF
# AOFA
ssh rootnh@192.168.120.114 << EOF
if [ ! -e "/storage/zero.img" ]
then
	dd if=/dev/zero of=/storage/zero.img bs=1M count=429
	chmod +r /storage/zero.img
fi
ls /storage | grep img
EOF
# ATLA
ssh rootnh@192.168.120.113 << EOF
if [ ! -e "/storage/zero.img" ]
then
	dd if=/dev/zero of=/storage/zero.img bs=1M count=178
	chmod +r /storage/zero.img
fi
ls /storage | grep img
EOF
# WASH
ssh rootnh@192.168.120.115 << EOF
if [ ! -e "/storage/zero.img" ]
then
	dd if=/dev/zero of=/storage/zero.img bs=1M count=85
	chmod +r /storage/zero.img
fi
ls /storage | grep img
EOF
# DENV
ssh rootnh@192.168.120.116 << EOF
if [ ! -e "/storage/zero.img" ]
then
	dd if=/dev/zero of=/storage/zero.img bs=1M count=57
	chmod +r /storage/zero.img
fi
ls /storage | grep img
EOF


echo "*******Contacting receiving server"

scp alias-file xfer-file rootnh@192.168.120.118:~

ssh rootnh@192.168.120.118 << EOF
ifconfig eth1 mtu 9000
ps aux | grep gridftp
EOF
#globus-gridftp-server -S -p 8118 -data-interface 192.168.200.118 -aa -anonymous-user 'nhanford' -home-dir / -Z ~/118.log -log-level all

echo "*******Initiatiing Transfer"
time globus-url-copy -cc 6 -p 1 -af alias-file -f xfer-file

d=$(date +%F-%H-%M)
mkdir ~/$d

# move logs, stop servers
for i in 111 112 113 114 115 116 118
do
	echo "********Third contact to $i"
	scp rootnh@192.168.120.$i:~/$i.log ~/$d
	ssh rootnh@192.168.120.$i << EOF
mkdir ~/$d
mv *.log ~/$d
ps aux | grep gridftp
EOF
done
#pkill gridftp

cp results.py ~/$d
cd ~/$d
./results.py
