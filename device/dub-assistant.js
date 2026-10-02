autowatch = 1;
inlets = 1;
outlets = 3;

// outlet 0: status string
// outlet 1: 24-value list (sends[8] + prob[8] + dynam[8]) for meters
// outlet 2: row count (int)

var TRACK_COUNT = 8;
var INPUTS = 3;
var OUTPUTS = 24;
var MIN_TRAIN_ROWS = 8;
var WARN_TRAIN_ROWS = 100;
var UNITY_GAIN = 0.85;
var WRITE_EPS = 0.003;
var SMOOTH = 0.28;

var DEFAULT_NAMES = [
    "Drums", "Bass", "Vox", "Keys", "Guitar", "FX", "Perc", "Other"
];
var DEFAULT_HEART = ["Drums", "Bass"];

var state = {
    col: 0.5,
    rhy: 0.5,
    dyn: 0.5,
    heart: 1.0,
    drywet: 0.0,
    sendIndex: 0,
    division: 8,
    names: DEFAULT_NAMES.slice(0),
    heartNames: DEFAULT_HEART.slice(0),
    sends: zeros(TRACK_COUNT),
    prob: fill(TRACK_COUNT, 0.35),
    dynam: fill(TRACK_COUNT, 0.4),
    ready: false,
    trained: false,
    writing: false
};

var dataset = [];
var mlp = null;
var binds = [];
var songApi = null;
var tickTask = null;
var lastBeat = -1;
var faderCurrent = fill(TRACK_COUNT, UNITY_GAIN);
var faderTarget = fill(TRACK_COUNT, UNITY_GAIN);
var sendCurrent = zeros(TRACK_COUNT);
var sendTarget = zeros(TRACK_COUNT);
var snapshotVol = fill(TRACK_COUNT, UNITY_GAIN);
var snapshotSend = zeros(TRACK_COUNT);
var lastWrittenVol = fill(TRACK_COUNT, -1);
var lastWrittenSend = fill(TRACK_COUNT, -1);
var lastStatus = "";

function zeros(n) {
    var a = [];
    for (var i = 0; i < n; i++) a[i] = 0;
    return a;
}

function fill(n, v) {
    var a = [];
    for (var i = 0; i < n; i++) a[i] = v;
    return a;
}

