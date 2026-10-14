
def myfunction():
    x = 10;
    print("Hello, World!" , x);
    
myfunction();                                           #this is not belongs to class hence its a function and not a method

class MyClass:                                          #self is a keyword which is used to access the class variables and methods
    x = 5;
    y = 10;
    def myfunction(self):                              #this is a method because it belongs to class
        print("Sum of x and y:" ,(self.x + self.y));   #if this is method then we have to use self keyword to access the class variables
    def myfunction1(self):
        print("Hello, World!" , self.x);
    def myfunction2(self):
        print("Hello, World!" , self.y);
    def myfunction3(self):
        print("Hello, World!" , (self.x + self.y));
    def myfunction4(self):
        print("Hello, World!" , (self.x * (self.y+10)));
        
x1 = MyClass();
print(x1.x);
print(x1.y);
x1.myfunction();
x1.myfunction1();
x1.myfunction2();
x1.myfunction3();
x1.myfunction4();

x2 = MyClass();
x2.x = 20;
x2.y = 30;
print(x2.x);
print(x2.y);
x2.myfunction();
x2.myfunction1();
x2.myfunction2();
x2.myfunction3();

print("---------------------------------------------------");

class student:

   def details(self):
       self.name = "John"
       self.age = 20
   def display(self):
        print("Name:", self.name)
        print("Age:", self.age)

std1 = student()
std1.details()
std1.display()


print("---------------------------------------------------");

class Product:

 def __init__(self, product_id, product_name, price):
        self.product_id = product_id
        self.product_name = product_name
        self.price = price
 def display(self):
        print("Product ID:", self.product_id)
        print("Product Name:", self.product_name)
        print("Price:", self.price)

p1 = Product(101, "Laptop", 50000)
p1.display()
p2 = Product(102, "Mobile", 20000)
p2.display()
p3 = Product(103, "Tablet", 15000)
p3.display()