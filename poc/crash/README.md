# Crash page

This is a single widget message. Send it and
the client that renders it goes down. Works iOS, Android, Linux.
It did not work on MacOS. You might need to send two or three before it crashes.
Or you could just a single 4096-byte buffer!

It is platform-independent by construction, the page contains no native code;
it is a widget that the receiving client parses and runs in its own QuickJS
sandbox. The crash comes from the engine, not from the host.

## What it does

1. Creates 65,600 symbols and keeps a window of the last 3,000. The atom array
   stays large and slot 65535 stays occupied while the rest of the heap is
   reclaimed.
2. Allocates 1,100 `ArrayBuffer(2560)` objects with views, 3,000
   `ArrayBuffer(64)` objects and 600 more, then drops one slot in the last
   array. That lays out the 64-byte class so a live buffer follows the closure
   array the compiler is about to allocate.
3. Fills the 2560-byte buffers with a 40-byte record pattern in both phases and
   calls `f()` for each phase. `f` has an `eval` default parameter, so
   compiling it makes the compiler walk the vardefs.
4. When a phase lands the record at the walk address, the compiler writes a
   closure variable built from it into the neighbouring `ArrayBuffer` and
   forges `byteLength` to 327744.
5. The page builds a `Uint8Array` on that buffer. The same write chain has
   already overwritten the buffer's `data` and `array_list`, so typed-array
   setup faults and the client goes down.

## Delivery

```sh
python3 tools/send-widget.py --html poc/crash/c2560.html --env-file .env \
    --chat-id <id> --api-root https://api.telegram.org/beta \
    --no-test-env --allow-queries --background-query --yes
```

The page runs when the message is rendered, so the receiving chat must be open
or the message must be laid out for the widget to execute. No click is needed.

The page produces no request call on the non-forged path. Silence in the log
means the phase loop did not land a record; a crash means it did. The loop is
why the page is not deterministic: a run where no phase lands leaves the client
alive and the widget silent.

A client with the message still queued will fault again when the chat is
opened. Delete the message through the bot API before restarting.
