"""Incremental JSON framing for hash-bound native mode observations.

Every frame is decoded and yielded. Other top-level values have an explicit
complete-value budget; oversized values fail instead of being truncated.
The surface consumer validates clocks, participants and all transform values.
"""
import json,math


def require(value,message):
    if not value:raise ValueError(message)


def _pairs(pairs):
    result={}
    for key,value in pairs:
        require(key not in result,'Duplicate mode JSON field')
        result[key]=value
    return result


def _float(text):
    value=float(text);require(math.isfinite(value),'Finite mode JSON numbers required');return value


def _constant(value):raise ValueError('Finite mode JSON numbers required: '+value)


class Reader:
    def __init__(self,stream,*,chunk_chars=65536,maximum_value_chars=64*1024**2):
        require(type(chunk_chars) is int and chunk_chars>0 and type(maximum_value_chars) is int
            and maximum_value_chars>=chunk_chars,'Positive complete JSON value budget required')
        self.stream=stream;self.chunk=chunk_chars;self.maximum=maximum_value_chars
        self.buffer='';self.position=0;self.eof=False
        self.decoder=json.JSONDecoder(object_pairs_hook=_pairs,parse_float=_float,parse_constant=_constant)

    def _fill(self,size=None):
        if self.position:self.buffer=self.buffer[self.position:];self.position=0
        part=self.stream.read(size or self.chunk)
        if not part:self.eof=True
        self.buffer+=part

    def peek(self):
        while True:
            while self.position<len(self.buffer) and self.buffer[self.position] in ' \t\n\r':self.position+=1
            if self.position<len(self.buffer):return self.buffer[self.position]
            if self.eof:return ''
            self._fill()

    def expect(self,text):
        require(self.peek()==text,'Malformed mode JSON delimiter: expected '+repr(text));self.position+=1

    def value(self):
        require(bool(self.peek()),'Truncated mode JSON value')
        growth=self.chunk
        while True:
            try:
                value,end=self.decoder.raw_decode(self.buffer,self.position)
                require(end-self.position<=self.maximum,'Complete mode JSON value exceeds budget')
                if end<len(self.buffer) and self.buffer[end] in ' \t\n\r,}]:':
                    self.position=end;return value
                if end==len(self.buffer) and self.eof:self.position=end;return value
                # A number may end at a buffer boundary before its remaining
                # digits/exponent arrive. Confirm its delimiter before returning.
                if self.eof:raise ValueError('Malformed mode JSON value suffix')
            except json.JSONDecodeError as exc:
                if self.eof:raise ValueError('Truncated or malformed mode JSON value') from exc
            require(len(self.buffer)-self.position<=self.maximum,'Complete mode JSON value exceeds budget')
            self._fill(growth);growth=min(growth*2,1024**2)


def records(path,*,chunk_chars=65536,maximum_value_chars=64*1024**2):
    """Yield ('field', key, value), ('frame', index, value), and frame_count."""
    with open(path,encoding='utf8') as stream:
        reader=Reader(stream,chunk_chars=chunk_chars,maximum_value_chars=maximum_value_chars)
        reader.expect('{');seen=set()
        if reader.peek()!='}':
            while True:
                key=reader.value();require(type(key) is str and key not in seen,'Distinct string mode JSON keys required')
                seen.add(key);reader.expect(':')
                if key=='frames':
                    reader.expect('[');index=0
                    if reader.peek()!=']':
                        while True:
                            yield 'frame',index,reader.value();index+=1
                            if reader.peek()!=',':break
                            reader.expect(',');require(reader.peek()!=']','Trailing mode frame comma')
                    reader.expect(']');yield 'frame_count',index,None
                else:yield 'field',key,reader.value()
                if reader.peek()!=',':break
                reader.expect(',');require(reader.peek()!='}','Trailing mode object comma')
        reader.expect('}');require(reader.peek()=='','Trailing mode JSON data')
        require('frames' in seen,'Complete mode frame array required')
