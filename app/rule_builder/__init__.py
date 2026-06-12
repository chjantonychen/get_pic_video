def generalize_selectors(selectors: list[str]) -> str:
    if not selectors:
        return ""
    if len(selectors) == 1:
        return selectors[0]
    parts = [s.split(" > ") for s in selectors]
    common = []
    for segs in zip(*parts):
        if len(set(segs)) == 1:
            common.append(segs[0])
        else:
            break
    return " > ".join(common) if common else selectors[0]
