# From oob read to code execution

The chain below is an outline. The step that is missing is marked.

1. Trigger the out-of-range vardef read from a widget that renders on its own.
   This happens on 7.4.1 as part of compiling the page.
2. Put a controlled record at the address the walk reads. The record has a
   free 32-bit atom, a free 16-bit scope index and a small set of flag bits, so
   the closure variable it produces can carry chosen values. Making the read
   address land on controlled memory is the open step for 7.4.1 and the reason
   the repo has no complete write primitive.
3. Use the resulting write to forge a length on a neighbouring object. The
   compiler writes 8 bytes per accepted record, starting past the end of the
   closure array. For an `ArrayBuffer` neighbour the second write lands on
   `byte_length`.
4. Build a typed array on the forged buffer to get an out-of-bounds write, then
   rewrite a neighbouring buffer's `data` pointer and turn that into arbitrary
   read and write.
5. Leak a GOT entry for the libc base and `environ` for the stack.
6. Write a chain into a known heap buffer and overwrite a return address.

## Constraints found

These came from work on a local debug build of the same source, not from the
zero-click path, but they bound what a finished chain has to solve.

The closure-var value written per record is
`{ flags, pad, var_idx = (u16)scope_next, var_name = atom }`. The atom and the
scope index can be chosen; the low byte is the flags byte. A pointer written
this way therefore has a constrained low byte, which rules out arbitrary
addresses for the first write.

With arbitrary read/write on the debug build, three hijack attempts failed:

- Overwriting the `free` GOT entry. libc `free` is called through the PLT for
  large arena blocks, but it receives the arena block header, not the JS buffer
  pointer, so `system` would get allocator metadata.
- Overwriting the `memcpy` and `memmove` GOT entries. Both are inlined at their
  call sites, so those slots are not consulted.
- Reaching `JSRuntime.mf.js_free`. The runtime was not locatable from heap data
  alone: the GC list ended at the second node, the slab header held a null
  pointer, and the longest run of code pointers in the scanned window was two.

A finished chain needs a call site whose first argument is attacker-controlled,
or a stack address so that a ROP chain can replace the argument problem
entirely.

## Options with a realistic chance

1. Arena free-list redirect. `arena_get_block` does not check the index and
   `free_next` is a 16-bit block index. The writable value is limited by the
   flags byte, but a structure that writes a free low byte would make the
   redirect arbitrary.
2. Forged `JSFunctionBytecode`. Point a `JSFunction` at a fake bytecode object
   so the interpreter makes the call with JS-chosen arguments.
3. The host bridge. `WidgetHost::onOps` and `SandboxEngine::hostCall` marshal
   strings and arrays between C++ and the sandbox, and run in the client
   process rather than in the JS sandbox. None of the fuzzing covered it, so it
   is the most likely place for a bug that is still present in 7.4.2.
4. Class confusion. The overrun writes at a fixed 8-byte stride, so a neighbour
   whose class id falls under one of those write slots can be retyped.
