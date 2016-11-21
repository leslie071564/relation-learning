#!/bin/sh
NICE="nice -n 19"
base_dir="$1"
root_dir=/zinnia/huang/EventKnowledge/align_learn/$base_dir

### 
mkdir -p $root_dir
result_dir=$root_dir/result
mkdir -p $result_dir
cp ./setting.ini $root_dir
print_feature_script=./print_feature_file.py

### preprocessing:
rawIDS=./ids.txt
IDS=$root_dir/ids.txt
shuf $rawIDS > $IDS 
total_instance=$(cat $IDS | wc -l )
echo "number of instances: $total_instance"
fold_instance=$(($total_instance / 10 + 1))
split -dl $fold_instance -a 1 $IDS $root_dir/ids_

###
train_script=./train.py
for i in $(seq 0 9)
do
    cv_dir=$root_dir/$i
    test_ids=$cv_dir/test_ids.txt
    train_ids=$cv_dir/train_ids.txt
    mkdir -p $cv_dir 
    cp $root_dir/ids_* $cv_dir
    mv $cv_dir/ids_$i $test_ids
    cat $cv_dir/ids_* > $train_ids
    rm $cv_dir/ids_* -f
    cv_train_dir=$cv_dir/train
    cv_test_dir=$cv_dir/test
    cv_choose_dir=$cv_dir/choose
    mkdir -p $cv_train_dir
    mkdir -p $cv_test_dir
    mkdir -p $cv_choose_dir
    echo "##### in the $i-th fold #####"
    ./train.sh $cv_dir
    cp $cv_dir/result.txt $result_dir/result_$i.txt
done
all_result_file=$result_dir/all_results.txt
cat $result_dir/* > $all_result_file
evaluation_script=./evaluation.py
python $evaluation_script -f $all_result_file
