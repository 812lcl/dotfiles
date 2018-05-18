#!/bin/sh
if [ $1x != x ]
then
    file_window_id="$1"
else
    file_window_id='file_window_id'
fi
if [ -f $MEDIA_KEYS_PATH/$file_window_id ]
then
    window_id=`cat $MEDIA_KEYS_PATH/$file_window_id`
    xdotool key --window $window_id Return
else
    echo "error: $file_window_id does not exist"
fi
