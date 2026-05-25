import os
from flask import Flask, request, jsonify
import wikipediaapi
import requests

app = Flask(__name__)

# Инициализируем Википедию
wiki = wikipediaapi.Wikipedia('MyAIWebBot/1.0 (contact@example.com)', 'ru')

# Находим корень проекта, чтобы Vercel не терял HTML и CSS файлы
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route('/')
def home():
    html_path = os.path.join(BASE_DIR, 'index.html')
    with open(html_path, 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/style.css')
def css():
    css_path = os.path.join(BASE_DIR, 'style.css')
    with open(css_path, 'r', encoding='utf-8') as f:
        return f.read(), 200, {'Content-Type': 'text/css'}

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('question', '')
    web_search = data.get('web_search', False)
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}

    try:
        # Логика поиска в Вики
        if web_search:
            extract_prompt = f"Извлеки ключевое слово для поиска. Вопрос: {question}. Ответь ТОЛЬКО одним словом."
            payload = {"model": "llama3-8b-8192", "messages": [{"role": "user", "content": extract_prompt}]}
            
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
            
            # --- ВАЖНАЯ ПРОВЕРКА ---
            if res.status_code != 200:
                return jsonify({'error': f'Ошибка Groq (поиск): {res.text}'}), 500
            
            res_data = res.json()
            topic = res_data["choices"][0]["message"]["content"].strip().replace('"', '').replace('.', '')
            
            wiki = wikipediaapi.Wikipedia('MyAIWebBot/1.0', 'ru')
            page = wiki.page(topic)
            wiki_text = page.summary[0:2000] if page.exists() else "Инфо не найдено."
            prompt = f"Вики: {wiki_text}\nВопрос: {question}"
        else:
            prompt = question

        # Финальный запрос
        payload = {"model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}]}
        final_res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)

        # --- ВАЖНАЯ ПРОВЕРКА ---
        if final_res.status_code != 200:
            return jsonify({'error': f'Ошибка Groq (генерация): {final_res.text}'}), 500

        final_data = final_res.json()
        answer = final_data["choices"][0]["message"]["content"]
        return jsonify({'answer': answer})

    except Exception as e:
        return jsonify({'error': f'Критическая ошибка сервера: {str(e)}'}), 500
if __name__ == '__main__':
    app.run(debug=True, port=5000)