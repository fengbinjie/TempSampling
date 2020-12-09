import json

class he:
    def one(self, num):
        func = getattr(self,'two')
        func(num)

    def two(self, num):
        print(num+1)
h = he()
he.one(h,1)