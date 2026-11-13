# 7.4.1 internals

Offsets are file offsets in the 7.4.1 Linux x86-64 binary, which is 270,333,776
bytes. Add the load base from the first executable mapping.

## The walk

`__JS_EvalInternal` at `0x5f886a0` compiles eval code. When the eval has a
parent function, it walks that function's vardefs to build the closure-variable
list. Each accepted vardef becomes an 8-byte entry in the closure array. The
record fetch is the instruction at `0x5f88f23`.

The walk trusts `scope_next`, which is an index into the vardef array. A large
value sends the next lookup far outside the array, and the record found there
is used as if it were a real vardef.

The minimal page shape is a function with a default parameter that calls
`eval`:

```js
function f([] = eval("1")) {}
f();
```

Compiling that function makes the compiler walk the enclosing scope, and on
7.4.1 the walk reaches `vardefs + 20 * (1 + 65534)`, which is 1,310,700 bytes
past the array. The read is part of normal compilation, so it happens when the
message is rendered and needs nothing from the user.

## Record layout

Each record is 20 bytes.

| offset | field | effect |
|---|---|---|
| +0 | `var_name` (u32) | atom copied into the closure variable |
| +4 | `scope_level` (int) | record is skipped unless it is greater than 0 |
| +8 | `scope_next` (int) | next read is at `vars + 20 * (nvars + scope_next)` |
| +12 | flag bits | `is_local`, `is_arg`, `is_const`, `is_lexical`, `var_kind` |
| +16 | unused | part of the 20-byte stride |

Each accepted record is copied into the closure array as:

```
{ flags, pad, var_idx = (u16)scope_next, var_name = atom }
```

The atom and the low 16 bits of the scope index are free. The flags byte is
built from the flag bits. The pad byte keeps whatever was in the recycled
block.

## Where the writes land

The closure array is allocated for the number of variables the compiler
expects. Writes go to `cv + 8*n` as the count grows. Once the walk produces more
entries than the allocation holds, the writes cross into the next block:

```
entry 7   block header of the neighbour
entry 8   neighbour payload +0    byte_length of an ArrayBuffer, len of a string
entry 9   neighbour payload +8
entry 10  neighbour payload +16   data pointer of an ArrayBuffer
```

A groom of `new ArrayBuffer(64)` objects puts a live `JSArrayBuffer` there. Its
fields are `byte_length` at +0, `max` at +4, `data` at +16 and the self-linked
`array_list` at +24 and +32. That is the layout the write model targets.

## Arena

The fork uses slab arenas with a per-class free list:

```c
#define JS_ARENA_FREE_NIL 0xffff
static inline void *arena_get_block(JSArena *ar, unsigned int idx, unsigned int block_size)
{ return ar->blocks + (size_t)idx * block_size; }
```

`arena_get_block` does not check the index. Classes start at 16 bytes and step
by 8. Pages are 4096 bytes and `sizeof(JSArena)` is 48, so a 56-byte payload is
class 6, which is 64-byte blocks.

`JSString` is 40 bytes in a debug build and 24 in release, because the debug
build enables `ENABLE_DUMPS` and adds a list head. A 15-character string
therefore falls in the 64-byte class only in a debug build; a release build
needs 24 to 31 characters to land there.

Free-list order decides which block ends up next to the closure array. Freeing
every other slot in ascending order leaves the highest block at the head, so
the array lands in the last block of the page and the block after it is
padding. Freeing in descending order puts a low block at the head with a live
neighbour after it.

## Addresses

```
__JS_EvalInternal          0x5f886a0
vardef record fetch        0x5f88f23   (+0x883)
later build, function      0x5faf020
later build, fetch         0x5faf8a3
```

Struct fields confirmed on the local build:

```
JSArrayBuffer  byte_length +0, max +4, data +16, array_list +24/+32,
               opaque +40, free_func +48
JSObject       class_id +0x12, shape +0x18
JSRuntime      mf +0, js_free +0x10, gc_obj_list +0x498, size 1544
JS_CLASS_ARRAY_BUFFER = 20
```
