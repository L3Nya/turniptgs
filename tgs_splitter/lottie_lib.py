from copy import deepcopy

DEFAULT_MULTIDIMENSIONAL = {"a": 0, "k": [0, 0, 0]}
DEFAULT_VALUE = {"a": 0, "k": 0}

DEFAULT_TRANSFORM = {
    "a": deepcopy(DEFAULT_MULTIDIMENSIONAL),
    "p": deepcopy(DEFAULT_MULTIDIMENSIONAL),
    "s": {"a": 0, "k": [100, 100, 100]},
    "r": DEFAULT_VALUE.copy(),
    "o": {"a": 0, "k": 100},
    "px": DEFAULT_VALUE.copy(),
    "py": DEFAULT_VALUE.copy(),
    "pz": DEFAULT_VALUE.copy(),
    "sk": DEFAULT_VALUE.copy(),
    "sa": DEFAULT_VALUE.copy(),
}


def multi_dimensional_updater(transform, *change, coefficient=False, equal=False):
    tr = transform["k"]

    if isinstance(tr[0], (int, float)):
        length = min(len(tr), len(change))
        for i in range(length):
            if equal:
                tr[i] = change[i]
            elif coefficient:
                tr[i] *= change[i]
            else:
                tr[i] += change[i]
    else:
        for i, k in enumerate(tr):
            if k.get("s"):
                length = min(len(k["s"]), len(change))
                for j in range(length):
                    if equal:
                        k["s"][j] = change[j]
                    elif coefficient:
                        k["s"][j] *= change[j]
                    else:
                        k["s"][j] += change[j]
            else:
                k["s"] = tr[abs(i - 1)]["s"]
    return transform


def transform(layer, key, *change, coefficient=False, equal=False):
    if not layer["ks"].get(key):
        layer["ks"][key] = deepcopy(DEFAULT_TRANSFORM[key])
    ks = layer["ks"][key]

    return multi_dimensional_updater(ks, *change, coefficient=coefficient, equal=equal)


def scale_layer(layer, kx, ky):
    transform(layer, "s", kx, ky, coefficient=True)
    return layer


def move_layer(layer, dx, dy, equal=False):
    transform(layer, "p", dx, dy, equal=equal)
    return layer


def move_anchor_point(layer, dx, dy):
    transform(layer, "a", dx, dy, equal=True)
    # layer["ks"]["a"]["k"] = [dx, dy, 0]
    return layer


def create_asset(id, layers, op, w=512, h=512):
    asset = {"id": id, "layers": layers, "w": w, "h": h}
    layer = {"ty": 0, "refId": id, "ks": deepcopy(DEFAULT_TRANSFORM), "ip": 0, "op": op}
    return asset, layer
