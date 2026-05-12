configs=("gemma-2-9b-it.yaml")
model_ids=('human_24' 'human_22' 'human_131' 'human_10' 'human_141' 'human_7' 'human_21' 'human_0' 'human_2' 'human_19' 'human_132')
for config in "${configs[@]}"; do
    for model_id in "${model_ids[@]}";do
        python -m experiments.run_examples --data_type human --max_run 10  --task_id $model_id --config $config
    done
done
# # config list
# configs=("gemma-2-9b-it.yaml")

# # data type list
# data_types=("bcb" "csv_excel" "dl" "human")

# # iterate through model list
# for config in "${configs[@]}"; do
#     echo "Running tests for config: $config"
    
#     # iterate through data type list
#     for data_type in "${data_types[@]}"; do
#         echo "  Running data type: $data_type"
#         python -m experiments.run_examples --data_type $data_type --max_run 10 --config $config
#     done
    
#     echo "Completed tests for config: $config"
#     echo
# done

# echo "All tests completed."
