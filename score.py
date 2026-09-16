score_dict = {"1":88,"2":66,"3":78,"4":86}
for staff_id,score in score_dict.items():
    if score >= 77:
        print(staff_id + ":" + str(score))