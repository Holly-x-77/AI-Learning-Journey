#mood_index=今晚完成的任务*10+买的礼物*20-犯得错误*30
tesk=int(input("今晚完成了多少任务？"))
gift=int(input("买了多少件礼物？"))
mistake=int(input("犯了多少错？"))
mood_index=tesk*10+gift*20-mistake*30
if mood_index>=60:
    print("可以玩游戏！")
else:
    print("不能玩游戏！")