import asyncio

from metagpt.roles.di.data_interpreter import DataInterpreter


async def main(requirement: str):
    role = DataInterpreter()
    await role.run(requirement)


if __name__ == "__main__":
    data_path = "examples/data/math_test/algebra/1.json"
    save_path = "../output/results.csv"
    ckpt_path = "../output/finetuned_checkpoint.pth"
    # train_path = f"{data_path}/split_train.csv"
    # eval_path = f"{data_path}/split_eval.csv"
    requirement = f"""You are required to solve a sentiment classification task using the gpt2-small model.
    
The dataset is `EleutherAI/twitter-sentiment` from huggingface. Please dowanload and preprocess the data, and then fine-tune the model on the training set.

The model should be evaluated on the evaluation set and the results should be saved in a csv file at {save_path}, and the checkpoint should be saved in {ckpt_path}.

Finally, also generate a comprehensive report on the model's performance.

If there're missing packages, please install them.
"""
    asyncio.run(main(requirement))
