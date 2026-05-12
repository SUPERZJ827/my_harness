# config list
configs=("CodeLlama-34b-Instruct-hf.yaml")

# data type list
# data_types=("human" "bcb" "csv_excel" "dl")
data_types=("bcb")

# iterate through model list
for config in "${configs[@]}"; do
    echo "Running tests for config: $config"
    
    # iterate through data type list
    for data_type in "${data_types[@]}"; do
        echo "  Running data type: $data_type"
        python -m experiments.run_examples --data_type $data_type --max_run 10 --config $config
    done
    
    echo "Completed tests for config: $config"
    echo
done

echo "All tests completed."
