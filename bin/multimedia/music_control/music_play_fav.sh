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
    file_favourite="$MUSIC_CONTROL_PATH/favourite"
    music_list="$MUSIC_CONTROL_PATH/music_list"
else
    file_favourite=favourite
    music_list="music_list"
fi

tmp_file=`mktemp`
for item in `cat $file_favourite`
do
    echo $item
    choice=$(grep -i $item $music_list)
    for i in $choice
    do
        echo $i
        echo $i >> $tmp_file
    done
done
if [ $1 == 'r' ]
then
    mplayer -shuffle -playlist $tmp_file
else
    mplayer -playlist $tmp_file
fi
rm -f $tmp_file


(cd $MEDIA_KEYS_PATH ; ./rm_file_window_id.sh)
