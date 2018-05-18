#/bin/sh
if [ $MUSIC_CONTROL_PATH ]
then
    conf_file="$MUSIC_CONTROL_PATH/path_conf"
    format_file="$MUSIC_CONTROL_PATH/format_conf"
    music_list="$MUSIC_CONTROL_PATH/music_list"
    >$music_list
else
    conf_file=path_conf
    format_file=format_conf
    music_list=music_list
    >$music_list
fi


cat $conf_file |
while read path
do
	tmp_file=`mktemp`
	find $path > $tmp_file
	cat $format_file |
	while read format
	do
		grep -i "$format" $tmp_file >> $music_list
	done
	rm -f $tmp_file
done
