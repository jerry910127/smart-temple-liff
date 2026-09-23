"""
智慧宮廟 (Smart Temple) LINE 官方圖文選單 (Rich Menu) 2500x1686 圖像生成器 V3
精修版：
1. 解決字型缺失方塊，改用典雅高尚宮廟徽標造型【 誠心請示 】
2. 精緻化如意祥雲四角金紋
3. 頂級宮廟朱砂、赤金、沉香木與古法宣紙質調
4. 強化圖標光影立體感與按鈕層次
"""

import math
import os
from PIL import Image, ImageDraw, ImageFont

WIDTH = 2500
HEIGHT = 1686
COLS = 3
ROWS = 2
CELL_W = WIDTH // COLS   # 833
CELL_H = HEIGHT // ROWS  # 843

ASSETS_DIR = "C:/Users/user/Documents/line_AI2026/web_page/assets"
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")

FONT_SERIF_BOLD = "C:/Windows/Fonts/NotoSerifTC-VF.ttf"
FONT_SANS_BOLD = "C:/Windows/Fonts/msjhbd.ttc"
if not os.path.exists(FONT_SERIF_BOLD):
    FONT_SERIF_BOLD = FONT_SANS_BOLD

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def draw_rounded_rect(draw, box, radius, fill, outline=None, width=1):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=width)

