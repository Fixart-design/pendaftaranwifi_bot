import os
import cv2
import numpy as np
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Mengambil data rahasia dari setting server
TOKEN = os.getenv('BOT_TOKEN')
raw_users = os.getenv('ALLOWED_USERS', '')
ALLOWED_USERS = [int(i) for i in raw_users.split(',') if i]

NAMA, HP, PAKET, SALES, TIKOR, NOTE, KTP = range(7)

def is_authorized(user_id):
    return user_id in ALLOWED_USERS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("❌ Akses Ditolak! Anda bukan admin.")
        return ConversationHandler.END
    await update.message.reply_text("Halo! Siapa **Nama Pelanggan**?")
    return NAMA

async def get_nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nama'] = update.message.text
    await update.message.reply_text("Nomor HP/WhatsApp:")
    return HP

async def get_hp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['hp'] = update.message.text
    
    # Daftar pilihan paket sesuai permintaan Anda
    pilihan_paket = [
        ['22 Mbps', '27 Mbps'],
        ['35 Mbps', '40 Mbps'],
        ['50 Mbps', '75 Mbps'],
        ['Corporate 15 Mbps', 'Corporate 20 Mbps'],
        ['Corporate 25 Mbps', 'Corporate 30 Mbps'],
        ['Corporate 50 Mbps', 'Corporate 60 Mbps']
    ]
    
    markup = ReplyKeyboardMarkup(pilihan_paket, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "Silakan pilih **Paket Kecepatan (Mbps)**:",
        reply_markup=markup,
        parse_mode='Markdown'
    )
    return PAKET

async def get_paket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Menyimpan pilihan yang diklik user
    context.user_data['paket'] = update.message.text
    
    # Menghapus keyboard tombol dan lanjut ke pertanyaan Nama Sales
    await update.message.reply_text(
        f"✅ Paket **{update.message.text}** dipilih.\n\nMasukkan **Nama Sales**:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='Markdown'
    )
    return SALES

async def get_sales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sales'] = update.message.text
    await update.message.reply_text("Titik Koordinat (Tikor):")
    return TIKOR

async def get_tikor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['tikor'] = update.message.text
    await update.message.reply_text("Catatan (Note):")
    return NOTE

async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['note'] = update.message.text
    await update.message.reply_text("Kirim Foto KTP untuk di-crop:")
    return KTP

async def get_ktp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    in_p, out_p = "in.jpg", "out.jpg"
    await photo_file.download_to_drive(in_p)

    # Proses Crop Sederhana
    img = cv2.imread(in_p)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if cnts:
        c = max(cnts, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(c)
        cv2.imwrite(out_p, img[y:y+h, x:x+w])
        final_img = out_p
    else:
        final_img = in_p

    caption = (
        f"📄 **PASANG SAMBUNGAN BARU**\n\n🌍 : Kalianda\n👤 : {context.user_data['nama']}\n"
        f"📱 : {context.user_data['hp']}\n📶 : {context.user_data['paket']}\n"
        f"👷 : {context.user_data['sales']}\n📍 : {context.user_data['tikor']}\n📝 : {context.user_data['note']}"
    )

    await update.message.reply_photo(photo=open(final_img, 'rb'), caption=caption, parse_mode='Markdown')
    if os.path.exists(in_p): os.remove(in_p)
    if os.path.exists(out_p): os.remove(out_p)
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nama)],
            HP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_hp)],
            PAKET: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_paket)],
            SALES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_sales)],
            TIKOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tikor)],
            NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_note)],
            KTP: [MessageHandler(filters.PHOTO, get_ktp)],
        },
        fallbacks=[],
    )
    app.add_handler(conv)
    app.run_polling()

if __name__ == '__main__':
    main()
