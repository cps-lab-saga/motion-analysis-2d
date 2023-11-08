from enum import Enum


class StepsEnum(Enum):
    def next(self):
        members = list(self.__class__)
        index = members.index(self) + 1
        if index >= len(members):
            index = 0
        return members[index]

    def first(self):
        members = list(self.__class__)
        return members[0]

    def is_last(self):
        members = list(self.__class__)
        index = members.index(self)
        if index >= len(members) - 1:
            return True
        else:
            return False
