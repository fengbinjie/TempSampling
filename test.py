import json

class he:
    i = 'a'

    def one(self, num):
        func = getattr(self,'two')
        func(num)

    def two(self, num):
        print(num+1)
class she(he):
    def __
    def __new__(cls, *args, **kwargs):

        print(cls)

print(he.i)
print(she.i)