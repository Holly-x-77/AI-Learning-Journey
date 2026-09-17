#BMI=体重 / (身高**2)
# user_weight = float(input("请输入你的体重"))
# user_height = float(input("请输入你的身高"))
# BMI = user_weight /(user_height**2)
# print(str(BMI))
# if BMI <= 18.5:
#     print("此BMI属于偏瘦")
# elif 18.5 < BMI <= 25:
#     print("此BMI属于正常值")
# elif 30 >= BMI > 25:
#     print("此BMI属于偏胖")
# else:
#     print("严重超重")

def calculate(height, weight):
    BMI = weight / (height **2)
    return BMI
user_weight = float(input("输入你的体重："))
user_height = float(input("输入你的身高："))
calculate(user_height, user_weight)
print(f"你的体重是：{calculate(user_height, user_weight):.2f}")
if calculate(user_height, user_weight) <= 18.5:
    print("此BMI属于偏瘦")
elif 18.5 < calculate(user_height, user_weight) <= 25:
    print("此BMI属于正常值")
elif 30 >= calculate(user_height, user_weight) > 25:
    print("此BMI属于偏胖")
else:
    print("严重超重")
