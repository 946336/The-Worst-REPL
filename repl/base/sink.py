
import io
import os, sys

class Wiretap(io.StringIO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__concerned_parties = []
        self.__silent = False

    @property
    def listeners(self):
        return self.__concerned_parties

    def join(self, party):
        self.__concerned_parties.append(party)

    def leave(self, who):
        self.__concerned_parties = [party for party in
                self.__concerned_parties if party != who]

    def gag(self):
        self.__silent = True

    def ungag(self):
        self.__silent = False

    def write(self, s):
        if not self.__silent:
            for listener in self.__concerned_parties:
                listener.write(s)
                listener.flush()

        super().write(s)
        self.flush()

