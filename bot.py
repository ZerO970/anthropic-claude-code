import json
import logging
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from db import init_db, upsert_candidate
from questions import QUESTIONS

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN", "")

NAME, NATIONALITY, EXPERIENCE, QUIZ = range(4)

EXPERIENCE_OPTIONS = [
    ["Нет опыта (0)", "Менее 1 года"],
    ["1–2 года", "3–5 лет"],
    ["5+ лет"],
]


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 👋 Я помогу тебе пройти отбор на позицию *бармена в Лондоне*.\n\n"
        "Это займёт около 5 минут: пара вопросов о тебе и небольшой тест.\n\n"
        "Как тебя зовут? (Имя и Фамилия)",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return NAME


async def get_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Отлично! Какая у тебя национальность / откуда ты?")
    return NATIONALITY


async def get_nationality(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["nationality"] = update.message.text.strip()
    await update.message.reply_text(
        "Сколько у тебя опыта работы за баром?",
        reply_markup=ReplyKeyboardMarkup(EXPERIENCE_OPTIONS, one_time_keyboard=True, resize_keyboard=True)
    )
    return EXPERIENCE


async def get_experience(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["experience"] = update.message.text.strip()
    ctx.user_data["q_index"] = 0
    ctx.user_data["answers"] = []

    await update.message.reply_text(
        f"Супер! Теперь тест — *{len(QUESTIONS)} вопросов* по барной теме.\n"
        "Отвечай просто буквой: *A*, *B*, *C* или *D*.\n\nПоехали! 🍹",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["A", "B"], ["C", "D"]], resize_keyboard=True)
    )
    await send_question(update, ctx)
    return QUIZ


async def send_question(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    idx = ctx.user_data["q_index"]
    q = QUESTIONS[idx]
    text = f"*Вопрос {idx + 1}/{len(QUESTIONS)}*\n\n{q['q']}\n\n" + "\n".join(q["opts"])
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_answer(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.strip().upper()
    if answer not in ("A", "B", "C", "D"):
        await update.message.reply_text("Пожалуйста, ответь только буквой: A, B, C или D.")
        return QUIZ

    idx = ctx.user_data["q_index"]
    q = QUESTIONS[idx]
    correct = answer == q["ans"]

    ctx.user_data["answers"].append({
        "q": q["q"],
        "your": answer,
        "correct": q["ans"],
        "is_correct": correct,
        "hint": q["hint"],
    })

    ctx.user_data["q_index"] += 1

    if ctx.user_data["q_index"] < len(QUESTIONS):
        await send_question(update, ctx)
        return QUIZ
    else:
        return await finish(update, ctx)


async def finish(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    answers = ctx.user_data["answers"]
    score = sum(1 for a in answers if a["is_correct"])
    total = len(QUESTIONS)
    ud = ctx.user_data

    upsert_candidate(
        tg_id=update.effective_user.id,
        name=ud["name"],
        nationality=ud["nationality"],
        experience=ud["experience"],
        score=score,
        total=total,
        answers_json=json.dumps(answers, ensure_ascii=False),
    )

    stars = "⭐" * score + "☆" * (total - score)
    await update.message.reply_text(
        f"✅ Готово, {ud['name']}!\n\n"
        f"Твой результат: *{score}/{total}*\n{stars}\n\n"
        "Мы свяжемся с тобой в ближайшее время. Удачи! 🍀",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Анкета отменена. Напиши /start чтобы начать заново.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    if not TOKEN:
        raise ValueError("Укажи BOT_TOKEN в переменной окружения или в bot.py")

    init_db()
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            NATIONALITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nationality)],
            EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_experience)],
            QUIZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    app.run_polling()


if __name__ == "__main__":
    main()
