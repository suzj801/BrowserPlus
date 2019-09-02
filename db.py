#-*-coding:utf-8-*-
import os
import sys
import inspect
import json
from peewee import *

def get_db(filepath):
    if os.path.isdir(os.path.realpath(os.path.dirname(filepath))):
        return SqliteDatabase(filepath)
    else:
        return SqliteDatabase(':memory:')

def init_tables(db):
    current_module = sys.modules[__name__]
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj.__name__!='BaseModel':
            obj._meta.database = db
            obj._meta.tablename = obj.__name__.lower()
            obj.create_table(safe=True)

def printTable(myDict, colList=None):
   """ Pretty print a list of dictionaries (myDict) as a dynamically sized table.
   If column names (colList) aren't specified, they will show in random order.
   Author: Thierry Husson - Use it as you want but don't blame me.
   """
   if not colList: colList = list(myDict[0].keys() if myDict else [])
   myList = [colList] # 1st row = header
   for item in myDict: myList.append([str(item[col] or '') for col in colList])
   colSize = [max(map(len,col)) for col in zip(*myList)]
   formatStr = ' | '.join(["{{:<{}}}".format(i) for i in colSize])
   myList.insert(1, ['-' * i for i in colSize]) # Seperating line
   for item in myList: print(formatStr.format(*item))

def dump_table_dates():
    current_module = sys.modules[__name__]
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj.__name__!='BaseModel':
            print('{:-^100s}'.format('Table: ' + obj.__name__))
            printTable(obj.select().dicts())

class BaseModel(Model):
    def to_dict(self):
        return self.__data__

class Configration(BaseModel):
    name = TextField(primary_key=True)
    value = TextField()

    class Meta:
        index = ((('name',), True),)

def set_config(name, value):
    conf = Configration.get_or_none(name=name)
    if conf:
        conf.value = value
        conf.save()
    else:
        conf = Configration.create(name=name, value=value)
    return conf

def get_config(name):
    conf = Configration.get_or_none(name=name)
    return conf.value if conf else None

class Cookie(BaseModel):
    url = TextField()
    key = TextField()
    value = TextField()

    class Meta:
        indexes = ((('url', 'key'), True),)

def parse_url(method, *args, **kargs):
    def wrapper(*args, **kargs):
        if args:
            if '?' in args[0]:
                args = [args[0][:args[0].index('?')]] + [_arg for _arg in args[1:]]
        elif 'url' in kargs:
            if '?' in kargs['url']:
                kargs['url'] = kargs['url'][:kargs['url'].index('?')]
        return method(*args, **kargs)
    return wrapper

@parse_url
def add_cookie(url, key, value):
    cookie = Cookie.get_or_none(url=url, key=key)
    if cookie:
        cookie.value = value
        cookie.save()
    else:
        cookie = Cookie.create(url=url, key=key, value=value)
    return cookie

@parse_url
def remove_cookie(url, key):
    Cookie.delete().where(Cookie.url==url, Cookie.key==key).execute()

@parse_url
def clear_cookie(url):
    Cookie.delete().where(Cookie.url==url).execute()

@parse_url
def get_cookie(url, key):
    cookie = Cookie.get_or_none(url=url, key=key)
    if cookie:
        return cookie.to_dict()
    else:
        return {}

@parse_url
def list_cookie(url):
    '''仅原样数据返回'''
    return [row for row in Cookie.select().where(Cookie.url==url).dicts()]

@parse_url
def list_cookie2(url):
    '''组合成requests.utils.cookiejar_from_dict需要的数据类型'''
    _cookie_dict = {}
    for row in Cookie.select().where(Cookie.url==url):
        _cookie_dict[row.key] = row.value
    return _cookie_dict

if __name__ == '__main__':
    db = get_db('database')
    init_tables(db)
    dump_table_dates()