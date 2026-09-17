dict={"欢":1882888888,"秦":1322999999}
dict["高"]="162999999"
search = input("请输入你想知道的人")
if search in dict:
    print(dict[search])
else:
    print("查找的用户不存在")
    print("当前字典的长度为" + str(len(dict)))