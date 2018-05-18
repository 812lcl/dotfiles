#!/bin/sh

# need to set the MEDIA_KEYS_PATH variable in the ~/.bashrc file
if [ $MEDIA_KEYS_PATH ]
then
    (cd $MEDIA_KEYS_PATH ; ./get_window_id.sh)
else
    echo "MEDIA_KEYS_PATH variable in ~/.bashrc file not set"
    exit 1
fi

if [ $MUSIC_CONTROL_PATH ]
then
    music_list="$MUSIC_CONTROL_PATH/music_list"
else
    music_list=music_list
fi

if [ $1 ]
then
	choice=$(grep -i $1 $music_list)
	echo "###########################################"
	echo "###########################################"
	tmp_file=`mktemp`
	for i in $choice
	do
		echo $i
		echo $i >> $tmp_file
	done
	echo "###########################################"
	echo "###########################################"
	mplayer -playlist $tmp_file
	rm -f $tmp_file
else
	echo "###########################################"
	echo "###########################################"
	echo "Play the songs in the $music_list"
	echo "###########################################"
	echo "###########################################"
	mplayer -shuffle -playlist $music_list
fi

(cd $MEDIA_KEYS_PATH ; ./rm_file_window_id.sh)
