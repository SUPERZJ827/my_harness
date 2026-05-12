# Prompt for taking on "eda" tasks
EDA_PROMPT = """
The current task is about exploratory data analysis, please note the following:
- Distinguish column types with `select_dtypes` for tailored analysis and visualization, such as correlation.
- Remember to `import numpy as np` before using Numpy functions.
"""

# Prompt for taking on "data_preprocess" tasks
DATA_PREPROCESS_PROMPT = """
The current task is about data preprocessing, please note the following:
- Monitor data types per column, applying appropriate methods.
- Ensure operations are on existing dataset columns.
- Avoid writing processed data to files.
- Avoid any change to label column, such as standardization, etc.
- Prefer alternatives to one-hot encoding for categorical data.
- Only encode or scale necessary columns to allow for potential feature-specific engineering tasks (like time_extract, binning, extraction, etc.) later.
- Each step do data preprocessing to train, must do same for test separately at the same time.
- Always copy the DataFrame before processing it and use the copy to process.
"""

# Prompt for taking on "feature_engineering" tasks
FEATURE_ENGINEERING_PROMPT = """
The current task is about feature engineering. when performing it, please adhere to the following principles:
- Generate as diverse features as possible to improve the model's performance step-by-step. 
- Use available feature engineering tools if they are potential impactful.
- Avoid creating redundant or excessively numerous features in one step.
- Exclude ID columns from feature generation and remove them.
- Each feature engineering operation performed on the train set must also applies to the test separately at the same time.
- Avoid using the label column to create features, except for cat encoding.
- Use the data from previous task result if exist, do not mock or reload data yourself.
- Always copy the DataFrame before processing it and use the copy to process.
"""

# Prompt for taking on "model_train" tasks
MODEL_TRAIN_PROMPT = """
The current task is about training a model, please ensure high performance:
- Keep in mind that your user prioritizes results and is highly focused on model performance. So, when needed, feel free to use models of any complexity to improve effectiveness, such as XGBoost, CatBoost, etc.
- If non-numeric columns exist, perform label encode together with all steps.
- Use the data from previous task result directly, do not mock or reload data yourself.
- Set suitable hyperparameters for the model, make metrics as high as possible.
"""

# Prompt for taking on "model_evaluate" tasks
MODEL_EVALUATE_PROMPT = """
The current task is about evaluating a model, please note the following:
- Ensure that the evaluated data is same processed as the training data. If not, remember use object in 'Done Tasks' to transform the data.
- Use trained model from previous task result directly, do not mock or reload model yourself.
"""

# Prompt for taking on "image2webpage" tasks
IMAGE2WEBPAGE_PROMPT = """
The current task is about converting image into webpage code. please note the following:
- Single-Step Code Generation: Execute the entire code generation process in a single step, encompassing HTML, CSS, and JavaScript. Avoid fragmenting the code generation into multiple separate steps to maintain consistency and simplify the development workflow.
- Save webpages: Be sure to use the save method provided.
"""

# SciAgentBench prompts
DATA_PREPROCESS_CLEANING_PROMPT = """
The current task is focused on data cleaning and preprocessing. Please adhere to the following:
- Detect and address missing values, outliers, and duplicate entries.
- Standardize data formats, ensuring uniformity in dates, times, and other relevant fields.
- Apply appropriate methods for handling outliers and abnormal data.
- Ensure that operations are performed on a copy of the DataFrame to preserve the original dataset.
"""

DATA_EXPLORATION_PROMPT = """
The current task involves exploring and understanding data. Please perform the following:
- Calculate and interpret basic statistical indicators, such as mean, median, and standard deviation.
- Generate charts to visualize data distributions, including histograms and box plots.
- Assess correlations between variables and create correlation matrices or heat maps.
"""

DATA_VISUALIZATION_PROMPT = """
The current task is centered on data visualization. Please ensure the following:
- Distinguish column types using `select_dtypes` for tailored visualizations and analyses.
- Import necessary libraries, such as `numpy`, for numerical operations.
- Create visualizations including bar charts, line charts, scatter plots, and interactive charts.
- Develop geographic visualizations, such as heat maps, to display geographical data distribution.
- Utilize techniques like clustering and PCA for data reduction and visualization.
"""

PREDICTIVE_MODELING_PROMPT = """
The current task is about predictive modeling. Please adhere to the following:
- Choose suitable machine learning algorithms based on the problem type, such as regression, decision trees, or random forests.
- Implement feature engineering techniques including selection, transformation, and combination.
- Split the dataset into training and test sets, train the model, and evaluate its performance.
- Use appropriate evaluation metrics for different types of predictive problems, such as classification or regression.
"""

DATA_MINING_PROMPT = """
The current task involves data mining. Please follow these guidelines:
- Apply methods such as association rule mining and frequent item set mining to uncover interesting patterns.
- Utilize text mining techniques to extract keywords, topics, and other relevant information from text data.
- Perform cluster analysis and classification to identify underlying patterns and structures within the data.
"""

PATTERN_RECOGNITION_PROMPT = """
The current task is related to pattern recognition. Please address tasks such as:
- Image recognition to identify and classify objects within images.
- Text clustering to group similar textual data.
- Anomaly detection in time series data to identify unusual patterns or deviations.
"""

INTERPRETABILITY_REPORT_PROMPT = """
The current task is focused on model interpretability and report generation. Please ensure the following:
- Provide detailed explanations of model results, including feature importance and model parameters.
- Generate comprehensive and understandable reports that summarize and present analysis results effectively.
"""