def create_rich_menu():
    # 建立主畫布：深邃沉香老紫檀木底 (襯托六宮格卡片)
    img = Image.new("RGBA", (WIDTH, HEIGHT), color=(26, 18, 14, 255))
    draw = ImageDraw.Draw(img)

    # 頂部宮廟大殿橫樑金線飾條
    draw.rectangle([0, 0, WIDTH, 16], fill=(166, 40, 36, 255))
    draw.rectangle([0, 16, WIDTH, 24], fill=(212, 160, 74, 255))

    # 六宮格卡片設定
    cards_config = [
        {
            "col": 0, "row": 0,
            "badge": "【 誠心請示 】",
            "title": "線上靈籤",
            "subtitle": "搖筒請示・三聖筊定意",
            "cta": "即刻求籤 ›",
            "theme": (166, 40, 36),     # 朱紅
            "gold": (212, 160, 74),
            "asset_icon": "抽籤.png"
        },
        {
            "col": 1, "row": 0,
            "badge": "【 定心安神 】",
            "title": "正念冥想",
            "subtitle": "3D立體捻珠・累積功德",
            "cta": "靜心捻珠 ›",
            "theme": (135, 78, 36),     # 檀木棕
            "gold": (224, 178, 92),
            "asset_icon": None,
            "custom_icon": "beads"
        },
        {
            "col": 2, "row": 0,
            "badge": "【 數位巡禮 】",
            "title": "參拜腳印",
            "subtitle": "四大名廟路線・感應打卡",
            "cta": "巡禮地圖 ›",
            "theme": (38, 76, 96),      # 群青靛藍
            "gold": (212, 160, 74),
            "asset_icon": "腳印收集.png"
        },
        {
            "col": 0, "row": 1,
            "badge": "【 福慧雙修 】",
            "title": "祈安點燈",
            "subtitle": "文昌光明・元辰文教公益",
            "cta": "植福點燈 ›",
            "theme": (175, 95, 30),     # 琥珀金棕
            "gold": (230, 185, 100),
            "asset_icon": None,
            "custom_icon": "lamp"
        },
        {
            "col": 1, "row": 1,
            "badge": "【 數位執事 】",
            "title": "智慧廟祝",
            "subtitle": "生肖歲煞・白米收驚諮詢",
            "cta": "信眾中心 ›",
            "theme": (142, 28, 25),     # 宮廟絳紅
            "gold": (224, 178, 92),
            "asset_icon": "白米_米袋.png"
        },
        {
            "col": 2, "row": 1,
            "badge": "【 敬神儀軌 】",
            "title": "參拜指南",
            "subtitle": "持香順序・拜拜求神小撇步",
            "cta": "儀軌解說 ›",
            "theme": (36, 78, 64),      # 翡翠碧青
            "gold": (212, 160, 74),
            "asset_icon": None,
            "custom_icon": "incense"
        }
    ]

    font_badge = get_font(FONT_SANS_BOLD, 36)
    font_title = get_font(FONT_SERIF_BOLD, 88)
    font_sub = get_font(FONT_SANS_BOLD, 38)
    font_cta = get_font(FONT_SERIF_BOLD, 46)

    margin_x = 24
    margin_y = 22

    for card in cards_config:
        col = card["col"]
        row = card["row"]

        x0 = col * CELL_W + margin_x
        y0 = row * CELL_H + margin_y + (16 if row == 0 else 0)
        x1 = (col + 1) * CELL_W - margin_x
        y1 = (row + 1) * CELL_H - margin_y

        card_w = x1 - x0
        card_h = y1 - y0

        theme = card["theme"]
        gold = card["gold"]

        # 卡片底色（米白宣紙古色）
        draw_rounded_rect(draw, (x0, y0, x1, y1), radius=34, fill=(255, 252, 246, 255), outline=(198, 143, 66, 220), width=4)
        # 內緣細金框
        draw_rounded_rect(draw, (x0 + 10, y0 + 10, x1 - 10, y1 - 10), radius=26, fill=None, outline=(232, 212, 182, 170), width=2)

        # 古典如意四角包角金飾
        c_len = 34
        # 左上
        draw.line([x0 + 16, y0 + 16, x0 + 16 + c_len, y0 + 16], fill=gold, width=3)
        draw.line([x0 + 16, y0 + 16, x0 + 16, y0 + 16 + c_len], fill=gold, width=3)
        # 右上
        draw.line([x1 - 16 - c_len, y0 + 16, x1 - 16, y0 + 16], fill=gold, width=3)
        draw.line([x1 - 16, y0 + 16, x1 - 16, y0 + 16 + c_len], fill=gold, width=3)
        # 左下
        draw.line([x0 + 16, y1 - 16, x0 + 16 + c_len, y1 - 16], fill=gold, width=3)
        draw.line([x0 + 16, y1 - 16 - c_len, x0 + 16, y1 - 16], fill=gold, width=3)
        # 右下
        draw.line([x1 - 16 - c_len, y1 - 16, x1 - 16, y1 - 16], fill=gold, width=3)
        draw.line([x1 - 16, y1 - 16 - c_len, x1 - 16, y1 - 16], fill=gold, width=3)

        # 1. 頂部徽章 (Badge Pill) - 實心沉穩底色配純白字
        badge_text = card["badge"]
        badge_bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
        bw = badge_bbox[2] - badge_bbox[0] + 52
        bh = badge_bbox[3] - badge_bbox[1] + 20
        bx0 = x0 + (card_w - bw) // 2
        by0 = y0 + 38
        draw_rounded_rect(draw, (bx0, by0, bx0 + bw, by0 + bh), radius=bh // 2, fill=theme, outline=gold, width=2)
        draw.text((bx0 + 26, by0 + 8), badge_text, font=font_badge, fill=(255, 250, 240, 255))

        # 2. 中央 Icon 特效圓環區
        icon_cx = x0 + card_w // 2
        icon_cy = y0 + 278
        icon_r = 106

        # 雙層泥金祥光外環
        draw.ellipse([icon_cx - icon_r, icon_cy - icon_r, icon_cx + icon_r, icon_cy + icon_r], fill=(gold[0], gold[1], gold[2], 38), outline=(gold[0], gold[1], gold[2], 160), width=3)
        draw.ellipse([icon_cx - icon_r + 14, icon_cy - icon_r + 14, icon_cx + icon_r - 14, icon_cy + icon_r - 14], fill=(255, 255, 255, 255), outline=(theme[0], theme[1], theme[2], 65), width=2)

        # 載入資產圖示或繪製
        if card["asset_icon"]:
            icon_file = os.path.join(ICONS_DIR, card["asset_icon"])
            if os.path.exists(icon_file):
                try:
                    loaded_icon = Image.open(icon_file).convert("RGBA")
                    target_sz = 146
                    loaded_icon = loaded_icon.resize((target_sz, target_sz), Image.Resampling.LANCZOS)
                    px = icon_cx - target_sz // 2
                    py = icon_cy - target_sz // 2
                    img.paste(loaded_icon, (px, py), loaded_icon)
                except Exception:
                    draw_custom_icon(draw, icon_cx, icon_cy, "generic", theme, gold)
            else:
                draw_custom_icon(draw, icon_cx, icon_cy, card.get("custom_icon", "generic"), theme, gold)
        else:
            draw_custom_icon(draw, icon_cx, icon_cy, card["custom_icon"], theme, gold)

        # 3. 主標題 (Title) - 88pt 大器襯線字
        title_text = card["title"]
        t_box = draw.textbbox((0, 0), title_text, font=font_title)
        tw = t_box[2] - t_box[0]
        draw.text((x0 + (card_w - tw) // 2, y0 + 490), title_text, font=font_title, fill=(28, 20, 16, 255))

        # 4. 副標題 (Subtitle) - 38pt 雅緻棕褐
        sub_text = card["subtitle"]
        s_box = draw.textbbox((0, 0), sub_text, font=font_sub)
        sw = s_box[2] - s_box[0]
        draw.text((x0 + (card_w - sw) // 2, y0 + 600), sub_text, font=font_sub, fill=(112, 82, 58, 255))

        # 5. 底部 CTA 膠囊按鈕
        cta_text = card["cta"]
        cta_box = draw.textbbox((0, 0), cta_text, font=font_cta)
        cw = cta_box[2] - cta_box[0] + 96
        ch = cta_box[3] - cta_box[1] + 32
        cbx0 = x0 + (card_w - cw) // 2
        cby0 = y1 - 114
        draw_rounded_rect(draw, (cbx0, cby0, cbx0 + cw, cby0 + ch), radius=ch // 2, fill=theme, outline=gold, width=3)
        draw.text((cbx0 + 48, cby0 + 15), cta_text, font=font_cta, fill=(255, 250, 240, 255))

    # 輸出目錄
    out_path = os.path.join(ASSETS_DIR, "richmenu_smart_temple.png")
    img.convert("RGB").save(out_path, format="PNG", optimize=True)
    print(f"[OK] Rich Menu generated successfully: {out_path} ({WIDTH}x{HEIGHT})")
    return out_path

def draw_custom_icon(draw, cx, cy, icon_type, theme, gold):
    if icon_type == "beads":
        # 3D 佛珠串
        r = 54
        num_beads = 8
        for i in range(num_beads):
            ang = i * (2 * math.pi / num_beads)
            bx = cx + r * math.cos(ang)
            by = cy + r * math.sin(ang)
            br = 15 if i == 0 else 12
            b_fill = gold if i == 0 else theme
            draw.ellipse([bx - br, by - br, bx + br, by + br], fill=b_fill, outline=(36, 18, 10, 180), width=2)
            draw.ellipse([bx - br//2, by - br//2, bx - br//4, by - br//4], fill=(255, 255, 255, 210))
        draw.line([cx, cy + r + 12, cx, cy + r + 42], fill=(166, 40, 36), width=6)

    elif icon_type == "lamp":
        # 光明蓮花祈福燈
        draw.polygon([(cx - 38, cy + 46), (cx + 38, cy + 46), (cx + 22, cy + 18), (cx - 22, cy + 18)], fill=gold)
        draw.rectangle([cx - 16, cy + 6, cx + 16, cy + 18], fill=theme)
        draw.arc([cx - 40, cy - 6, cx + 40, cy + 34], 0, 180, fill=gold, width=5)
        draw.ellipse([cx - 32, cy - 44, cx + 32, cy + 12], fill=(255, 245, 220, 230), outline=gold, width=3)
        draw.ellipse([cx - 13, cy - 28, cx + 13, cy - 2], fill=(235, 75, 45))
        draw.ellipse([cx - 7, cy - 24, cx + 7, cy - 6], fill=(255, 220, 80))

    elif icon_type == "incense":
        # 三足大鼎銅爐與清香
        draw.ellipse([cx - 42, cy + 5, cx + 42, cy + 38], fill=theme)
        draw.rectangle([cx - 38, cy + 18, cx + 38, cy + 44], fill=theme)
        draw.line([cx - 46, cy + 12, cx + 46, cy + 12], fill=gold, width=5)
        draw.arc([cx - 54, cy + 8, cx - 38, cy + 28], 90, 270, fill=gold, width=4)
        draw.arc([cx + 38, cy + 8, cx + 54, cy + 28], 270, 90, fill=gold, width=4)
        draw.line([cx - 16, cy + 10, cx - 16, cy - 48], fill=gold, width=4)
        draw.line([cx, cy + 10, cx, cy - 60], fill=(166, 40, 36), width=5)
        draw.line([cx + 16, cy + 10, cx + 16, cy - 48], fill=gold, width=4)
        draw.ellipse([cx - 18, cy - 50, cx - 14, cy - 46], fill=(255, 80, 50))
        draw.ellipse([cx - 2, cy - 62, cx + 2, cy - 58], fill=(255, 80, 50))
        draw.ellipse([cx + 14, cy - 50, cx + 18, cy - 46], fill=(255, 80, 50))

    else:
        draw.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=theme, outline=gold, width=3)

if __name__ == "__main__":
    create_rich_menu()