function clamp(v, lo, hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

function unwrap(v) {
    if (v === null || v === undefined) return v;
    if (typeof v === "object" && v.length !== undefined && typeof v !== "string") {
        return v.length ? v[0] : v;
    }
    return v;
}

function status(msg) {
    lastStatus = String(msg);
    outlet(0, lastStatus);
    post("dub-assistant: " + lastStatus + "\n");
}

function emitRows() {
    outlet(2, dataset.length);
}

function emitVector() {
    var out = [];
    var i;
    for (i = 0; i < TRACK_COUNT; i++) out.push(state.sends[i]);
    for (i = 0; i < TRACK_COUNT; i++) out.push(state.prob[i]);
    for (i = 0; i < TRACK_COUNT; i++) out.push(state.dynam[i]);
    outlet(1, out);
}

// --- MLP (3 -> 8 tanh -> 24 sigmoid) ---------------------------------------

function randn() {
    var u = 0;
    var v = 0;
    while (u === 0) u = Math.random();
    while (v === 0) v = Math.random();
    return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
}

function newMlp() {
    var hidden = 8;
    var i;
    var j;
    var w1 = [];
    var b1 = [];
    var w2 = [];
    var b2 = [];
    var scale1 = Math.sqrt(2 / (INPUTS + hidden));
    var scale2 = Math.sqrt(2 / (hidden + OUTPUTS));
    for (i = 0; i < hidden; i++) {
        w1[i] = [];
        for (j = 0; j < INPUTS; j++) w1[i][j] = randn() * scale1;
        b1[i] = 0;
    }
    for (i = 0; i < OUTPUTS; i++) {
        w2[i] = [];
        for (j = 0; j < hidden; j++) w2[i][j] = randn() * scale2;
        b2[i] = 0;
    }
    return { hidden: hidden, w1: w1, b1: b1, w2: w2, b2: b2 };
}

function tanhAct(x) {
    if (x > 8) return 1;
    if (x < -8) return -1;
    var e = Math.exp(2 * x);
    return (e - 1) / (e + 1);
}

function sigmoid(x) {
    if (x > 12) return 1;
    if (x < -12) return 0;
    return 1 / (1 + Math.exp(-x));
}

function mlpForward(net, x) {
    var h = [];
    var y = [];
    var i;
    var j;
    var s;
    for (i = 0; i < net.hidden; i++) {
        s = net.b1[i];
        for (j = 0; j < INPUTS; j++) s += net.w1[i][j] * x[j];
        h[i] = tanhAct(s);
    }
    for (i = 0; i < OUTPUTS; i++) {
        s = net.b2[i];
        for (j = 0; j < net.hidden; j++) s += net.w2[i][j] * h[j];
        y[i] = sigmoid(s);
    }
    return { h: h, y: y };
}

function mlpTrain(net, rows, epochs, lr) {
    var e;
    var r;
    var i;
    var j;
    var k;
    var fwd;
    var err;
    var dy;
    var dh;
    var row;
    var x;
    var t;
    var h;
    var y;
    for (e = 0; e < epochs; e++) {
        for (r = 0; r < rows.length; r++) {
            row = rows[r];
            x = row.inn;
            t = row.out;
            fwd = mlpForward(net, x);
            h = fwd.h;
            y = fwd.y;
            dy = [];
            for (i = 0; i < OUTPUTS; i++) {
                err = y[i] - t[i];
                dy[i] = err * y[i] * (1 - y[i]);
            }
            dh = [];
            for (j = 0; j < net.hidden; j++) {
                s = 0;
                for (i = 0; i < OUTPUTS; i++) s += net.w2[i][j] * dy[i];
                dh[j] = s * (1 - h[j] * h[j]);
            }
            for (i = 0; i < OUTPUTS; i++) {
                for (j = 0; j < net.hidden; j++) {
                    net.w2[i][j] -= lr * dy[i] * h[j];
                }
                net.b2[i] -= lr * dy[i];
            }
            for (j = 0; j < net.hidden; j++) {
                for (k = 0; k < INPUTS; k++) {
                    net.w1[j][k] -= lr * dh[j] * x[k];
                }
                net.b1[j] -= lr * dh[j];
            }
        }
        if (e === 200) lr *= 0.6;
        if (e === 400) lr *= 0.5;
    }
}

function fallbackMap(col, rhy, dyn) {
    var out = [];
    var i;
    for (i = 0; i < TRACK_COUNT; i++) {
        out[i] = clamp(col * (0.45 + 0.07 * (i % 4)), 0, 1);
    }
    for (i = 0; i < TRACK_COUNT; i++) {
        out[8 + i] = clamp(rhy * (i < 2 ? 0.35 : 0.85), 0, 1);
    }
    for (i = 0; i < TRACK_COUNT; i++) {
        out[16 + i] = clamp(dyn, 0, 1);
    }
    return out;
}

function applyOutputs(vec) {
    var i;
    for (i = 0; i < TRACK_COUNT; i++) {
        state.sends[i] = clamp(vec[i], 0, 1);
        state.prob[i] = clamp(vec[8 + i], 0, 1);
        state.dynam[i] = clamp(vec[16 + i], 0, 1);
        sendTarget[i] = state.sends[i];
    }
    emitVector();
}

function predictFromKnobs() {
    var x = [state.col, state.rhy, state.dyn];
    var vec;
    if (state.trained && mlp) {
        vec = mlpForward(mlp, x).y;
    } else {
        vec = fallbackMap(state.col, state.rhy, state.dyn);
    }
    applyOutputs(vec);
}

// --- Live bind / write ------------------------------------------------------

function isHeart(name) {
    var i;
    var n = String(name).toLowerCase();
    for (i = 0; i < state.heartNames.length; i++) {
        if (String(state.heartNames[i]).toLowerCase() === n) return true;
    }
    return false;
}

function findTrackIndexByName(name) {
    if (!songApi || !songApi.valid) return -1;
    var count = songApi.getcount("tracks");
    var i;
    var t;
    var tn;
    var want = String(name).toLowerCase();
    for (i = 0; i < count; i++) {
        t = new LiveAPI("live_set tracks " + i);
        if (!t || !t.valid) continue;
        tn = String(unwrap(t.get("name"))).toLowerCase();
        if (tn === want) return i;
    }
    return -1;
}

function bindTracks() {
    var i;
    var idx;
    var vol;
    var send;
    var name;
    binds = [];
    if (!songApi) {
        try {
            songApi = new LiveAPI("live_set");
        } catch (e) {
            status("Live API not ready");
            return 0;
        }
    }
    if (!songApi || !songApi.valid) {
        status("Live API not ready");
        return 0;
    }
    var found = 0;
    for (i = 0; i < TRACK_COUNT; i++) {
        name = state.names[i];
        idx = findTrackIndexByName(name);
        if (idx < 0) {
            binds[i] = { name: name, index: -1, vol: null, send: null, heart: isHeart(name) };
            continue;
        }
        vol = new LiveAPI("live_set tracks " + idx + " mixer_device volume");
        send = new LiveAPI(
            "live_set tracks " + idx + " mixer_device sends " + state.sendIndex
        );
        binds[i] = {
            name: name,
            index: idx,
            vol: vol && vol.valid ? vol : null,
            send: send && send.valid ? send : null,
            heart: isHeart(name)
        };
        if (binds[i].vol) found++;
    }
    status("bound " + found + "/" + TRACK_COUNT + " tracks");
    return found;
}

function readParam(api) {
    if (!api || !api.valid) return null;
    var v = unwrap(api.get("value"));
    v = parseFloat(v);
    if (isNaN(v)) return null;
    return v;
}

function writeParam(api, value, lastArr, i) {
    if (!api || !api.valid) return;
    if (Math.abs(value - lastArr[i]) < WRITE_EPS) return;
    try {
        api.set("value", value);
        lastArr[i] = value;
    } catch (e) {
        // ignore a single failed write
    }
}

function captureSnapshot() {
    var i;
    var v;
    var s;
    for (i = 0; i < TRACK_COUNT; i++) {
        if (!binds[i]) continue;
        v = readParam(binds[i].vol);
        s = readParam(binds[i].send);
        if (v !== null) {
            snapshotVol[i] = v;
            faderCurrent[i] = v;
            faderTarget[i] = v;
        }
        if (s !== null) {
            snapshotSend[i] = s;
            sendCurrent[i] = s;
            sendTarget[i] = s;
        }
    }
}

function isPlaying() {
    if (!songApi || !songApi.valid) return false;
    var p = unwrap(songApi.get("is_playing"));
    return parseInt(p, 10) === 1;
}

function songBeats() {
    if (!songApi || !songApi.valid) return 0;
    var b = unwrap(songApi.get("current_song_time"));
    b = parseFloat(b);
    return isNaN(b) ? 0 : b;
}

function heartScale(i) {
    if (binds[i] && binds[i].heart) return state.heart;
    return 1;
}

function maybeFireFaders(beats) {
    var step = state.division === 4 ? 1 : 0.5;
    var quantized = Math.floor(beats / step);
    var i;
    var p;
    var d;
    var hs;
    var drop;
    if (quantized === lastBeat) return;
    lastBeat = quantized;
    for (i = 0; i < TRACK_COUNT; i++) {
        hs = heartScale(i);
        p = state.prob[i] * (0.35 + 0.65 * hs);
        d = state.dynam[i] * hs;
        if (Math.random() < p && d > 0.02) {
            // Dub isolation: usually drop the track, occasionally snap back up.
            drop = Math.random() < 0.72;
            if (drop) {
                faderTarget[i] = clamp(snapshotVol[i] * (1 - d), 0.02, 1);
            } else {
                faderTarget[i] = clamp(snapshotVol[i] + (UNITY_GAIN - snapshotVol[i]) * d, 0.02, 1);
            }
        } else {
            faderTarget[i] = snapshotVol[i];
        }
    }
}

function mixDryWet(modelVal, dryVal) {
    return dryVal * (1 - state.drywet) + modelVal * state.drywet;
}

function onTick() {
    var i;
    var volOut;
    var sendOut;
    if (!state.ready) return;
    if (state.drywet <= 0.001) {
        state.writing = false;
        return;
    }
    if (isPlaying()) {
        maybeFireFaders(songBeats());
    }
    for (i = 0; i < TRACK_COUNT; i++) {
        faderCurrent[i] += (faderTarget[i] - faderCurrent[i]) * SMOOTH;
        sendCurrent[i] += (sendTarget[i] - sendCurrent[i]) * SMOOTH;
        volOut = mixDryWet(faderCurrent[i], snapshotVol[i]);
        sendOut = mixDryWet(sendCurrent[i], snapshotSend[i]);
        if (binds[i]) {
            writeParam(binds[i].vol, volOut, lastWrittenVol, i);
            writeParam(binds[i].send, sendOut, lastWrittenSend, i);
        }
    }
    state.writing = true;
}

// --- Max messages -----------------------------------------------------------

function init() {
    try {
        songApi = new LiveAPI("live_set");
    } catch (e) {
        status("wait for Live API");
        return;
    }
    state.ready = true;
    bindTracks();
    captureSnapshot();
    predictFromKnobs();
    if (tickTask) {
        tickTask.cancel();
        tickTask = null;
    }
    tickTask = new Task(onTick, this);
    tickTask.interval = 30;
    tickTask.repeat();
    emitRows();
    status("ready — bind tracks, then Learn this!");
}

function bang() {
    if (!state.ready) init();
    else bindTracks();
}

function col(v) {
    state.col = clamp(parseFloat(v), 0, 1);
    predictFromKnobs();
}

function rhy(v) {
    state.rhy = clamp(parseFloat(v), 0, 1);
    predictFromKnobs();
}

function dyn(v) {
    state.dyn = clamp(parseFloat(v), 0, 1);
    predictFromKnobs();
}

function heart(v) {
    var n = parseFloat(v);
    if (n > 1.5) n = n / 100;
    state.heart = clamp(n, 0, 1);
}

function drywet(v) {
    var n = parseFloat(v);
    if (n > 1.5) n = n / 100;
    n = clamp(n, 0, 1);
    if (state.drywet <= 0.001 && n > 0.001) {
        captureSnapshot();
        predictFromKnobs();
    }
    state.drywet = n;
}

function sendindex(v) {
    state.sendIndex = Math.max(0, parseInt(v, 10) || 0);
    if (state.ready) bindTracks();
}

function division(v) {
    var n = parseInt(v, 10);
    if (n === 4 || n === 1) state.division = 4;
    else state.division = 8;
    lastBeat = -1;
    status("faders on 1/" + state.division);
}

function send(i, v) {
    i = parseInt(i, 10);
    if (i < 0 || i >= TRACK_COUNT) return;
    state.sends[i] = clamp(parseFloat(v), 0, 1);
    sendTarget[i] = state.sends[i];
}

function prob(i, v) {
    i = parseInt(i, 10);
    if (i < 0 || i >= TRACK_COUNT) return;
    state.prob[i] = clamp(parseFloat(v), 0, 1);
}

function dynam(i, v) {
    i = parseInt(i, 10);
    if (i < 0 || i >= TRACK_COUNT) return;
    state.dynam[i] = clamp(parseFloat(v), 0, 1);
}

function names() {
    var a = arrayfromargs(arguments);
    var i;
    for (i = 0; i < TRACK_COUNT && i < a.length; i++) {
        state.names[i] = String(a[i]);
    }
    if (state.ready) bindTracks();
}

function heartnames() {
    var a = arrayfromargs(arguments);
    var i;
    state.heartNames = [];
    for (i = 0; i < a.length; i++) state.heartNames.push(String(a[i]));
    if (state.ready) bindTracks();
}

function currentOutputs() {
    var out = [];
    var i;
    for (i = 0; i < TRACK_COUNT; i++) out.push(state.sends[i]);
    for (i = 0; i < TRACK_COUNT; i++) out.push(state.prob[i]);
    for (i = 0; i < TRACK_COUNT; i++) out.push(state.dynam[i]);
    return out;
}

function learn() {
    var row = {
        inn: [state.col, state.rhy, state.dyn],
        out: currentOutputs()
    };
    dataset.push(row);
    captureSnapshot();
    emitRows();
    state.trained = false;
    var extra = dataset.length < WARN_TRAIN_ROWS
        ? " (paper floor is 100+)"
        : "";
    status("learned row " + dataset.length + extra);
}

function clear() {
    dataset = [];
    mlp = null;
    state.trained = false;
    emitRows();
    status("dataset cleared");
}

function train() {
    if (dataset.length < MIN_TRAIN_ROWS) {
        status("need at least " + MIN_TRAIN_ROWS + " rows (have " + dataset.length + ")");
        return;
    }
    var prev = state.drywet;
    state.drywet = 0;
    status("training " + dataset.length + " rows…");
    mlp = newMlp();
    mlpTrain(mlp, dataset, 550, 0.08);
    state.trained = true;
    state.drywet = prev;
    predictFromKnobs();
    var note = dataset.length < WARN_TRAIN_ROWS
        ? " — add rows toward 100 for a stronger map"
        : "";
    status("trained on " + dataset.length + " rows" + note);
}

function bind() {
    bindTracks();
    captureSnapshot();
}

function snapshot() {
    captureSnapshot();
    status("snapshot captured");
}

function tick() {
    onTick();
}

function save(path) {
    if (!path) {
        status("save needs a path");
        return;
    }
    var f = new File(path, "write");
    if (!f.isopen) {
        status("could not write " + path);
        return;
    }
    var header = "col,rhy,dyn";
    var i;
    for (i = 0; i < OUTPUTS; i++) header += ",y" + i;
    f.writeline(header);
    var r;
    var line;
    var j;
    for (r = 0; r < dataset.length; r++) {
        line = dataset[r].inn[0] + "," + dataset[r].inn[1] + "," + dataset[r].inn[2];
        for (j = 0; j < OUTPUTS; j++) line += "," + dataset[r].out[j];
        f.writeline(line);
    }
    f.close();
    status("saved " + dataset.length + " rows");
}

function load(path) {
    if (!path) {
        status("load needs a path");
        return;
    }
    var f = new File(path, "read");
    if (!f.isopen) {
        status("could not read " + path);
        return;
    }
    dataset = [];
    var first = true;
    var line;
    var parts;
    var row;
    var i;
    while (f.position < f.eof) {
        line = f.readline();
        if (!line) continue;
        line = String(line);
        if (first) {
            first = false;
            if (line.indexOf("col") === 0) continue;
        }
        parts = line.split(",");
        if (parts.length < INPUTS + OUTPUTS) continue;
        row = { inn: [], out: [] };
        for (i = 0; i < INPUTS; i++) row.inn[i] = parseFloat(parts[i]);
        for (i = 0; i < OUTPUTS; i++) row.out[i] = parseFloat(parts[INPUTS + i]);
        dataset.push(row);
    }
    f.close();
    state.trained = false;
    mlp = null;
    emitRows();
    status("loaded " + dataset.length + " rows — click Train");
}

function loadbang() {
    // LiveAPI is not legal here. Wait for live.thisdevice.
}

function notifydeleted() {
    if (tickTask) {
        tickTask.cancel();
        tickTask = null;
    }
}
