import random
import asyncio
import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# File lưu trữ số dư vĩnh viễn
DATA_FILE = "balances.json"
game_history = []

# ID Admin của bạn
ADMIN_ID = 6861219347 

def load_balances():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return {int(k): v for k, v in json.load(f).items()}
        except Exception:
            return {}
    return {}

def save_balances():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(user_balances, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("Lỗi lưu file:", e)

user_balances = load_balances()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    if user_id not in user_balances:
        user_balances[user_id] = 500_000
        save_balances()

    welcome_text = (
        "🎲 *HỆ THỐNG TÀI XỈU VIP (CÓ LỆNH ALL-IN)* 🎲\n\n"
        "📥 *Điểm danh:* `/daily` (Nhận 400.000 xu)\n"
        "💰 *Xem số dư:* `/sodu`\n"
        "📊 *Xem soi cầu:* `/cau`\n"
        "👑 *Admin cấp tiền:* Reply tin nhắn người khác kèm `/congtien [tiền]`\n\n"
        "🎮 *Cú pháp cược:*\n"
        "• Cược số tiền: `/tai 50k`, `/xiu 12345`\n"
        "• 🔥 **Tất tay (All-in):** `/tai all` hoặc `/xiu all`\n"
        "*(Lưu trữ số dư vĩnh viễn không lo mất tiền)*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if user_id not in user_balances:
        user_balances[user_id] = 500_000

    user_balances[user_id] += 400_000
    save_balances()
    
    await update.message.reply_text(
        f"🎁 *{user_name}* đã điểm danh nhận `+400,000` xu!\n"
        f"💳 Số dư ví: `{user_balances[user_id]:,}` xu",
        parse_mode="Markdown"
    )

async def sodu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = user_balances.get(user_id, 500_000)
    user_balances[user_id] = balance
    save_balances()
    
    await update.message.reply_text(
        f"💳 Số dư tài khoản của bạn là: `{balance:,}` xu",
        parse_mode="Markdown"
    )

async def xem_cau(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not game_history:
        await update.message.reply_text("📊 Chưa có dữ liệu cầu gần đây.")
        return
    
    cau_str = " - ".join(game_history)
    await update.message.reply_text(
        f"📊 *BẢNG SOI CẦU (5 ván gần nhất):*\n`{cau_str}`",
        parse_mode="Markdown"
    )

async def cong_tien_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_user_id = update.effective_user.id
    
    if admin_user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không có quyền sử dụng lệnh này!")
        return

    if not context.args:
        await update.message.reply_text("❌ Vui lòng nhập số tiền! Ví dụ: `/congtien 1500000`")
        return

    raw_money = context.args[0].lower().replace(',', '')
    try:
        if 'k' in raw_money:
            so_tien = int(float(raw_money.replace('k', '')) * 1000)
        else:
            so_tien = int(float(raw_money))
    except ValueError:
        await update.message.reply_text("❌ Số tiền không hợp lệ!")
        return

    target_user_id = admin_user_id
    target_user_name = update.effective_user.first_name

    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        target_user_id = target_user.id
        target_user_name = target_user.first_name

    if target_user_id not in user_balances:
        user_balances[target_user_id] = 500_000

    user_balances[target_user_id] += so_tien
    save_balances()

    await update.message.reply_text(
        f"👑 *[ADMIN] Cấp tiền thành công!*\n"
        f"👤 Người nhận: *{target_user_name}*\n"
        f"💰 Cộng thêm: `+{so_tien:,}` xu\n"
        f"💳 Số dư ví mới: `{user_balances[target_user_id]:,}` xu",
        parse_mode="Markdown"
    )

async def dat_cuoc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = update.message.text.lstrip('/').split()[0].lower()
    if command not in ['tai', 'xiu']:
        return

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if user_id not in user_balances:
        user_balances[user_id] = 500_000

    current_balance = user_balances[user_id]

    if current_balance <= 0:
        await update.message.reply_text(
            f"❌ *{user_name}* đã hết sạch tiền và không thể chơi tiếp!\n"
            f"📥 Hãy gõ `/daily` để nhận xu hoặc nhờ Admin cấp thêm.",
            parse_mode="Markdown"
        )
        return

    if not context.args:
        await update.message.reply_text(f"❌ Vui lòng nhập số tiền hoặc 'all'! Ví dụ: `/{command} all` hoặc `/{command} 50k`", parse_mode="Markdown")
        return

    raw_money = context.args[0].lower().replace(',', '')
    
    # --- XỬ LÝ LỆNH ALL-IN (TẤT TAY) ---
    is_all_in = False
    if raw_money in ['all', 'allin', 'tattay']:
        so_tien = current_balance
        is_all_in = True
    else:
        try:
            if 'k' in raw_money:
                so_tien = int(float(raw_money.replace('k', '')) * 1000)
            else:
                so_tien = int(float(raw_money))
        except ValueError:
            await update.message.reply_text("❌ Cú pháp cược không hợp lệ! (Dùng ví dụ: `/tai 50k` hoặc `/tai all`)", parse_mode="Markdown")
            return

    if so_tien <= 0:
        await update.message.reply_text("❌ Số tiền cược phải lớn hơn 0!")
        return

    if current_balance < so_tien:
        await update.message.reply_text(
            f"❌ Số dư của bạn (`{current_balance:,}` xu) không đủ để cược `{so_tien:,}` xu!",
            parse_mode="Markdown"
        )
        return

    # Trừ tiền cược
    user_balances[user_id] -= so_tien
    save_balances()

    # Hiển thị thông báo nhận cược (Nếu All-in sẽ hiện biểu tượng TẤT TAY 🔥)
    all_in_text = " 🔥 *(TẤT TAY ALL-IN)*" if is_all_in else ""
    
    msg = await update.message.reply_text(
        f"⏳ *{user_name}* đã cược `{so_tien:,}` xu vào *{command.upper()}*{all_in_text}.\n"
        f"🎲 Đang chờ mở bát... *(Còn 10 giây)*",
        parse_mode="Markdown"
    )

    await asyncio.sleep(5)

    await msg.edit_text(
        f"⏳ *{user_name}* đã cược `{so_tien:,}` xu vào *{command.upper()}*{all_in_text}.\n"
        f"🔥 SẮP MỞ BÁT! *(Còn 5 giây)*",
        parse_mode="Markdown"
    )

    await asyncio.sleep(5)

    await msg.edit_text(
        f"🎲 *ĐANG BẮT ĐẦU LẮC XÍ NGẦU...* ⚄ ⚁ ⚃",
        parse_mode="Markdown"
    )
    await asyncio.sleep(1)

    # Lắc xí ngầu
    d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
    tong_diem = d1 + d2 + d3
    
    ket_qua = "tai" if tong_diem >= 11 else "xiu"
    ket_qua_text = "TÀI" if ket_qua == "tai" else "XỈU"

    game_history.append(ket_qua_text)
    if len(game_history) > 5:
        game_history.pop(0)

    thang_cuoc = (command == ket_qua)
    
    if thang_cuoc:
        tien_thuong = so_tien * 2
        user_balances[user_id] += tien_thuong
        thong_bao = f"🎉 Chúc mừng *{user_name}* đã *THẮNG* `+{tien_thuong:,}` xu!"
    else:
        thong_bao = f"😢 Chia buồn với *{user_name}* đã thua mất `-{so_tien:,}` xu."

    so_du_moi = user_balances[user_id]
    save_balances()

    response = (
        f"🎲 *KẾT QUẢ MỞ BÁT* 🎲\n"
        f"• Xí ngầu: `{d1} - {d2} - {d3}`\n"
        f"• Tổng điểm: *{tong_diem}* ➔ *{ket_qua_text}*\n\n"
        f"👉 Người chơi: *{user_name}* cược `{so_tien:,}` xu vào *{command.upper()}*{all_in_text}\n"
        f"{thong_bao}\n\n"
        f"💳 Số dư ví: `{so_du_moi:,}` xu"
    )
    
    await msg.edit_text(response, parse_mode="Markdown")

def main():
    TOKEN = "8636334701:AAFpINev7WwfjLfzaT0fjnaCjaZBouf_mhc"  # Thay Token bot thật của bạn ở đây
    
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("sodu", sodu))
    app.add_handler(CommandHandler("cau", xem_cau))
    app.add_handler(CommandHandler("congtien", cong_tien_admin))
    app.add_handler(CommandHandler("tai", dat_cuoc))
    app.add_handler(CommandHandler("xiu", dat_cuoc))

    print("🤖 Bot Tài Xỉu (All-in & Lưu dữ liệu) đang hoạt động...")
    app.run_polling()

if __name__ == "__main__":
    main()

