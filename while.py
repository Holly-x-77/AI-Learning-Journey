print("请输入求平均值数字")
user_input = input("输入数字求值需要求值按q：")
total = 0
num = 0
while user_input != "q":
    total+=float(user_input)
    num+=1
    user_input = input("输入数字求值需要求值按q：")
if user_input == "0":
    print("0")
else:
    result = total / num
    print(str(result))