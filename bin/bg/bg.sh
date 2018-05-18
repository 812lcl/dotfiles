#!/bin/sh
feh --bg-scale ~/Pictures/Mac_book_pro_retina072.jpg
bg_path="$HOME/Pictures"
time1=`date +%s`
while true
do
    time2=`date +%s`
    let "gap=$time2-$time1"
    if [[ $gap = 45 ]]
    then
        fcount=`ls -l $bg_path/*jpg | wc -l`
        random_num=$(($RANDOM%$fcount))
        tmp=0
        for file in $bg_path/*.jpg
        do
            if [ $tmp -lt $random_num ]
            then
                let "tmp=tmp+1"
                continue
            fi
            feh --bg-scale $file
            break
        done
        time1=`date +%s`
    fi
done
