import os
import cv2
import numpy as np
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Konfigurasi Token dan Akses
TOKEN = os.getenv('BOT_TOKEN')
raw_users = os.getenv('ALLOWED_USERS', '')
ALLOWED_USERS = [int(i) for i in raw_users.split(',') if i]

# Definisi Urutan Pertanyaan (States)
WILAYAH, NAMA, HP, PAKET, SALES, TIKOR, NOTE, KTP = range(8)

# --- FUNGSI PEMBANTU ---
async def save_and_reply(update, context, text, reply_markup=None):
    if 'msg_to_delete' not in context.user_data:
        context.user_data['msg_to_delete'] = []
    if update.message:
        context.user_data['msg_to_delete'].append(update.message.message_id)
    sent_msg = await update.message.reply_text(text, reply_markup=reply_markup)
    context.user_data['msg_to_delete'].append(sent_msg.message_id)
    return sent_msg

# --- TAHAPAN CONVERSATION ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Akses Ditolak!")
        return ConversationHandler.END
    context.user_data['msg_to_delete'] = []
    context.user_data['force_no_crop'] = False
    await save_and_reply(update, context, "Halo! Mari buat pendaftaran baru.\nMasukkan *Alamat/Wilayah*:")
    return WILAYAH

async def get_wilayah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['wilayah'] = update.message.text
    await save_and_reply(update, context, "Masukkan *Nama Pelanggan*:")
    return NAMA

async def get_nama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['nama'] = update.message.text
    await save_and_reply(update, context, "Masukkan *Nomor HP/WA*:")
    return HP

async def get_hp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['hp'] = update.message.text
    pilihan = [['22 Mbps', '27 Mbps'], ['35 Mbps', '40 Mbps'], ['50 Mbps', '75 Mbps'], ['Corporate', 'Lainnya']]
    markup = ReplyKeyboardMarkup(pilihan, one_time_keyboard=True, resize_keyboard=True)
    await save_and_reply(update, context, "Pilih *Paket Kecepatan*:", reply_markup=markup)
    return PAKET

async def get_paket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['paket'] = update.message.text
    await save_and_reply(update, context, "Masukkan *Nama Sales*:", reply_markup=ReplyKeyboardRemove())
    return SALES

async def get_sales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sales'] = update.message.text
    await save_and_reply(update, context, "Masukkan *Titik Koordinat (Tikor)*:")
    return TIKOR

async def get_tikor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['tikor'] = update.message.text
    await save_and_reply(update, context, "Masukkan *Catatan (Note)*:")
    return NOTE

async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['note'] = update.message.text
    await save_and_reply(update, context, "Terakhir, kirim *Foto KTP*:")
    return KTP

async def get_ktp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Mohon kirimkan gambar (foto) KTP.")
        return KTP

    if 'msg_to_delete' in context.user_data:
        context.user_data['msg_to_delete'].append(update.message.message_id)

    photo_file = await update.message.photo[-1].get_file()
    in_p, out_p = "in.jpg", "out.jpg"
    await photo_file.download_to_drive(in_p)
    
    final_img = in_p

    # LOGIKA CROP (Hanya jika bukan upload ulang manual)
    if not context.user_data.get('force_no_crop', False):
        img = cv2.imread(in_p)
        if img is not None:
            # 1. Coba Biru
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            lower_blue = np.array([90, 50, 50])
            upper_blue = np.array([130, 255, 255])
            mask = cv2.inRange(hsv, lower_blue, upper_blue)
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            target = None
            if cnts:
                target = max(cnts, key=cv2.contourArea)
                if cv2.contourArea(target) < (img.shape[0] * img.shape[1] * 0.05): target = None
            
            # 2. Coba Kotak (Fotokopi)
            if target is None:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                edged = cv2.Canny(cv2.GaussianBlur(gray, (7,7), 0), 30, 150)
                dilated = cv2.dilate(edged, np.ones((5,5), np.uint8), iterations=1)
                cnts_box, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if cnts_box:
                    target = max(cnts_box, key=cv2.contourArea)

            if target is not None and cv2.contourArea(target) > (img.shape[0]*img.shape[1]*0.05):
                x, y, w, h = cv2.boundingRect(target)
                margin = 20
                y1, y2, x1, x2 = max(0,y-margin), min(img.shape[0],y+h+margin), max(0,x-margin), min(img.shape[1],x+w+margin)
                cv2.imwrite(out_p, img[y1:y2, x1:x2])
                final_img = out_p

    # FORMAT LAPORAN
    nama_user = str(context.user_data.get('nama', '-')).upper()
    caption = (
        f"*DATA PSB SPEEDHOME*\n\n"
        f"🌍 : {context.user_data.get('wilayah', '-')}\n"
        f"👤 : *{nama_user}*\n"
        f"📱 : {context.user_data.get('hp', '-')}\n"
        f"📶 : *{context.user_data.get('paket', '-')}*\n"
        f"👷 : {context.user_data.get('sales', '-')}\n\n"
        f"📍 : {context.user_data.get('tikor', '-')}\n"
        f"📝 : {context.user_data.get('note', '-')}"
    )

    # Bersihkan chat
    for msg_id in context.user_data.get('msg_to_delete', []):
        try: await context.bot.delete_message(update.effective_chat.id, msg_id)
        except: pass
    context.user_data['msg_to_delete'] = []

    # Kirim hasil + tombol upload ulang
    keyboard = [[InlineKeyboardButton("🔄 Upload Ulang (Manual)", callback_data='ulang_manual')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_photo(
        photo=open(final_img, 'rb'), 
        caption=caption, 
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    if os.path.exists(in_p): os.remove(in_p)
    if os.path.exists(out_p): os.remove(out_p)
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'ulang_manual':
        context.user_data['force_no_crop'] = True
        await query.message.delete()
        msg = await query.message.reply_text("Silakan kirimkan *Foto KTP editan manual* Anda.\n(Bot akan mengirimkannya apa adanya)")
        context.user_data['msg_to_delete'] = [msg.message_id]
        return KTP

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
            KTP: [
                MessageHandler(filters.PHOTO, get_ktp),
                CallbackQueryHandler(button_handler, pattern='^ulang_manual$')
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    app.add_handler(conv)
    app.run_polling()

if __name__ == '__main__':
    main()
