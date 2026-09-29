principal = float(input("Enter the Principal Amount: "))
rate = float(input("Enter the Rate of Interest: "))
time = float(input("Enter the Time in Years: "))
n = int(input("Enter the compounding frequency: "))
amount = principal * (1 + rate/(100*n)) ** (n*time)
ci = amount - principal
print("Compound Interest:", ci)