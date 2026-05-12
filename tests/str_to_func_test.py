from src.utils import create_function_from_string

func_str = """
def my_dynamic_function(x, y):
    return x - y
"""

# Create the function and get its name
func_name, my_func = create_function_from_string(func_str)

# Use the dynamically created function
print(f"Function name: {func_name}")
print(my_func(10, 3))  # Output: 7