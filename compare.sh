#!/bin/sh

find ~/ubuntu/linux-firmware -type f|grep -v git|while read f
do
	if ! find ~/proj/linux/linux-firmware -name `basename $f` 2>&1 > /dev/null
	then
		echo $f
	fi
done

