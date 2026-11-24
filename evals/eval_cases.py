# Each case: the question, the expected intent, and (for docs questions)
# a phrase that must appear in one of the retrieved chunks.
CASES = [
    # --- docs questions ---
    {"question": "اگه جنس خراب رسید هزینه برگشتش با کیه؟", "intent": "docs", "keyword": "هزینه بازگشت کالا"},
    {"question": "چند روز وقت دارم کالا رو پس بدم؟", "intent": "docs", "keyword": "قوانین بازگشت کالا"},
    {"question": "کالای باز شده رو می‌تونم برگردونم؟", "intent": "docs", "keyword": "شرایط پذیرش بازگشت"},
    {"question": "پول کی به حسابم برمی‌گرده؟", "intent": "docs", "keyword": "زمان بازپرداخت وجه"},
    {"question": "ارسال به شهرستان چند روز طول می‌کشه؟", "intent": "docs", "keyword": "مدت تحویل"},
    {"question": "ارسال برای خرید گرون رایگانه؟", "intent": "docs", "keyword": "هزینه ارسال"},
    {"question": "کد رهگیری رو چطور می‌گیرم؟", "intent": "docs", "keyword": "پیگیری مرسوله"},
    # --- orders questions ---
    {"question": "وضعیت سفارش من با ایمیل ali@example.com چیه؟", "intent": "orders", "keyword": None},
    {"question": "سفارشم چی بود؟ ایمیلم sara@example.com هست", "intent": "orders", "keyword": None},
    # --- unrelated questions ---
    {"question": "بهترین گوشی برای عکاسی کدومه؟", "intent": "other", "keyword": None},
    {"question": "امروز هوا چطوره؟", "intent": "other", "keyword": None},
     # --- fresh questions (not used in the classifier prompt) ---
    {"question": "اگه کالا رو پس بدم، چقدر طول می‌کشه پولم برگرده؟", "intent": "docs", "keyword": "زمان بازپرداخت وجه"},
    {"question": "برای سفارش‌های کوچیک پست‌کرایه چنده؟", "intent": "docs", "keyword": "هزینه ارسال"},
    {"question": "جنسی که بسته‌بندیش پاره شده رو پس می‌گیرید؟", "intent": "docs", "keyword": "شرایط پذیرش بازگشت"},
    {"question": "ایمیلم ali@example.com ـه، چی خریده بودم؟", "intent": "orders", "keyword": None},
    {"question": "آیا شما موبایل سامسونگ دارید؟", "intent": "other", "keyword": None},
]