model_list=("o1-mini" "gpt-4o-2024-05-13" "gpt-4-turbo" "gpt-4o-mini" "claude-3-5-sonnet-20240620" "glm-4-flash" \ 
                "deepseek-coder-1.3b-instruct" \ "deepseek-coder-6.7b-instruct" \ "deepseek-coder-33b-instruct" \ "CodeLlama-7b-Instruct-hf" \ "CodeLlama-13b-Instruct-hf" \ "CodeLlama-34b-Instruct-hf" \ 
                "Qwen2.5-Coder-1.5B-Instruct" \ "starcoder2-3b" \ "starcoder2-7b" \ "starcoder2-15b" \ 
                "Meta-Llama-3.1-70B-Instruct" \ 
                "Qwen/Qwen2.5-Coder-7B-Instruct" \ 
                "01-ai/Yi-1.5-9B-Chat-16K" \ "google/gemma-2-9b-it" \ "meta-llama/Meta-Llama-3-8B-Instruct" \ "meta-llama/Meta-Llama-3.1-8B-Instruct" \ "Qwen/Qwen2-1.5B-Instruct" \ "Qwen/Qwen2-7B-Instruct" \ "Qwen/Qwen2.5-7B-Instruct" \ "THUDM/glm-4-9b-chat")
# model_list=("01-ai/Yi-1.5-9B-Chat-16K" "google/gemma-2-9b-it" "meta-llama/Meta-Llama-3-8B-Instruct" "meta-llama/Meta-Llama-3.1-8B-Instruct" "Qwen/Qwen2-1.5B-Instruct" "Qwen/Qwen2-7B-Instruct" "Qwen/Qwen2.5-7B-Instruct" "THUDM/glm-4-9b-chat")
# model-list=()
# cd ..
for model in "${model_list[@]}"; do
    echo "Running tests for model: $model"
    python -m experiments.evaluate --task_id all --model_id $model
    echo "Completed tests for model: $model"
    echo
done
