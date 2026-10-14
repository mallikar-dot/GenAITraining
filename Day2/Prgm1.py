for i in range(5):
    print("Hello, World!", i)

print("=========================================.")

for i in range(10, 0, -1):
    print("Hello, Python!", i)

print("=========================================.")

for i in range(1,11,2):
    print("Hello, Python!", i)

print("=========================================.")

number = 2;
for i in range(1, 11):
    print(number, 'x', i, '=', number*i)

print("=========================================.")

num = int(input("Enter a number: "))
for i in range(1, 11):
    print(num, 'x', i, '=', num*i)


print("=========================================.")

for i in range(1, 6):
    if i % 2 == 0:
        print(i, "is even")
    else:
        print(i, "is odd")

print("=========================================.")

for i in range(1, 11):
    if i == 6:
        break;
    print(i)
print("=========================================.")

for i in range(1, 11):
    if i == 6:
        continue;
    print(i)

print("=========================================.")

for i in range(1, 11):
    if i == 6:
        pass; #now i will not do anything and will continue to next loop
    else:
        print(i)