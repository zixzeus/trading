
def square(x):
    return x * x

def add_five(x):
    return x + 5

# 使用管道运算符链式调用
x= 3
result = x | square | add_five