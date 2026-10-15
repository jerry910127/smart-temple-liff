"""
產生萬春宮 LINE 圖文宣傳海報 Banner (1200x675, 16:9 比例)
可用於 LINE Flex Message Hero 區塊、LINE 官方帳號圖文訊息 (Rich Message) 或社群推廣
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def create_banner():
    width = 1200
    height = 675
    
    # 建立主畫布 (深宮殿朱紅沉香木漸層色)
    base = Image.new("RGBA", (width, height), (32, 12, 10, 255))
    draw = ImageDraw.Draw(base)
    
    # 漸層背景 (由左上朱紅紫檀漸變至右下深黑檀木)
    for y in range(height):
        ratio = y / height
        r = int(72 * (1 - ratio*0.5) + 26 * (ratio*0.5))
        g = int(22 * (1 - ratio*0.6) + 12 * (ratio*0.6))
        b = int(18 * (1 - ratio*0.6) + 10 * (ratio*0.6))
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
    
    # 金色邊框與四角祥紋
    gold = (218, 165, 78, 255)
    gold_dim = (160, 115, 50, 180)
    
    draw.rectangle([20, 20, width - 20, height - 20], outline=gold_dim, width=2)
    draw.rectangle([26, 26, width - 26, height - 26], outline=gold, width=1)
    
    # 頂部裝飾樑飾
    draw.rectangle([26, 26, width - 26, 34], fill=gold)
    
    # 字型設定
    font_serif = "C:/Windows/Fonts/NotoSerifTC-VF.ttf"
    font_sans = "C:/Windows/Fonts/msjhbd.ttc"
    
    def get_font(path, size):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()
            
    f_badge = get_font(font_sans, 22)
    f_title_main = get_font(font_serif, 66)
    f_title_sub = get_font(font_serif, 44)
    f_tag = get_font(font_sans, 22)
    f_footer = get_font(font_sans, 23)
    
    # 1. 頂部徽章 Tag
    badge_text = "【 三百年開基媽祖・台中萬春宮 】"
    badge_bg = (166, 40, 36, 230)
    draw.rounded_rectangle([60, 65, 450, 105], radius=20, fill=badge_bg, outline=gold, width=1)
    draw.text((76, 72), badge_text, font=f_badge, fill=(255, 246, 230, 255))
    
    # 2. 主標題：台中萬春宮
    draw.text((60, 130), "萬春宮・大墩行腳", font=f_title_main, fill=(255, 238, 205, 255))
    
    # 3. 副標題：實境尋寶走讀《藍興之謎》
    draw.text((60, 218), "實境解謎《藍興之謎》", font=f_title_sub, fill=(242, 192, 105, 255))
    
    # 描述小字
    f_desc = get_font(font_sans, 24)
    desc_lines = [
        "一封沒有署名的信，揭開三百年前大墩舊城傳奇",
        "跟隨開基媽祖指引，漫步舊城街廓解開時空之謎！"
    ]
    draw.text((60, 290), desc_lines[0], font=f_desc, fill=(235, 220, 205, 240))
    draw.text((60, 330), desc_lines[1], font=f_desc, fill=(215, 195, 180, 220))
    
    # 4. 特色標籤群
    tags = [
        ("◆ 免費體驗序章", (125, 30, 28)),
        ("◆ 90分鐘舊城走讀", (85, 45, 25)),
        ("◆ IG實境短影音熱播中", (145, 38, 68))
    ]
    
    curr_x = 60
    for t_text, t_col in tags:
        bbox = f_tag.getbbox(t_text)
        t_w = bbox[2] - bbox[0] + 32
        draw.rounded_rectangle([curr_x, 395, curr_x + t_w, 445], radius=10, fill=t_col, outline=gold, width=1)
        draw.text((curr_x + 16, 407), t_text, font=f_tag, fill=(255, 255, 255, 255))
        curr_x += t_w + 16
        
    # 5. 右側媽祖貼圖 - 做成雅緻宮廟圓形徽章
    badge_center = (940, 290)
    badge_radius = 185
    
    # 金色同心圓裝飾光環
    draw.ellipse(
        [badge_center[0] - badge_radius - 12, badge_center[1] - badge_radius - 12,
         badge_center[0] + badge_radius + 12, badge_center[1] + badge_radius + 12],
        outline=(218, 165, 78, 120),
        width=1
    )
    draw.ellipse(
        [badge_center[0] - badge_radius - 4, badge_center[1] - badge_radius - 4,
         badge_center[0] + badge_radius + 4, badge_center[1] + badge_radius + 4],
        outline=gold,
        width=3
    )
    
    # 讀取右側媽祖貼圖並以圓形裁切
    stickers_dir = r"D:\1_Need_SYNC\研究所\競賽\line_AI2026\web_page\assets\stickers"
    sticker_path = None
    for f in os.listdir(stickers_dir):
        if "03" in f:
            sticker_path = os.path.join(stickers_dir, f)
            break
            
    if sticker_path and os.path.exists(sticker_path):
        matsu_img = Image.open(sticker_path).convert("RGBA")
        
        # 建立圓形裁切遮罩
        diameter = badge_radius * 2
        matsu_square = matsu_img.resize((diameter, diameter), Image.Resampling.LANCZOS)
        
        mask = Image.new("L", (diameter, diameter), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([0, 0, diameter, diameter], fill=255)
        
        paste_x = badge_center[0] - badge_radius
        paste_y = badge_center[1] - badge_radius
        base.paste(matsu_square, (paste_x, paste_y), mask)
        draw = ImageDraw.Draw(base)
        
    # 6. 底部行動呼籲橫條 (Footer CTA Bar)
    footer_box = [60, 520, width - 60, 600]
    draw.rounded_rectangle(footer_box, radius=14, fill=(18, 10, 8, 240), outline=gold, width=2)
    
    cta_text = "【 點此觀看 IG 精彩實境短片 】  ｜  點擊 LINE 選單即刻免費啟程！"
    bbox_cta = f_footer.getbbox(cta_text)
    cta_w = bbox_cta[2] - bbox_cta[0]
    draw.text(((width - cta_w) // 2, 545), cta_text, font=f_footer, fill=(255, 235, 190, 255))
    
    # 輸出圖檔
    out_dir = r"D:\1_Need_SYNC\研究所\競賽\line_AI2026\web_page\assets"
    out_file = os.path.join(out_dir, "promo_wanchun_banner.png")
    final_rgb = base.convert("RGB")
    final_rgb.save(out_file, "PNG", quality=95)
    print(f"[OK] 成功生成萬春宮宣傳 Banner: {out_file}")

if __name__ == "__main__":
    create_banner()
