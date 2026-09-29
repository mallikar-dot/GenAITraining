basic = float(input("Enter the Basic Salary: "))
if basic <= 10000:
    hra = basic * 20 / 100
    da = basic * 80 / 100
else:
    hra = basic * 25 / 100
    da = basic * 90 / 100
gross = basic + hra + da
print("Basic Salary:", basic)
print("HRA:", hra)
print("DA:", da)
print("Gross Salary:", gross)