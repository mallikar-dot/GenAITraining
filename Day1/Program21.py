kannada = float(input("Enter the Kannada Marks: "))
english = float(input("Enter the English Marks: "))
hindi = float(input("Enter the Hindi Marks: "))
total = kannada + english + hindi
percentage = (total / 300) * 100
if percentage >= 90:
    grade = "A"
elif percentage >= 80:
    grade = "B"
else:
    grade = "C"
print("Total Marks:", total)
print("Percentage:", percentage)
print("Grade:", grade)