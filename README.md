# tg-quickjs-poc

**THIS CAN BRICK YOUR TELEGRAM APP. Upon testing it on iOS it was impossible to exit the chat due to a crash loop.**\
***IF SENT IN A GROUP IT WILL BRICK ALL MEMBERS. THE ONLY SOLUTION WILL BE TO DELETE THE WHOLE GROUP OR THE MESSAGE VIA THE BOT API.***

Telegram Desktop renders bot widgets with a QuickJS-ng sandbox that runs inside
the client process. A widget message that arrives in a chat is parsed and
executed as soon as the message is displayed. That is a zero-click surface,
the sender does not need the recipient to click anything, and the page runs as
part of normal chat rendering.

This repo documents a parser bug in that engine and the road from it to code
execution. Only material that works without a debugger is included. Code
execution is not included; it is outlined in `docs/rce-path.md` for safety reasons.

## Main crash tool

`poc/crash/c2560.html` is the crash page. It is a single zero-click widget message, with
no debugger and no click. It works against 7.4.1 and 7.4.2 on
iOS, Android and Linux. The page is plain HTML and JavaScript, and the client
runs it in its own QuickJS sandbox, so the same file applies to every platform
that renders widgets.

## The bug

`__JS_EvalInternal` compiles eval code and builds the closure-variable list by
walking the parent function's vardefs:

```c
scope_idx = fd->scopes[scope_level].first;
while (scope_idx >= 0) {
    vd = &fd->vars[scope_idx];
    ...
    scope_idx = vd->scope_next;
}
```

`scope_next` is read from the vardef array and used as the next index without a
bounds check. A record with a large `scope_next` makes the compiler read the
next vardef from an address far outside the array. The compiler then emits a
closure variable from that out-of-range record.

The page reaches this path during normal compilation: a function with a default
parameter that calls `eval` makes the compiler walk the enclosing scope while
the page is being set up, before any user code runs.

## Zero-click on 7.4.1/2

On these versions the walk reads at `vardefs + 20 * (1 + 65534)`, which is 1,310,700
bytes past the vardef array. The read happens inside the client while the
message renders. Nothing in the page asks for a click, a key press or a
permission.

The out-of-range record is then treated as a vardef, and the compiler writes a
closure variable built from it. If the memory at that address contains a
crafted record, the write lands outside the closure array, which is how the
primitive grows from a read into a write.

`poc/crash/c2560.html` does that without a debugger. It keeps a 65,600-entry
symbol atom array alive, grooms the 64-byte arena class so a live
`ArrayBuffer` follows the closure array, fills the spray with the record in
both phases, and calls the trigger function for each phase. The phase that
lands the record at the read address forges `byteLength` on the neighbour, and
the typed-array view the page builds on that buffer faults. The forged length
was 327744. The same page runs and stays silent on the later build.

## From here to code execution

The outline, with the step that is missing marked:

1. Trigger the out-of-range vardef read from a rendered widget. Done on 7.4.1.
2. Place a controlled record at the read address so the compiler emits closure
   variables with chosen fields. Done on 7.4.1; that is the crash page.
3. Use the resulting write to forge a length on a neighbouring object and get
   an out-of-bounds write, not just a read.
4. Rewrite a neighbouring `JSArrayBuffer.data` pointer and build arbitrary
   read/write.
5. Leak a GOT entry for the libc base and `environ` for the stack.
6. Write a chain into a known heap buffer and overwrite a return address.

`docs/rce-path.md` covers the constraints at each step, including the two
hijack attempts that fail even with arbitrary read/write.

## The later build

The update replaced the client binary in place. In that build the widget script
is compiled as global code, so a top-level indirect `eval` has no parent
function and the walk is not entered. Pages that reach the walk on 7.4.1 run
and return `none` there. `docs/742-status.md` has the details and the pages
that were tried.

## Delivering a page

```sh
python3 tools/send-widget.py --html poc/crash/c2560.html --env-file .env \
    --chat-id <id> --api-root https://api.telegram.org/beta \
    --no-test-env --allow-queries --background-query --yes
python3 tools/supervisor.py --duration 3600
```

`send-widget.py` is a dry run unless `--yes` is passed for safety purposes. The supervisor consumes
`getUpdates` and writes every widget request to its log; run only one instance.

## Layout

```
poc/crash/c2560.html    main crash page
poc/crash/README.md     how the page works and how to deliver it
poc/742/                pages that run zero-click on the later build
docs/741-internals.md   record format, write model, arena layout, addresses
docs/742.md             the later build: what changed, what was tried
docs/rce-path.md        the RCE outline and the hijack problem
tools/send-widget.py    bot sender, dry run unless --yes
tools/supervisor.py     getUpdates consumer, writes the request log
```

## Safety

For educational purposes only. Do not use for bad.
Test only your own client. A page that crashes the renderer can wedge widget
rendering until the client restarts, and a crashing widget left in the chat
will fault again when the chat opens. Delete it through the bot API first.
Use at your own risk.