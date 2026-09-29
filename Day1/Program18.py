principal = float(input("Enter the Principal Amount: "))
rate = float(input("Enter the Rate of Interest: "))
time = float(input("Enter the Time in Years: "))
si = (principal * rate * time) / 100
amt = principal + si
print("Simple Interest:", si)
print("Total Amount:", amt)