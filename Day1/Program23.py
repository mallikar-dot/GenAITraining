a = float (input("Enter first number: "))
b = float (input("Enter second number: "))
opr = input("Enter the operator (+, -, *, /): ")
match opr:
    case "+":
        result = a + b
    case "-":
        result = a - b
    case "*":
        result = a * b
    case "/":
        result = a / b
    case _:
        print("Invalid operator")
        result = None

if result is not None:
    print("Result:", result)