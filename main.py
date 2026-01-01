import os
import cv2
import numpy as np
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Konfigurasi Token dan Akses
TOKEN = os.getenv('BOT_TOKEN')
raw_users = os.getenv('ALLOWED_USERS', '')
ALLOWED_USERS = [int(i) for i in raw_users.split(',') if i]

# Definisi Urutan Pertanyaan (States)
WILAYAH, NAMA, HP, PAKET, SALES, TIKOR, NOTE, KTP = range(8)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Akses Ditolak!")
        return ConversationHandler.END
    
    await update.message.reply_text("Halo! Mari buat pendaftaran baru.\nMasukkan **Alamat/Wilayah** (Contoh: Kalianda):")
    return WILAYAH

async def get_wilayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['wilayah'] = update.message.text
    await update.message.reply_text("Masukkan **Nama Pelanggan**:")
    return NAMA

async def get_nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nama'] = update.message.text
    await update.message.reply_text("Masukkan **Nomor HP/WA**:")
    return HP

async def get_hp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['hp'] = update.message.text
    
    pilihan = [
        ['22 Mbps', '27 Mbps'], ['35 Mbps', '40 Mbps'],
        ['50 Mbps', '75 Mbps'], ['Corporate 15 Mbps', 'Corporate 20 Mbps'],
        ['Corporate 25 Mbps', 'Corporate 30 Mbps'], ['Corporate 50 Mbps', 'Corporate 60 Mbps']
    ]
    markup = ReplyKeyboardMarkup(pilihan, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text("Pilih **Paket Kecepatan**:", reply_markup=markup)
    return PAKET

async def get_paket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['paket'] = update.message.text
    await update.message.reply_text("Masukkan **Nama Sales**:", reply_markup=ReplyKeyboardRemove())
    return SALES

async def get_sales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sales'] = update.message.text
    await update.message.reply_text("Masukkan **Titik Koordinat (Tikor)**:")
    return TIKOR

async def get_tikor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['tikor'] = update.message.text
    await update.message.reply_text("Masukkan **Catatan (Note)**:")
    return NOTE

async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['note'] = update.message.text
    await update.message.reply_text("Terakhir, kirim **Foto KTP**:")
    return KTP

async def get_ktp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Mohon kirimkan gambar (foto) KTP.")
        return KTP

    photo_file = await update.message.photo[-1].get_file()
    in_p, out_p = "in.jpg", "out.jpg"
    await photo_file.download_to_drive(in_p)

    # --- PROSES CROP ---
    img = cv2.imread(in_p)
    if img is not None:
        original = img.copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.medianBlur(gray, 5)
        thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        cnts, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_cnts = [c for c in cnts if cv2.contourArea(c) > (img.shape[0] * img.shape[1] * 0.1)]
        
        if valid_cnts:
            best_cnt = max(valid_cnts, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(best_cnt)
            # Padding 5%
            y1, y2 = max(0, y-int(h*0.05)), min(img.shape[0], y+h+int(h*0.05))
            x1, x2 = max(0, x-int(w*0.05)), min(img.shape[1], x+w+int(w*0.05))
            cv2.imwrite(out_p, original[y1:y2, x1:x2])
            final_img = out_p
        else:
            final_img = in_p
    else:
        final_img = in_p

    # --- FORMAT LAPORAN (EMOJI TETAP + NAMA HURUF BESAR) ---
    nama_user = str(context.user_data.get('nama', '-')).upper()
    
    caption = (
        f"<b>DATA PSB SPEEDHOME</b>\n\n"
        f"🌍 : {context.user_data.get('wilayah', '-')}\n"
        f"👤 : <b>{nama_user}</b>\n"
        f"📱 : {context.user_data.get('hp', '-')}\n"
        f"📶 : <b>{context.user_data.get('paket', '-')}</b>\n"
        f"👷 : {context.user_data.get('sales', '-')}\n\n"
        f"📍 : {context.user_data.get('tikor', '-')}\n"
        f"📝 : {context.user_data.get('note', '-')}"
    )

    await update.message.reply_photo(
        photo=open(final_img, 'rb'), 
        caption=caption, 
        parse_mode='Markdown'
    )
    
    if os.path.exists(in_p): os.remove(in_p)
    if os.path.exists(out_p): os.remove(out_p)
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WILAYAH: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_wilayah)],
            NAMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nama)],
            HP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_hp)],
            PAKET: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_paket)],
            SALES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_sales)],
            TIKOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tikor)],
            NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_note)],
            KTP: [MessageHandler(filters.PHOTO, get_ktp)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    app.add_handler(conv)
    app.run_polling()

if __name__ == '__main__':
    main()
