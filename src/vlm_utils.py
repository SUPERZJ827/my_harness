import os
from openai import OpenAI
client = OpenAI(
    base_url="https://api.turboai.one/v1"
)

import base64
def vlm_vis_quality(ground_truth_path, test_path):
    # Open the image file and encode it as a base64 string
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    gt_image = encode_image(ground_truth_path)
    test_image = encode_image(test_path)

    REWADRING_PROMPT = """Above are two figures, which are A and B. The first figure is the ground truth image and the second figure is the predicted image. The total score is 5. Please score B following the criteria below:
    - add 1 point for Data Representation Consistency: Ensure that the underlying data represented by the two charts is identical. This includes the values for all data points and the range of the data. Any variation in the dataset used would make the charts different.
    - add 1 point for Axis Labels and Scales: Verify that both charts have identical axis labels, units, and scales. Any difference in how the axes are labeled or scaled, such as using logarithmic vs. linear scales, can affect the interpretation of the data.
    - add 1 point for Graphical Elements: Check if the visual elements (such as lines, bars, markers, etc.) are represented the same way in both charts. Line thickness, marker styles, and colors should match across charts for them to be considered visually equal.
    - add 1 point for Legend and Annotations: Confirm that any legends, titles, or annotations (e.g., text labels, arrows, or highlights) are the same in both charts. These elements often provide crucial context for interpreting the chart.
    - add 1 point for Chart Dimensions and Layout: Ensure that the dimensions (height and width), aspect ratios, and layout of the charts are identical. Even if the content and representation are similar, a different aspect ratio or spacing between elements can change the chart’s overall appearance and interpretation.

    Please write down the total score for B based on the criteria above, and provide a brief explanation of your reasoning. If you believe that the two figures are not identical, please explain the differences you observed.

    ### Explanation:
    your explanation here

    ### Total Score:
    x/5
    """

    success = False
    max_retry = 5
    retry = 0
    while not success:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {"role": "system", "content": "You are a helpful assistant that responds in Markdown. Help me with my math homework!"},
                {"role": "user", "content": [
                    {"type": "text", "text": "Image A:"},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{gt_image}"}
                    },
                    {"type": "text", "text": "Image B:"},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{test_image}"}
                    },
                    {"type": "text", "text": REWADRING_PROMPT},
                ]}
            ],
            temperature=1.0,
        )
        if "### Total Score:" in response.choices[0].message.content:
            success = True
        else:
            retry += 1
            if retry >= max_retry:
                raise Exception("Failed to get response from the model.")
    return int(response.choices[0].message.content.split("### Total Score:")[1].strip().split("/")[0])