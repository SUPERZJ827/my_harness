from src.schemas.schemas import Metric, Evaluator
from src.schemas.dag import LineairzedDAG, Node
from src.evaluator.cr_evaluator import CREvaluator
import asyncio
from src.utils import load_yaml, list_to_dict_by_task


metric = Metric()
evaluator = Evaluator()
config = load_yaml("tests/testcases/example.yaml")
task_to_gt = list_to_dict_by_task(config['TMC-list'])


async def main(requirement: str, plan: list):
    lineairzed_dag = LineairzedDAG(requirement, task_to_gt)
    # plan_list, cost_list, error_counter_list = await lineairzed_dag.get_results()
    dag = lineairzed_dag.get_dag(plan)
    # print([node.task_type for node in dag])
    for node in dag:
        node.evaluate_node()
    CR_evaluator = CREvaluator()

    CR = CR_evaluator.evaluate(dag)
    # CR = lineairzed_dag.launch_test()

    # dag[0].evaluate_node()
    print(f"Completion Rate: {CR}")
    return CR

if __name__ == "__main__":
    true = True
    false = False
    plan = [
    {
        "task_id": "1",
        "dependent_task_ids": [],
        "instruction": "Calculate the daily percentage change for each ticker",
        "task_type": "test_int",
        "code": "import pandas as pd\n\n# Example DataFrame as provided in the user requirement\nprices = pd.DataFrame.from_dict({\n    'GOOG': [\n        742.66, 738.40, 738.22, 741.16,\n        739.98, 747.28, 746.22, 741.80,\n        745.33, 741.29, 742.83, 750.50\n    ],\n    'FB': [\n        108.40, 107.92, 109.64, 112.22,\n        109.57, 113.82, 114.03, 112.24,\n        114.68, 112.92, 113.28, 115.40\n    ],\n    'MSFT': [\n        55.40, 54.63, 54.98, 55.88,\n        54.12, 59.16, 58.14, 55.97,\n        61.20, 57.14, 56.62, 59.25\n    ],\n    'AAPL': [\n        106.00, 104.66, 104.87, 105.69,\n        104.22, 110.16, 109.84, 108.86,\n        110.14, 107.66, 108.08, 109.90\n    ]\n})\n\n# Current Task: Calculate the daily percentage change for each ticker\ndef calculate_percentage_change(prices):\n    # Copy the DataFrame to avoid setting on copy warning\n    percentage_change = prices.pct_change()\n    return percentage_change\n\n# Apply the function to the example DataFrame\ndaily_percentage_change = calculate_percentage_change(prices)\n\n# Display the daily percentage change DataFrame\nprint(daily_percentage_change)\n",
        "result": "        GOOG        FB      MSFT      AAPL\n0        NaN       NaN       NaN       NaN\n1  -0.005736 -0.004428 -0.013899 -0.012642\n2  -0.000244  0.015938  0.006407  0.002006\n3   0.003983  0.023532  0.016370  0.007819\n4  -0.001592 -0.023614 -0.031496 -0.013909\n5   0.009865  0.038788  0.093126  0.056995\n6  -0.001418  0.001845 -0.017241 -0.002905\n7  -0.005923 -0.015698 -0.037324 -0.008922\n8   0.004759  0.021739  0.093443  0.011758\n9  -0.005420 -0.015347 -0.066340 -0.022517\n10  0.002077  0.003188 -0.009100  0.003901\n11  0.010325  0.018715  0.046450  0.016839\n",
        "is_success": true,
        "is_finished": true
    },
    {
        "task_id": "2",
        "dependent_task_ids": [
            "1"
        ],
        "instruction": "Compute the correlation matrix of the daily percentage changes",
        "task_type": "test_bool",
        "code": "# Current Task: Compute the correlation matrix of the daily percentage changes\n\n# Since we already have the daily_percentage_change DataFrame from the previous task,\n# we can directly compute the correlation matrix.\n\ncorrelation_matrix = daily_percentage_change.corr()\n\n# To find the most highly correlated pair, we need to iterate over the correlation matrix,\n# skipping the diagonal (which represents the correlation of a ticker with itself) and\n# only considering the upper triangle (since the matrix is symmetrical).\n# We'll also exclude the first row and column since they contain NaN values due to the\n# first day having no percentage change.\n\nmax_corr = 0\nmax_pair = ()\n\nfor i in range(1, len(correlation_matrix.columns)):\n    for j in range(i+1, len(correlation_matrix.columns)):\n        if abs(correlation_matrix.iloc[i, j]) > max_corr:\n            max_corr = abs(correlation_matrix.iloc[i, j])\n            max_pair = (correlation_matrix.columns[i], correlation_matrix.columns[j])\n\n# Output the most highly correlated pair\nprint(max_pair)\n",
        "result": "20",
        "is_success": true,
        "is_finished": true
    },
    {
        "task_id": "3",
        "dependent_task_ids": [
            "2"
        ],
        "instruction": "Identify the pair of tickers with the highest positive correlation",
        "task_type": "test_bool",
        "code": "import numpy as np\n\n# Function to find the pair of tickers with the highest positive correlation\ndef most_highly_correlated_pair(df):\n    # Select only the numerical columns for correlation analysis\n    num_df = df.select_dtypes(include=[np.number])\n    \n    # Calculate the daily percentage change\n    daily_pc = num_df.pct_change()\n    \n    # Calculate the correlation matrix\n    corr_matrix = daily_pc.corr()\n    \n    # Initialize maximum correlation and corresponding pair\n    max_corr = 0\n    max_pair = ()\n    \n    # Iterate over the correlation matrix to find the maximum positive correlation\n    for i in range(len(corr_matrix.columns)):\n        for j in range(i+1, len(corr_matrix.columns)):\n            if corr_matrix.iloc[i, j] > max_corr and corr_matrix.iloc[i, j] != 1.0:  # Exclude perfect correlation\n                max_corr = corr_matrix.iloc[i, j]\n                max_pair = (corr_matrix.columns[i], corr_matrix.columns[j])\n    \n    return max_pair\n\n# Use the function to find the most highly correlated pair\nprint(most_highly_correlated_pair(prices))\n",
        "result": "5",
        "is_success": true,
        "is_finished": true
    }
]
    requirement = '''You are given a list of tickers and their daily closing prices for a given period.
    Implement the most_corr function that, when given each ticker's daily closing prices, returns the pair of tickers that are the most highly (linearly) correlated by daily percentage change.
    Starter Code: 
    ```python
    import pandas as pd
    import numpy as np

    def most_corr(prices):
        """
        :param prices: (pandas.DataFrame) A dataframe containing each ticker's 
                    daily closing prices.
        :returns: (container of strings) A container, containing the two tickers that 
                are the most highly (linearly) correlated by daily percentage change.
        """
        return None

    #For example, the code below should print: ('FB', 'MSFT')
    print(most_corr(pd.DataFrame.from_dict({
        'GOOG' : [
            742.66, 738.40, 738.22, 741.16,
            739.98, 747.28, 746.22, 741.80,
            745.33, 741.29, 742.83, 750.50
        ],
        'FB' : [
            108.40, 107.92, 109.64, 112.22,
            109.57, 113.82, 114.03, 112.24,
            114.68, 112.92, 113.28, 115.40
        ],
        'MSFT' : [
            55.40, 54.63, 54.98, 55.88,
            54.12, 59.16, 58.14, 55.97,
            61.20, 57.14, 56.62, 59.25
        ],
        'AAPL' : [
            106.00, 104.66, 104.87, 105.69,
            104.22, 110.16, 109.84, 108.86,
            110.14, 107.66, 108.08, 109.90
        ]
    }))) 
    ```
    '''
    results = asyncio.run(main(requirement, plan))