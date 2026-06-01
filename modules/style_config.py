from colorsys import rgb_to_hls, hls_to_rgb


TTD_CORPORATE_PALETTE = [
    "#0372E2",  # TTD Blue Sky
    "#ADE3FF",  # Misty
    "#F45213",  # Orange Sunset
    "#FFE4A9",  # Sand
    "#EAD8F2",  # Dawn
    "#C1510F",  # Koa Wood
    "#FFB803",  # Sunshine
    "#CFF7EE",  # Seafoam
    "#00564C",  # Green Pickles
    "#FCDDD0",  # Peach Cloud
    "#541346",  # Purple Rain
]


def _hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#" + "".join(f"{int(max(0, min(1, c)) * 255):02X}" for c in rgb)


def adjust_lightness(hex_color: str, factor: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    h, l, s = rgb_to_hls(r, g, b)
    l = max(0, min(1, l * factor))
    r2, g2, b2 = hls_to_rgb(h, l, s)
    return _rgb_to_hex((r2, g2, b2))


def build_extended_palette(min_size: int) -> list[str]:
    """
    コーポレートパレットをベースに、足りない場合は近いトーンを追加生成する
    """
    base = TTD_CORPORATE_PALETTE.copy()

    if min_size <= len(base):
        return base[:min_size]

    extended = base.copy()

    # 少し暗く / 少し明るく の順で増やす
    tone_factors = [0.82, 1.18, 0.68, 1.32]

    while len(extended) < min_size:
        for factor in tone_factors:
            for color in base:
                candidate = adjust_lightness(color, factor)
                if candidate not in extended:
                    extended.append(candidate)
                    if len(extended) >= min_size:
                        return extended

    return extended[:min_size]