shopping_list = []

while True:
    print ("\n========= SHOPPING MENU =========")
    print ("1. Add Item")
    print ("2. Remove Item")
    print ("3. View Shopping List")
    print ("4. Exit")

    choice = int(input("Enter your choice: "))

    if choice == 1:
        item = input("Enter the item to add: ")
        shopping_list.append(item)
        print(f"{item} has been added to the shopping list.")

    elif choice == 2:
        item = input("Enter the item to remove: ")
        if item in shopping_list:
            shopping_list.remove(item)
            print(f"{item} has been removed from the shopping list.")
        else:
            print(f"{item} is not in the shopping list.")

    elif choice == 3:
        print("\n========= SHOPPING LIST =========")
        for i, item in enumerate(shopping_list, start=1):
            print(f"{i}. {item}")

    elif choice == 4:
        print("Exiting the program.")
        break
    else:
        print("Invalid choice. Please try again.")