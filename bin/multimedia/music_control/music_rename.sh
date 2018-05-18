#!/bin/sh
if [ $MUSIC_CONTROL_PATH ]
then
    conf_file="$MUSIC_CONTROL_PATH/path_conf"
else
    conf_file=path_conf
fi

path=`cat $conf_file`
cat $conf_file | 
while read path
do
	find $path -type d -name "*---*" -print |
	while read name
	do
		na=$(echo $name | tr '---' '-')
		if [[ $name != $na ]]; then
			mv "$name" $na
		fi
	done
done

cat $conf_file |
while read path
do
	find $path -type f -name "*---*" -print |
	while read name
	do
		na=$(echo $name | tr '---' '-')
		if [[ $name != $na ]]; then
			mv "$name" $na
		fi
	done
done
