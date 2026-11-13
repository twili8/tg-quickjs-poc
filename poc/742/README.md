# Later build pages

These pages are sent the same way as any widget: they render when the message
is displayed

`attempt.html` is a heavy groom and the
record pattern with no debugger involvement. It renders and returns `none`,
because the top-level `eval` has no parent function in that build and the walk
is not entered.

`walk_probe_gen.py` puts the eval call inside a function with locals:

```js
function wrap(){ var a = 1, b = 2;
  (0, eval)('globalThis.f = function ([] = eval("1")) { return a + b; };'); }
```

That shape reached the vardef fetch once when it was watched under a
breakpoint, with `r11=5` and no closure variables counted yet. It did not hit
again in later attempts. The page itself is ordinary and safe to send; it prints
`none`.

The obstacle after a hit is the array size. The closure array is allocated for
the number of variables the compiler expects, and the count was zero at the
first hit, so the first writes stay inside the allocation. A longer fake chain,
20 or more records with increasing scope indices, is the next step and needs a
reproducible walk first. This is left as an exercise to the reader !
