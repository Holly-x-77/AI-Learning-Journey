with open("./data.txt","r",encoding="utf-8") as f:
    content = f.readlines()
    for item in content:
        print(item)