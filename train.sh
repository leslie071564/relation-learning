#!/bin/sh
NICE="nice -n 19"
cv_dir="$1"

###
train_script=./train.py
print_feature_script=./print_feature_file.py
model_file=$cv_dir/model

cv_train_dir=$cv_dir/train
cv_test_dir=$cv_dir/test
cv_choose_dir=$cv_dir/choose
test_ids=$cv_dir/test_ids.txt
train_ids=$cv_dir/train_ids.txt
ids_cf=$cv_dir/ids_cf.txt

task_file=./print.task
python $print_feature_script --print_test_task --output_dir $cv_choose_dir --ids_file $train_ids --only_gold_align > $task_file
#python $print_feature_script --print_test_task --output_dir $cv_choose_dir --ids_file $train_ids --without_impossible_align > $task_file
echo extracting test feature file:
gxpc js -a work_file=print.task -a cpu_factor=0.75
echo finished.
rm -f $task_file

### initialize
python $train_script --initialize --train_ids $train_ids > $ids_cf
python $print_feature_script --print_train_task --output_dir $cv_train_dir --ids_file $ids_cf > $task_file 
echo extracting train feature file:
gxpc js -a work_file=print.task -a cpu_factor=0.75
echo finished.
rm -f $task_file
echo learn model:
classias-train -tc -a lbfgs.logistic -m $model_file $cv_train_dir/*
echo finished.


### itierations
END=20
for i in $(seq 1 $END)
do
    echo "##### iteration $i #####"
    cat $cv_choose_dir/* | classias-tag -m $model_file > $ids_cf
    echo extracting train feature file:
    python $print_feature_script --print_train_task --output_dir $cv_train_dir --ids_file $ids_cf > $task_file 
    gxpc js -a work_file=print.task -a cpu_factor=0.75
    echo finished.
    echo learn model:
    classias-train -tc -a lbfgs.logistic -m $model_file $cv_train_dir/*
    echo finished.
done

### evaluation
python $print_feature_script --print_test_task --output_dir $cv_test_dir --ids_file $test_ids --without_impossible_align > $task_file
echo extracting test feature file:
gxpc js -a work_file=print.task -a cpu_factor=0.75
echo finished.
rm -f $task_file

result_file=$cv_dir/result.txt
cat $cv_test_dir/* | classias-tag -m $model_file -tk > $result_file
