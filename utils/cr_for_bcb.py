def evaluate_cr(output_tuple, gt_tuple: tuple):
    # empty
    if output_tuple is None or ((isinstance(output_tuple, tuple) or isinstance(output_tuple, list)) and not output_tuple):
        return 0

    else:
        # single item
        if len(gt_tuple) == 1:
            gt_item = gt_tuple[0]
            output_item = output_tuple[0] if isinstance(output_tuple, tuple) else output_tuple
            if isinstance(output_item, type(gt_item)):
                return 1
            else:
                return 0.5

        # multiple items
        score_list = []
        for i in range(len(gt_tuple)):
            if i >= len(output_tuple):
                score_list.append(0)
                continue
            gt_item = gt_tuple[i]
            output_item = output_tuple[i]
            if isinstance(output_item, type(gt_item)):
                score_list.append(2)
            else:
                score_list.append(1)
        return sum(score_list) / (len(score_list)*2.0)
