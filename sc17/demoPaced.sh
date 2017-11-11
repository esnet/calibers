#!/bin/bash


# create junk files, start servers
for i in 190 191 192 194 200 201 118
do
	echo "*******First contact to $i"
    ssh rootnh@192.168.120.$i << EOF
pkill gridftp
ps aux | grep gridftp
globus-gridftp-server -S -p 8$i -data-interface 192.168.112.$i -aa -anonymous-user 'nhanford' -home-dir / -Z ~/$i.log -log-level all
ps aux | grep gridftp
ifconfig eth1 mtu 9000
tc qdisc del dev eth1 root
tc qdisc show dev eth1
EOF
done
# AMST
ssh rootnh@192.168.120.190 << EOF
if [ ! -e "/storage/zero.img" ]
then
	dd if=/dev/zero of=/storage/zero.img bs=1M count=2145
	chmod +r /storage/zero.img
fi
ls /storage | grep img
tc qdisc add dev eth1 root fq
tc qdisc change dev eth1 root fq maxrate 171000002bit
tc qdisc show
EOF
# CERN
ssh rootnh@192.168.120.194 << EOF
if [ ! -e "/storage/zero.img" ]
then
	dd if=/dev/zero of=/storage/zero.img bs=1M count=1609
	chmod +r /storage/zero.img
fi
ls /storage | grep img
tc qdisc add dev eth1 root fq
tc qdisc change dev eth1 root fq maxrate 149955555bit
tc qdisc show
EOF
# AOFA
ssh rootnh@192.168.120.191 << EOF
if [ ! -e "/storage/zero.img" ]
then
	dd if=/dev/zero of=/storage/zero.img bs=1M count=429
	chmod +r /storage/zero.img
fi
ls /storage | grep img
tc qdisc add dev eth1 root fq
tc qdisc change dev eth1 root fq maxrate 99777777bit
tc qdisc show
EOF
# ATLA
ssh rootnh@192.168.120.200 << EOF
if [ ! -e "/storage/zero.img" ]
then
	dd if=/dev/zero of=/storage/zero.img bs=1M count=178
	chmod +r /storage/zero.img
fi
ls /storage | grep img
tc qdisc add dev eth1 root fq
tc qdisc change dev eth1 root fq maxrate 49600000bit
tc qdisc show
EOF
# WASH
ssh rootnh@192.168.120.192 << EOF
if [ ! -e "/storage/zero.img" ]
then
	dd if=/dev/zero of=/storage/zero.img bs=1M count=85
	chmod +r /storage/zero.img
fi
ls /storage | grep img
tc qdisc add dev eth1 root fq
tc qdisc change dev eth1 root fq maxrate 29666666bit
tc qdisc show
EOF
# DENV
ssh rootnh@192.168.120.201 << EOF
if [ ! -e "/storage/zero.img" ]
then
	dd if=/dev/zero of=/storage/zero.img bs=1M count=57
	chmod +r /storage/zero.img
fi
ls /storage | grep img
tc qdisc add dev eth1 root fq
tc qdisc change dev eth1 root fq maxrate 19666666bit
tc qdisc show
EOF

echo "*******Initiatiing Transfer"
time globus-url-copy -cc 6 -p 1 -af calibersAliasFile -f xfer-file

d=$(date +%F-%H-%M)
mkdir ~/$d

# move logs, stop servers
for i in 190 191 192 194 200 201 118
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
