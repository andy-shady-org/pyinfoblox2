# coding: utf-8

class ExtraAttr:
    def __init__(self):
        self.data = list()

    def __add__(self, obj):
        for x in self.data:
            if isinstance(obj, AttrObj):
                if x.name == obj.name:
                    self.data.remove(x)
            elif isinstance(obj, str):
                if x.name == obj:
                    self.data.remove(x)

        self.data.append(obj)
        return self

    def __del__(self, obj=None):
        for x in self.data:
            if isinstance(obj, AttrObj):
                if x.name == obj.name:
                    self.data.remove(x)
            elif isinstance(obj, str):
                if x.name == obj:
                    self.data.remove(x)
        return self

    def __sub__(self, obj):
        for x in self.data:
            if isinstance(obj, AttrObj):
                if x.name == obj.name:
                    self.data.remove(x)
            elif isinstance(obj, str):
                if x.name == obj:
                    self.data.remove(x)
        return self

    def to_json(self):
        r = dict()
        for o in self.data:
            r[o.name] = dict(value=o.value)
        return r

    def to_dict(self):
        r = dict()
        for o in self.data:
            r.update({o.name: o.value})
        return r

    def get(self, item):
        for x in self.data:
            if isinstance(item, AttrObj):
                if x.name == item.name:
                    return x.value
            elif isinstance(item, str):
                if x.name == item:
                    return x.value
        raise IndexError('Attribute Not found')

    def __getitem__(self, item):
        for x in self.data:
            if isinstance(item, AttrObj):
                if x.name == item.name:
                    return x
            elif isinstance(item, str):
                if x.name == item:
                    return x
        raise IndexError('Attribute Not found')

    def __contains__(self, item):
        result = list()
        for x in self.data:
            if isinstance(item, AttrObj):
                if x.name == item.name:
                    result.append(item.name)
            elif isinstance(item, str):
                if x.name == item:
                    result.append(item)
        return result.__contains__(item)


class AttrObj:
    def __init__(self, name=None, value=None):
        self.name = name
        self.value = value

    def __repr__(self):
        return self.name


class DHCPMembers:
    def __init__(self):
        self.data = list()

    def add(self, obj):
        self.data.append(obj)
        return self

    def __add__(self, obj):
        self.data.append(obj)
        return self

    def to_json(self):
        r = list()
        for o in self.data:
            r.append(dict(_struct="dhcpmember", name=o.name))
        return r


class DHCPMember:
    def __init__(self, name=None):
        self.name = name
