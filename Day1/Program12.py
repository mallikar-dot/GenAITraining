a = (input("Enter an Character: "))
if a.isalpha():
    print(a, "is an Alphabet")
elif a.isdigit():
    print(a, "is a Digit")
else:
    print(a, "is a Special Character")